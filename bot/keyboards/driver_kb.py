from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_message

def get_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])
    return keyboard

def get_share_contact_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_message("share_contact_button", lang), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_start_registration_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_message("start_registration", lang))]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_driver_main_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message("my_profile", lang)),
                KeyboardButton(text=get_message("my_balance", lang))
            ],
            [
                KeyboardButton(text=get_message("my_stats", lang)),
                KeyboardButton(text=get_message("update_info", lang))
            ],
            [
                KeyboardButton(text=get_message("withdraw_money", lang)),
                KeyboardButton(text=get_message("instructions", lang))
            ],
            [
                KeyboardButton(text=get_message("contact_admins", lang)),
                KeyboardButton(text=get_message("settings", lang))
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_withdrawal_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_message("refresh_balance", lang),
                callback_data="refresh_balance"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_message("withdraw", lang),
                callback_data="withdraw_start"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_message("back", lang),
                callback_data="back_to_menu"
            )
        ]
    ])
    return keyboard

def get_inactive_check_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_message("inactive_yes", lang),
                callback_data="inactive_ok"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_message("inactive_no", lang),
                callback_data="inactive_problem"
            )
        ]
    ])
    return keyboard

def get_back_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_message("back", lang))]
        ],
        resize_keyboard=True
    )
    return keyboard
