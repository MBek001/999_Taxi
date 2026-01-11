import asyncio
import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from database import db
from config import settings
from utils import get_message
from bot.keyboards import get_inactive_check_keyboard

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, bot: Bot):
        self.scheduler = AsyncIOScheduler()
        self.bot = bot

    def start(self):
        self.scheduler.add_job(
            self.daily_sync_task,
            CronTrigger(hour=0, minute=0, timezone="Asia/Tashkent"),
            id="daily_sync",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.check_inactive_drivers_task,
            CronTrigger(hour=10, minute=0, timezone="Asia/Tashkent"),
            id="inactive_check",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler started")

    async def daily_sync_task(self):
        logger.info("Starting daily sync task")

        from services.yandex_api import sync_all_drivers
        from services.queue_manager import queue_manager

        try:
            drivers = await db.get_all_drivers()

            for driver in drivers:
                if driver.yandex_driver_id:
                    await queue_manager.add_task(self._sync_single_driver, driver.telegram_id)

            logger.info(f"Scheduled sync for {len(drivers)} drivers")
        except Exception as e:
            logger.error(f"Error in daily sync task: {e}")

    async def _sync_single_driver(self, telegram_id: int):
        from services.yandex_api import sync_driver_data

        try:
            await sync_driver_data(telegram_id)
        except Exception as e:
            logger.error(f"Error syncing driver {telegram_id}: {e}")

    async def check_inactive_drivers_task(self):
        logger.info("Starting inactive drivers check")

        try:
            inactive_drivers = await db.get_inactive_drivers(days=7)

            for driver in inactive_drivers:
                try:
                    user = await db.get_user(driver.telegram_id)
                    if not user:
                        continue

                    lang = user.language

                    await self.bot.send_message(
                        chat_id=driver.telegram_id,
                        text=get_message("inactive_check", lang),
                        reply_markup=get_inactive_check_keyboard(lang)
                    )

                    logger.info(f"Sent inactive check to driver {driver.telegram_id}")
                except Exception as e:
                    logger.error(f"Error sending inactive check to {driver.telegram_id}: {e}")

            logger.info(f"Inactive check sent to {len(inactive_drivers)} drivers")
        except Exception as e:
            logger.error(f"Error in inactive drivers check: {e}")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

def create_scheduler(bot: Bot) -> Scheduler:
    return Scheduler(bot)
