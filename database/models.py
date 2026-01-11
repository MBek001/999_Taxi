from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    telegram_id: int
    phone: Optional[str] = None
    language: str = "uz"
    role: str = "driver"
    registration_status: str = "not_started"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Driver:
    id: Optional[int] = None
    telegram_id: int = 0
    yandex_driver_id: Optional[str] = None
    name: Optional[str] = None
    callsign: Optional[str] = None
    car_model: Optional[str] = None
    balance: float = 0.0
    last_trip_date: Optional[datetime] = None
    last_trip_sum: float = 0.0
    is_active: bool = True
    last_sync: Optional[datetime] = None
    last_manual_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Document:
    id: Optional[int] = None
    telegram_id: int = 0
    document_type: str = ""
    file_id: str = ""
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class BotSetting:
    key: str
    value: str
    updated_at: Optional[datetime] = None

@dataclass
class Transaction:
    id: Optional[int] = None
    telegram_id: int = 0
    amount: float = 0.0
    transaction_type: str = "withdrawal"
    status: str = "pending"
    card_number: Optional[str] = None
    payme_transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class AdminAction:
    id: Optional[int] = None
    admin_id: int = 0
    action_type: str = ""
    target_id: int = 0
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
