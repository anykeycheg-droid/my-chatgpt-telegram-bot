import base64
import httpx
from openai import OpenAI

from src.utils import model, sys_mess

client = OpenAI()


# ==============================
# IMAGE GENERATION
# ==============================

async def generate_image(prompt: str) -> bytes:
    try:
        if not prompt:
            prompt = "Милое домашнее животное, дружелюбный стиль"

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        url = result.data[0].url

        async with httpx.AsyncClient() as http:
            response = await http.get(url)
            response.raise_for_status()

            return response.content  # BYTES !!!

    except Exception as e:
        return f"❌ Ошибка генерации изображения: {e}"


# ==============================
# IMAGE ANALYSIS (VISION)
# ==============================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    user_prompt: str | None = None
) -> str:
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
        return f"❌ Ошибка анализа изображения: {e}"
