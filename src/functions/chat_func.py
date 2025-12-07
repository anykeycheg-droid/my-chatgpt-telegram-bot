import os
import json
import logging
from datetime import datetime

from openai import AsyncOpenAI

from src.utils import (
    sys_mess,
    model,
    max_token,
    num_tokens_from_messages,
)


# =========================
# INIT OPENAI CLIENT
# =========================
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# FILE STORAGE
# =========================
BASE_PATH = "chats"

os.makedirs(BASE_PATH, exist_ok=True)


# =========================
# START / LOAD CHAT
# =========================
async def start_and_check(chat_id: int, clear: bool = False):
    """
    Load or create chat history file.
    """
    filename = os.path.join(BASE_PATH, f"{chat_id}.json")

    if clear and os.path.exists(filename):
        os.remove(filename)

    history = []

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    # добавляем системный промпт если его нет
    if not history:
        history = [
            {"role": "system", "content": sys_mess}
        ]

    return filename, history


# =========================
# SAVE CHAT
# =========================
def save_chat(filename, history):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Ошибка сохранения истории")


# =========================
# OPENAI REQUEST
# =========================
async def get_openai_response(history):

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=history,
            max_tokens=max_token,
            temperature=0.7,
        )

        message = response.choices[0].message.content.strip()
        return message

    except Exception:
        logging.exception("OpenAI ERROR")
        return "⚠️ OpenAI временно недоступен. Попробуй чуть позже."


# =========================
# SEND MESSAGE TO TELEGRAM
# =========================
async def process_and_send_mess(event, answer: str):

    max_length = 4000

    # режем слишком длинный текст
    chunks = [
        answer[i:i + max_length]
        for i in range(0, len(answer), max_length)
    ]

    for chunk in chunks:
        await event.reply(chunk)

    try:
        # считаем токены
        tokens_left = max_token - num_tokens_from_messages(answer)

        await event.reply(
            f"\n(осталось {tokens_left} токенов)"
        )

    except Exception:
        pass

