import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.bot import bot, TOKEN
from app.checker import check_and_notify

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("steam_deals_scheduler")

load_dotenv()

CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "6"))

async def scheduled_check():
    logger.info("Starting scheduled deal check...")
    try:
        stats = await check_and_notify(bot)
        logger.info(f"Check completed successfully. Checked {stats['servers_checked']} servers, sent {stats['total_deals_sent']} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled deal check: {e}", exc_info=True)

async def main():
    if not TOKEN:
        logger.error("Error: DISCORD_TOKEN is missing. Bot cannot start.")
        return

    # Set up APScheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule every CHECK_INTERVAL_HOURS hours, starting at 9 AM
    trigger = CronTrigger(hour=f"9-23/{CHECK_INTERVAL_HOURS}")
    scheduler.add_job(scheduled_check, trigger)
    
    scheduler.start()
    logger.info(f"Scheduler started. Checks run every {CHECK_INTERVAL_HOURS} hours starting at 9 AM.")
    
    # Start the Discord bot
    async with bot:
        await bot.start(TOKEN)

