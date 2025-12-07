import subprocess
import logging

from openai import OpenAI

from src.utils import model

client = OpenAI()

# =====================================================
# Командная оболочка (bash)
# =====================================================

async def bash(command: str) -> str:
    """
    Выполняет локальную bash-команду.
    Используется редко — оставляем для совместимости.
    """
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8")[:4000]
    except subprocess.CalledProcessError as e:
        return f"Ошибка команды:\n{e.output.decode('utf-8')[:4000]}"


# =====================================================
# Заглушка поиска
# =====================================================

async def search(query: str) -> str:
    """
    Временная функция-заглушка.
    Реальный веб-поиск можно подключить позже.
    """
    return f"🔎 Поиск по запросу: «{query}» пока не подключён."


# =====================================================
# Генерация изображений
# =====================================================

async def generate_image(prompt: str) -> str:
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        return result.data[0].url
    except Exception as e:
        logging.error(f"Image generation error: {e}")
        return "Ошибка генерации изображения."


# =====================================================
# Анализ изображений
# =====================================================

async def analyze_image_with_gpt(image_bytes: bytes, caption: str | None = None) -> str:
    try:
        text = caption or "Опиши, что изображено на картинке."

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты помощник для сотрудников сети зоомагазинов «4 лапы»."},
                {"role": "user", "content": text},
            ],
            max_tokens=500
        )
        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Vision analyze error: {e}")
        return "Ошибка анализа изображения."
