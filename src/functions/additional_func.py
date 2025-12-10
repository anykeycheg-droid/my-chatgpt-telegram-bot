import base64
import logging

from openai import OpenAI

from utils.utils import model, sys_mess

client = OpenAI()


# ==============================
# WEB SEARCH (реальный интернет-поиск)
# ==============================

async def search(query: str) -> str:
    """
    Поиск информации для команд /search, /поиск и текстовых триггеров.

    ✅ Использует реальный интернет-поиск через OpenAI Web Search.
    ✅ Всегда отвечает по-русски.
    ✅ Если web_search недоступен, делает аккуратный fallback на обычный ответ модели.
    """

    query = (query or "").strip()
    if not query:
        return "❌ Пожалуйста, укажи запрос для поиска."

    prompt = (
        "Ты — внимательный ассистент сети зоомагазинов «Четыре Лапы — и не только».\n"
        "Сначала при необходимости используй web_search, затем дай понятный, "
        "структурированный ответ по-русски.\n"
        "Если информация не найдена, честно скажи об этом."
        f"\n\nЗапрос пользователя: {query}"
    )

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            tools=[{"type": "web_search"}],
            max_output_tokens=800,
        )

        text_parts = []

        for item in getattr(response, "output", []):
            for c in getattr(item, "content", []):
                if getattr(c, "type", None) == "output_text":
                    text_parts.append(c.text)

        result = "\n".join(text_parts).strip()

        if not result:
            raise ValueError("Пустой результат web_search")

        return result

    except Exception:
        logging.exception("SEARCH ERROR")

        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_mess},
                    {"role": "user", "content": query}
                ],
                max_tokens=800,
                temperature=0.4,
            )

            return completion.choices[0].message.content.strip()

        except Exception as e:
            logging.exception("SEARCH FALLBACK ERROR")
            return f"❌ Ошибка поиска: {e}"


# ==============================
# IMAGE GENERATION
# ==============================

async def generate_image(prompt: str) -> bytes:
    if not prompt:
        prompt = "Домашнее животное в фирменном стиле «Четыре Лапы»"

    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
        )

        image_b64 = result.data[0].b64_json
        return base64.b64decode(image_b64)

    except Exception:
        logging.exception("IMAGE GENERATION ERROR")
        raise


# ==============================
# IMAGE ANALYSIS (VISION)
# ==============================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None,
) -> str:
    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = user_prompt or "Опиши, пожалуйста, это изображение."

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

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.exception("VISION ERROR")
        return f"❌ Ошибка анализа изображения: {e}"
