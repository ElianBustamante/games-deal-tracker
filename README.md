# Steam Deals Bot

## What it does

Discord bot that monitors Steam deals and posts alerts to a configured channel.
Tracks a per-server watchlist and general deals above a configurable discount threshold.
Builds its own price history over time to identify all-time low prices.

## How price history works

Steam's public API only provides current prices.
This bot saves a price snapshot on every check and uses that data to determine
whether the current deal is the best price it has ever recorded.

## Requirements

Python 3.11+, a Discord bot token, no external API keys needed.

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
python app/scheduler.py

### 3. Configure in Discord

/setcanal #your-channel
/setdescuento 60
/watchlist add Cyberpunk 2077

## Adding to more servers

Use the same invite link. Each server configures its own channel and thresholds.
Price history is shared globally — data accumulates regardless of which server
is watching a game.

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
4. Make sure the Startup File is set to `app/scheduler.py` and click Start.

### Oracle Cloud Free Tier (Best free alternative)

cloud.oracle.com/free → Ubuntu 22.04 ARM instance → SSH in:
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip git -y
git clone {repo} && cd steam-deal-tracker
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env && nano .env
nohup python app/scheduler.py &   (or set up systemd for auto-restart)

### Self-Hosting

Can be hosted on any Raspberry Pi or old PC. Just install Python 3.11+ and run `app/scheduler.py`.
