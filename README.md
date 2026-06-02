# Steam & Epic Deals Bot

A Discord bot that monitors Steam and Epic Games Store (EGS) deals and posts alerts to configured channels or private Direct Messages. It tracks per-server/per-user watchlists, monitors general deals above a discount threshold, alerts on weekly EGS free games, and builds its own price history to identify all-time low prices.

---

## Key Features

- **Cross-Store Price Comparison**: Checks deals on both Steam and Epic Games Store side-by-side (via `/compare`), and automatically appends EGS price comparisons to Steam watchlist alerts.
- **Weekly EGS Free Games Alerts**: Automatically tracks and alerts when Epic Games Store rotates its free games (every Thursday at 17:05 UTC).
- **Hybrid Architecture**: Supports both Server channels and Private DMs.
- **Global Multi-Region**: Monitors prices in over 40 countries, displaying deals in your local currency.
- **Native Localization (i18n)**: Automatically translates slash commands and bot responses into Spanish or English based on your Discord app settings.
- **Price History**: Tracks historical lows across multiple currencies dynamically to identify true all-time low prices for both stores.
- **Privacy-First**: Data is automatically deleted when the bot is removed from a server, after 3 failed DM deliveries, or instantly via `/stop`.
- **Safe for Work (SFW)**: Automatically filters out explicit, pornographic, and "Adults Only" games from Steam deals and the watchlist.

---

## Tech Stack

- **Python 3.11+** & **discord.py** (Bot Framework)
- **aiohttp** (Async HTTP Client for Steam and EGS GraphQL/JSON API requests)
- **SQLite** & **aiosqlite** (Async Database for configurations, watchlists, and price history)
- **apscheduler** (Cron-based task scheduling)
- **pytest**, **pytest-asyncio** & **pytest-mock** (Testing suite)

---

## Setup & Installation

### 1. Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot → Reset Token.
2. Under **Privileged Gateway Intents**, leave all options OFF.
3. Go to the **Installation** tab and ensure both **Guild Install** and **User Install** are checked.
   - For **User Install** Scopes, select ONLY `applications.commands`.
   - Use the **Discord Provided Link** to invite the bot to servers or personal accounts.

### 2. Running Locally

```bash
git clone https://github.com/ElianBustamante/steam-deal-tracker.git
cd steam-deal-tracker
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.\.venv\Scripts\activate   # Windows

pip install -r requirements.txt
cp .env.example .env       # Fill in your DISCORD_TOKEN
python main.py
```

---

## Discord Commands

- `/setchannel` - Set the channel where Steam deals alerts will be sent (Servers only).
- `/setepicchannel` - Set the channel where Epic Games Store alerts will be sent (falls back to Steam channel if not set).
- `/setdiscount` - Set the minimum % discount for general alerts.
- `/setlanguage` - Set the bot response language (en/es).
- `/setcountry` - Set the country region to get local currency prices.
- `/watchlist add` | `remove` | `show` - Manage your monitored games (supports Steam and Epic Games Store).
- `/compare` - Compare current prices and histories side-by-side between Steam and Epic.
- `/history` - Show the recorded price history for a specific game (checks Steam, falls back to Epic).
- `/deals` - Search for Steam deals manually right now.
- `/epicdeals` - Search for Epic Games Store deals manually right now.
- `/epicfree` - Show the current and upcoming free games from Epic Games Store.
- `/stop` - Stop notifications and delete all your data instantly.

---

## Hosting Options

### PebbleHost (Recommended)

1. Purchase a Bot Hosting plan at pebblehost.com.
2. Deploy via the **Git tab** (Pull from repository URL) OR via **File Upload** (Upload project `.zip` and extract).
3. Create a `.env` file via File Manager with your `DISCORD_TOKEN`.
4. Set the Startup File to `main.py` and start the server.

### Oracle Cloud Free Tier

Deploy an Ubuntu 22.04 ARM instance, SSH into the machine, install Python 3.11+, clone the repository, install dependencies, and run via `nohup python main.py &` (or set up a systemd service).

### Self-Hosting

Can be hosted on any Raspberry Pi or PC. Ensure Python 3.11+ is installed and run `main.py`.

---

## Discord Bot Verification

The bot works seamlessly on up to 75 servers without verification. To scale beyond that, visit the Developer Portal and submit a Verification request. Prepare a use case description, privacy policy URL (found in this repository), and a short demo video.
