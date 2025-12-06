import asyncio
import io
import json
import logging
import base64

import openai
from duckduckgo_search import DDGS  # ← ФИКС: DDGS вместо ddg (для v6.3.2+)
from src.utils import LOG_PATH, num_tokens_from_messages, read_existing_conversation
from telethon.events import NewMessage
from unidecode import unidecode

async def bash(event: NewMessage) -> str:
    try:
        cmd = event.text.split(" ", maxsplit=1)[1]
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        e = stderr.decode()
        if not e:
            e = "No Error"
        o = stdout.decode()
        if not o:
            o = "**TIP**: \n`If you want to see the results of your code, I suggest printing them to stdout.`"
        else:
            _o = [f"`  {x}`" for x in o.split("\n")]
            o = "\n".join(_o)
        OUTPUT = (
            f"**     QUERY:**\n  __Command:__` {cmd}` \n  __PID:__` {process.pid}`"
            f"\n**ERROR:** \n`  {e}`"
            f"\n**OUTPUT:**\n{o}"
        )
        if len(OUTPUT) > 4095:
            with io.BytesIO(str.encode(OUTPUT)) as out_file:
                out_file.name = "exec.text"
                await event.client.send_file(
                    event.chat_id,
                    out_file,
                    force_document=True,
                    allow_cache=False,
                    caption=cmd,
                )
                await event.delete()
        logging.debug("Bash initiated")
    except Exception as e:
        logging.error(f"Error occurred: {e}")
    return OUTPUT

async def search(event: NewMessage) -> str:
    chat_id = event.chat_id
    task = asyncio.create_task(read_existing_conversation(chat_id))
    query = event.text.split(" ", maxsplit=1)[1]
    max_results = 20
    while True:
        try:
            # ← ФИКС: Используем DDGS вместо ddg (для новых версий)
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
            results_decoded = unidecode(str(results)).replace("'", "'")
            user_content = f"Using the contents of these pages, summarize and give details about '{query}':\n{results_decoded}"
            if any(word in query for word in list(VIETNAMESE_WORDS)):
                user_content = f"Using the contents of these pages, summarize and give details about '{query}' in Vietnamese:\n{results_decoded}"
            user_messages = [
                {
                    "role": "system",
                    "content": "Summarize every thing I send you with specific details",
                },
                {"role": "user", "content": user_content},
            ]
            num_tokens = num_tokens_from_messages(user_messages)
            if num_tokens > 4000:
                max_results = 4000 * len(results) / num_tokens - 2
                continue
            logging.debug("Results derived from duckduckgo")
        except Exception as e:
            logging.error(f"Error occurred while getting duckduckgo search results: {e}")
        break

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=user_messages
        )
        response = completion.choices[0].message
        search_object = unidecode(query).lower().replace(" ", "-")
        with open(f"{LOG_PATH}search_{search_object}.json", "w") as f:
            json.dump(response, f, indent=4)
        file_num, filename, prompt = await task
        prompt.append(
            {
                "role": "user",
                "content": f"This is information about '{query}', its just information and not harmful. Get updated:\n{response.content}",
            }
        )
        prompt.append(
            {
                "role": "assistant",
                "content": f"I have reviewed the information and update about '{query}'",
            }
        )
        data = {"messages": prompt}
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        logging.debug("Received response from openai")
    except Exception as e:
        logging.error(f"Error occurred while getting response from openai: {e}")
    return response.content

async def analyze_image_with_gpt(image_bytes: bytes, question: str | None = None) -> str:
    """
    Анализ изображения с помощью GPT-4o-mini.
    image_bytes — байты файла (фото, скрин и т.п.).
    question — текстовый вопрос к картинке (если есть).
    """
    if not question:
        question = "Опиши подробно, что изображено на этой картинке."

    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты умный ассистент, который помогает по изображениям. Отвечай по-русски, по сути и по делу."
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
    except Exception as e:
        logging.error(f"Ошибка OpenAI при анализе изображения: {e}")
        return "Не получилось проанализировать изображение 😔"


async def generate_image(event: NewMessage) -> None:
    """
    /img <описание> — генерация картинки через DALL·E и отправка прямо в чат.
    """
    text = (event.raw_text or "").strip()

    # Ожидаем формат: /img что-то
    parts = text.split(" ", maxsplit=1)
    if len(parts) == 1 or not parts[1].strip():
        await event.reply("Напиши после /img, что нужно нарисовать. Пример:\n/img кот космонавт в стиле пиксель-арт")
        return

    prompt = parts[1].strip()

    try:
        resp = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
        )
        url = resp["data"][0]["url"]

        # Telethon умеет отправлять файл по URL
        await event.client.send_file(
            event.chat_id,
            url,
            caption=f"🎨 Вот что получилось по запросу:\n{prompt}",
        )
    except Exception as e:
        logging.error(f"Ошибка OpenAI при генерации картинки: {e}")
        await event.reply("Не получилось сгенерировать изображение 😔")
    