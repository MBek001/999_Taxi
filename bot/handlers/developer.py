from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from utils import get_message
from bot.keyboards import get_developer_panel_keyboard, get_settings_keyboard
from datetime import datetime
import logging
import os

router = Router()
logger = logging.getLogger(__name__)

class DeveloperStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_setting_value = State()

setting_context = {}

@router.message(F.text.in_(["👥 Adminlarni boshqarish", "👥 Управление админами"]))
async def manage_admins(message: Message):
    admin_ids = await db.get_admin_ids()
    admin_list = "\n".join([f"• {admin_id}" for admin_id in admin_ids]) if admin_ids else "No admins configured"

    keyboard = {
        "keyboard": [
            [{"text": "➕ Add Admin"}],
            [{"text": "➖ Remove Admin"}],
            [{"text": "🔙 Back"}]
        ],
        "resize_keyboard": True
    }

    await message.answer(
        f"👥 Admin Management\n\n"
        f"Current Admins:\n{admin_list}",
        reply_markup=keyboard
    )

@router.message(F.text == "➕ Add Admin")
async def add_admin_start(message: Message, state: FSMContext):
    await message.answer("Send the Telegram ID of the new admin:")
    await state.set_state(DeveloperStates.waiting_for_admin_id)
    await state.update_data(action="add")

@router.message(F.text == "➖ Remove Admin")
async def remove_admin_start(message: Message, state: FSMContext):
    await message.answer("Send the Telegram ID of the admin to remove:")
    await state.set_state(DeveloperStates.waiting_for_admin_id)
    await state.update_data(action="remove")

@router.message(DeveloperStates.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID. Please send a valid Telegram ID (numbers only).")
        return

    data = await state.get_data()
    action = data.get("action")

    admin_ids = await db.get_admin_ids()

    if action == "add":
        if admin_id in admin_ids:
            await message.answer(f"Admin {admin_id} is already in the list.")
        else:
            admin_ids.append(admin_id)
            await db.set_admin_ids(admin_ids)
            await message.answer(
                f"✅ Admin {admin_id} added successfully!",
                reply_markup=get_developer_panel_keyboard()
            )
    elif action == "remove":
        if admin_id not in admin_ids:
            await message.answer(f"Admin {admin_id} is not in the list.")
        else:
            admin_ids.remove(admin_id)
            await db.set_admin_ids(admin_ids)
            await message.answer(
                f"✅ Admin {admin_id} removed successfully!",
                reply_markup=get_developer_panel_keyboard()
            )

    await state.clear()

@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def manage_settings(message: Message):
    settings_data = await db.get_all_settings()

    settings_text = "⚙️ Current Settings:\n\n"
    for key, value in settings_data.items():
        settings_text += f"• {key}: {value}\n"

    if not settings_data:
        settings_text += "No settings configured yet."

    await message.answer(settings_text, reply_markup=get_settings_keyboard())

@router.callback_query(F.data == "set_admin_group")
async def set_admin_group(callback: CallbackQuery, state: FSMContext):
    setting_context[callback.from_user.id] = "admin_group_id"
    await callback.message.answer("Send the Admin Group ID (e.g., -1001234567890):")
    await state.set_state(DeveloperStates.waiting_for_setting_value)
    await callback.answer()

@router.callback_query(F.data == "set_info_channel")
async def set_info_channel(callback: CallbackQuery, state: FSMContext):
    setting_context[callback.from_user.id] = "info_channel_id"
    await callback.message.answer("Send the Info Channel ID (e.g., -1001234567890):")
    await state.set_state(DeveloperStates.waiting_for_setting_value)
    await callback.answer()

@router.callback_query(F.data == "set_limits")
async def set_limits(callback: CallbackQuery, state: FSMContext):
    setting_context[callback.from_user.id] = "withdrawal_limit"
    await callback.message.answer("Send the withdrawal limit (e.g., 100000):")
    await state.set_state(DeveloperStates.waiting_for_setting_value)
    await callback.answer()

@router.message(DeveloperStates.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext):
    user_id = message.from_user.id
    key = setting_context.get(user_id)

    if not key:
        await state.clear()
        return

    value = message.text.strip()
    await db.set_setting(key, value)

    await message.answer(
        f"✅ Setting '{key}' updated to: {value}",
        reply_markup=get_developer_panel_keyboard()
    )

    del setting_context[user_id]
    await state.clear()

@router.callback_query(F.data == "back_to_dev_panel")
async def back_to_dev_panel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        get_message("developer_panel", "ru"),
        reply_markup=get_developer_panel_keyboard()
    )
    await callback.answer()

@router.message(F.text.in_(["📥 Loglarni yuklash", "📥 Скачать логи"]))
async def download_logs(message: Message):
    log_file = "bot.log"

    if not os.path.exists(log_file):
        await message.answer("❌ Log file not found.")
        return

    try:
        document = FSInputFile(log_file)
        await message.answer_document(
            document=document,
            caption=f"📥 Bot Logs - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        logger.error(f"Error sending log file: {e}")
        await message.answer(f"❌ Error sending log file: {e}")

@router.message(F.text.in_(["💾 Backup yuklash", "💾 Скачать backup"]))
async def download_backup(message: Message):
    from config import settings

    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    try:
        await db.backup_database(backup_file)

        document = FSInputFile(backup_file)
        await message.answer_document(
            document=document,
            caption=f"💾 Database Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        os.remove(backup_file)
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        await message.answer(f"❌ Error creating backup: {e}")

@router.message(F.text.in_(["💳 Tranzaksiyalar", "💳 Транзакции"]))
async def view_transactions(message: Message):
    transactions = await db.get_all_transactions()

    if not transactions:
        await message.answer("📝 No transactions found.")
        return

    text = "💳 Recent Transactions:\n\n"
    for i, tx in enumerate(transactions[:20], 1):
        status_emoji = "✅" if tx.status == "completed" else "⏳" if tx.status == "pending" else "❌"
        text += (f"{i}. {status_emoji} ID: {tx.id}\n"
                f"   Driver: {tx.telegram_id}\n"
                f"   Amount: {tx.amount:,.2f}\n"
                f"   Status: {tx.status}\n"
                f"   Date: {tx.created_at}\n\n")

    await message.answer(text)

@router.message(F.text == "🔙 Back")
async def back_to_panel(message: Message):
    await message.answer(
        get_message("developer_panel", "ru"),
        reply_markup=get_developer_panel_keyboard()
    )

def register_handlers(dp):
    dp.include_router(router)
