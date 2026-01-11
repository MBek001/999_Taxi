import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    DEVELOPER_IDS: list[int] = [
        int(id.strip())
        for id in os.getenv("DEVELOPER_IDS", "").split(",")
        if id.strip()
    ]

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "taxi_bot.db")

    YANDEX_API_URL: str = os.getenv("YANDEX_API_URL", "")
    YANDEX_PARK_ID: str = os.getenv("YANDEX_PARK_ID", "")
    YANDEX_CLIENT_ID: str = os.getenv("YANDEX_CLIENT_ID", "")
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_API_SECRET: str = os.getenv("YANDEX_API_SECRET", "")

    PAYME_ID: str = os.getenv("PAYME_ID", "")
    PAYME_KEY: str = os.getenv("PAYME_KEY", "")
    PAYME_URL: str = os.getenv("PAYME_URL", "")

    def validate(self) -> tuple[bool, str]:
        if not self.BOT_TOKEN:
            return False, "BOT_TOKEN is required in .env"
        if not self.DEVELOPER_IDS:
            return False, "DEVELOPER_IDS is required in .env"
        return True, "Configuration valid"
