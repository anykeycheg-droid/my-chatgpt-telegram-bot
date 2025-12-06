import logging
import os
from typing import Tuple

import google.generativeai as genai
import openai
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UnauthorizedError

# Теперь импортируем только то, что реально существует после наших правок
from src.handlers.handlers import (
    universal_handler,
    search_handler,
    bash_handler,
    clear_handler,
)

# Если у тебя есть отдельный файл с security_check — оставь, если нет — можно убрать
# (мы уже проверяем ALLOW_USERS внутри universal_handler)
# from src.handlers.handlers import security_check


def load_keys() -> Tuple[str, int, str]:
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.organization = os.getenv("OPENAI_ORG", None)  # может быть пустым
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOTTOKEN")
    return api_id, api_hash, bot_token


async def bot() -> None:
    while True:
        try:
            api_id, api_hash, bot_token = load_keys()

            client = await TelegramClient(None, api_id, api_hash).start(bot_token=bot_token)
            logging.info("Successfully initiate bot")

            # === Регистрируем только нужные обработчики ===

            # Основной чат (личка + группы по триггерам)
            client.add_event_handler(universal_handler)

            # Команды
            client.add_event_handler(search_handler)
            client.add_event_handler(bash_handler)
            client.add_event_handler(clear_handler)

            # Защита по ALLOW_USERS (если хочешь оставить отдельно)
            # client.add_event_handler(security_check)

            logging.info("Все обработчики зарегистрированы. Бот запущен!")
            print("Бот Душнилла работает — пиши мне в Telegram!")

            await client.run_until_disconnected()

        except UnauthorizedError:
            logging.error("Ошибка авторизации. Проверь BOTTOKEN, API_ID и API_HASH")
            break
        except Exception as e:
            logging.error(f"Критическая ошибка: {e}")
            await asyncio.sleep(10)  # пауза перед перезапуском