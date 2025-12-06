import logging
import os
from typing import Tuple

import google.generativeai as genai
import openai
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UnauthorizedError

# Импортируем только то, что используется
from src.handlers.handlers import universal_handler, search_handler, bash_handler, clear_handler

def load_keys() -> Tuple[str, int, str]:
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.organization = os.getenv("OPENAI_ORG", None)
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

            # Регистрируем обработчики
            client.add_event_handler(universal_handler)
            client.add_event_handler(search_handler)
            client.add_event_handler(bash_handler)
            client.add_event_handler(clear_handler)

            logging.info("Все обработчики зарегистрированы. Бот запущен!")
            print("Бот Душнилла работает — пиши мне в Telegram!")

            await client.run_until_disconnected()

        except UnauthorizedError:
            logging.error("Ошибка авторизации. Проверь BOTTOKEN, API_ID и API_HASH")
            break
        except Exception as e:
            logging.error(f"Критическая ошибка: {e}")
            await asyncio.sleep(10)  # пауза перед перезапуском