from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_message

def get_admin_panel_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message("broadcast", lang)),
                KeyboardButton(text=get_message("statistics", lang))
            ],
            [
                KeyboardButton(text=get_message("pending_registrations", lang))
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_approval_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{telegram_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{telegram_id}")
        ]
    ])
    return keyboard
