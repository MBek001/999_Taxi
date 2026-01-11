from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from database.models import Driver, AdminAction
from utils import get_message
from bot.keyboards import get_driver_main_menu, get_withdrawal_menu
import logging

router = Router()
logger = logging.getLogger(__name__)

class RejectionState(StatesGroup):
    waiting_for_reason = State()

rejection_data = {}

@router.callback_query(F.data.startswith("approve_"))
async def process_approval(callback: CallbackQuery):
    admin_id = callback.from_user.id
    telegram_id = int(callback.data.split("_")[1])

    user = await db.get_user(telegram_id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    await db.update_user(telegram_id, registration_status="approved")

    driver = await db.get_driver(telegram_id)
    if not driver:
        driver = Driver(telegram_id=telegram_id)
        await db.create_driver(driver)

    action = AdminAction(
        admin_id=admin_id,
        action_type="approve_registration",
        target_id=telegram_id
    )
    await db.log_admin_action(action)

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    lang = user.language
    await bot.send_message(
        chat_id=telegram_id,
        text=get_message("registration_approved", lang),
        reply_markup=get_driver_main_menu(lang)
    )

    admin_name = callback.from_user.full_name
    admin_username = f"@{callback.from_user.username}" if callback.from_user.username else "No username"
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ APPROVED by:\n"
        f"Name: {admin_name}\n"
        f"Username: {admin_username}\n"
        f"ID: {admin_id}"
    )

    await callback.answer("✅ Registration approved")

@router.callback_query(F.data.startswith("reject_"))
async def process_rejection_start(callback: CallbackQuery, state: FSMContext):
    admin_id = callback.from_user.id
    telegram_id = int(callback.data.split("_")[1])

    rejection_data[admin_id] = {
        "telegram_id": telegram_id,
        "message_id": callback.message.message_id
    }

    await callback.message.reply(
        "Please reply to this message with the rejection reason:"
    )
    await state.set_state(RejectionState.waiting_for_reason)
    await callback.answer()

@router.message(RejectionState.waiting_for_reason)
async def process_rejection_reason(message: Message, state: FSMContext):
    admin_id = message.from_user.id

    if admin_id not in rejection_data:
        return

    reason = message.text
    data = rejection_data[admin_id]
    telegram_id = data["telegram_id"]

    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("User not found")
        await state.clear()
        del rejection_data[admin_id]
        return

    await db.update_user(telegram_id, registration_status="rejected")

    action = AdminAction(
        admin_id=admin_id,
        action_type="reject_registration",
        target_id=telegram_id,
        reason=reason
    )
    await db.log_admin_action(action)

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    lang = user.language
    await bot.send_message(
        chat_id=telegram_id,
        text=get_message("registration_rejected", lang, reason=reason)
    )

    admin_name = message.from_user.full_name
    admin_username = f"@{message.from_user.username}" if message.from_user.username else "No username"

    admin_group_id = await db.get_setting("admin_group_id")
    if admin_group_id:
        await bot.send_message(
            chat_id=int(admin_group_id),
            text=f"❌ Registration REJECTED\n\n"
                 f"Driver ID: {telegram_id}\n\n"
                 f"Rejected by:\n"
                 f"Name: {admin_name}\n"
                 f"Username: {admin_username}\n"
                 f"ID: {admin_id}\n\n"
                 f"Reason: {reason}"
        )

    await message.answer("✅ Rejection sent to driver")
    await state.clear()
    del rejection_data[admin_id]

@router.callback_query(F.data == "refresh_balance")
async def refresh_balance_callback(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    driver = await db.get_driver(telegram_id)
    if not driver:
        await callback.answer(get_message("error_occurred", lang), show_alert=True)
        return

    from services.yandex_api import sync_driver_data
    try:
        await sync_driver_data(telegram_id)
        driver = await db.get_driver(telegram_id)
        balance = driver.balance if driver else 0

        await callback.message.edit_text(
            get_message("withdrawal_menu", lang, balance=balance),
            reply_markup=get_withdrawal_menu(lang)
        )
        await callback.answer("✅ Balance refreshed")
    except Exception as e:
        logger.error(f"Error refreshing balance: {e}")
        await callback.answer(get_message("error_occurred", lang), show_alert=True)

@router.callback_query(F.data == "withdraw_start")
async def withdraw_start_callback(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    await callback.answer(get_message("withdrawal_not_implemented", lang), show_alert=True)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    await callback.message.delete()
    await callback.message.answer(
        get_message("main_menu", lang),
        reply_markup=get_driver_main_menu(lang)
    )
    await callback.answer()

@router.callback_query(F.data == "inactive_ok")
async def inactive_ok_callback(callback: CallbackQuery):
    await callback.message.edit_text("✅ Great! Happy driving!")
    await callback.answer()

@router.callback_query(F.data == "inactive_problem")
async def inactive_problem_callback(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    await callback.message.edit_text(get_message("inactive_problem", lang))
    await state.set_state("waiting_for_problem_description")
    await callback.answer()

@router.message(F.text, F.state == "waiting_for_problem_description")
async def process_problem_description(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    admin_group_id = await db.get_setting("admin_group_id")
    if admin_group_id:
        await bot.send_message(
            chat_id=int(admin_group_id),
            text=f"⚠️ Driver Problem Report\n\n"
                 f"Driver ID: {telegram_id}\n"
                 f"Phone: {user.phone}\n\n"
                 f"Problem: {message.text}"
        )

    await message.answer(get_message("inactive_problem_sent", lang))
    await state.clear()

def register_handlers(dp):
    dp.include_router(router)
