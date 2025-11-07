#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPARK Wallet Generator
Генерация self-custodial SPARK кошелька (L2-решение для Bitcoin от Lightspark)

Использует:
- BIP-39 для mnemonic фразы
- BIP-32 с custom derivation path m/8797555'/0'/0' (identity key)
- Bech32m encoding с HRP "spark" для mainnet / "sparkrt" для regtest
"""

import sys
import os
from typing import Tuple

# Устанавливаем UTF-8 кодировку для Windows консоли
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Для старых версий Python
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    from bip_utils import (
        Bip39SeedGenerator,
        Bip39MnemonicGenerator,
        Bip39WordsNum,
        Bip32Slip10Secp256k1,
    )
    from bech32m_encoder import encode_bech32m, convertbits  # For bech32m encoding
    from spark_protobuf import encode_spark_address_protobuf
except ImportError as e:
    print("ERROR: Установите библиотеки:", file=sys.stderr)
    print("  pip install bip-utils", file=sys.stderr)
    print(f"\nДетали ошибки: {e}", file=sys.stderr)
    sys.exit(1)


def generate_spark_wallet(network: str = "mainnet", account: int = 1) -> Tuple[str, str, str, str]:
    """
    Генерирует новый SPARK кошелёк используя официальный Spark SDK derivation path
    
    Args:
        network: "mainnet" или "regtest" (для тестирования)
        account: номер аккаунта (по умолчанию 1 для совместимости с UXTO wallet)
    
    Returns:
        Tuple[str, str, str, str]: (mnemonic, private_key_hex, public_key_hex, address)
    """
    try:
        # 1. Генерируем случайный 12-словный mnemonic (BIP-39, английский wordlist)
        mnemonic_generator = Bip39MnemonicGenerator()
        mnemonic = mnemonic_generator.FromWordsNumber(Bip39WordsNum.WORDS_NUM_12)
        
        # Конвертируем mnemonic в строку (если это объект)
        mnemonic_str = str(mnemonic) if mnemonic else ""
        
        # Валидация mnemonic
        if not mnemonic_str:
            raise ValueError("Не удалось сгенерировать mnemonic")
        
        # 2. Генерируем master seed из mnemonic (PBKDF2 с пустой passphrase по умолчанию)
        seed_bytes = Bip39SeedGenerator(mnemonic_str).Generate("")
        
        # 3. ВАЖНО: Используем CUSTOM derivation path, который использует Spark SDK
        # Derivation path для identity key: m/8797555'/{account}'/0'
        # Это НЕ стандартный BIP-84!
        
        # Создаем BIP-32 контекст из seed
        bip32_ctx = Bip32Slip10Secp256k1.FromSeed(seed_bytes)
        
        # Деривируем identity key по пути m/8797555'/0'/0'
        # 8797555 = 0x860E9B (hardened: 0x860E9B + 0x80000000)
        identity_path = f"m/8797555'/{account}'/0'"
        identity_ctx = bip32_ctx.DerivePath(identity_path)
        
        # 4. Получаем приватный ключ identity
        private_key_bytes = identity_ctx.PrivateKey().Raw().ToBytes()
        private_key_hex = private_key_bytes.hex()
        
        # 5. Получаем публичный ключ (compressed, 33 bytes)
        public_key_bytes = identity_ctx.PublicKey().RawCompressed().ToBytes()
        public_key_hex = public_key_bytes.hex()
        
        # 6. Генерируем Spark адрес используя bech32m (НЕ bech32!)
        # ВАЖНО: Spark адрес кодирует protobuf-структуру, а не просто публичный ключ
        # где HRP = "spark" для mainnet, "sparkrt" для regtest
        
        hrp = "spark" if network == "mainnet" else "sparkrt"
        
        # Кодируем публичный ключ в protobuf формат
        protobuf_payload = encode_spark_address_protobuf(public_key_bytes)
        
        # Конвертируем protobuf payload в 5-bit words для bech32m
        words = convertbits(protobuf_payload, 8, 5)
        
        # Кодируем в bech32m (без witness version, т.к. это не SegWit адрес)
        from bech32m_encoder import bech32_encode
        address = bech32_encode(hrp, words, 0x2bc830a3)  # 0x2bc830a3 = bech32m const
        
        if not address:
            raise ValueError("Не удалось закодировать адрес")
        
        return mnemonic_str, private_key_hex, public_key_hex, address
        
    except Exception as e:
        raise RuntimeError(f"Ошибка при генерации кошелька: {e}")


def derive_private_key_from_mnemonic(mnemonic_str: str, account: int = 1) -> str:
    """
    Извлекает приватный ключ из существующего mnemonic
    
    Args:
        mnemonic_str: BIP-39 mnemonic фраза
        account: номер аккаунта (по умолчанию 1)
    
    Returns:
        str: Приватный ключ в hex формате
    """
    try:
        # Генерируем seed из mnemonic
        seed_bytes = Bip39SeedGenerator(mnemonic_str).Generate("")
        
        # Создаем BIP-32 контекст
        bip32_ctx = Bip32Slip10Secp256k1.FromSeed(seed_bytes)
        
        # Деривируем по Spark пути
        identity_path = f"m/8797555'/{account}'/0'"
        identity_ctx = bip32_ctx.DerivePath(identity_path)
        
        # Получаем приватный ключ
        private_key_bytes = identity_ctx.PrivateKey().Raw().ToBytes()
        private_key_hex = private_key_bytes.hex()
        
        return private_key_hex
        
    except Exception as e:
        raise RuntimeError(f"Ошибка при извлечении приватного ключа: {e}")


def main():
    """Основная функция"""
    print("=" * 70)
    print("[SPARK] SPARK Wallet Generator")
    print("Генерация self-custodial SPARK кошелька (L2 Bitcoin от Lightspark)")
    print("=" * 70)
    print()
    
    try:
        # Генерируем кошелёк
        mnemonic, private_key_hex, public_key_hex, address = generate_spark_wallet()
        
        # Выводим результаты
        print("[OK] Кошелёк успешно сгенерирован!")
        print()
        print("-" * 70)
        print("[MNEMONIC] MNEMONIC PHRASE (12 слов):")
        print("-" * 70)
        print(f"Mnemonic: {mnemonic}")
        print()
        
        print("-" * 70)
        print("[PRIVATE KEY] ПРИВАТНЫЙ КЛЮЧ (hex, identity key):")
        print("-" * 70)
        print(f"Private Key (hex): {private_key_hex}")
        print()
        
        print("-" * 70)
        print("[PUBLIC KEY] ПУБЛИЧНЫЙ КЛЮЧ (hex, compressed, 33 bytes):")
        print("-" * 70)
        print(f"Public Key: {public_key_hex}")
        print()
        
        print("-" * 70)
        print("[ADDRESS] АДРЕС SPARK (bech32m, spark1...):")
        print("-" * 70)
        print(f"Address: {address}")
        print()
        print(f"[INFO] Derivation path: m/8797555'/1'/0' (совместимость с UXTO wallet)")
        print("[INFO] Для Spark CLI используйте: m/8797555'/0'/0'")
        print()
        
        print("=" * 70)
        print("[WARNING] ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:")
        print("=" * 70)
        print("Храни mnemonic и privkey в секрете! Это self-custody.")
        print("Тот, кто имеет доступ к этим данным, имеет полный контроль")
        print("над кошельком. Никогда не делитесь ими ни с кем!")
        print("=" * 70)
        
    except ValueError as e:
        print(f"❌ Ошибка валидации: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Ошибка выполнения: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
