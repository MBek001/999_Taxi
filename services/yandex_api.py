import aiohttp
import logging
from typing import Optional, Dict, List
from datetime import datetime

from config import settings
from database import db

logger = logging.getLogger(__name__)

class YandexFleetAPI:
    def __init__(self):
        self.base_url = settings.YANDEX_API_URL
        self.park_id = settings.YANDEX_PARK_ID
        self.client_id = settings.YANDEX_CLIENT_ID
        self.api_key = settings.YANDEX_API_KEY
        self.api_secret = settings.YANDEX_API_SECRET

    async def get_auth_headers(self) -> Dict[str, str]:
        return {
            "X-Client-ID": self.client_id,
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def get_driver_info(self, driver_profile_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/v1/parks/driver-profiles/list"

        headers = await self.get_auth_headers()

        payload = {
            "query": {
                "park": {
                    "id": self.park_id,
                    "driver_profile": {
                        "id": driver_profile_id
                    }
                }
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("driver_profiles"):
                            return data["driver_profiles"][0]
                    else:
                        logger.error(f"Yandex API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching driver info: {e}")
            return None

    async def get_all_drivers(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        url = f"{self.base_url}/v1/parks/driver-profiles/list"

        headers = await self.get_auth_headers()

        payload = {
            "limit": limit,
            "offset": offset,
            "query": {
                "park": {
                    "id": self.park_id
                }
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("driver_profiles", [])
                    else:
                        logger.error(f"Yandex API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching all drivers: {e}")
            return []

    async def get_driver_balance(self, driver_profile_id: str) -> Optional[float]:
        url = f"{self.base_url}/v1/parks/driver-profiles/balances/list"

        headers = await self.get_auth_headers()

        payload = {
            "query": {
                "park": {
                    "id": self.park_id,
                    "driver_profile": {
                        "id": driver_profile_id
                    }
                }
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("accounts"):
                            return float(data["accounts"][0].get("balance", 0))
                    else:
                        logger.error(f"Yandex API balance error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching driver balance: {e}")
            return None

    async def get_driver_orders(self, driver_profile_id: str) -> List[Dict]:
        url = f"{self.base_url}/v2/parks/orders/list"

        headers = await self.get_auth_headers()

        payload = {
            "query": {
                "park": {
                    "id": self.park_id,
                    "driver_profile": {
                        "id": driver_profile_id
                    }
                }
            },
            "limit": 10
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("orders", [])
                    else:
                        logger.error(f"Yandex API orders error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching driver orders: {e}")
            return []

yandex_api = YandexFleetAPI()

async def sync_driver_data(telegram_id: int) -> bool:
    driver = await db.get_driver(telegram_id)

    if not driver or not driver.yandex_driver_id:
        logger.warning(f"Driver {telegram_id} not found or no Yandex ID")
        return False

    driver_info = await yandex_api.get_driver_info(driver.yandex_driver_id)

    if not driver_info:
        logger.error(f"Failed to fetch driver info for {telegram_id}")
        return False

    balance = await yandex_api.get_driver_balance(driver.yandex_driver_id)
    orders = await yandex_api.get_driver_orders(driver.yandex_driver_id)

    last_trip_date = None
    last_trip_sum = 0.0

    if orders:
        last_order = orders[0]
        last_trip_date = datetime.fromisoformat(last_order.get("created_at", "").replace("Z", "+00:00"))
        last_trip_sum = float(last_order.get("price", 0))

    update_data = {
        "name": driver_info.get("driver", {}).get("first_name", "") + " " + driver_info.get("driver", {}).get("last_name", ""),
        "callsign": driver_info.get("driver_profile", {}).get("callsign", ""),
        "car_model": driver_info.get("car", {}).get("model", ""),
        "balance": balance if balance is not None else driver.balance,
        "last_trip_date": last_trip_date,
        "last_trip_sum": last_trip_sum,
        "last_sync": datetime.now(),
        "last_manual_sync": datetime.now()
    }

    await db.update_driver(telegram_id, **update_data)
    logger.info(f"Driver {telegram_id} data synced successfully")
    return True

async def sync_all_drivers(limit: int = 100) -> int:
    drivers_data = await yandex_api.get_all_drivers(limit=limit)

    synced_count = 0

    for driver_data in drivers_data:
        yandex_driver_id = driver_data.get("driver_profile", {}).get("id")

        if not yandex_driver_id:
            continue

        driver = await db.get_driver_by_yandex_id(yandex_driver_id)

        if driver:
            await sync_driver_data(driver.telegram_id)
            synced_count += 1

    logger.info(f"Synced {synced_count} drivers from Yandex Fleet API")
    return synced_count
