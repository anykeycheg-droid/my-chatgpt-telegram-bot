import asyncio
import logging

from bot.bot import client, start_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logging.info("🐾 Старт Telegram-ассистента «Четыре Лапы — и не только»")

if __name__ == "__main__":
    # Асинхронный старт клиента
    asyncio.run(start_bot())

    # Блокирующий цикл Telethon
    client.run_until_disconnected()
