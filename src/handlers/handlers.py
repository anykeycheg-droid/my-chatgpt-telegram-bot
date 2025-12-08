import re
import logging

from telethon import events, Button
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

SEARCH_TRIGGERS = ["найди в интернете", "найди", "поиск"]


HELP_TEXT = """
🤖 Ассистент сети зоомагазинов «Четыре Лапы» — и не только!

Команды:
/search <запрос> — поиск в интернете
/поиск <запрос>
/img <описание> — генерация изображения
/today — текущая дата
/clear — очистка истории
/bash <cmd> — shell-команда
/help — справка

Пиши:
«найди в интернете …»
или
«поиск …»

👨‍💼 Вопросы:
Дмитрий Лесных — @anykeycheg
"""

def help_keyboard():
    return [[Button.inline("ℹ Помощь", b"HELP")]]


@events.register(events.CallbackQuery(data=b"HELP"))
async def help_cb(event):
    await event.respond(HELP_TEXT, buttons=help_keyboard(), link_preview=False)


@events.register(events.NewMessage(pattern=r"/start"))
@events.register(events.NewMessage(pattern=r"/help"))
async def help_cmd(event):
    await event.reply(HELP_TEXT, buttons=help_keyboard(), link_preview=False)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/search"))
@events.register(events.NewMessage(pattern=r"/поиск"))
async def search_cmd(event):
    q = re.sub(r"/(search|поиск)", "", event.raw_text, flags=re.IGNORECASE).strip()
    await event.reply(await search(q))
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/bash"))
async def bash_cmd(event):
    await event.reply(await bash(event.raw_text.replace("/bash", "").strip()))
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/clear"))
async def clear_cmd(event):
    await start_and_check(event, "Очистка истории", event.chat_id)
    await event.reply("🗑 История диалога очищена")
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/img"))
async def img_cmd(event):
    await event.reply(await generate_image(event.raw_text.replace("/img", "").strip()))
    raise events.StopPropagation


@events.register(events.NewMessage(pattern=r"/today"))
async def today_cmd(event):
    await event.reply(f"📅 Сегодня: {get_date_time()}")
    raise events.StopPropagation


@events.register(events.NewMessage)
async def universal(event):

    try:
        if event.message.media:
            b = await event.client.download_media(event.message, file=bytes)
            a = await analyze_image_with_gpt(b, (event.message.text or "").strip())
            await event.reply(a)
            raise events.StopPropagation

        text = (event.raw_text or "").strip()
        tl = text.lower()

        for p in SEARCH_TRIGGERS:
            if p in tl:
                q = tl.replace(p, "").strip()
                await event.reply(await search(q))
                raise events.StopPropagation

        if not event.is_private and not any(t in tl for t in TRIGGERS):
            return

        await event.client(SetTypingRequest(peer=event.chat_id, action=SendMessageTypingAction()))

        fn, hist = await start_and_check(event, text, event.chat_id)
        a = await get_openai_response(hist, fn)

        await process_and_send_mess(event, a)

        raise events.StopPropagation

    except events.StopPropagation:
        return

    except Exception:
        logging.exception("GLOBAL ERROR")
        await event.reply("⚠ Ошибка обработки сообщения")
