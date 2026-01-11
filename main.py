import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database import db
from bot.handlers import register_all_handlers
from services.scheduler import create_scheduler
from services.queue_manager import queue_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    valid, message = settings.validate()
    if not valid:
        logger.error(f"Configuration error: {message}")
        return

    logger.info("Starting 999 Taxi Bot...")

    await db.connect()

    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    register_all_handlers(dp)

    scheduler = create_scheduler(bot)
    scheduler.start()

    asyncio.create_task(queue_manager.start())

    logger.info("Bot is running...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.stop()
        await queue_manager.stop()
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
