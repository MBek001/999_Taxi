from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from utils import get_message
import logging

router = Router()
logger = logging.getLogger(__name__)

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    selecting_audience = State()

@router.message(F.text.in_(["📢 Xabar yuborish", "📢 Рассылка"]))
async def start_broadcast(message: Message, state: FSMContext):
    await message.answer(
        "Send the message you want to broadcast (text, photo, or both):",
        reply_markup={"remove_keyboard": True}
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(message=message)

    keyboard = {
        "keyboard": [
            [{"text": "All drivers"}],
            [{"text": "Active drivers"}, {"text": "Inactive drivers"}],
            [{"text": "Cancel"}]
        ],
        "resize_keyboard": True
    }

    await message.answer("Select audience:", reply_markup=keyboard)
    await state.set_state(BroadcastStates.selecting_audience)

@router.message(BroadcastStates.selecting_audience)
async def process_broadcast_audience(message: Message, state: FSMContext):
    audience = message.text

    if audience == "Cancel":
        await state.clear()
        await message.answer("Broadcast cancelled")
        return

    data = await state.get_data()
    broadcast_message = data.get("message")

    if audience == "All drivers":
        drivers = await db.get_all_drivers()
    elif audience == "Active drivers":
        drivers = await db.get_active_drivers()
    elif audience == "Inactive drivers":
        drivers = await db.get_inactive_drivers()
    else:
        await message.answer("Invalid audience")
        return

    from aiogram import Bot
    from config import settings
    bot = Bot(token=settings.BOT_TOKEN)

    success_count = 0
    fail_count = 0

    await message.answer(f"Starting broadcast to {len(drivers)} drivers...")

    for driver in drivers:
        try:
            if broadcast_message.photo:
                await bot.send_photo(
                    chat_id=driver.telegram_id,
                    photo=broadcast_message.photo[-1].file_id,
                    caption=broadcast_message.caption
                )
            else:
                await bot.send_message(
                    chat_id=driver.telegram_id,
                    text=broadcast_message.text
                )
            success_count += 1
        except Exception as e:
            logger.error(f"Error broadcasting to {driver.telegram_id}: {e}")
            fail_count += 1

    await message.answer(
        f"✅ Broadcast complete!\n\n"
        f"Success: {success_count}\n"
        f"Failed: {fail_count}"
    )
    await state.clear()

@router.message(F.text.in_(["📊 Statistika", "📊 Статистика"]))
async def show_statistics(message: Message):
    total_users = await db.get_user_count()
    total_drivers = await db.get_driver_count()
    pending_registrations = await db.get_pending_registrations_count()

    active_drivers = len(await db.get_active_drivers())
    inactive_drivers = len(await db.get_inactive_drivers())

    await message.answer(
        f"📊 Bot Statistics\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🚗 Total Drivers: {total_drivers}\n"
        f"📋 Pending Registrations: {pending_registrations}\n"
        f"🟢 Active Drivers: {active_drivers}\n"
        f"🔴 Inactive Drivers (7+ days): {inactive_drivers}"
    )

@router.message(F.text.in_(["📋 Kutilayotgan arizalar", "📋 Ожидающие заявки"]))
async def show_pending_registrations(message: Message):
    pending_count = await db.get_pending_registrations_count()
    await message.answer(
        f"📋 Pending Registrations: {pending_count}\n\n"
        f"New registrations will appear in the admin group for approval."
    )

def register_handlers(dp):
    dp.include_router(router)
