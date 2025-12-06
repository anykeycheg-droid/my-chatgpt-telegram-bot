import asyncio
import logging
import random
import re

from telethon import events
from telethon.tl.custom import Button
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

from src.functions.additional_func import bash, search
from src.functions.chat_func import process_and_send_mess, start_and_check, get_openai_response
from src.utils.utils.utils import RANDOM_ACTION, ALLOW_USERS, sys_mess

# Список триггер-слов (в любом регистре)
TRIGGERS = [
    "душнилла", "душнила", "душ", "душик", "душечка",
    "dushnilla", "dushnila", "dush", "dushik", "dushechka"
]

# === ОСНОВНОЙ УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ===
@events.register(events.NewMessage)
async def universal_handler(event):
    # Игнорируем свои сообщения
    if event.out:
        return

    # Проверка доступа (если ALLOW_USERS не пустой)
    if ALLOW_USERS and event.chat_id not in ALLOW_USERS:
        return

    message_text = (event.message.message or "").strip()
    if not message_text:
        return

    text_lower = message_text.lower()

    # Проверка триггера в группах
    is_private = event.is_private
    triggered = any(trigger in text_lower for trigger in TRIGGERS)

    # В личке отвечаем всегда, в группе — только по триггеру
    if not (is_private or triggered):
        return

    # Убираем триггер-слово из начала сообщения (чтобы не повторялось)
    clean_text = message_text
    if not is_private:
        for trigger in TRIGGERS:
            clean_text = re.sub(rf"(?i)^{re.escape(trigger)}[\s,:;!?-]*", "", clean_text).strip()
            if clean_text:
                break
        if not clean_text:
            clean_text = "Привет! Я Душнилла, чем помочь?"

    # Показываем, что печатаем
    await event.client.parse_mode = "md"
    await event.client(SetTypingRequest(
        peer=event.chat_id,
        action=SendMessageTypingAction()
    ))

    # Основная логика ответа через OpenAI
    try:
        filename, prompt = await start_and_check(event, clean_text, event.chat_id)
        response = get_openai_response(prompt, filename)

        await process_and_send_mess(event, response)

        # Случайные действия, чтобы было видно, что бот "думает"
        for _ in range(random.randint(2, 5)):
            await asyncio.sleep(random.uniform(1, 3))
            await event.client(SetTypingRequest(
                peer=event.chat_id,
                action=random.choice(RANDOM_ACTION)
            ))
    except Exception as e:
        logging.error(f"Ошибка в universal_handler: {e}")
        await event.reply("Ой, что-то пошло не так... Попробуй ещё раз!")

    # Останавливаем дальнейшую обработку (чтобы не срабатывали старые хендлеры)
    raise events.StopPropagation


# Оставляем только нужные команды
@events.register(events.NewMessage(pattern="/search"))
async def search_handler(event):
    await search(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern="/bash"))
async def bash_handler(event):
    await bash(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern="/clear"))
async def clear_handler(event):
    await bash(event)  # уже есть логика очистки в /bash
    raise events.StopPropagation