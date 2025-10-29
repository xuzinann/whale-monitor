# 🐋 Whale Monitor

A Python-based cryptocurrency whale monitoring system that tracks the top 100 wallet holders for Bitcoin, Dogecoin, and Litecoin, analyzes their transactions, and sends daily digest notifications to Discord.

## Features

- **Multi-Chain Support**: Monitors BTC, DOGE, and LTC wallets
- **Exchange Detection**: Identifies transactions involving major exchanges (Binance, Coinbase, Kraken, etc.)
- **Significance Analysis**:
  - Large transaction detection (customizable thresholds)
  - Exchange flow tracking (inflow/outflow)
  - Unusual activity patterns
  - Accumulation/distribution detection
- **Daily Digests**: Automated Discord notifications with formatted summaries
- **Data Retention**: 30-day transaction history + permanent monthly summaries
- **Rate-Limit Friendly**: Respects API limits with built-in throttling

## Project Structure

```
whale-monitor/
├── data/
│   ├── top_100_bitcoin_wallets.txt      # BTC whale addresses
│   ├── top_100_dogecoin_wallets.txt     # DOGE whale addresses
│   ├── top_100_litecoin_wallets.txt     # LTC whale addresses
│   ├── exchange_addresses.json          # Known exchange addresses
│   └── whale_monitor.db                 # SQLite database (auto-created)
├── src/
│   ├── wallet_parser.py                 # Parse wallet address files
│   ├── blockchain_api.py                # BlockCypher & CoinGecko API clients
│   ├── database.py                      # SQLite database operations
│   ├── exchange_db.py                   # Exchange address management
│   ├── monitor.py                       # Core monitoring logic
│   ├── analyzer.py                      # Transaction significance analysis
│   ├── notifier.py                      # Discord webhook notifications
│   └── config.py                        # Configuration management
├── main.py                              # Main application entry point
├── requirements.txt                     # Python dependencies
├── .env.example                         # Example configuration
└── README.md                            # This file
```

## Installation

### Prerequisites

- Python 3.10 or higher
- Discord server with webhook access
- (Optional) BlockCypher API key for higher rate limits

### Setup Steps

1. **Clone/download this repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Create Discord Webhook**:
   - Go to your Discord server settings
   - Navigate to Integrations → Webhooks
   - Create a new webhook for your desired channel
   - Copy the webhook URL

4. **Configure environment**:
```bash
cp .env.example .env
```

Edit `.env` and set your configuration:
```env
# Required
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL

# Optional - Schedule
NOTIFICATION_TIME=20:00
NOTIFICATION_TIMEZONE=America/New_York

# Optional - API Keys (for higher rate limits)
BLOCKCYPHER_API_KEY=

# Optional - Thresholds
BTC_LARGE_TX_THRESHOLD=50
DOGE_LARGE_TX_THRESHOLD=10000000
LTC_LARGE_TX_THRESHOLD=5000

# Optional - Monitoring
POLL_INTERVAL_MINUTES=10
```

5. **Test the setup**:
```bash
python main.py --mode once
```

This will run a single check of all wallets and verify your configuration.

## Usage

### Run Modes

**Continuous Monitoring** (recommended for production):
```bash
python main.py --mode continuous
```
- Checks wallets every 10 minutes (configurable)
- Sends daily digest at configured time
- Runs indefinitely until stopped (Ctrl+C)

**Single Check** (for testing):
```bash
python main.py --mode once
```
- Runs one wallet check cycle
- Exits after completion
- Useful for testing and debugging

**Send Digest Now** (for testing notifications):
```bash
python main.py --mode digest
```
- Generates and sends digest immediately
- Uses last 24 hours of data
- Useful for testing Discord notifications

### Custom Configuration File

```bash
python main.py --mode continuous --config /path/to/custom.env
```

## Configuration Options

### Transaction Thresholds

Adjust what counts as a "large" transaction:

- **BTC_LARGE_TX_THRESHOLD**: Default 50 BTC (~$3M+)
- **DOGE_LARGE_TX_THRESHOLD**: Default 10,000,000 DOGE (~$1M+)
- **LTC_LARGE_TX_THRESHOLD**: Default 5,000 LTC (~$500K+)

### Monitoring Frequency

- **POLL_INTERVAL_MINUTES**: Default 23 minutes (optimized for free tier)
  - **Free tier (no API key)**: 23 minutes minimum
    - 75 wallets × (60/23) = 195 requests/hour (under 200 limit)
  - **With API key (500 req/hour)**: 9 minutes possible
    - 75 wallets × (60/9) = 500 requests/hour (at limit)
  - **More wallets?** Use formula: `Interval ≥ (Wallets × 60) / Rate_Limit`

### Daily Digest Schedule

- **NOTIFICATION_TIME**: Time to send daily digest (HH:MM format)
- **NOTIFICATION_TIMEZONE**: Timezone for notifications
  - Examples: `America/New_York`, `Europe/London`, `Asia/Tokyo`

## Discord Notification Format

### Daily Digest Example

```
🐋 DAILY WHALE DIGEST - 2025-10-28
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔷 BTC Whales
━━━━━━━━━━━━━━━━━━━━
🚨 7 significant moves | $142.0M total volume
📊 Exchange flow: 650.00 BTC net inflow
⚡ Most active: Whale #12 (8 transactions)

🟡 DOGE Whales
━━━━━━━━━━━━━━━━━━━━
🚨 12 significant moves | $8.5M total volume
📊 Exchange flow: 150M DOGE net inflow
⚡ Most active: Whale #3 (15 transactions)

⚪ LTC Whales
━━━━━━━━━━━━━━━━━━━━
🚨 3 significant moves | $1.5M total volume
📊 Exchange flow: 5.0K LTC net outflow
⚡ Most active: Whale #5 (4 transactions)
```

## Deployment

### Option 1: Railway.app (Recommended)

1. Create account at [railway.app](https://railway.app)

2. Create new project from GitHub repo

3. Add environment variables in Railway dashboard

4. Deploy! Railway will:
   - Auto-detect Python
   - Install dependencies
   - Run `main.py` continuously

**Cost**: ~$5/month for always-on service

### Option 2: DigitalOcean Droplet

1. Create a $6/month droplet (Ubuntu 22.04)

2. SSH into droplet and setup:
```bash
git clone <your-repo>
cd whale-monitor
pip install -r requirements.txt

# Create .env file with your settings
nano .env
```

3. Run with systemd for auto-restart:
```bash
sudo nano /etc/systemd/system/whale-monitor.service
```

```ini
[Unit]
Description=Whale Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/whale-monitor
ExecStart=/usr/bin/python3 /path/to/whale-monitor/main.py --mode continuous
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable whale-monitor
sudo systemctl start whale-monitor
sudo systemctl status whale-monitor
```

### Option 3: Render.com

1. Create account at [render.com](https://render.com)

2. Create new "Background Worker"

3. Connect GitHub repo

4. Set environment variables

5. Set start command: `python main.py --mode continuous`

**Cost**: Free tier available, $7/month for always-on

### Option 4: Local / Home Server

Run in a `screen` or `tmux` session:

```bash
screen -S whale-monitor
python main.py --mode continuous
# Press Ctrl+A, then D to detach
```

Reattach later:
```bash
screen -r whale-monitor
```

## Updating Wallet Lists

The whale wallet lists can change over time. To update:

1. **Scrape new data** from bitinfocharts.com or similar sources

2. **Update txt files** in `data/` directory:
   - `top_100_bitcoin_wallets.txt`
   - `top_100_dogecoin_wallets.txt`
   - `top_100_litecoin_wallets.txt`

3. **Restart the monitor** to load new addresses

The system will automatically start tracking the new wallets.

## Exchange Address Database

Located in `data/exchange_addresses.json`. Currently includes:

- **Bitcoin**: Binance, Bitfinex, Crypto.com, OKEx, Coincheck
- **Dogecoin**: Robinhood, Binance, Upbit, Kraken, Gate.io, Gemini, Bybit, Crypto.com, and more
- **Litecoin**: Limited data (expandable)

To add new exchange addresses, edit the JSON file and restart.

## Troubleshooting

### "Rate limit exceeded" errors

- Increase `POLL_INTERVAL_MINUTES` to 15 or 20
- Get a free BlockCypher API key for higher limits
- Consider monitoring fewer wallets

### No transactions detected

- System starts fresh - it will only detect NEW transactions after it starts
- First run builds baseline for each wallet
- Give it 24-48 hours to collect meaningful data

### Discord notifications not working

- Verify webhook URL is correct
- Check webhook hasn't been deleted in Discord
- Test with: `python main.py --mode digest`

### Database errors

- Delete `data/whale_monitor.db` to reset (will lose history)
- Check disk space is available
- Ensure write permissions to `data/` directory

## API Rate Limits

### BlockCypher (Free Tier)
- 3 requests/second
- **200 requests/hour** (critical limit)
- ~4,800 requests/day

### Current Optimized Setup
- **75 wallets** (25 per coin)
- **23-minute intervals** = 2.6 checks/hour
- **195 requests/hour** (safely under 200 limit)
- ~4,680 requests/day

### Scaling Options

**Want to monitor more wallets?**
- Get free BlockCypher API key → 500 req/hour
- With API key: Can monitor 150 wallets at 18-minute intervals
- Or: 75 wallets at 9-minute intervals (more frequent)

**Formula**: `Min Interval = (Wallets × 60) / Rate_Limit`

## Data Privacy & Security

- **No private keys**: Only public wallet addresses are monitored
- **Read-only**: System cannot initiate any blockchain transactions
- **Local database**: All data stored locally in SQLite
- **Webhook security**: Keep your Discord webhook URL private

## Contributing

To expand this project:

1. **Add more exchanges**: Update `data/exchange_addresses.json`
2. **Add more coins**: Extend `blockchain_api.py` and add wallet lists
3. **Enhanced analysis**: Modify `analyzer.py` for new patterns
4. **Custom notifications**: Extend `notifier.py` for other platforms

## License

MIT License - Feel free to use and modify for your needs.

## Credits

- Built with Claude Code
- Uses BlockCypher API for blockchain data
- Uses CoinGecko API for price data
- Discord webhooks for notifications

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Verify configuration in `.env` file
4. Test with `--mode once` for debugging

---

**⚠️ Disclaimer**: This tool is for informational purposes only. Whale movements do not guarantee market direction. Always do your own research before making investment decisions.
