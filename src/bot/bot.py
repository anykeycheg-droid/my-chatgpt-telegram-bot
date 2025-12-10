import asyncio
import logging
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import UnauthorizedError

# ✅ ИМПОРТЫ БЕЗ `src.`
from handlers.handlers import (
    universal_handler,
    help_handler,
    search_handler,
    img_handler,
    today_handler,
    clear_handler,
)

from utils.utils import create_initial_folders


# ======================
# SETTINGS
# ======================

SESSION_FILE = "bot_session"


# ======================
# ENV LOADING
# ======================

def load_keys():
    load_dotenv()

    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    # Унификация имени токена
    bot_token = os.getenv("BOT_TOKEN") or os.getenv("BOTTOKEN")

    if not api_id or not api_hash or not bot_token:
        raise RuntimeError(
            "❌ Не заданы переменные окружения: "
            "API_ID / API_HASH / BOT_TOKEN"
        )

    return int(api_id), api_hash, bot_token


# ======================
# MAIN BOT LOOP
# ======================

async def bot() -> None:
    """
    Safe main bot loop with reconnect logic
    """

    create_initial_folders()

    while True:
        client = None

        try:
            api_id, api_hash, bot_token = load_keys()

            client = TelegramClient(SESSION_FILE, api_id, api_hash)
            await client.start(bot_token=bot_token)

            logging.info("🐾 Ассистент сети «Четыре Лапы» успешно запущен")

            # регистрируем handlers
            client.add_event_handler(help_handler)
            client.add_event_handler(search_handler)
            client.add_event_handler(img_handler)
            client.add_event_handler(today_handler)
            client.add_event_handler(clear_handler)
            client.add_event_handler(universal_handler)

            await client.run_until_disconnected()

        except UnauthorizedError:
            logging.critical(
                "❌ Telegram Unauthorized — проверь BOT_TOKEN / API_ID / API_HASH"
            )
            break

        except Exception:
            logging.exception("⚠ Критическая ошибка в цикле бота")
            await asyncio.sleep(10)

        finally:
            if client:
                await client.disconnect()
                logging.info("🔌 Telegram client disconnected — reconnect")
