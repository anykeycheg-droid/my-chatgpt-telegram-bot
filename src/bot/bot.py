import asyncio
import logging
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UnauthorizedError

from src.handlers.handlers import universal_handler
from src.utils.utils import create_initial_folders   # ✅ ПРАВИЛЬНЫЙ ИМПОРТ


# ======================
# SETTINGS
# ======================

SESSION_FILE = "bot_session"


# ======================
# ENV LOADING
# ======================

def load_keys():
    load_dotenv()

    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOTTOKEN")

    if not all([api_id, api_hash, bot_token]):
        raise RuntimeError("❌ Не заданы переменные окружения Telegram API")

    return api_id, api_hash, bot_token


# ======================
# MAIN BOT LOOP
# ======================

async def bot() -> None:
    """
    Main telegram bot loop with safe reconnect
    """

    # ✅ создаём папки логов и истории диалогов
    create_initial_folders()

    while True:
        try:
            api_id, api_hash, bot_token = load_keys()

            client = TelegramClient(
                SESSION_FILE,
                api_id,
                api_hash,
            )

            await client.start(bot_token=bot_token)

            logging.info("🐾 Ассистент сети «Четыре Лапы — и не только» запущен!")

            # ✅ Единственный обработчик
            client.add_event_handler(universal_handler)

            # ✅ блокировка до отключения
            await client.run_until_disconnected()

        except UnauthorizedError:
            logging.critical(
                "❌ Telegram отказал в доступе. "
                "Проверь BOTTOKEN / API_ID / API_HASH"
            )
            break

        except Exception as e:
            logging.exception(
                f"⚠ Критическая ошибка bot loop: {e}"
            )
            await asyncio.sleep(10)
