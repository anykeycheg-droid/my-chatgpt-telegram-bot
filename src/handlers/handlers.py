import asyncio
import logging
import random
import re
import base64
import io
from telethon import events
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction, MessageMediaPhoto

from src.functions.chat_func import process_and_send_mess, start_and_check, get_openai_response
from src.utils import RANDOM_ACTION, ALLOW_USERS, model

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
    is_private = event.is_private
    triggered = any(word in text.lower() for word in TRIGGERS)

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

    # ОБРАБОТКА ФОТО: если фото, скачиваем и кодируем в base64
    if event.message.media and isinstance(event.message.media, MessageMediaPhoto):
        # Скачиваем фото
        photo_bytes = await event.download_media(bytes)
        # Кодируем в base64
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        # Добавляем в prompt как image_url
        image_prompt = [
            {"type": "text", "text": clean_text or "Опиши это фото подробно"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        # Используем image_prompt вместо текста
        filename, prompt = await start_and_check(event, image_prompt, event.chat_id)
        response = get_openai_response(prompt, filename)
    else:
        # Обычный текст
        filename, prompt = await start_and_check(event, clean_text, event.chat_id)
        response = get_openai_response(prompt, filename)

    # Отправляем ответ
    await process_and_send_mess(event, response)

    # Анимация "думает"
    for _ in range(random.randint(2, 5)):
        await asyncio.sleep(random.uniform(1.5, 3.5))
        await event.client(SetTypingRequest(
            peer=event.chat_id,
            action=random.choice(RANDOM_ACTION)
        ))

    raise events.StopPropagation

# Команды
@events.register(events.NewMessage(pattern="/search"))
async def search_handler(event):
    from src.functions.additional_func import search
    await search(event)
    raise events.StopPropagation

@events.register(events.NewMessage(pattern="/bash"))
async def bash_handler(event):
    from src.functions.additional_func import bash
    await bash(event)
    raise events.StopPropagation

@events.register(events.NewMessage(pattern="/clear"))
async def clear_handler(event):
    from src.functions.additional_func import bash
    event.message.message = f"/bash rm -f {LOG_PATH}chats/history/{event.chat_id}* {LOG_PATH}chats/session/{event.chat_id}.json"
    await bash(event)
    raise events.StopPropagation