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
    "dushnilla",
]

SEARCH_TRIGGERS = [
    "найди в интернете",
    "найди",
    "поиск",
]

HELP_TEXT = """
🤖 *Ассистент сети зоомагазинов «Четыре Лапы» — и не только!*

Я помогаю:
• с поиском информации в интернете  
• с консультациями по товарам  
• с объяснениями и подсказками  
• с обработкой изображений  
• с генерацией картинок  

📌 *Команды:*
/search `<запрос>` — поиск в интернете  
/поиск `<запрос>` — то же самое  
/img `<описание>` — генерация изображения  
/today — текущая дата  
/clear — очистка истории  
/bash `<команда>` — выполнение shell-команды  
/help — справка

🔊 В группах я отвечаю:
• при упоминании по триггерным словам  
• по фразам типа *«найди в интернете…»*, *«поиск…»*  
• по командам

👨‍💼 По всем вопросам работы бота:
**Дмитрий Лесных — @anykeycheg**

🦴 Всегда рад помочь вашей работе в сети «Четыре Лапы»  
и в любых других задачах!
"""


def help_keyboard():
    return [[Button.inline("ℹ️ Помощь", b"HELP")]]


# =======================
# BLOCK: HELP BUTTON
# =======================

@events.register(events.CallbackQuery(data=b"HELP"))
async def on_help_callback(event):
    await event.respond(
        HELP_TEXT,
        buttons=help_keyboard(),
        link_preview=False
    )


# =======================
# COMMAND HANDLERS
# =======================

@events.register(events.NewMessage(pattern=r"/start"))
@events.register(events.NewMessage(pattern=r"/help"))
async def help_handler(event):
    try:
        await event.reply(
            HELP_TEXT,
            buttons=help_keyboard(),
            link_preview=False
        )
        raise events.StopPropagation
    except events.StopPropagation:
        return


@events.register(events.NewMessage(pattern=r"/search"))
@events.register(events.NewMessage(pattern=r"/поиск"))
async def search_handler(event):
    try:
        query = re.sub(r"/(search|поиск)", "", event.raw_text, flags=re.IGNORECASE).strip()
        answer = await search(query)
        await event.reply(answer)
        raise events.StopPropagation
    except events.StopPropagation:
        return


@events.register(events.NewMessage(pattern=r"/bash"))
async def bash_handler(event):
    try:
        cmd = (event.raw_text or "").replace("/bash", "").strip()
        result = await bash(cmd)
        await event.reply(result)
        raise events.StopPropagation
    except events.StopPropagation:
        return


@events.register(events.NewMessage(pattern=r"/clear"))
async def clear_handler(event):
    try:
        await start_and_check(
            event=event,
            message="Очистка истории диалога",
            chat_id=event.chat_id,
        )
        await event.reply("🗑 История диалога очищена!")
        raise events.StopPropagation
    except events.StopPropagation:
        return


@events.register(events.NewMessage(pattern=r"/img"))
async def img_handler(event):
    try:
        prompt = (event.raw_text or "").replace("/img", "").strip()
        url = await generate_image(prompt)
        await event.reply(url)
        raise events.StopPropagation
    except events.StopPropagation:
        return


@events.register(events.NewMessage(pattern=r"/today"))
async def today_handler(event):
    try:
        await event.reply(f"📅 Сегодня: {get_date_time()}")
        raise events.StopPropagation
    except events.StopPropagation:
        return


# =======================
# UNIVERSAL HANDLER
# =======================

@events.register(events.NewMessage)
async def universal_handler(event):

    try:
        if event.out:
            return

        # ============================
        # Файлы и изображения
        # ============================

        if event.message.media:
            try:
                media_bytes = await event.client.download_media(
                    event.message,
                    file=bytes,
                )

                if not media_bytes:
                    await event.reply("⚠️ Не удалось получить файл.")
                    return

                await event.reply("👀 Анализирую изображение...")

                caption = (event.message.text or "").strip() or None

                answer = await analyze_image_with_gpt(
                    image_bytes=media_bytes,
                    user_prompt=caption,
                )

                await event.reply(answer)

            except Exception:
                logging.exception("Ошибка обработки изображения")
                await event.reply("❌ Не удалось обработать файл.")

            raise events.StopPropagation

        # ============================
        # Текст
        # ============================

        text = (event.raw_text or "").strip()
        if not text:
            return

        text_lower = text.lower()
        is_private = event.is_private

        # ----------------------------
        # Реакция на поиск фразой
        # ----------------------------

        for phrase in SEARCH_TRIGGERS:
            if phrase in text_lower:
                query = text_lower.replace(phrase, "").strip()
                result = await search(query)
                await event.reply(result)
                raise events.StopPropagation

        # ----------------------------

        triggered = any(t in text_lower for t in TRIGGERS)

        if not is_private and not triggered:
            return

        cleaned_text = text

        if not is_private:
            pattern = r"^(?:" + "|".join(map(re.escape, TRIGGERS)) + r")\s*[:,—–\- ]*"
            cleaned_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

            if not cleaned_text:
                cleaned_text = text

        await event.client(
            SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction(),
            )
        )

        filename, history = await start_and_check(
            event=event,
            message=cleaned_text,
            chat_id=event.chat_id,
        )

        gpt_answer = await get_openai_response(history, filename)

        await process_and_send_mess(event, gpt_answer)

        raise events.StopPropagation

    except events.StopPropagation:
        return

    except Exception:
        logging.exception("UNEXPECTED HANDLER ERROR")
        await event.reply("⚠️ Что-то пошло не так…")
        return
