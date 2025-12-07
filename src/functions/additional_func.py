import base64
import logging
from typing import Optional

from telethon.events import NewMessage
from openai import OpenAI

client = OpenAI()

# =====================================================
# BASH COMMAND
# =====================================================

async def bash(event: NewMessage) -> None:
    """
    Техническая команда /bash
    """

    await event.reply(
        "🔧 Команда /bash активна.\n\n"
        "Служебная функция для отладки и технических проверок.\n"
        "Можно расширять под внутренние задачи сотрудников «4 Лапы»."
    )


# =====================================================
# SEARCH COMMAND (заглушка)
# =====================================================

async def search(event: NewMessage) -> None:
    """
    Команда /search

    Пока работает как умная заглушка.
    В будущем можно подключить настоящий web-поиск.
    """

    text = (event.raw_text or "").replace("/search", "").strip()

    if not text:
        await event.reply(
            "🔍 Использование:\n"
            "/search ваш запрос"
        )
        return

    await event.reply(
        "🔎 Поиск временно работает в тестовом режиме.\n\n"
        f"Ваш запрос:\n<b>{text}</b>\n\n"
        "⚙ Пока используется только внутренняя база ответов "
        "и возможности ИИ.\n"
        "Внешний web-поиск будет подключён позже.",
        parse_mode="html",
    )


# =====================================================
# IMAGE ANALYSIS (VISION)
# =====================================================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    question: Optional[str] = None,
) -> str:
    """
    Анализ изображения через GPT Vision
    """

    if not question:
        question = (
            "Опиши подробно, что изображено на картинке. "
            "Если это товары для животных — перечисли их и дай рекомендации."
        )

    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — ассистент сети зоомагазинов «4 Лапы». "
                        "Отвечай профессионально, полезно и дружелюбно."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=800,
        )

        return completion.choices[0].message.content.strip()

    except Exception:
        logging.exception("Ошибка анализа изображения")
        return "❌ Не удалось распознать изображение. Попробуй прислать другое фото."


# =====================================================
# IMAGE GENERATION
# =====================================================

async def generate_image(event: NewMessage) -> None:
    """
    Генерация изображений
    Команда:
    /img описание
    """

    text = (event.raw_text or "").strip()
    parts = text.split(" ", maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await event.reply(
            "ℹ Используй команду так:\n"
            "/img описание картинки"
        )
        return

    prompt = parts[1].strip()

    try:
        image = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
        )

        image_url = image.data[0].url

        await event.client.send_file(
            event.chat_id,
            image_url,
            caption=f"🎨 Сгенерировано по запросу:\n{prompt}",
        )

    except Exception:
        logging.exception("Ошибка генерации картинки")
        await event.reply(
            "❌ Не получилось сгенерировать изображение 😔"
        )
