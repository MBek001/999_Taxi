from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from database.models import User, Document
from utils import get_message
from bot.states import RegistrationStates
from bot.keyboards import get_share_contact_keyboard, get_start_registration_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    telegram_id = callback.from_user.id

    user = await db.get_user(telegram_id)

    if not user:
        user = User(telegram_id=telegram_id, language=lang)
        await db.create_user(user)
    else:
        await db.update_user(telegram_id, language=lang)

    await callback.message.edit_text(get_message("language_selected", lang))
    await callback.message.answer(
        get_message("share_contact", lang),
        reply_markup=get_share_contact_keyboard(lang)
    )
    await callback.answer()

@router.message(F.contact)
async def process_contact(message: Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        return

    telegram_id = message.from_user.id
    phone = message.contact.phone_number

    user = await db.get_user(telegram_id)
    if not user:
        user = User(telegram_id=telegram_id, phone=phone)
        await db.create_user(user)
    else:
        await db.update_user(telegram_id, phone=phone)

    lang = user.language if user else "uz"

    if user and user.registration_status == "approved":
        from bot.keyboards import get_driver_main_menu
        driver = await db.get_driver(telegram_id)
        name = driver.name if driver else message.from_user.first_name
        await message.answer(
            get_message("welcome_driver", lang, name=name),
            reply_markup=get_driver_main_menu(lang)
        )
    else:
        await message.answer(
            get_message("welcome_new_driver", lang),
            reply_markup=get_start_registration_keyboard(lang)
        )

@router.message(F.text.in_([
    "📝 Ro'yxatdan o'tish",
    "📝 Начать регистрацию"
]))
async def start_registration(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        return

    lang = user.language

    await db.update_user(telegram_id, registration_status="in_progress")
    await db.delete_documents(telegram_id)

    await state.set_state(RegistrationStates.waiting_for_driver_license_front)
    await message.answer(
        get_message("registration_started", lang),
        reply_markup={"remove_keyboard": True}
    )
    await message.answer(get_message("send_driver_license_front", lang))

@router.message(RegistrationStates.waiting_for_driver_license_front)
async def process_driver_license_front(message: Message, state: FSMContext):
    await process_document(message, state, "driver_license_front",
                          RegistrationStates.waiting_for_driver_license_back,
                          "send_driver_license_back")

@router.message(RegistrationStates.waiting_for_driver_license_back)
async def process_driver_license_back(message: Message, state: FSMContext):
    await process_document(message, state, "driver_license_back",
                          RegistrationStates.waiting_for_tech_passport_front,
                          "send_tech_passport_front")

@router.message(RegistrationStates.waiting_for_tech_passport_front)
async def process_tech_passport_front(message: Message, state: FSMContext):
    await process_document(message, state, "tech_passport_front",
                          RegistrationStates.waiting_for_tech_passport_back,
                          "send_tech_passport_back")

@router.message(RegistrationStates.waiting_for_tech_passport_back)
async def process_tech_passport_back(message: Message, state: FSMContext):
    await process_document(message, state, "tech_passport_back", None, None, is_last=True)

async def process_document(message: Message, state: FSMContext, doc_type: str,
                          next_state, next_message_key: str, is_last: bool = False):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    lang = user.language if user else "uz"

    if not message.photo:
        await message.answer(get_message("document_invalid", lang))
        return

    photo = message.photo[-1]
    file_id = photo.file_id

    doc = Document(
        telegram_id=telegram_id,
        document_type=doc_type,
        file_id=file_id
    )
    await db.save_document(doc)

    await message.answer(get_message("document_accepted", lang))

    if is_last:
        await state.clear()
        await db.update_user(telegram_id, registration_status="pending")
        await send_to_admin_group(telegram_id, user)
        await message.answer(get_message("registration_completed", lang))
    else:
        await state.set_state(next_state)
        await message.answer(get_message(next_message_key, lang))

async def send_to_admin_group(telegram_id: int, user: User):
    from aiogram import Bot
    from config import settings
    from bot.keyboards import get_approval_keyboard

    admin_group_id = await db.get_setting("admin_group_id")

    if not admin_group_id:
        logger.error("Admin group ID not configured")
        return

    bot = Bot(token=settings.BOT_TOKEN)

    documents = await db.get_documents(telegram_id)

    text = f"📋 New Driver Registration\n\n"
    text += f"👤 Name: {user.telegram_id}\n"
    text += f"📱 Phone: {user.phone}\n"
    text += f"🆔 Telegram ID: {telegram_id}\n\n"
    text += f"📄 Documents: {len(documents)}"

    try:
        msg = await bot.send_message(
            chat_id=int(admin_group_id),
            text=text,
            reply_markup=get_approval_keyboard(telegram_id)
        )

        for doc in documents:
            await bot.send_photo(
                chat_id=int(admin_group_id),
                photo=doc.file_id,
                caption=f"📄 {doc.document_type}"
            )

    except Exception as e:
        logger.error(f"Error sending to admin group: {e}")

def register_handlers(dp):
    dp.include_router(router)
