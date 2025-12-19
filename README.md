# BSG Magazine Product Tracker

A Python bot that monitors [BSG Magazine](https://bsgmag.ro/catalog/produse-recente) for newly added products and sends real-time notifications via Telegram.

## Features

✅ **Continuous Monitoring** - Automatically checks for new products every 5 minutes  
✅ **Multi-Page Scraping** - Handles pagination across all product pages  
✅ **Telegram Notifications** - Instant alerts with product name, price, and link  
✅ **Duplicate Detection** - Tracks seen products to avoid repeat notifications  
✅ **Auto-Recovery** - Handles network errors gracefully  
✅ **Raspberry Pi Optimized** - Lightweight and runs 24/7 on Pi Zero W

## Requirements

- Python 3.7+
- Raspberry Pi (or any Linux system)
- Telegram account

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/justblu3/Notifysite-raspb.git
cd Notifysite-raspb
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install requests beautifulsoup4
```

### 4. Set Up Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the bot token (looks like: `123456:ABC-DEF...`)
4. Search for **@userinfobot** 
5. Send `/start` and copy your chat ID

### 5. Configure the Bot
```bash
cp bot_config.example.json bot_config.json
nano bot_config.json
```

Edit the file with your credentials:
```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "check_interval_seconds": 300,
  "notifications_enabled": true
}
```

## Usage

### Run Single Check (One-Time)
```bash
python bsg.py
```

### Run Continuous Bot Mode
```bash
python bsg.py --bot
```

### Keep Running 24/7

**Using screen (recommended for testing):**
```bash
screen -S bsg-bot
python bsg.py --bot
# Press Ctrl+A then D to detach
# Reattach with: screen -r bsg-bot
```

**Using systemd (recommended for production):**

Create service file:
```bash
sudo nano /etc/systemd/system/bsg-bot.service
```

Add:
```ini
[Unit]
Description=BSG Magazine Product Tracker Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/bsg-tracker
ExecStart=/home/pi/bsg-tracker/.venv/bin/python /home/pi/bsg-tracker/bsg.py --bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bsg-bot
sudo systemctl start bsg-bot
```

Check status:
```bash
sudo systemctl status bsg-bot
```

## Configuration Options

Edit `bot_config.json`:

- **telegram_bot_token**: Your Telegram bot token from @BotFather
- **telegram_chat_id**: Your Telegram chat ID
- **check_interval_seconds**: How often to check for new products (default: 300 = 5 minutes)
- **notifications_enabled**: Enable/disable Telegram notifications

## File Structure
```
bsg-tracker/
├── bsg.py                    # Main script
├── bot_config.json           # Your credentials (not in git)
├── bot_config.example.json   # Template config file
├── bsg_products.json         # Database of seen products (auto-generated)
└── README.md                 # This file
```

## Troubleshooting

**Bot not connecting to Telegram:**
- Verify bot token and chat ID are correct
- Make sure you've started a chat with your bot on Telegram

**No products found:**
- Website structure may have changed
- Check internet connection on your Pi

**Bot stops after a while:**
- Use systemd service for auto-restart
- Check logs: `sudo journalctl -u bsg-bot -f`

## License

MIT License - Feel free to modify and use as needed!

## Author

Created for monitoring BSG Magazine product listings on Raspberry Pi.
