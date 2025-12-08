import base64
import logging

from openai import OpenAI

from src.utils import model, sys_mess

client = OpenAI()


# ==============================
# WEB SEARCH
# ==============================

async def search(query: str) -> str:
    """Поиск информации для команд /search, /поиск и текстовых триггеров.

    Делает разумный краткий ответ по-русски в тональности бренда
    «Четыре Лапы — и не только».
    """
    query = (query or "").strip()
    if not query:
        return "❌ Пожалуйста, укажи запрос для поиска."

    system_prompt = (
        "Ты — внимательный ассистент сети зоомагазинов «Четыре Лапы», и не только. "
        "Отвечай всегда по-русски, дружелюбно и по делу. Если вопрос связан с животными, "
        "зоотоварами или уходом, опирайся на экспертизу бренда, приглашай в магазиы «Четыре Лапы», консультанты всегда помогут. "
        "Если тема другая, всё равно помоги, и переставай напоминать про «Четыре Лапы». "
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Найди актуальную информацию в интернете и кратко ответь на запрос: {query}"
                    ),
                },
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logging.exception("SEARCH ERROR")
        return f"❌ Ошибка поиска: {e}"


# ==============================
# IMAGE GENERATION
# ==============================

async def generate_image(prompt: str) -> bytes:
    """Генерация изображения через OpenAI Images API.

    Возвращает байты PNG, которые можно сразу отправлять в Telethon:
    await event.respond(file=image_bytes, ...)
    """
    if not prompt:
        prompt = (
            "Милое домашнее животное в фирменном стиле сети зоомагазинов "
            "«Четыре Лапы — и не только», яркие дружелюбные цвета, позитивное настроение"
        )

    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            response_format="b64_json",
        )

        image_b64 = result.data[0].b64_json
        return base64.b64decode(image_b64)

    except Exception as e:
        logging.exception("IMAGE GENERATION ERROR")
        # Пробрасываем ошибку выше, чтобы хендлер /img показал аккуратное сообщение
        raise


# ==============================
# IMAGE ANALYSIS (VISION)
# ==============================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None,
) -> str:
    """Анализ изображения с помощью GPT-Vision."""
    try:
        prompt = user_prompt or "Опиши, что изображено на картинке."

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_mess},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=500,
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.exception("VISION ERROR")
        return f"❌ Ошибка анализа изображения: {e}"
