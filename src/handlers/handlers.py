import os
import logging
from telethon import events
from src.utils.utils import LOG_PATH, create_initial_folders, get_date_time
from src.bot.bot import ALLOW_USERS

create_initial_folders()

@events.register(events.NewMessage)
async def universal_handler(event):
    if event.out:
        return

    if ALLOW_USERS and event.chat_id not in ALLOW_USERS:
        return

    # ==== ОБРАБОТКА МЕДИА ====
    if getattr(event.message, "media", None):
        try:
            media_folder = f"{LOG_PATH}media"
            os.makedirs(media_folder, exist_ok=True)

            path = await event.client.download_media(
                event.message,
                file=f"{media_folder}/{event.id}"
            )

            if path:
                await event.client.send_file(event.chat_id, path, caption="✅ Файл принят")
            else:
                bio = await event.client.download_media(event.message, file=bytes)
                await event.client.send_file(event.chat_id, bio, caption="✅ Файл принят")

            raise events.StopPropagation

        except Exception:
            logging.exception("Ошибка при обработке медиа")
            await event.reply("❌ Ошибка при работе с изображением")
            raise events.StopPropagation


    # ==== ОБРАБОТКА ТЕКСТА ====
    text = (event.message.message or "").strip()
    if not text:
        return

    if text.lower() == "/today":
        await event.reply(f"📅 Сейчас: {get_date_time()}")
        raise events.StopPropagation

    # далее твоя стандартная логика GPT-ответов
