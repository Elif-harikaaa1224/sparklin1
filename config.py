"""
Загрузчик конфигурации с поддержкой MOCK/REAL режимов
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Загружаем .env файл
load_dotenv()

# ============================================
# ГЛАВНЫЙ ФЛАГ - РЕЖИМ РАБОТЫ
# ============================================
USE_MOCK_MODE = os.getenv('USE_MOCK_MODE', 'true').lower() in ('true', '1', 'yes')

print(f"\n{'='*60}")
print(f"🎭 MODE: {'MOCK (Development)' if USE_MOCK_MODE else 'REAL (Production)'}")
print(f"{'='*60}\n")

# ============================================
# 🤖 Telegram Bot
# ============================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set in .env")

print(f"✅ Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")

# ============================================
# 📡 Flashnet Configuration
# ============================================
FLASHNET_ENABLED = os.getenv('FLASHNET_ENABLED', 'true').lower() in ('true', '1', 'yes')
FLASHNET_API_KEY = os.getenv('FLASHNET_API_KEY', '')
FLASHNET_API_URL = os.getenv('FLASHNET_API_URL', 'https://api.amm.flashnet.xyz')

if FLASHNET_ENABLED and not USE_MOCK_MODE and not FLASHNET_API_KEY:
    print("⚠️  FLASHNET enabled but no API key - will use MOCK mode")
    USE_MOCK_MODE = True

print(f"📡 Flashnet: {'✅ Enabled' if FLASHNET_ENABLED else '❌ Disabled'}")
if FLASHNET_ENABLED and not USE_MOCK_MODE:
    print(f"   API Key: {FLASHNET_API_KEY[:10]}...")
    print(f"   API URL: {FLASHNET_API_URL}")
elif FLASHNET_ENABLED and USE_MOCK_MODE:
    print(f"   Mode: 🎭 MOCK (Flashnet credentials will be ignored)")

# ============================================
# ⚡ Lightspark Configuration
# ============================================
LIGHTSPARK_ENABLED = os.getenv('LIGHTSPARK_ENABLED', 'true').lower() in ('true', '1', 'yes')
LIGHTSPARK_CLIENT_ID = os.getenv('LIGHTSPARK_CLIENT_ID', '')
LIGHTSPARK_CLIENT_SECRET = os.getenv('LIGHTSPARK_CLIENT_SECRET', '')
LS_OAUTH_URL = os.getenv('LS_OAUTH_URL', 'https://api.lightspark.com/oauth/token')
LS_GRAPHQL_URL = os.getenv('LS_GRAPHQL_URL', 'https://api.lightspark.com/graphql')
LIGHTSPARK_NODE_ID = os.getenv('LIGHTSPARK_NODE_ID', '')
LIGHTSPARK_NODE_PASSWORD = os.getenv('LIGHTSPARK_NODE_PASSWORD', '')

if LIGHTSPARK_ENABLED and not USE_MOCK_MODE and not LIGHTSPARK_CLIENT_ID:
    print("⚠️  LIGHTSPARK enabled but no credentials - will use MOCK mode")
    USE_MOCK_MODE = True

print(f"⚡ Lightspark: {'✅ Enabled' if LIGHTSPARK_ENABLED else '❌ Disabled'}")
if LIGHTSPARK_ENABLED and not USE_MOCK_MODE:
    print(f"   Client ID: {LIGHTSPARK_CLIENT_ID[:20]}...")
    if LIGHTSPARK_NODE_ID:
        print(f"   Node ID: {LIGHTSPARK_NODE_ID[:40]}...")

# ============================================
# 🔐 Security
# ============================================
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD', 'spark_wallet_default_pwd')

# ============================================
# 🌐 API Endpoints
# ============================================
UTXO_API_URL = os.getenv('UTXO_API_URL', 'https://api.utxo.fun')
BTC_PRICE_API_URL = os.getenv('BTC_PRICE_API_URL', 'https://api.coingecko.com')

# ============================================
# 📊 Logging & Debug
# ============================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if USE_MOCK_MODE else 'INFO')
DEBUG_API_REQUESTS = os.getenv('DEBUG_API_REQUESTS', 'true').lower() in ('true', '1', 'yes')

# ============================================
# 💾 Storage
# ============================================
WALLETS_DIR = os.getenv('WALLETS_DIR', './spark_wallets')
LOGS_DIR = os.getenv('LOGS_DIR', './logs')
TOKEN_CACHE_FILE = os.getenv('TOKEN_CACHE_FILE', './token_cache.json')

# Создаем папки если их нет
os.makedirs(WALLETS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

print(f"📊 Logging: {LOG_LEVEL}")
print(f"💾 Wallets dir: {WALLETS_DIR}")
print(f"\n{'='*60}\n")


# ============================================
# 🎭 РЕЖИМ ПЕРЕКЛЮЧЕНИЕ
# ============================================

def get_trading_mode() -> str:
    """Получить текущий режим торговли"""
    return 'MOCK' if USE_MOCK_MODE else 'REAL'


def is_mock_mode() -> bool:
    """Проверить включен ли MOCK режим"""
    return USE_MOCK_MODE


def is_real_mode() -> bool:
    """Проверить включен ли REAL режим"""
    return not USE_MOCK_MODE


def print_config_summary():
    """Вывести сводку конфигурации"""
    print(f"""
╔════════════════════════════════════════════════════════════╗
║           🎭 SPARK WALLET BOT - CONFIGURATION              ║
╚════════════════════════════════════════════════════════════╝

📱 TELEGRAM:
   Token: {TELEGRAM_BOT_TOKEN[:25]}...

🎭 MODE:
   {'✅ MOCK (Development)' if USE_MOCK_MODE else '❌ REAL (Production)'}

📡 INTEGRATIONS:
   Flashnet: {'✅ Enabled' if FLASHNET_ENABLED else '❌ Disabled'}
   Lightspark: {'✅ Enabled' if LIGHTSPARK_ENABLED else '❌ Disabled'}

🌐 APIs:
   UTXO: {UTXO_API_URL}
   BTC Price: {BTC_PRICE_API_URL}

💾 STORAGE:
   Wallets: {WALLETS_DIR}
   Logs: {LOGS_DIR}

📊 DEBUG:
   Level: {LOG_LEVEL}
   API Requests: {'✅ Enabled' if DEBUG_API_REQUESTS else '❌ Disabled'}

{'='*60}
    """)


# Вывести сводку при загрузке
print_config_summary()