import re
import logging
import os
import uuid

from telethon import events, Button
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from telethon.errors import FloodWaitError

# ✅ УБРАН `src.`
from functions.additional_func import (
    search,
    generate_image,
    analyze_image_with_gpt,
)

from functions.chat_func import (
    process_and_send_mess,
    start_and_check,
    get_openai_response,
)

from utils.utils import get_date_time


# =====================================================
# SETTINGS
# =====================================================

TRIGGERS = [
    "душнилла",
    "бот",
    "@dushnillabot",
    "душ",
    "душик",
    "душнила",
    "душечка",
    "dush",
    "dushik",
    "dushnila",
    "dushnilla",
]

SEARCH_TRIGGERS = [
    "найди в интернете",
    "найди",
    "поиск",
]

HELP_TEXT = """
🤖 Ассистент сети зоомагазинов «Четыре Лапы» и не только! 🐾

Команды:
/search <запрос> — поиск в интернете
/img <описание> — генерация изображения
/today — текущая дата
/clear — очистка истории
/help — справка

Триггеры в группах:
«найди в интернете …»
или
«поиск …»

ℹ️ Напишите «помощь» — покажу возможности бота.
"""


def help_keyboard():
    return [[Button.inline("ℹ️ Помощь", b"HELP")]]


# =====================================================
# HELP
# =====================================================

@events.register(events.CallbackQuery(data=b"HELP"))
async def help_callback(event):
    await event.respond(
        HELP_TEXT,
        buttons=help_keyboard(),
        link_preview=False,
    )


@events.register(events.NewMessage(pattern=r"/start"))
@events.register(events.NewMessage(pattern=r"/help"))
async def help_handler(event):
    await event.reply(
        HELP_TEXT,
        buttons=help_keyboard(),
        link_preview=False,
    )
    raise events.StopPropagation


# =====================================================
# COMMANDS
# =====================================================

@events.register(events.NewMessage(pattern=r"/search"))
@events.register(events.NewMessage(pattern=r"/поиск"))
async def search_handler(event):
    query = re.sub(
        r"/(search|поиск)",
        "",
        event.raw_text,
        flags=re.IGNORECASE,
    ).strip()

    await process_and_send_mess(
        event,
        await search(query)
    )
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/clear"))
async def clear_handler(event):
    await start_and_check(event, "Очистка истории", event.chat_id)
    await process_and_send_mess(event, "🗑 История диалога очищена!")
    raise events.StopPropagation


# =====================================================
# IMAGE GENERATION (/img)
# =====================================================

@events.register(events.NewMessage(pattern=r"/img"))
async def img_handler(event):
    if event.out:
        return

    try:
        prompt = event.raw_text.replace("/img", "").strip()

        if not prompt:
            await event.respond("Укажите описание изображения после команды /img")
            return

        # ===== Получаем БАЙТЫ PNG от OpenAI
        image_bytes = await generate_image(prompt)

        if not image_bytes or len(image_bytes) < 1000:
            raise ValueError("Invalid image bytes result")

        # ===== Сохраняем во временный файл
        filename = f"/tmp/{uuid.uuid4().hex}.png"

        with open(filename, "wb") as f:
            f.write(image_bytes)

        # ===== Отправка гарантированным методом Telethon
        await event.client.send_file(
            event.chat_id,
            file=filename,
            caption=f"🖼 Генерация изображения:\n{prompt}",
        )

        # ===== Чистим временный файл
        try:
            os.remove(filename)
        except Exception:
            pass

    except Exception:
        logging.exception("IMG ERROR")
        await event.respond("❌ Ошибка генерации изображения")


# =====================================================
# TODAY
# =====================================================

@events.register(events.NewMessage(pattern=r"/today"))
async def today_handler(event):
    await process_and_send_mess(
        event,
        f"📅 Сегодня: {get_date_time()}",
    )
    raise events.StopPropagation


# =====================================================
# MEDIA FILTER
# =====================================================

async def should_process_image(event, text_lower: str) -> bool:
    """
    Логика обработки изображений:
    — Личка -> ВСЕГДА
    — Группы:
        • если ответ на бота
        • если упоминание бота
        • если триггер в тексте
    """

    if event.is_private:
        return True

    # Проверка ответа боту
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id == (await event.client.get_me()).id:
            return True

    # Упоминание бота
    if "@dushnillabot" in text_lower:
        return True

    # Триггеры
    if any(t in text_lower for t in TRIGGERS):
        return True

    return False


# =====================================================
# MAIN HANDLER
# =====================================================

@events.register(events.NewMessage)
async def universal_handler(event):
    try:
        if event.out:
            return

        text = (event.raw_text or "").strip()
        text_lower = text.lower()

        if not text:
            return

        if text.startswith("/"):
            return

        # -------- help trigger ----------
        if text_lower.strip() == "помощь":
            await process_and_send_mess(event, HELP_TEXT)
            raise events.StopPropagation

        # -------- search trigger ----------
        for phrase in SEARCH_TRIGGERS:
            if phrase in text_lower:
                query = text_lower.replace(phrase, "").strip()
                await process_and_send_mess(event, await search(query))
                raise events.StopPropagation

        # -------------------------------------------------
        # MEDIA (VISION)
        # -------------------------------------------------
        if event.message.media:
            allowed = await should_process_image(event, text_lower)
            if not allowed:
                return

            media_bytes = await event.client.download_media(
                event.message,
                file=bytes,
            )

            answer = await analyze_image_with_gpt(
                media_bytes,
                text,
            )

            await process_and_send_mess(event, answer)
            raise events.StopPropagation

        # -------------------------------------------------
        # GROUP FILTER
        # -------------------------------------------------
        if not event.is_private and not any(t in text_lower for t in TRIGGERS):
            return

        # typing indicator
        try:
            await event.client(
                SetTypingRequest(
                    peer=event.chat_id,
                    action=SendMessageTypingAction(),
                )
            )
        except FloodWaitError:
            pass
        except Exception:
            logging.debug("Typing indicator failed")

        # -------------------------------------------------
        # LLM PIPELINE
        # -------------------------------------------------
        filename, history = await start_and_check(
            event,
            text,
            event.chat_id,
        )

        answer = await get_openai_response(history, filename)

        await process_and_send_mess(event, answer)

        raise events.StopPropagation

    except events.StopPropagation:
        return

    except Exception:
        logging.exception("GLOBAL HANDLER ERROR")
        await event.reply("⚠️ Ошибка обработки сообщения")
