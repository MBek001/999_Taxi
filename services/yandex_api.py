import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from dateutil import parser

from config import settings
from database import db

logger = logging.getLogger(__name__)

class YandexFleetAPI:
    def __init__(self):
        self.base_url = settings.YANDEX_API_URL
        self.park_id = settings.YANDEX_PARK_ID
        self.client_id = settings.YANDEX_CLIENT_ID
        self.api_key = settings.YANDEX_API_KEY
        self._refresh_lock = asyncio.Lock()

    def get_auth_headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "X-Client-ID": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _normalize_driver(self, raw: dict) -> dict:
        dp = raw.get("driver_profile") or {}
        car = raw.get("car") or {}
        accounts = raw.get("accounts") or []
        current_status = raw.get("current_status") or {}

        account = accounts[0] if accounts else {}

        raw_date = account.get("last_transaction_date")
        dt = None
        if raw_date:
            try:
                dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                try:
                    dt = parser.isoparse(raw_date)
                except Exception:
                    dt = None

        phones = dp.get("phones") or []
        phone_str = phones[0] if phones else None

        return {
            "yandex_driver_id": dp.get("id"),
            "name": f"{dp.get('first_name', '')} {dp.get('last_name', '')}".strip(),
            "callsign": car.get("callsign"),
            "car_model": f"{car.get('brand', '')} {car.get('model', '')}".strip(),
            "balance": float(account.get("balance", 0.0)),
            "last_trip_date": dt,
            "last_trip_sum": 0.0,
            "is_active": True,
        }

    async def fetch_all_drivers(self, notify_channel=False, bot=None) -> int:
        async with self._refresh_lock:
            try:
                logger.info("Fetching ALL drivers from Yandex API...")
                offset = 0
                limit = 1000
                total = 0

                retries = 0
                max_retries = 6
                backoff_base = 1.5

                url = f"{self.base_url}/parks/driver-profiles/list"
                headers = self.get_auth_headers()

                base_query = {
                    "fields": {
                        "driver_profile": ["id", "first_name", "last_name", "phones", "work_status"],
                        "car": ["brand", "model", "number", "callsign", "category"],
                        "accounts": ["balance", "last_transaction_date"],
                        "current_status": ["status"],
                    },
                    "query": {"park": {"id": self.park_id}},
                }

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as session:
                    while True:
                        body = dict(base_query)
                        body.update({
                            "limit": limit,
                            "offset": offset,
                            "sort_order": [{"field": "driver_profile.created_date", "direction": "desc"}],
                        })

                        try:
                            async with session.post(url, headers=headers, json=body) as resp:
                                if resp.status == 429:
                                    retry_after = resp.headers.get("Retry-After")
                                    if retry_after:
                                        delay = float(retry_after)
                                    else:
                                        delay = min(60, backoff_base ** retries) + (0.25 * (retries + 1))
                                    retries += 1
                                    if retries > max_retries:
                                        logger.error("Hit 429 too many times; aborting refresh")
                                        break
                                    logger.warning(
                                        f"Rate limited (429). Sleeping {delay:.2f}s before retry (try {retries}/{max_retries})"
                                    )
                                    await asyncio.sleep(delay)
                                    continue

                                resp.raise_for_status()
                                data = await resp.json()
                                profiles = data.get("driver_profiles") or []
                                if not profiles:
                                    break

                                for pr in profiles:
                                    driver_data = self._normalize_driver(pr)

                                    yandex_id = driver_data.get("yandex_driver_id")
                                    if not yandex_id:
                                        continue

                                    existing_driver = await db.get_driver_by_yandex_id(yandex_id)
                                    if existing_driver:
                                        await db.update_driver(existing_driver.telegram_id, **driver_data)
                                    total += 1

                                logger.info(f"Fetched {len(profiles)} drivers (offset={offset})")

                                if len(profiles) < limit:
                                    break

                                offset += len(profiles)
                                retries = 0
                                await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Request error: {e}")
                            break

                msg = f"✅ Full refresh completed. {total} drivers synced."
                logger.info(msg)

                if notify_channel and bot:
                    try:
                        update_channel_id = await db.get_setting("update_info_channel_id")
                        if update_channel_id:
                            await bot.send_message(chat_id=int(update_channel_id), text=msg)
                    except Exception as e:
                        logger.error(f"Error sending notification: {e}")

                return total
            except Exception as e:
                logger.error(f"Error fetching all drivers: {e}")
                return 0

    async def fetch_recent_drivers(self, days: int, notify_channel=True, bot=None) -> int:
        async with self._refresh_lock:
            try:
                logger.info(f"Starting refresh for last {days} days...")
                since = datetime.now(timezone.utc) - timedelta(days=days)
                offset = 0
                limit = 1000
                total = 0

                url = f"{self.base_url}/parks/driver-profiles/list"
                headers = self.get_auth_headers()

                base_query = {
                    "fields": {
                        "driver_profile": ["id", "first_name", "last_name", "phones", "created_date"],
                        "car": ["brand", "model", "callsign"],
                        "accounts": ["balance", "last_transaction_date"],
                    },
                    "query": {"park": {"id": self.park_id}},
                }

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as session:
                    while True:
                        body = dict(base_query)
                        body.update({
                            "limit": limit,
                            "offset": offset,
                            "sort_order": [{"field": "driver_profile.created_date", "direction": "desc"}],
                        })

                        try:
                            async with session.post(url, headers=headers, json=body) as resp:
                                resp.raise_for_status()
                                data = await resp.json()
                                profiles = data.get("driver_profiles") or []
                                if not profiles:
                                    break

                                oldest_in_page = None
                                for pr in profiles:
                                    dp = pr.get("driver_profile") or {}
                                    ts = dp.get("created_date")
                                    if not ts:
                                        continue
                                    try:
                                        ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                    except Exception:
                                        ts_dt = parser.isoparse(ts)
                                    if oldest_in_page is None or ts_dt < oldest_in_page:
                                        oldest_in_page = ts_dt
                                    if ts_dt >= since:
                                        driver_data = self._normalize_driver(pr)
                                        yandex_id = driver_data.get("yandex_driver_id")
                                        if yandex_id:
                                            existing_driver = await db.get_driver_by_yandex_id(yandex_id)
                                            if existing_driver:
                                                await db.update_driver(existing_driver.telegram_id, **driver_data)
                                        total += 1

                                if oldest_in_page and oldest_in_page < since:
                                    break
                                if len(profiles) < limit:
                                    break
                                offset += len(profiles)
                                await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Error fetching recent drivers: {e}")
                            break

                total_in_db = await db.get_driver_count()
                msg = f"✅ Recent refresh completed. {total} drivers (last {days} days) synced. Total in DB: {total_in_db}"
                logger.info(msg)

                if notify_channel and bot:
                    try:
                        update_channel_id = await db.get_setting("update_info_channel_id")
                        if update_channel_id:
                            await bot.send_message(chat_id=int(update_channel_id), text=msg)
                    except Exception as e:
                        logger.error(f"Error sending notification: {e}")

                return total
            except Exception as e:
                logger.error(f"Error fetching recent drivers: {e}")
                return 0

    async def auto_refresh(self, context):
        last_full_refresh = None

        while True:
            try:
                now = datetime.now()

                if not last_full_refresh or (now - last_full_refresh).total_seconds() >= 86400:
                    logger.info("⏳ Running scheduled FULL refresh...")
                    total = await self.fetch_all_drivers(notify_channel=True, bot=context.bot)
                    last_full_refresh = now

                    msg = f"🕐 FULL refresh finished.\n✅ Synced {total} drivers.\n📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
                    try:
                        update_channel_id = await db.get_setting("update_info_channel_id")
                        if update_channel_id:
                            await context.bot.send_message(chat_id=int(update_channel_id), text=msg)
                    except Exception:
                        pass

                logger.info("⏳ Running scheduled RECENT refresh (last 1 day)...")
                total = await self.fetch_recent_drivers(1, bot=context.bot)

                msg = f"🔄 Recent refresh finished.\n✅ Synced {total} drivers (last 24h).\n📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
                try:
                    update_channel_id = await db.get_setting("update_info_channel_id")
                    if update_channel_id:
                        await context.bot.send_message(chat_id=int(update_channel_id), text=msg)
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"Auto-refresh loop error: {e}")
                try:
                    update_channel_id = await db.get_setting("update_info_channel_id")
                    if update_channel_id:
                        await context.bot.send_message(
                            chat_id=int(update_channel_id),
                            text=f"❌ Auto-refresh failed: {e}"
                        )
                except Exception:
                    pass

            await asyncio.sleep(900)

yandex_api = YandexFleetAPI()

async def sync_driver_data(telegram_id: int) -> bool:
    driver = await db.get_driver(telegram_id)

    if not driver or not driver.yandex_driver_id:
        logger.warning(f"Driver {telegram_id} not found or no Yandex ID")
        return False

    try:
        url = f"{yandex_api.base_url}/parks/driver-profiles/list"
        headers = yandex_api.get_auth_headers()

        body = {
            "fields": {
                "driver_profile": ["id", "first_name", "last_name", "phones"],
                "car": ["brand", "model", "callsign"],
                "accounts": ["balance", "last_transaction_date"],
            },
            "query": {
                "park": {
                    "id": yandex_api.park_id,
                    "driver_profile": {
                        "id": driver.yandex_driver_id
                    }
                }
            },
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(url, headers=headers, json=body) as resp:
                resp.raise_for_status()
                data = await resp.json()
                profiles = data.get("driver_profiles") or []

                if not profiles:
                    logger.error(f"No profile found for driver {telegram_id}")
                    return False

                driver_data = yandex_api._normalize_driver(profiles[0])
                driver_data["last_sync"] = datetime.now()
                driver_data["last_manual_sync"] = datetime.now()

                await db.update_driver(telegram_id, **driver_data)
                logger.info(f"Driver {telegram_id} data synced successfully")
                return True
    except Exception as e:
        logger.error(f"Error syncing driver data: {e}")
        return False
