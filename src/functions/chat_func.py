import os
import json
import logging
import base64
from typing import List, Optional

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
# STORAGE
# =========================
BASE_PATH = "chats"
os.makedirs(BASE_PATH, exist_ok=True)

# =========================
# START / LOAD CHAT
# =========================
async def start_and_check(
    chat_id: int,
    clear: bool = False,
    user_text: Optional[str] = None,
):
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

    if not history:
        history = [{"role": "system", "content": sys_mess}]

    return filename, history


# =========================
# SAVE CHAT
# =========================
def save_chat(filename: str, history: List[dict]):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Ошибка сохранения диалога")


# =========================
# GPT TEXT REQUEST
# =========================
async def get_openai_response(history: List[dict]) -> str:
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=history,
            max_tokens=max_token,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        logging.exception("OpenAI error")
        return "⚠️ OpenAI временно недоступен. Попробуй позже."


# =========================
# GPT IMAGE REQUEST
# =========================
async def analyze_image_with_gpt(
    image_path: str,
    user_prompt: Optional[str] = None
) -> str:
    """
    Анализ изображения + опциональный текстовый промпт
    Поддерживает именованный аргумент user_prompt
    полностью совместим с handlers.py
    """

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(
                f.read()
            ).decode("utf-8")

        if not user_prompt:
            user_prompt = "Что изображено на фотографии?"

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        },
                    ],
                }
            ],
            max_tokens=max_token,
        )

        return response.choices[0].message.content.strip()

    except Exception:
        logging.exception("Ошибка анализа изображения")
        return "⚠️ Не удалось распознать изображение."


# =========================
# TELEGRAM OUTPUT
# =========================
async def process_and_send_mess(event, answer: str):

    max_length = 4000

    for i in range(0, len(answer), max_length):
        await event.reply(answer[i:i + max_length])

    try:
        used_tokens = num_tokens_from_messages(answer)
        tokens_left = max(0, max_token - used_tokens)

        await event.reply(f"\n(осталось {tokens_left} токенов)")

    except Exception:
        pass
