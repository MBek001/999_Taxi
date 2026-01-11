import re

def validate_phone(phone: str) -> bool:
    cleaned = re.sub(r'\D', '', phone)
    return len(cleaned) >= 9

def normalize_card_number(card: str) -> str:
    digits = re.sub(r'\D', '', card)
    return digits[:16] if len(digits) >= 16 else digits

def is_valid_card_number(card: str) -> bool:
    normalized = normalize_card_number(card)
    return len(normalized) == 16
