# Steam Deals Bot

## What it does

Discord bot that monitors Steam deals and posts alerts to a configured channel or private Direct Messages (DMs).
Tracks a per-server/per-user watchlist and general deals above a configurable discount threshold.
Builds its own price history over time to identify all-time low prices.

## Features

- **Hybrid Architecture**: Supports both Server channels and Private DMs.
- **Global Multi-Region**: Monitors prices in over 40 countries, displaying deals in your local currency.
- **Native Localization (i18n)**: Automatically translates slash commands and bot responses into Spanish or English based on your Discord app settings.
- **Price History**: Tracks historical lows across multiple currencies dynamically.

## How price history works

Steam's public API only provides current prices.
This bot saves a price snapshot on every check and uses that data to determine
whether the current deal is the best price it has ever recorded.

## Requirements

Python 3.11+, a Discord bot token, no external API keys needed.

## Tech Stack

- **Language**: Python 3.11+
- **Discord API**: `discord.py`
- **HTTP Client**: `aiohttp` (for async Steam API requests)
- **Database**: SQLite via `aiosqlite` (async)
- **Task Scheduling**: `apscheduler` (Cron-based triggers)
- **Environment**: `python-dotenv`
- **Testing**:
  - `pytest` (Test runner)
  - `pytest-asyncio` (Async testing support)
  - `pytest-mock` (Mocking API responses and DB connections)

## Setup

### 1. Create the Discord bot

- discord.com/developers/applications → New Application → Bot → Reset Token
- Privileged Gateway Intents: leave all OFF
- OAuth2 → URL Generator:
  Scopes: bot, applications.commands
  Permissions: Send Messages, Embed Links, Use Slash Commands
- Open the generated invite URL to add the bot to your server

### 2. Install and run

git clone → pip install -r requirements.txt
cp .env.example .env → fill in DISCORD_TOKEN
python main.py

### 3. Configure in Discord

/setchannel #your-channel (Only for servers)
/setdiscount 60
/setcountry Chile
/setlanguage es
/watchlist add Cyberpunk 2077
/stop (To pause alerts and wipe your data)

## Adding to more servers

Use the same invite link. Each server configures its own channel and thresholds.
Price history is shared globally — data accumulates regardless of which server or user
is watching a game. Users can also just DM the bot directly to get private alerts!

## Discord Bot Verification

Works on up to 75 servers without verification.
To scale beyond that: discord.com/developers → your app → Bot → Verify
Prepare: use case description, privacy policy URL, short demo video.
Free, takes 1–5 business days.

## Hosting

### PebbleHost (Recommended)

1. Purchase a Bot Hosting plan at pebblehost.com.
2. In the PebbleHost panel, go to the Console and run: `git clone https://github.com/ElianBustamante/steam-deal-tracker.git .`
3. Create a `.env` file via the File Manager with your `DISCORD_TOKEN`.
4. Make sure the Startup File is set to `main.py` and click Start.

### Oracle Cloud Free Tier (Best free alternative)

cloud.oracle.com/free → Ubuntu 22.04 ARM instance → SSH in:
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip git -y
git clone {repo} && cd steam-deal-tracker
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env && nano .env
nohup python main.py &   (or set up systemd for auto-restart)

### Self-Hosting

Can be hosted on any Raspberry Pi or old PC. Just install Python 3.11+ and run `main.py`.
