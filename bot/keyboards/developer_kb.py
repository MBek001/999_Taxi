from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_message

def get_developer_panel_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message("manage_admins", lang)),
                KeyboardButton(text=get_message("manage_settings", lang))
            ],
            [
                KeyboardButton(text=get_message("download_logs", lang)),
                KeyboardButton(text=get_message("download_backup", lang))
            ],
            [
                KeyboardButton(text=get_message("view_transactions", lang)),
                KeyboardButton(text=get_message("statistics", lang))
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Set Admin Group ID", callback_data="set_admin_group")],
        [InlineKeyboardButton(text="📝 Set Info Channel ID", callback_data="set_info_channel")],
        [InlineKeyboardButton(text="💰 Set Withdrawal Limits", callback_data="set_limits")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_dev_panel")]
    ])
    return keyboard
