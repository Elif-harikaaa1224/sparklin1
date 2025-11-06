# Sparklin1 - Spark L2 Trading Bot

Telegram bot for trading meme tokens on Spark L2 Bitcoin network.

## Features

✅ **Multi-Wallet Management**
- Create unlimited Spark wallets
- Import wallets from mnemonic/private key
- Switch between wallets easily
- Secure encrypted storage

✅ **Real-Time Balance Tracking**
- Live BTC balance from UTXO.fun API
- USD value conversion
- Transaction history

✅ **Lightning Network Integration**
- Create Lightning invoices for deposits
- Fast withdrawals via Lightning
- Low fees (~0.1%)

✅ **Bitcoin L1 Deposits**
- Permanent deposit addresses
- Support for exchange withdrawals
- Automatic balance updates

✅ **Token Trading** (Flashnet AMM - Coming Soon)
- Buy/Sell meme tokens
- Real-time pool data
- Slippage protection
- Priority fee control

## Installation

### Prerequisites
- Python 3.9+
- Telegram Bot Token

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/sparklin1.git
cd sparklin1
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
Create a `.env` file:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Lightspark API (for Lightning Network)
LIGHTSPARK_CLIENT_ID=your_client_id
LIGHTSPARK_CLIENT_SECRET=your_client_secret

# Optional: UTXO Pool API
UTXO_POOL_API_ENABLED=true
UTXO_POOL_RATE_LIMIT=0
UTXO_POOL_CACHE_TTL=60
```

4. **Run the bot:**
```bash
python telegram_bot.py
```

## Project Structure

```
sparklin1/
├── telegram_bot.py              # Main bot entry point
├── spark_wallet.py              # Wallet management & balance
├── generate_spark_wallet.py     # Wallet generation (BIP39/BIP32)
├── spark_withdrawal.py          # Lightning withdrawals
├── withdrawal_handlers.py       # Deposit/withdrawal UI
├── buy_handlers.py              # Buy token handlers
├── buy_handlers_extended.py     # Extended buy features
├── sell_handlers.py             # Sell token handlers
├── flashnet_integration.py      # Flashnet AMM client
├── utxo_pool_api.py            # UTXO.fun API client
├── btc_price.py                # Bitcoin price service
├── token_info.py               # Token metadata
├── requirements.txt            # Python dependencies
└── docs/                       # Documentation
```

## Usage

### Create a Wallet
```
/start - Initialize bot and create first wallet
/create_wallet - Create additional wallets
```

### Manage Wallets
```
/my_wallets - View all wallets with balances
- Switch active wallet
- Delete wallets
- Refresh balances
```

### Deposit Funds
```
Main Menu → 💰 Deposit
- ⚡ Lightning Network (instant, low fees)
- 🏦 Bitcoin L1 (permanent address)
```

### Trading (Coming Soon)
```
Main Menu → 📈 Buy
Main Menu → 📉 Sell
```

## API Integrations

### UTXO.fun API
- **Balance**: `https://utxo.fun/api/sparkscan/v1/address/{address}?network=MAINNET`
- **Transactions**: `https://utxo.fun/api/sparkscan/v1/address/{address}/transactions`
- **Pools**: `https://utxo.fun/api/pools/{token_address}`

### Lightspark API
- Lightning Network payments
- Invoice creation
- Withdrawal processing

### Flashnet AMM (Status: HTTP 403)
- **Note**: Currently investigating API access
- See `FLASHNET_SUPPORT_EMAIL.md` for details

## Development

### Key Files Fixed in This Version

1. **spark_wallet.py**
   - ✅ Fixed balance API endpoint (now uses `/address/{wallet}?network=MAINNET`)
   - ✅ Correct parsing of `balance.btcSoftBalanceSats`
   - ✅ Added USD value display

2. **telegram_bot.py**
   - ✅ Added refresh handler for `/my_wallets`
   - ✅ Improved balance display formatting
   - ✅ Better error handling

3. **generate_spark_wallet.py**
   - ✅ Correct BIP32 derivation path: `m/8797555'/1'/0'`
   - ✅ Spark address format: `spark1...` (bech32m)
   - ✅ Protobuf encoding for addresses

### Testing

Test balance API:
```bash
python test_balance_api.py
```

Test wallet generation:
```bash
python generate_spark_wallet.py
```

## Known Issues

1. **Flashnet AMM**: HTTP 403 Forbidden
   - Investigating API access requirements
   - Contact: See `FLASHNET_SUPPORT_EMAIL.md`

2. **Rate Limiting**: UTXO.fun API
   - Implemented caching (60s TTL)
   - Configurable rate limits

## Security

⚠️ **IMPORTANT SECURITY NOTES:**

- **Never commit `.env` file** to Git
- **Never share your mnemonic phrases**
- **Never share private keys**
- Wallets are encrypted with master password
- Keep backups of mnemonic phrases offline

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [github.com/yourusername/sparklin1/issues]
- Telegram: @yourusername

## Roadmap

- [x] Multi-wallet support
- [x] Lightning Network deposits/withdrawals
- [x] Bitcoin L1 deposits
- [x] Real-time balance tracking
- [ ] Flashnet AMM trading integration
- [ ] Token portfolio tracking
- [ ] Price alerts
- [ ] Swap history
- [ ] Advanced trading features

---

**Built with ❤️ for the Spark L2 community**
