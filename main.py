import asyncio
import logging
from app.scheduler import main

logger = logging.getLogger("steam_deals_scheduler")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
