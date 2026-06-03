import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.bot import bot, TOKEN
from app.checker import check_and_notify, check_epic_and_notify, check_epic_free_games

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("steam_deals_scheduler")

load_dotenv()

CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "6"))

async def scheduled_check():
    logger.info("Starting scheduled deals check...")
    
    # Run Epic check
    try:
        logger.info("Running Epic Games Store deals check...")
        stats_epic = await check_epic_and_notify(bot)
        logger.info(f"Epic check completed. Checked {stats_epic['targets_checked']} targets, sent {stats_epic['total_deals_sent']} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled Epic deal check: {e}", exc_info=True)
        
    # Run Steam check
    try:
        logger.info("Running Steam deals check...")
        stats = await check_and_notify(bot)
        logger.info(f"Steam check completed. Checked {stats['targets_checked']} targets, sent {stats['total_deals_sent']} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled Steam deal check: {e}", exc_info=True)

async def scheduled_epic_free_games_check():
    logger.info("Starting scheduled Epic Games Store free games check...")
    try:
        stats = await check_epic_free_games(bot)
        logger.info(f"Epic free games check completed. Checked {stats['targets_checked']} targets, sent {stats['total_deals_sent']} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled Epic free games check: {e}", exc_info=True)

async def main():
    if not TOKEN:
        logger.error("Error: DISCORD_TOKEN is missing. Bot cannot start.")
        return

    # Set up APScheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule deals checks every CHECK_INTERVAL_HOURS hours, starting at 9 AM
    trigger = CronTrigger(hour=f"9-23/{CHECK_INTERVAL_HOURS}")
    scheduler.add_job(scheduled_check, trigger)
    
    # Schedule Epic weekly free games check (Thursdays at 17:05 UTC)
    free_trigger = CronTrigger(day_of_week='thu', hour=17, minute=5, timezone='UTC')
    scheduler.add_job(scheduled_epic_free_games_check, free_trigger)
    
    scheduler.start()
    logger.info(f"Scheduler started. Deals checks run every {CHECK_INTERVAL_HOURS} hours starting at 9 AM.")
    logger.info("Epic Games Store free games check scheduled for Thursdays at 17:05 UTC.")
    
    # Start the Discord bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
