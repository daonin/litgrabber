from .config import load_config

_config = load_config()
ALLOWED_IDS = set(_config.get("allowed_telegram_ids", []))

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_IDS 