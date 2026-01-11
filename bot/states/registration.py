from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_driver_license_front = State()
    waiting_for_driver_license_back = State()
    waiting_for_tech_passport_front = State()
    waiting_for_tech_passport_back = State()

DOCUMENT_STEPS = [
    ("driver_license_front", "send_driver_license_front", "waiting_for_driver_license_back"),
    ("driver_license_back", "send_driver_license_back", "waiting_for_tech_passport_front"),
    ("tech_passport_front", "send_tech_passport_front", "waiting_for_tech_passport_back"),
    ("tech_passport_back", "send_tech_passport_back", None),
]
