import hmac
import hashlib
import json
from urllib.parse import parse_qs
from fastapi import Header, HTTPException, Depends
from typing import Dict, Any
from ..config import settings

def validate_telegram_data(init_data: str) -> Dict[str, Any]:
    """
    Проверяет подпись данных от Telegram Mini App.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="Init data missing")

    try:
        parsed_data = {k: v[0] for k, v in parse_qs(init_data).items()}
        received_hash = parsed_data.pop("hash", None)
        
        if not received_hash:
            raise HTTPException(status_code=401, detail="Hash missing")

        # Формируем строку данных в алфавитном порядке
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # Вычисляем секретный ключ
        secret_key = hmac.new(
            b"WebAppData", 
            settings.BOT_TOKEN.encode(), 
            hashlib.sha256
        ).digest()

        # Вычисляем финальный хеш
        calculated_hash = hmac.new(
            secret_key, 
            data_check_string.encode(), 
            hashlib.sha256
        ).hexdigest()

        if calculated_hash != received_hash:
            raise HTTPException(status_code=401, detail="Invalid hash")

        # Извлекаем данные пользователя
        user_data = json.loads(parsed_data.get("user", "{}"))
        return user_data
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")

async def get_current_user(x_telegram_init_data: str = Header(None)):
    """
    Зависимость FastAPI для защиты роутов.
    """
    return validate_telegram_data(x_telegram_init_data)
