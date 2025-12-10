import asyncio
import logging
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import UnauthorizedError

from handlers.handlers import (
    universal_handler,
    help_handler,
    search_handler,
    img_handler,
    today_handler,
    clear_handler,
)
from utils.utils import create_initial_folders


SESSION_FILE = "bot_session"


def load_keys():
    """
    Загружаем ключи из окружения.
    Ожидаем:
      API_ID
      API_HASH
      BOTTOKEN
    """

    load_dotenv()

    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOTTOKEN")

    if not api_id or not api_hash or not bot_token:
        raise RuntimeError(
            "❌ Не заданы переменные окружения: API_ID / API_HASH / BOTTOKEN"
        )

    return int(api_id), api_hash, bot_token


async def bot() -> None:
    """
    Главный цикл Telegram-бота с безопасным переподключением.
    """

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

            # Регистрируем обработчики
            client.add_event_handler(help_handler)
            client.add_event_handler(search_handler)
            client.add_event_handler(img_handler)
            client.add_event_handler(today_handler)
            client.add_event_handler(clear_handler)
            client.add_event_handler(universal_handler)

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
