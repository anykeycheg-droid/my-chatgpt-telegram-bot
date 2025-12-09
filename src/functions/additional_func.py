import base64
import logging

from openai import OpenAI

from src.utils.utils import model, sys_mess


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

    # Инструкции для ассистента под бренд
    prompt = (
        "Ты — внимательный ассистент сети зоомагазинов «Четыре Лапы — и не только».\n"
        "Твоя задача — сначала найти актуальную информацию в интернете, а затем кратко и понятно "
        "ответить по-русски.\n\n"
        "Требования к ответу:\n"
        "• Отвечай по-русски.\n"
        "• Если вопрос связан с животными, товарами для животных, здоровьем питомцев — "
        "делай акцент на экспертности сети зоомагазинов «Четыре Лапы».\n"
        "• Если указываешь факты (цены, даты, составы, нормативы) — опирайся на найденные источники.\n"
        "• Если данных недостаточно или они противоречат друг другу — честно скажи об этом.\n\n"
        f"Запрос пользователя: {query}"
    )

    try:
        # Основной путь — через responses + web_search tool
        response = client.responses.create(
            model=model,  # тот же модельный идентификатор, что и для чата
            input=prompt,
            tools=[{"type": "web_search"}],
            max_output_tokens=800,
        )

        # Структура ответа: response.output[0].content[0].text
        try:
            text = response.output[0].content[0].text
        except Exception:
            # На всякий случай более «широкий» разбор
            parts = []
            for item in getattr(response, "output", []):
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) == "output_text":
                        parts.append(c.text)
            text = "\n".join(parts).strip() if parts else ""

        if not text:
            raise ValueError("Пустой ответ от web_search модели")

        return text.strip()

    except Exception as e:
        # Логируем, но не ломаем бота
        logging.exception("SEARCH ERROR (web_search)")

        # Fallback: обычный ответ модели без web_search
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — ассистент сети зоомагазинов «Четыре Лапы — и не только». "
                            "Отвечай всегда по-русски. "
                            "Скажи честно, что тебе не удалось выполнить интернет-поиск, "
                            "и отвечай только из своих общих знаний."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Ответь, насколько можешь, без интернета: {query}",
                    },
                ],
                max_tokens=800,
                temperature=0.4,
            )

            return completion.choices[0].message.content.strip()

        except Exception as e2:
            logging.exception("SEARCH ERROR (fallback)")
            return f"❌ Ошибка поиска: {e2}"


# ==============================
# IMAGE GENERATION
# ==============================

async def generate_image(prompt: str) -> bytes:
    """Генерация изображения через OpenAI Images API.
    Возвращает байты PNG.
    """

    if not prompt:
        prompt = (
            "Милое домашнее животное в фирменном стиле сети зоомагазинов "
            "«Четыре Лапы — и не только»"
        )

    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
            # ⚠️ response_format УБРАН — это главный фикс
        )

        image_b64 = result.data[0].b64_json
        return base64.b64decode(image_b64)

    except Exception as e:
        logging.exception("IMAGE GENERATION ERROR")
        raise


# ==============================
# IMAGE ANALYSIS (VISION)
# ==============================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None
) -> str:
    """Анализ изображений GPT Vision"""

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
