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
# ✅ REAL INTERNET SEARCH
# =====================================================

async def search(query: str) -> str:
    """
    Настоящий live-поиск в интернете через OpenAI web_search.
    """
    try:
        if not query:
            return "Введите запрос для поиска."

        response = client.responses.create(
            model="gpt-4.1-mini",
            tools=[{"type": "web_search"}],
            input=f"Найди актуальную информацию в интернете и ответь максимально точно:\n{query}",
            max_output_tokens=700,
            temperature=0.2
        )

        text = response.output_text.strip()

        if not text:
            return "🔎 Не удалось получить результат поиска."

        return text

    except Exception as e:
        logging.error(f"Web search error: {e}")
        return "❌ Ошибка поиска. Попробуй позже."


# =====================================================
# IMAGE GENERATION
# =====================================================

async def generate_image(prompt: str) -> str:
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
# IMAGE ANALYSIS (VISION)
# =====================================================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None
) -> str:
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
