import asyncio
import logging

from bot.bot import bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logging.info("🐾 Старт Telegram-ассистента «Четыре Лапы — и не только»")


if __name__ == "__main__":
    asyncio.run(bot())
