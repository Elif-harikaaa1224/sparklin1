
"""
SPARK Wallet Manager
Управление кошельками на SPARK L2 Bitcoin
- Создание новых кошельков
- Импорт существующих кошельков
- Получение приватных ключей
- Работа с адресами и балансом
"""

import json
import os
import sys
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import hmac
from pathlib import Path

try:
    from spark_sdk_client import SparkSDKClient  # локальный тонкий клиент к SPARK API
except Exception:
    SparkSDKClient = None  # опционально

try:
    from mnemonic import Mnemonic
    from ecdsa import SigningKey, NIST256p
    from Crypto.Hash import SHA256
    try:
        from bitcoinlib.mnemonic import Mnemonic as BitcoinMnemonic
    except ImportError:
        BitcoinMnemonic = None  # Опционально
except ImportError as e:
    import sys
    print("ERROR: Install dependencies: pip install mnemonic ecdsa pycryptodome", file=sys.stderr)
    raise


@dataclass
class WalletData:
    """Структура данных кошелька"""
    name: str
    address: str
    public_key: str
    private_key: str  # Зашифрован
    mnemonic: Optional[str]
    created_at: str
    network: str = "bitcoin"
    bitcoin_deposit_address: Optional[str] = None  # Постоянный Bitcoin адрес для депозитов
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SparkWalletManager:
    """Управление кошельками SPARK"""
    
    def __init__(self, storage_path: str = "./wallets"):
        """
        Инициализация менеджера кошельков
        
        Args:
            storage_path: Путь для хранения данных кошельков
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.wallets: Dict[str, WalletData] = {}
        self.master_password: Optional[str] = None
        self.active_wallet: Optional[str] = None  # Имя активного кошелька
        self._load_wallets()
        # Конфиг Lightspark API для интеграции
        self.spark_client_id: Optional[str] = os.getenv("LIGHTSPARK_CLIENT_ID")
        self.spark_client_secret: Optional[str] = os.getenv("LIGHTSPARK_CLIENT_SECRET")
        # Обратная совместимость со старыми переменными
        self.spark_endpoint: Optional[str] = os.getenv("SPARK_API_ENDPOINT")
        self.spark_api_key: Optional[str] = os.getenv("SPARK_API_KEY")
        self._spark_client: Optional[SparkSDKClient] = None
        
        if SparkSDKClient is not None:
            try:
                # Приоритет: Lightspark (client_id + client_secret)
                if self.spark_client_id and self.spark_client_secret:
                    self._spark_client = SparkSDKClient(
                        client_id=self.spark_client_id,
                        client_secret=self.spark_client_secret
                    )
                # Фоллбэк: простой API key
                elif self.spark_endpoint and self.spark_api_key:
                    self._spark_client = SparkSDKClient(
                        base_url=self.spark_endpoint,
                        api_key=self.spark_api_key
                    )
            except Exception:
                self._spark_client = None

    # ===== Адреса SPARK (btkn1...) =====
    def validate_spark_btkn_address(self, address: str) -> bool:
        """
        Базовая валидация адресов SPARK BTKN формата btkn1...
        Это не полноценная проверка checksum, а практичная предвалидация:
        - префикс btkn1
        - длина 20..120
        - алфавит bech32-подобный (без 1,b,i,o)
        """
        if not isinstance(address, str):
            return False
        address = address.strip().lower()
        if not address.startswith("btkn1"):
            return False
        if not (20 <= len(address) <= 120):
            return False
        allowed = set("023456789acdefghjklmnpqrstuvwxyz")
        payload = address[5:]
        return all(ch in allowed for ch in payload)

    def validate_spark_wallet_address(self, address: str) -> bool:
        """
        Валидация SPARK wallet address (sp1...)
        Это адрес кошелька для получения/отправки токенов и BTC на SPARK L2.
        ВАЖНО: Это НЕ token identifier (btkn1...), а адрес вашего кошелька!
        """
        if not isinstance(address, str):
            return False
        address = address.strip().lower()
        if not address.startswith("sp1"):
            return False
        if not (20 <= len(address) <= 120):
            return False
        allowed = set("023456789acdefghjklmnpqrstuvwxyz")
        payload = address[3:]
        return all(ch in allowed for ch in payload)
    
    def ensure_valid_btkn(self, address: str) -> None:
        """Исключение, если token identifier некорректен (btkn1... - для токенов, не кошельков)"""
        if not self.validate_spark_btkn_address(address):
            raise ValueError("Некорректный SPARK BTKN token identifier (ожидается формат btkn1...)")
    
    def ensure_valid_wallet_address(self, address: str) -> None:
        """Исключение, если wallet address некорректен (sp1... - для кошельков)"""
        if not self.validate_spark_wallet_address(address):
            raise ValueError("Некорректный SPARK wallet address (ожидается формат sp1...)")
    
    def set_master_password(self, password: str) -> None:
        """Установить мастер-пароль для шифрования приватных ключей"""
        self.master_password = password
    
    def _encrypt_private_key(self, private_key: str) -> str:
        """Простое шифрование приватного ключа"""
        if not self.master_password:
            raise ValueError("Установите мастер-пароль через set_master_password()")
        
        key = hashlib.pbkdf2_hmac('sha256', 
                                   self.master_password.encode(), 
                                   b'spark_salt', 
                                   100000)
        encrypted = hmac.new(key, private_key.encode(), hashlib.sha256).hexdigest()
        return encrypted
    
    def _decrypt_private_key(self, encrypted: str, private_key: str) -> bool:
        """Проверка приватного ключа"""
        try:
            computed = self._encrypt_private_key(private_key)
            return computed == encrypted
        except:
            return False
    
    def create_new_wallet(self, name: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Создать новый кошелек SPARK
        
        Args:
            name: Имя кошелька
            password: Пароль (если не установлен мастер-пароль)
        
        Returns:
            Словарь с данными кошелька включая mnemonic
        """
        if password:
            self.set_master_password(password)
        
        if not self.master_password:
            raise ValueError("Требуется установить пароль")
        
        # Используем новый метод генерации с правильным Spark SDK derivation path m/8797555'/1'/0'
        # (account=1 для совместимости с UXTO wallet)
        # и адресами формата spark1... с protobuf encoding
        try:
            from generate_spark_wallet import generate_spark_wallet
            mnemonic_phrase, private_key_hex, public_key_hex, address = generate_spark_wallet(account=1)
            
            # Теперь generate_spark_wallet возвращает сразу hex, а не WIF
            
        except ImportError:
            # Fallback на старый метод если новый не доступен
            # Генерируем BIP39 mnemonic (12 слов)
            mnemo = Mnemonic("english")
            mnemonic_phrase = mnemo.generate(strength=128)
            
            # Генерируем seed из mnemonic
            seed = mnemo.to_seed(mnemonic_phrase)
            
            # Генерируем приватный ключ из seed
            private_key_bytes = seed[:32]
            private_key_hex = private_key_bytes.hex()
            
            # Генерируем публичный ключ
            sk = SigningKey.from_string(private_key_bytes, curve=NIST256p, hashfunc=SHA256)
            vk = sk.get_verifying_key()
            public_key_hex = vk.to_string().hex()
            
            # Генерируем адрес SPARK кошелька (формат sp1...)
            address = self._generate_spark_address(public_key_hex)
        
        # Зашифровываем приватный ключ
        encrypted_pk = self._encrypt_private_key(private_key_hex)
        
        wallet_data = WalletData(
            name=name,
            address=address,
            public_key=public_key_hex,
            private_key=encrypted_pk,
            mnemonic=mnemonic_phrase,
            created_at=datetime.now().isoformat()
        )
        
        self.wallets[name] = wallet_data
        self._save_wallets()
        
        return {
            "status": "success",
            "name": name,
            "address": address,
            "public_key": public_key_hex,
            "private_key": private_key_hex,  # Добавляем приватный ключ (НЕ зашифрованный, для показа пользователю)
            "mnemonic": mnemonic_phrase,
            "⚠️ WARNING": "Сохраните mnemonic фразу в безопасном месте! Это единственный способ восстановить кошелек."
        }
    
    def import_wallet(self, name: str, mnemonic_phrase: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Импортировать существующий кошелек из mnemonic
        
        Args:
            name: Имя кошелька
            mnemonic_phrase: BIP39 mnemonic (12, 15, 18, 21 или 24 слова)
            password: Пароль для шифрования
        
        Returns:
            Словарь с данными импортированного кошелька
        """
        if password:
            self.set_master_password(password)
        
        if not self.master_password:
            raise ValueError("Требуется установить пароль")
        
        # Валидация mnemonic
        mnemo = Mnemonic("english")
        if not mnemo.check(mnemonic_phrase):
            raise ValueError("Неверная mnemonic фраза")
        
        # Используем тот же метод генерации адреса, что и для создания нового кошелька
        # с правильным Spark SDK derivation path m/8797555'/1'/0' и адресами формата spark1...
        # (account=1 для совместимости с UXTO wallet)
        try:
            from bip_utils import Bip39SeedGenerator, Bip32Slip10Secp256k1
            from bech32m_encoder import convertbits, bech32_encode
            from spark_protobuf import encode_spark_address_protobuf
            
            # Генерируем master seed из mnemonic (PBKDF2 с пустой passphrase)
            seed_bytes = Bip39SeedGenerator(mnemonic_phrase).Generate("")
            
            # Используем Spark SDK derivation path: m/8797555'/1'/0' (identity key, account=1 для UXTO)
            bip32_ctx = Bip32Slip10Secp256k1.FromSeed(seed_bytes)
            identity_ctx = bip32_ctx.DerivePath("m/8797555'/1'/0'")
            
            # Получаем приватный ключ identity
            private_key_bytes = identity_ctx.PrivateKey().Raw().ToBytes()
            private_key_hex = private_key_bytes.hex()
            
            # Получаем публичный ключ (compressed, 33 bytes)
            public_key_bytes = identity_ctx.PublicKey().RawCompressed().ToBytes()
            public_key_hex = public_key_bytes.hex()
            
            # Генерируем Spark адрес с protobuf encoding и bech32m
            protobuf_payload = encode_spark_address_protobuf(public_key_bytes)
            words = convertbits(protobuf_payload, 8, 5)
            address = bech32_encode("spark", words, 0x2bc830a3)  # bech32m const
            
        except ImportError:
            # Fallback на старый метод если новый не доступен
            # Генерируем seed
            seed = mnemo.to_seed(mnemonic_phrase)
            
            # Получаем приватный ключ
            private_key_bytes = seed[:32]
            private_key_hex = private_key_bytes.hex()
            
            # Генерируем публичный ключ
            sk = SigningKey.from_string(private_key_bytes, curve=NIST256p, hashfunc=SHA256)
            vk = sk.get_verifying_key()
            public_key_hex = vk.to_string().hex()
            
            # Генерируем адрес SPARK кошелька (формат sp1...)
            address = self._generate_spark_address(public_key_hex)
        
        # Зашифровываем приватный ключ
        encrypted_pk = self._encrypt_private_key(private_key_hex)
        
        wallet_data = WalletData(
            name=name,
            address=address,
            public_key=public_key_hex,
            private_key=encrypted_pk,
            mnemonic=mnemonic_phrase,
            created_at=datetime.now().isoformat()
        )
        
        self.wallets[name] = wallet_data
        self._save_wallets()
        
        return {
            "status": "success",
            "name": name,
            "address": address,
            "public_key": public_key_hex,
            "message": "Кошелек успешно импортирован"
        }
    
    def import_from_private_key(self, name: str, private_key_hex: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Импортировать кошелек из приватного ключа
        
        Args:
            name: Имя кошелька
            private_key_hex: Приватный ключ в hex формате
            password: Пароль для шифрования
        
        Returns:
            Словарь с данными кошелька
        """
        if password:
            self.set_master_password(password)
        
        if not self.master_password:
            raise ValueError("Требуется установить пароль")
        
        try:
            # Валидируем приватный ключ
            private_key_bytes = bytes.fromhex(private_key_hex)
            if len(private_key_bytes) != 32:
                raise ValueError("Приватный ключ должен быть 32 байта (64 символа hex)")
            
            # Генерируем публичный ключ
            sk = SigningKey.from_string(private_key_bytes, curve=NIST256p, hashfunc=SHA256)
            vk = sk.get_verifying_key()
            public_key_hex = vk.to_string().hex()
            
            # Генерируем адрес SPARK
            address = self._generate_spark_address(public_key_hex)
            
            # Зашифровываем приватный ключ
            encrypted_pk = self._encrypt_private_key(private_key_hex)
            
            wallet_data = WalletData(
                name=name,
                address=address,
                public_key=public_key_hex,
                private_key=encrypted_pk,
                mnemonic=None,
                created_at=datetime.now().isoformat()
            )
            
            self.wallets[name] = wallet_data
            self._save_wallets()
            
            return {
                "status": "success",
                "name": name,
                "address": address,
                "public_key": public_key_hex,
                "message": "Кошелек успешно импортирован из приватного ключа"
            }
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_wallet_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о кошельке (без приватного ключа)"""
        if name not in self.wallets:
            return None
        
        wallet = self.wallets[name]
        return {
            "name": wallet.name,
            "address": wallet.address,
            "public_key": wallet.public_key,
            "created_at": wallet.created_at,
            "has_mnemonic": wallet.mnemonic is not None
        }
    
    def get_private_key(self, name: str, private_key_hex: str) -> Optional[str]:
        """
        Получить приватный ключ (требуется верификация)
        
        Args:
            name: Имя кошелька
            private_key_hex: Приватный ключ для верификации
        
        Returns:
            Приватный ключ если верификация пройдена
        """
        if name not in self.wallets:
            return None
        
        wallet = self.wallets[name]
        
        # Проверяем, верный ли приватный ключ
        encrypted = self._encrypt_private_key(private_key_hex)
        if encrypted == wallet.private_key:
            return private_key_hex
        
        return None
    
    def get_mnemonic(self, name: str, private_key_hex: str) -> Optional[str]:
        """
        Получить mnemonic фразу (требуется верификация приватным ключом)
        
        Args:
            name: Имя кошелька
            private_key_hex: Приватный ключ для верификации
        
        Returns:
            Mnemonic если верификация пройдена
        """
        if name not in self.wallets:
            return None
        
        wallet = self.wallets[name]
        
        if not wallet.mnemonic:
            return None
        
        # Проверяем приватный ключ
        if self.get_private_key(name, private_key_hex):
            return wallet.mnemonic
        
        return None
    
    def set_active_wallet(self, wallet_name: str) -> bool:
        """
        Установить активный кошелек
        
        Args:
            wallet_name: Имя кошелька
            
        Returns:
            True если успешно, False если кошелек не найден
        """
        if wallet_name in self.wallets:
            self.active_wallet = wallet_name
            self._save_wallets()
            return True
        return False
    
    def get_active_wallet(self) -> Optional[Tuple[str, WalletData]]:
        """
        Получить активный кошелек
        
        Returns:
            Tuple (имя, WalletData) или None
        """
        if self.active_wallet and self.active_wallet in self.wallets:
            return (self.active_wallet, self.wallets[self.active_wallet])
        elif self.wallets:
            # Если активный не установлен, берем первый
            first_name = list(self.wallets.keys())[0]
            self.active_wallet = first_name
            self._save_wallets()
            return (first_name, self.wallets[first_name])
        return None
    
    def delete_wallet(self, wallet_name: str) -> bool:
        """
        Удалить кошелек
        
        Args:
            wallet_name: Имя кошелька для удаления
            
        Returns:
            True если успешно, False если кошелек не найден
        """
        if wallet_name not in self.wallets:
            return False
        
        # Удаляем кошелек
        del self.wallets[wallet_name]
        
        # Если удалили активный кошелек, устанавливаем новый активный
        if self.active_wallet == wallet_name:
            if self.wallets:
                # Берем первый доступный кошелек
                self.active_wallet = list(self.wallets.keys())[0]
            else:
                # Больше нет кошельков
                self.active_wallet = None
        
        # Сохраняем изменения
        self._save_wallets()
        return True
    
    def set_bitcoin_deposit_address(self, wallet_name: str, btc_address: str) -> bool:
        """
        Сохранить Bitcoin deposit address для кошелька
        
        Args:
            wallet_name: Имя кошелька
            btc_address: Bitcoin адрес для депозитов
            
        Returns:
            True если успешно
        """
        if wallet_name not in self.wallets:
            return False
        
        wallet_data = self.wallets[wallet_name]
        wallet_data.bitcoin_deposit_address = btc_address
        self._save_wallets()
        return True
    
    def get_bitcoin_deposit_address(self, wallet_name: str) -> Optional[str]:
        """
        Получить сохраненный Bitcoin deposit address
        
        Args:
            wallet_name: Имя кошелька
            
        Returns:
            Bitcoin адрес или None если не сохранен
        """
        if wallet_name not in self.wallets:
            return None
        
        wallet_data = self.wallets[wallet_name]
        return wallet_data.bitcoin_deposit_address
    
    def list_wallets(self) -> Dict[str, Dict[str, Any]]:
        """Получить список всех кошельков"""
        result = {}
        for name, wallet in self.wallets.items():
            result[name] = {
                "address": wallet.address,
                "public_key": wallet.public_key[:20] + "...",
                "created_at": wallet.created_at,
                "has_mnemonic": wallet.mnemonic is not None
            }
        return result
    
    def delete_wallet(self, name: str) -> bool:
        """Удалить кошелек"""
        if name in self.wallets:
            del self.wallets[name]
            self._save_wallets()
            return True
        return False
    
    def _generate_spark_address(self, public_key_hex: str) -> str:
        """
        Генерировать адрес SPARK кошелька формата sp1...
        
        ВАЖНО: Это SPARK wallet address (sp1...), а не token identifier (btkn1...)
        Token identifier (btkn1...) используется только для самих токенов, не для кошельков.
        """
        # Хешируем публичный ключ для создания адреса
        pk_hash = hashlib.sha256(bytes.fromhex(public_key_hex)).digest()
        pk_hash = hashlib.new('ripemd160', pk_hash).digest()
        
        # Кодируем в bech32-подобный формат SPARK
        # Используем префикс sp1 для wallet addresses (не btkn1!)
        from base64 import b32encode
        encoded = b32encode(pk_hash).decode().lower()
        # Префикс sp1 для SPARK wallet addresses (как в Xverse)
        address = f"sp1{encoded[:56]}"
        return address

    # ===== Нативная покупка через Spark SDK (без Flashnet) =====
    async def buy_meme_native(self, contract_address: str, amount_sats: int, wallet_name: str,
                             slippage: float = 10.0, priority_fee_sats: int = 10000) -> Dict[str, Any]:
        """
        Покупка мем-токена через нативный Spark SDK (без Flashnet AMM)
        
        ВАЖНО: Этот метод НЕ РЕАЛИЗОВАН. Требуется интеграция с Spark Node API.
        Выбросит ошибку чтобы вы могли увидеть что именно нужно исправить.
        
        Args:
            contract_address: Адрес токена (btkn1...)
            amount_sats: Сумма в satoshis
            wallet_name: Имя кошелька
            slippage: Процент проскальзывания (игнорируется в этом методе)
            priority_fee_sats: Дополнительная комиссия в satoshis
        
        Returns:
            dict с результатом покупки
        """
        self.ensure_valid_btkn(contract_address)
        if amount_sats <= 0:
            raise ValueError("Сумма должна быть больше нуля (в сатоши)")
        if wallet_name not in self.wallets:
            raise ValueError("Кошелек не найден")

        wallet_data = self.wallets.get(wallet_name)
        if not wallet_data:
            raise ValueError("Кошелек не найден")
        
        wallet_address = wallet_data.address
        
        # ❌ НЕ РЕАЛИЗОВАНО - Требуется интеграция с Spark Node
        raise NotImplementedError(
            "buy_meme_native() не реализован!\n\n"
            "Требуется:\n"
            "1. Подключение к Spark Node API\n"
            "2. Создание реальной транзакции покупки токена\n"
            "3. Broadcast транзакции в сеть\n\n"
            "Используйте Flashnet AMM вместо этого метода:\n"
            "- Восстановите flashnet_integration.py из бекапа\n"
            "- Или реализуйте подключение к Spark Node"
        )

    # ===== Реальная торговля через Flashnet AMM =====
    async def buy_meme(self, contract_address: str, amount_sats: int, wallet_name: str, 
                      slippage: float = 10.0, priority_fee_sats: int = 10000) -> Dict[str, Any]:
        """
        Покупка мем-токена через Flashnet AMM (NEW IMPLEMENTATION)
        
        Args:
            contract_address: Адрес токена (btkn1...)
            amount_sats: Сумма в satoshis
            wallet_name: Имя кошелька
            slippage: Процент проскальзывания (по умолчанию 10%)
            priority_fee_sats: Дополнительная комиссия в satoshis (не используется в Flashnet)
        
        Returns:
            dict с результатом покупки
        """
        # Валидация
        if amount_sats <= 0:
            raise ValueError("Сумма должна быть больше нуля (в сатоши)")
        if wallet_name not in self.wallets:
            raise ValueError("Кошелек не найден")
        if slippage < 0.1 or slippage > 50:
            raise ValueError("Slippage должен быть между 0.1% и 50%")

        # Получаем данные кошелька
        wallet_data = self.wallets.get(wallet_name)
        if not wallet_data:
            raise ValueError("Кошелек не найден")
        
        try:
            # Используем новую интеграцию Flashnet AMM
            from flashnet_integration import execute_buy
            
            print(f"[INFO] Buying token via Flashnet AMM (New Implementation)...")
            print(f"  Token: {contract_address[:20]}...")
            print(f"  Amount: {amount_sats} sats ({amount_sats / 100_000_000:.8f} BTC)")
            print(f"  Slippage: {slippage}%")
            
            # Выполняем покупку через новую интеграцию
            result = await execute_buy(
                wallet_manager=self,
                wallet_name=wallet_name,
                token_address=contract_address,
                amount_btc_sats=amount_sats,
                slippage_pct=slippage
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Buy failed: {error_msg}")
            
            # Пробрасываем понятные ошибки
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                raise Exception(f"Flashnet API недоступен. Проверьте подключение.")
            if "pool not found" in error_msg.lower():
                raise Exception(f"Пул для токена не найден. Токен может не торговаться на Flashnet.")
            raise Exception(f"Ошибка при покупке: {error_msg}")

    async def get_wallet_balance(self, wallet_address: str) -> Dict[str, Any]:
        """
        Получить баланс кошелька SPARK через utxo.fun API (REAL-TIME из транзакций!)
        
        Args:
            wallet_address: SPARK адрес кошелька (spark1...)
        
        Returns:
            Словарь с балансом в сатоши и токенах
        """
        # ИСПОЛЬЗУЕМ REAL-TIME API - вычисляем баланс из транзакций!
        try:
            import httpx
            import time
            
            timestamp = int(time.time())
            
            # Получаем транзакции (это real-time, без кеша!)
            tx_api_url = f"https://utxo.fun/api/sparkscan/v1/address/{wallet_address}/transactions?network=MAINNET&limit=100&_t={timestamp}"
            
            print(f"[INFO] Getting real-time balance from transactions for {wallet_address[:40]}...", file=sys.stderr)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Cache-Control': 'no-cache',
            }
            
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                resp = await client.get(tx_api_url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    transactions = data.get('data', [])
                    
                    # Вычисляем баланс из транзакций
                    balance_sats = 0
                    
                    for tx in transactions:
                        direction = tx.get('direction')
                        amount = tx.get('amountSats', 0)
                        status = tx.get('status')
                        
                        # Считаем только confirmed и sent транзакции
                        if status in ['confirmed', 'sent']:
                            if direction == 'incoming':
                                balance_sats += amount
                            elif direction == 'outgoing':
                                balance_sats -= amount
                    
                    balance_btc = f"{balance_sats / 100_000_000:.8f}"
                    
                    print(f"[INFO] Real-time balance: {balance_sats} sats (from {len(transactions)} transactions)", file=sys.stderr)
                    
                    return {
                        "balance_sats": balance_sats,
                        "balance_btc": balance_btc,
                        "tokens": {},
                        "status": "success",
                        "tx_count": len(transactions)
                    }
                
                elif resp.status_code == 429:
                    print(f"[WARN] Rate limit from utxo.fun API", file=sys.stderr)
                    return {
                        "balance_sats": 0,
                        "balance_btc": "0.00000000",
                        "tokens": {},
                        "status": "rate_limit",
                        "error": "Too many requests - try again in a moment"
                    }
                else:
                    print(f"[ERROR] API returned status {resp.status_code}", file=sys.stderr)
                    return {
                        "balance_sats": 0,
                        "balance_btc": "0.00000000",
                        "tokens": {},
                        "status": "api_error",
                        "error": f"HTTP {resp.status_code}"
                    }
                    
        except Exception as e:
            print(f"[ERROR] Failed to get balance from API: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return {
                "balance_sats": 0,
                "balance_btc": "0.00000000",
                "tokens": {},
                "status": "error",
                "error": str(e)
            }
    
    async def get_balance_by_wallet_name(self, wallet_name: str) -> Dict[str, Any]:
        """
        Получить баланс кошелька по имени
        
        Args:
            wallet_name: Имя кошелька
        
        Returns:
            Словарь с балансом в сатоши и токенах
        """
        if wallet_name not in self.wallets:
            return {
                "balance_sats": 0,
                "balance_btc": "0.00000000",
                "tokens": {},
                "status": "wallet_not_found"
            }
        
        wallet_data = self.wallets[wallet_name]
        return await self.get_wallet_balance(wallet_data.address)
    
    async def sell_meme(self, contract_address: str, amount_tokens: int, wallet_name: str,
                       slippage: float = 10.0, priority_fee_sats: int = 10000) -> Dict[str, Any]:
        """
        Продажа мем-токена через Flashnet AMM (NEW IMPLEMENTATION)
        
        Args:
            contract_address: Адрес токена (hex формат)
            amount_tokens: Количество токенов для продажи
            wallet_name: Имя кошелька
            slippage: Процент проскальзывания (по умолчанию 10%)
            priority_fee_sats: Дополнительная комиссия в satoshis (не используется в Flashnet)
        
        Returns:
            dict с результатом продажи
        """
        # Валидация
        if amount_tokens <= 0:
            raise ValueError("Количество токенов должно быть больше нуля")
        if wallet_name not in self.wallets:
            raise ValueError("Кошелек не найден")
        if slippage < 0.1 or slippage > 50:
            raise ValueError("Slippage должен быть между 0.1% и 50%")

        # Получаем данные кошелька
        wallet_data = self.wallets.get(wallet_name)
        if not wallet_data:
            raise ValueError("Кошелек не найден")
        
        try:
            # Используем новую интеграцию Flashnet AMM
            from flashnet_integration import execute_sell
            
            print(f"[INFO] Selling token via Flashnet AMM (New Implementation)...")
            print(f"  Token: {contract_address[:20]}...")
            print(f"  Amount: {amount_tokens} tokens")
            print(f"  Slippage: {slippage}%")
            
            # Выполняем продажу через новую интеграцию
            result = await execute_sell(
                wallet_manager=self,
                wallet_name=wallet_name,
                token_address=contract_address,
                amount_tokens=amount_tokens,
                slippage_pct=slippage
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Sell failed: {error_msg}")
            
            # Пробрасываем понятные ошибки
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                raise Exception(f"Flashnet API недоступен. Проверьте подключение.")
            if "pool not found" in error_msg.lower():
                raise Exception(f"Пул для токена не найден. Токен может не торговаться на Flashnet.")
            raise Exception(f"Ошибка при продаже: {error_msg}")
    
    def _save_wallets(self) -> None:
        """Сохранить кошельки в файл"""
        wallets_dict = {}
        for name, wallet in self.wallets.items():
            wallets_dict[name] = wallet.to_dict()
        
        # Сохраняем активный кошелек
        if self.active_wallet:
            wallets_dict['_active_wallet'] = self.active_wallet
        
        filepath = self.storage_path / "wallets.json"
        with open(filepath, 'w') as f:
            json.dump(wallets_dict, f, indent=2)
    
    def _load_wallets(self) -> None:
        """Загрузить кошельки из файла"""
        filepath = self.storage_path / "wallets.json"
        if filepath.exists():
            with open(filepath, 'r') as f:
                wallets_dict = json.load(f)
            
            # Загружаем активный кошелек если есть
            if '_active_wallet' in wallets_dict:
                self.active_wallet = wallets_dict['_active_wallet']
                del wallets_dict['_active_wallet']
            
            for name, data in wallets_dict.items():
                self.wallets[name] = WalletData(**data)
            
            # Если активный кошелек не установлен, берем первый
            if not self.active_wallet and self.wallets:
                self.active_wallet = list(self.wallets.keys())[0]


# ============= ПРИМЕР ИСПОЛЬЗОВАНИЯ =============

if __name__ == "__main__":
    print("🔐 SPARK Wallet Manager Demo\n")
    
    # Инициализируем менеджер
    wallet_manager = SparkWalletManager()
    wallet_manager.set_master_password("my_secure_password_123")
    
    # 1. СОЗДАНИЕ НОВОГО КОШЕЛЬКА
    print("=" * 60)
    print("1️⃣  СОЗДАНИЕ НОВОГО КОШЕЛЬКА")
    print("=" * 60)
    
    result = wallet_manager.create_new_wallet("my_first_wallet")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Сохраняем mnemonic для последующих примеров
    mnemonic_phrase = result["mnemonic"]
    
    print("\n")
    
    # 2. ПОЛУЧЕНИЕ ИНФОРМАЦИИ О КОШЕЛЬКЕ
    print("=" * 60)
    print("2️⃣  ИНФОРМАЦИЯ О КОШЕЛЬКЕ")
    print("=" * 60)
    
    wallet_info = wallet_manager.get_wallet_info("my_first_wallet")
    print(json.dumps(wallet_info, indent=2, ensure_ascii=False))
    
    print("\n")
    
    # 3. СПИСОК ВСЕХ КОШЕЛЬКОВ
    print("=" * 60)
    print("3️⃣  СПИСОК КОШЕЛЬКОВ")
    print("=" * 60)
    
    wallets_list = wallet_manager.list_wallets()
    print(json.dumps(wallets_list, indent=2, ensure_ascii=False))
    
    print("\n")
    
    # 4. ИМПОРТ КОШЕЛЬКА ИЗ MNEMONIC
    print("=" * 60)
    print("4️⃣  ИМПОРТ КОШЕЛЬКА ИЗ MNEMONIC")
    print("=" * 60)
    
    import_result = wallet_manager.import_wallet("imported_wallet", mnemonic_phrase)
    print(json.dumps(import_result, indent=2, ensure_ascii=False))
    
    print("\n")
    
    # 5. ПОЛУЧЕНИЕ ПРИВАТНОГО КЛЮЧА
    print("=" * 60)
    print("5️⃣  ПОЛУЧЕНИЕ ПРИВАТНОГО КЛЮЧА")
    print("=" * 60)
    
    # Сначала создаём второй кошелек и получаем его приватный ключ
    second_wallet = wallet_manager.create_new_wallet("test_wallet")
    second_mnemonic = second_wallet["mnemonic"]
    
    # Импортируем его снова, чтобы получить приватный ключ
    wallet_manager.import_wallet("test_wallet_2", second_mnemonic)
    
    # В реальном приложении приватный ключ требует верификации
    print("ℹ️  Приватный ключ защищен и требует верификации")
    print("В боте это будет требовать подтверждение от пользователя")
    
    print("\n")
    
    # 6. СПИСОК ВСЕХ КОШЕЛЬКОВ (ФИНАЛЬНО)
    print("=" * 60)
    print("6️⃣  ФИНАЛЬНЫЙ СПИСОК КОШЕЛЬКОВ")
    print("=" * 60)
    
    final_wallets = wallet_manager.list_wallets()
    print(json.dumps(final_wallets, indent=2, ensure_ascii=False))
    
    print("\n✅ Все примеры выполнены успешно!")