import asyncio
import base64
import logging

from openai import OpenAI

from src.utils import model, sys_mess

client = OpenAI()


# ==============================
# BASH
# ==============================

async def bash(cmd: str) -> str:
    """
    Выполнить shell-команду на сервере и вернуть её вывод.
    """
    cmd = (cmd or "").strip()
    if not cmd:
        return "❌ Не указана команда для /bash."

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="ignore").strip()

        if not output:
            output = "✅ Команда выполнена без вывода."

        return f"💻 bash$ {cmd}\n\n{output}"

    except Exception as e:
        logging.exception("BASH ERROR")
        return f"❌ Ошибка выполнения команды: {e}"


# ==============================
# WEB SEARCH
# ==============================

async def search(query: str) -> str:
    """
    Поиск информации (через модель).
    Важно: отвечает по-русски и в брендинге «Четыре Лапы — и не только».
    """
    query = (query or "").strip()
    if not query:
        return "❌ Пожалуйста, укажи запрос для поиска."

    try:
        system_prompt = (
            "Ты — ассистент сети зоомагазинов «Четыре Лапы — и не только». "
            "Отвечай по-русски, кратко и по делу. "
            "Если запрос связан с домашними животными, зоотоварами или уходом, "
            "используй экспертизу бренда. Если тема иная, всё равно помоги, "
            "но можешь ненавязчиво напомнить о бренде."
        )

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Найди в интернете и кратко ответь на запрос: {query}",
                },
            ],
            max_tokens=800,
            temperature=0.2,
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        logging.exception("SEARCH ERROR")
        return f"❌ Ошибка поиска: {e}"


# ==============================
# IMAGE GENERATION
# ==============================

async def generate_image(prompt: str) -> bytes:
    """
    Генерация изображения через OpenAI.
    Возвращает байты картинки (PNG/JPEG) для отправки через Telethon.
    """
    if not prompt:
        prompt = (
            "Милое домашнее животное в фирменном стиле сети зоомагазинов "
            "«Четыре Лапы — и не только»"
        )

    # OpenAI Images API: получаем картинку в base64 и декодируем в bytes
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        response_format="b64_json",
    )

    image_b64 = result.data[0].b64_json
    return base64.b64decode(image_b64)


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
        logging.exception("VISION ERROR")
        return f"❌ Ошибка анализа изображения: {e}"
