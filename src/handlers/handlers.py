import os
import re
import logging

from telethon import events
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

from src.functions.additional_func import (
    bash,
    search,
    generate_image,
    analyze_image_with_gpt,
)

from src.functions.chat_func import (
    process_and_send_mess,
    start_and_check,
    get_openai_response,
)

from src.utils import get_date_time, create_initial_folders


# =======================
# НАСТРОЙКИ
# =======================

TRIGGERS = [
    "душнилла",
    "бот",
    "@DushnillaBot",
    "душ",
    "душик",
    "душнила",
    "душечка",
    "дух",
    "dush",
    "dushik",
    "dushnila",
    "dushnilla"
]

create_initial_folders()


# =======================
# UNIVERSAL HANDLER
# =======================

@events.register(events.NewMessage)
async def universal_handler(event):
    try:
        # Не отвечаем на свои сообщения
        if event.out:
            return

        # ==== 1. Media (фото, файлы) ====
        if getattr(event.message, "media", None):
            try:
                media_bytes = await event.client.download_media(
                    event.message,
                    file=bytes
                )

                if media_bytes:
                    await event.client.send_file(
                        event.chat_id,
                        media_bytes,
                        caption="✅ Файл принят, анализирую…",
                    )

                    caption = (event.message.message or "").strip()
                    answer = await analyze_image_with_gpt(
                        media_bytes,
                        caption or None
                    )

                    await event.reply(answer)

                else:
                    await event.reply(
                        "Я получил файл, но не смог его скачать 😔"
                    )

            except Exception:
                logging.exception(
                    "Ошибка обработки media в universal_handler"
                )
                await event.reply("Не получилось обработать файл 😔")

            raise events.StopPropagation

        # ==== 2. Текстовые сообщения ====
        text = (event.message.message or "").strip()
        if not text:
            return

        text_lower = text.lower()
        is_private = event.is_private

        # ---- команды идут отдельными хэндлерами ----
        if text_lower.startswith(
            ("/search", "/bash", "/clear", "/img", "/today")
        ):
            return

        # ---- В группах работаем только с триггером ----
        triggered = any(word in text_lower for word in TRIGGERS)
        if not is_private and not triggered:
            return

        # ---- чистим триггер ----
        clean_text = text

        if not is_private:
            escaped_triggers = [re.escape(t) for t in TRIGGERS]
            pattern = r"^(?:" + "|".join(escaped_triggers) + r")\s*[:,\\\-–— ]*"
            clean_text = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE
            ).strip()

            if not clean_text:
                clean_text = text

        # ==== typing ====
        await event.client(
            SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction(),
            )
        )

        # ==== GPT обработка ====
        filename, prompt = await start_and_check(
            event,
            clean_text,
            event.chat_id
        )

        response = get_openai_response(
            prompt,
            filename
        )

        await process_and_send_mess(
            event,
            response,
        )

    except Exception as e:
        logging.exception("Ошибка universal_handler")
        await event.reply("Ой, что-то сломалось… Попробуй ещё раз")

    raise events.StopPropagation


# =======================
# COMMAND HANDLERS
# =======================

@events.register(events.NewMessage(pattern=r"/search"))
async def search_handler(event):
    await search(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/bash"))
async def bash_handler(event):
    await bash(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/clear"))
async def clear_handler(event):
    # очищаем историю диалога
    filename, _ = await start_and_check(
        event,
        "",
        event.chat_id,
        clear=True,
    )

    if filename:
        await event.reply("🗑 История диалога очищена!")

    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/img"))
async def img_handler(event):
    await generate_image(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/today"))
async def today_handler(event):
    await event.reply(
        f"📅 Сейчас: {get_date_time()}"
    )
    raise events.StopPropagation
