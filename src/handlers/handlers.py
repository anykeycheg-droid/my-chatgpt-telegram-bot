import re
import logging

from telethon import events, Button
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

from src.functions.additional_func import (
    search,
    generate_image,
    analyze_image_with_gpt,
)

from src.functions.chat_func import (
    process_and_send_mess,
    start_and_check,
    get_openai_response,
)

from src.utils.utils import get_date_time


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
    "du sh",
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
🤖 Ассистент сети зоомагазинов «Четыре Лапы»  и не только! 🐾

Команды:
/search <запрос> — поиск в интернете
/поиск <запрос>
/img <описание> — генерация изображения
/today — текущая дата
/clear — очистка истории
/help — справка

В группах можно писать:
«найди в интернете …»
или
«поиск …»

ℹ️ Просто напишите «помощь» — и я подскажу, что умею.

👨‍💼 Контакт:
Дмитрий Лесных — @anykeycheg
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

    await event.reply(await search(query))
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/clear"))
async def clear_handler(event):
    await start_and_check(
        event,
        "Очистка истории",
        event.chat_id,
    )

    await event.reply("🗑 История диалога очищена!")
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/img"))
async def img_handler(event):
    if event.out:
        return

    try:
        prompt = event.raw_text.replace("/img", "").strip()

        if not prompt:
            await event.respond("Пожалуйста, укажите описание изображения после команды /img")
            return

        image_bytes = await generate_image(prompt)

        await event.respond(
            message=f"🖼 Генерация по запросу:\n{prompt}",
            file=image_bytes
        )

    except Exception as e:
        logging.error("IMG ERROR", exc_info=True)
        await event.respond("❌ Не удалось создать изображение.")



@events.register(events.NewMessage(pattern=r"/today"))
async def today_handler(event):
    await event.reply(
        f"📅 Сегодня: {get_date_time()}"
    )
    raise events.StopPropagation


# =====================================================
# MAIN HANDLER
# =====================================================

@events.register(events.NewMessage)
async def universal_handler(event):
    try:
        if event.out:
            return

        # игнор команд — чтобы не было дублей
        if event.raw_text and event.raw_text.startswith("/"):
            return

        # =============================
        # MEDIA (VISION)
        # =============================

        if event.message.media:
            media_bytes = await event.client.download_media(
                event.message,
                file=bytes,
            )

            answer = await analyze_image_with_gpt(
                media_bytes,
                (event.message.text or "").strip(),
            )

            await event.reply(answer)
            raise events.StopPropagation

        # =============================
        # TEXT
        # =============================

        text = (event.raw_text or "").strip()
        if not text:
            return

        text_lower = text.lower()

        # -------- help trigger ----------
        if text_lower == "помощь" or " помощь" in text_lower:
            await event.reply(
                HELP_TEXT,
                buttons=help_keyboard(),
                link_preview=False,
            )
            raise events.StopPropagation

        # -------- search trigger ----------
        for phrase in SEARCH_TRIGGERS:
            if phrase in text_lower:
                query = text_lower.replace(phrase, "").strip()
                await event.reply(await search(query))
                raise events.StopPropagation

        # -------- group trigger ----------
        if not event.is_private and not any(t in text_lower for t in TRIGGERS):
            return

        await event.client(
            SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction(),
            )
        )

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
        return
