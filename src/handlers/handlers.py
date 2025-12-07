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

from src.utils import get_date_time


# =======================
# НАСТРОЙКИ
# =======================

TRIGGERS = [
    "душнилла",
    "бот",
    "@dushnillabot",
    "душ",
    "душик",
    "душнила",
    "душечка",
    "du sh",
    "dush",
    "dushik",
    "dushnila",
    "dushnilla"
]


# =======================
# UNIVERSAL HANDLER
# =======================

@events.register(events.NewMessage)
async def universal_handler(event):
    try:
        # не отвечаем на свои
        if event.out:
            return

        # ============================
        # Работа с фото и файлами
        # ============================
        if event.message.media:

            try:
                media_bytes = await event.client.download_media(
                    event.message,
                    file=bytes
                )

                if not media_bytes:
                    await event.reply("⚠️ Я получил файл, но не смог его скачать.")
                    return

                # Уведомляем что анализируем
                await event.reply("👀 Файл получен — анализирую...")

                caption = (event.message.text or "").strip() or None

                answer = await analyze_image_with_gpt(
                    image_bytes=media_bytes,
                    user_prompt=caption
                )

                await event.reply(answer)

            except Exception as e:
                logging.exception("Ошибка обработки media")
                await event.reply("❌ Не получилось обработать файл 😔")

            raise events.StopPropagation

        # ============================
        # Работа с текстом
        # ============================

        text = (event.raw_text or "").strip()
        if not text:
            return

        text_lower = text.lower()
        is_private = event.is_private

        # Командные хендлеры отдельно
        if text_lower.startswith((
            "/search",
            "/bash",
            "/clear",
            "/img",
            "/today"
        )):
            return

        # В группах отвечаем только по триггеру
        triggered = any(t in text_lower for t in TRIGGERS)

        if not is_private and not triggered:
            return

        # Убираем триггер из запроса
        cleaned_text = text

        if not is_private:
            pattern = r"^(?:" + "|".join(map(re.escape, TRIGGERS)) + r")\s*[:,—–\- ]*"
            cleaned_text = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE
            ).strip()

            if not cleaned_text:
                cleaned_text = text

        # Показ индикатора typing
        await event.client(
            SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction(),
            )
        )

        # ============================
        # GPT обработка
        # ============================

        filename, prompt = await start_and_check(
            event=event,
            user_text=cleaned_text,
            chat_id=event.chat_id
        )

        gpt_response = get_openai_response(
            prompt=prompt,
            filename=filename
        )

        await process_and_send_mess(
            event,
            gpt_response,
        )

    except Exception as e:
        logging.exception("GLOBAL HANDLER ERROR")
        await event.reply("⚠️ Ой, что-то сломалось… Попробуй ещё раз.")

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
    filename, _ = await start_and_check(
        event=event,
        user_text="",
        chat_id=event.chat_id,
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
    await event.reply(f"📅 Сегодня: {get_date_time()}")
    raise events.StopPropagation
