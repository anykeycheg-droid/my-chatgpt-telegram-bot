import logging
import os

import openai
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UnauthorizedError

# Только нужные обработчики
from src.handlers.handlers import universal_handler, search_handler, bash_handler, clear_handler

def load_keys():
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.organization = os.getenv("OPENAI_ORG", None)
    
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOTTOKEN")
    return api_id, api_hash, bot_token

async def bot() -> None:
    while True:
        try:
            api_id, api_hash, bot_token = load_keys()
            client = await TelegramClient(None, api_id, api_hash).start(bot_token=bot_token)
            logging.info("Бот успешно запущен!")

            # Регистрируем только то, что реально используется
            client.add_event_handler(universal_handler)
            client.add_event_handler(search_handler)
            client.add_event_handler(bash_handler)
            client.add_event_handler(clear_handler)

            print("Душнилла онлайн — пиши мне!")
            await client.run_until_disconnected()

        except UnauthorizedError:
            logging.error("Неправильный BOTTOKEN или API_ID/API_HASH")
            break
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await asyncio.sleep(10)