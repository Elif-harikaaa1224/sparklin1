# config.py
import os
from dotenv import load_dotenv

load_dotenv()


# ---------- runtime flags ----------
USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "true").lower() in ("1", "true", "yes")
FLASH_ENABLED = os.getenv("FLASH_ENABLED", "true").lower() in ("1", "true", "yes")


# ---------- Flashnet ----------
FLASHNET_API_BASE = os.getenv(
    "FLASHNET_API_BASE",
    "https://api.amm.flashnet.xyz"
).strip()

FLASHNET_INTEGRATOR_PUBLIC_KEY = os.getenv(
    "FLASHNET_INTEGRATOR_PUBLIC_KEY",
    ""
).strip()

HTTP_TIMEOUT_SECS = float(os.getenv("HTTP_TIMEOUT_SECS", "15.0"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))

HTTP_USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "SparkWalletBot/1.0 (+flashnet-integration)"
).strip()


# ---------- Комиссии (BPS: 100 bps = 1.00%) ----------
# Наш фикс: всегда 1% интегратора (разрабы)
INTEGRATOR_DEV_FEE_BPS = int(os.getenv("INTEGRATOR_DEV_FEE_BPS", "100"))  # 1.00%

# Реф-уровни пользователя (добавляются сверху к нашим 1%):
REF_TIER1_BPS = int(os.getenv("REF_TIER1_BPS", "25"))   # 0.25%
REF_TIER2_BPS = int(os.getenv("REF_TIER2_BPS", "10"))   # 0.10%
REF_TIER3_BPS = int(os.getenv("REF_TIER3_BPS", "1"))    # 0.01%

# Торговля
DEFAULT_SLIPPAGE_PERCENT = float(os.getenv("DEFAULT_SLIPPAGE_PERCENT", "10.0"))
MAX_BUY_BTC = float(os.getenv("MAX_BUY_BTC", "1.0"))


# ---------- Хелперы ----------
def is_mock_mode() -> bool:
    return bool(USE_MOCK_MODE)

def get_trading_mode() -> str:
    return "MOCK" if is_mock_mode() else "REAL"

def print_boot_banner() -> None:
    mode = get_trading_mode()
    print("=" * 60)
    print(f"🎭 MODE: {mode}")
    print(f"📡 Flashnet enabled: {FLASH_ENABLED}")
    print(f"🌐 API: {FLASHNET_API_BASE}")
    if mode == "REAL":
        key_short = (
            FLASHNET_INTEGRATOR_PUBLIC_KEY[:8] + "..." + FLASHNET_INTEGRATOR_PUBLIC_KEY[-8:]
            if FLASHNET_INTEGRATOR_PUBLIC_KEY else "(not set)"
        )
        print(f"🔑 Integrator pubkey: {key_short}")
    else:
        print("🔑 Integrator pubkey: (ignored in MOCK)")
    print(f"💸 Fees -> dev: {INTEGRATOR_DEV_FEE_BPS/100:.2f}% | "
          f"ref tiers: {REF_TIER1_BPS/100:.2f}% / {REF_TIER2_BPS/100:.2f}% / {REF_TIER3_BPS/100:.2f}%")
    print("=" * 60)


__all__ = [
    "USE_MOCK_MODE", "FLASH_ENABLED",
    "FLASHNET_API_BASE", "FLASHNET_INTEGRATOR_PUBLIC_KEY",
    "HTTP_TIMEOUT_SECS", "HTTP_RETRIES", "HTTP_USER_AGENT",
    "INTEGRATOR_DEV_FEE_BPS", "REF_TIER1_BPS", "REF_TIER2_BPS", "REF_TIER3_BPS",
    "DEFAULT_SLIPPAGE_PERCENT", "MAX_BUY_BTC",
    "is_mock_mode", "get_trading_mode", "print_boot_banner",
]
