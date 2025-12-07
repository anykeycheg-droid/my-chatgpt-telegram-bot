import asyncio
import io
import json
import logging
import base64
from typing import Optional

from openai import OpenAI
from duckduckgo_search import DDGS
from telethon.events import NewMessage
from unidecode import unidecode

from src.utils import (
    LOG_PATH,
    read_existing_conversation,
    num_tokens_from_messages,
    VIETNAMESE_WORDS,
)

from src.functions.chat_func import get_openai_response


client = OpenAI()

# ====================================
# BASH
# ====================================

async def bash(event: NewMessage) -> str:
    try:
        cmd = event.raw_text.split(" ", maxsplit=1)[1]

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        out = stdout.decode() or "No output"
        err = stderr.decode() or "No error"

        result = (
            f"**QUERY**: `{cmd}`\n"
            f"**PID**: `{process.pid}`\n\n"
            f"**OUTPUT:**\n```{out}```\n"
            f"**ERROR:**\n```{err}```"
        )

        if len(result) > 4000:
            with io.BytesIO(result.encode()) as f:
                f.name = "bash_output.txt"
                await event.client.send_file(event.chat_id, f)
        else:
            await event.reply(result)

        return result

    except Exception as e:
        logging.exception("Bash error")
        await event.reply("Ошибка выполнения bash 😔")
        return ""


# ====================================
# SEARCH
# ====================================

async def search(event: NewMessage) -> str:
    query = event.raw_text.split(" ", maxsplit=1)[1]

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=15))

        text_results = unidecode(json.dumps(results, ensure_ascii=False))

        user_prompt = f"Summarize and explain the information:\n{text_results}"

        if any(w in query for w in VIETNAMESE_WORDS):
            user_prompt = f"Do this in Vietnamese:\n{text_results}"

        messages = [
            {"role": "system", "content": "You summarize search results."},
            {"role": "user", "content": user_prompt}
        ]

        answer = get_openai_response(messages, filename="search_tmp.json")

        chat_id = event.chat_id

        _, filename, prompt = await read_existing_conversation(chat_id)

        prompt.append(
            {
                "role": "assistant",
                "content": f"Search about '{query}':\n{answer}"
            }
        )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"messages": prompt}, f, ensure_ascii=False, indent=4)

        await event.reply(answer)
        return answer

    except Exception:
        logging.exception("Search failed")
        await event.reply("Ошибка поиска 😔")
        return ""


# ====================================
# IMAGE ANALYSIS (VISION)
# ====================================

async def analyze_image_with_gpt(
    image_bytes: bytes,
    question: Optional[str] = None
) -> str:

    if not question:
        question = "Опиши подробно, что изображено на картинке."

    try:
        img_b64 = base64.b64encode(image_bytes).decode()

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты описываешь содержание изображений максимально точно."
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
        logging.exception("Vision analyze failed")
        return "Не удалось проанализировать изображение 😔"


# ====================================
# IMAGE GENERATION
# ====================================

async def generate_image(event: NewMessage) -> None:
    text = (event.raw_text or "").strip()

    parts = text.split(" ", maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await event.reply(
            "Используй команду так:\n"
            "/img описание картинки"
        )
        return

    prompt = parts[1].strip()

    try:
        image = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_url = image.data[0].url

        await event.client.send_file(
            event.chat_id,
            image_url,
            caption=f"🎨 По запросу:\n{prompt}",
        )

    except Exception:
        logging.exception("Image generation failed")
        await event.reply("Не получилось сгенерировать изображение 😔")
