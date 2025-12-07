import subprocess
import logging
import base64

from openai import OpenAI

from src.utils import model, sys_mess

client = OpenAI()

# =====================================================
# Командная оболочка (bash)
# =====================================================

async def bash(command: str) -> str:
    """
    Выполняет локальную bash-команду.
    """
    try:
        if not command:
            return "❌ Команда не указана."

        result = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT
        )
        return result.decode("utf-8")[:4000]

    except subprocess.CalledProcessError as e:
        return f"Ошибка команды:\n{e.output.decode('utf-8')[:4000]}"


# =====================================================
# Заглушка поиска
# =====================================================

async def search(query: str) -> str:
    """
    Временная функция поиска-заглушка.
    """
    if not query:
        return "Введите текст запроса для поиска."

    return f"🔎 Поиск по запросу «{query}» пока не подключён."


# =====================================================
# Генерация изображений
# =====================================================

async def generate_image(prompt: str) -> str:
    """
    Генерирует изображение через OpenAI Images API.
    """
    try:
        if not prompt:
            prompt = "Милое домашнее животное, дружелюбный стиль"

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        return result.data[0].url

    except Exception as e:
        logging.error(f"Image generation error: {e}")
        return "❌ Ошибка генерации изображения."


# =====================================================
# Анализ изображений
# =====================================================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None
) -> str:
    """
    GPT-Vision анализ изображения.
    """
    try:
        prompt = user_prompt or "Опиши, что изображено на изображении."

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
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Vision analyze error: {e}")
        return "❌ Ошибка распознавания изображения."
