from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timedelta

from database import db
from utils import get_message
from bot.keyboards import get_driver_main_menu, get_language_keyboard, get_withdrawal_menu
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text.in_(["👤 Mening profilim", "👤 Мой профиль"]))
async def show_profile(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)

    if not driver:
        await message.answer(get_message("error_occurred", lang))
        return

    phone = user.phone or "N/A"
    callsign = driver.callsign or "N/A"
    car_model = driver.car_model or "N/A"
    balance = driver.balance or 0

    await message.answer(
        get_message("profile_info", lang,
                   phone=phone,
                   callsign=callsign,
                   car_model=car_model,
                   balance=f"{balance:,.2f}")
    )

@router.message(F.text.in_(["💰 Mening balansi", "💰 Мой баланс"]))
async def show_balance(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)

    if not driver:
        await message.answer(get_message("error_occurred", lang))
        return

    balance = driver.balance or 0
    last_trip_date = driver.last_trip_date.strftime("%Y-%m-%d %H:%M") if driver.last_trip_date else "N/A"
    last_trip_sum = driver.last_trip_sum or 0

    await message.answer(
        get_message("balance_info", lang,
                   balance=f"{balance:,.2f}",
                   last_trip_date=last_trip_date,
                   last_trip_sum=f"{last_trip_sum:,.2f}")
    )

@router.message(F.text.in_(["📊 Mening statistikam", "📊 Моя статистика"]))
async def show_stats(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)

    if not driver:
        await message.answer(get_message("error_occurred", lang))
        return

    last_trip_date = driver.last_trip_date.strftime("%Y-%m-%d %H:%M") if driver.last_trip_date else "N/A"
    last_trip_sum = driver.last_trip_sum or 0
    status = "🟢 Active" if driver.is_active else "🔴 Inactive"

    await message.answer(
        get_message("stats_info", lang,
                   last_trip_date=last_trip_date,
                   last_trip_sum=f"{last_trip_sum:,.2f}",
                   status=status)
    )

@router.message(F.text.in_(["🔄 Ma'lumotlarni yangilash", "🔄 Обновить данные"]))
async def update_info(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)

    if not driver:
        await message.answer(get_message("error_occurred", lang))
        return

    if driver.last_manual_sync:
        time_diff = datetime.now() - driver.last_manual_sync
        if time_diff < timedelta(hours=1):
            await message.answer(get_message("update_info_limit", lang))
            return

    await message.answer(get_message("update_info_started", lang))

    from services.yandex_api import sync_driver_data
    try:
        await sync_driver_data(telegram_id)
        await message.answer(get_message("update_info_success", lang))
    except Exception as e:
        logger.error(f"Error updating driver data: {e}")
        await message.answer(get_message("update_info_error", lang))

@router.message(F.text.in_(["💸 Pulni yechish", "💸 Вывести деньги"]))
async def withdraw_money(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)

    if not driver:
        await message.answer(get_message("error_occurred", lang))
        return

    balance = driver.balance or 0

    await message.answer(
        get_message("withdrawal_menu", lang, balance=f"{balance:,.2f}"),
        reply_markup=get_withdrawal_menu(lang)
    )

@router.message(F.text.in_(["📖 Yo'riqnoma", "📖 Инструкции"]))
async def show_instructions(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    info_channel_id = await db.get_setting("info_channel_id")

    if not info_channel_id:
        await message.answer(get_message("info_channel_not_configured", lang))
        return

    instruction_message_id = await db.get_setting("instruction_message_id")

    if not instruction_message_id:
        await message.answer("Instructions not configured yet.")
        return

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        await bot.copy_message(
            chat_id=telegram_id,
            from_chat_id=int(info_channel_id),
            message_id=int(instruction_message_id)
        )
    except Exception as e:
        logger.error(f"Error copying instruction message: {e}")
        await message.answer(get_message("error_occurred", lang))

@router.message(F.text.in_(["📞 Adminlar bilan bog'lanish", "📞 Связаться с админами"]))
async def contact_admins(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    admin_group_id = await db.get_setting("admin_group_id")

    if not admin_group_id:
        await message.answer(get_message("admin_group_not_configured", lang))
        return

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    driver = await db.get_driver(telegram_id)
    name = driver.name if driver else message.from_user.first_name

    try:
        await bot.send_message(
            chat_id=int(admin_group_id),
            text=f"📞 Driver Contact Request\n\n"
                 f"Name: {name}\n"
                 f"Phone: {user.phone}\n"
                 f"Telegram ID: {telegram_id}\n"
                 f"Username: @{message.from_user.username if message.from_user.username else 'N/A'}"
        )
        await message.answer("✅ Your contact request has been sent to admins.")
    except Exception as e:
        logger.error(f"Error sending contact request: {e}")
        await message.answer(get_message("error_occurred", lang))

@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def show_settings(message: Message):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    await message.answer(
        get_message("language_menu", lang),
        reply_markup=get_language_keyboard()
    )

def register_handlers(dp):
    dp.include_router(router)
