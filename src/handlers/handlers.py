import asyncio
import logging
import random
import re

from telethon import events
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

from src.functions.additional_func import bash, search
from src.functions.chat_func import process_and_send_mess, start_and_check, get_openai_response
from src.utils import RANDOM_ACTION, ALLOW_USERS

# Слова-триггеры для групп (в любом регистре)
TRIGGERS = [
    "душнилла", "душнила", "душ", "душик", "душечка",
    "dushnilla", "dushnila", "dush", "dushik", "dushechka"
]

@events.register(events.NewMessage)
async def universal_handler(event):
    # Игнорируем свои сообщения
    if event.out:
        return

    # Проверка доступа (если ALLOW_USERS не пустой)
    if ALLOW_USERS and event.chat_id not in ALLOW_USERS:
        return

    text = (event.message.message or "").strip()
    if not text:
        return

    text_lower = text.lower()
    is_private = event.is_private
    triggered = any(word in text_lower for word in TRIGGERS)

    # В личке отвечаем всегда, в группах — только по триггеру
    if not (is_private or triggered):
        return

    # Убираем триггер-слово из начала сообщения
    clean_text = text
    if not is_private:
        for trigger in TRIGGERS:
            clean_text = re.sub(rf"(?i)^{re.escape(trigger)}[\s,:;!?-]*", "", clean_text).strip()
            if clean_text:
                break
        if not clean_text:
            clean_text = "Привет! Я Душнилла, чем помочь?"

    # Показываем, что печатаем
    await event.client(SetTypingRequest(
        peer=event.chat_id,
        action=SendMessageTypingAction()
    ))

    # Основной ответ
    try:
        filename, prompt = await start_and_check(event, clean_text, event.chat_id)
        response = get_openai_response(prompt, filename)

        await process_and_send_mess(event, response)

        # Анимация "думает"
        for _ in range(random.randint(2, 5)):
            await asyncio.sleep(random.uniform(1.5, 3.5))
            await event.client(SetTypingRequest(
                peer=event.chat_id,
                action=random.choice(RANDOM_ACTION)
            ))

    except Exception as e:
        logging.error(f"Ошибка в universal_handler: {e}")
        await event.reply("Ой, что-то сломалось… Попробуй ещё разок")

    raise events.StopPropagation

# Команды
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
    await bash(event)
    raise events.StopPropagation