from src.config.bot_config import BOT_TOKEN
import re

def validate_token(token: str) -> bool:
    if not isinstance(token, str):
        return False
    
    # Паттерн для проверки токена
    pattern = r'^\d+:[\w-]{35}$'
    
    if not re.match(pattern, token):
        print(f"Токен не соответствует формату. Должен быть в формате 'число:35символов'")
        return False
    
    print(f"Токен валидный: {token}")
    return True

if __name__ == "__main__":
    print(f"Загруженный токен: {BOT_TOKEN}")
    validate_token(BOT_TOKEN) 