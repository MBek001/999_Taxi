from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import db
from database.models import User
from config import settings
from utils import get_message
from bot.keyboards import (
    get_language_keyboard,
    get_driver_main_menu,
    get_admin_panel_keyboard,
    get_developer_panel_keyboard
)

router = Router()

async def determine_role(telegram_id: int) -> str:
    if telegram_id in settings.DEVELOPER_IDS:
        return "developer"

    admin_ids = await db.get_admin_ids()
    if telegram_id in admin_ids:
        return "admin"

    return "driver"

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    telegram_id = message.from_user.id
    role = await determine_role(telegram_id)

    user = await db.get_user(telegram_id)

    if not user:
        if role == "developer":
            user = User(
                telegram_id=telegram_id,
                role="developer",
                language="ru",
                registration_status="approved"
            )
            await db.create_user(user)
            await message.answer(
                get_message("developer_panel", "ru"),
                reply_markup=get_developer_panel_keyboard("ru")
            )
            return

        if role == "admin":
            user = User(
                telegram_id=telegram_id,
                role="admin",
                language="ru",
                registration_status="approved"
            )
            await db.create_user(user)
            await message.answer(
                get_message("admin_panel", "ru"),
                reply_markup=get_admin_panel_keyboard("ru")
            )
            return

        await message.answer(
            get_message("select_language"),
            reply_markup=get_language_keyboard()
        )
        return

    if role != user.role:
        await db.update_user(telegram_id, role=role)

    lang = user.language

    if role == "developer":
        await message.answer(
            get_message("developer_panel", lang),
            reply_markup=get_developer_panel_keyboard(lang)
        )
    elif role == "admin":
        await message.answer(
            get_message("admin_panel", lang),
            reply_markup=get_admin_panel_keyboard(lang)
        )
    else:
        if user.registration_status == "approved":
            driver = await db.get_driver(telegram_id)
            name = driver.name if driver else message.from_user.first_name
            await message.answer(
                get_message("welcome_driver", lang, name=name),
                reply_markup=get_driver_main_menu(lang)
            )
        else:
            await message.answer(
                get_message("welcome_new_driver", lang),
                reply_markup=get_language_keyboard()
            )

def register_handlers(dp):
    dp.include_router(router)
