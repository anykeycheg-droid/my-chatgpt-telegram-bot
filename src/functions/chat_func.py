import json
import logging
import time
from typing import List, Tuple

from openai import OpenAI
from telethon.events import NewMessage

from src.utils import (
    LOG_PATH,
    model,
    max_token,
    sys_mess,
    read_existing_conversation,
    num_tokens_from_messages,
)

# Init OpenAI client
client = OpenAI()

Prompt = List[dict]


# ==============================
# CHAT FLOW
# ==============================

async def start_and_check(
    event: NewMessage,
    message: str,
    chat_id: int,
) -> Tuple[str, Prompt]:
    session, filename, prompt = read_existing_conversation(str(chat_id))

    prompt.append({"role": "user", "content": message})

    tokens = num_tokens_from_messages(prompt)

    if tokens > max_token - 500:
        await over_token(tokens, event, prompt, filename)
        session, filename, prompt = read_existing_conversation(str(chat_id))
        prompt.append({"role": "user", "content": message})

    return filename, prompt


# ==============================
# TOKEN OVERFLOW
# ==============================

async def over_token(
    num_tokens: int,
    event: NewMessage,
    prompt: Prompt,
    filename: str,
):
    try:
        await event.reply(
            f"Диалог стал слишком длинным ({num_tokens} токенов). Начинаю новый 🙂"
        )

        completion = client.chat.completions.create(
            model=model,
            messages=prompt,
            max_tokens=300,
            temperature=0.2,
        )

        summary = completion.choices[0].message.content

        new_prompt = [
            {
                "role": "system",
                "content": f"Резюме прошлого диалога: {summary}",
            }
        ]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"session": 0, "messages": new_prompt},
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        logging.error(f"Ошибка обрезки диалога: {e}")


# ==============================
# OPENAI RESPONSE
# ==============================

async def get_openai_response(prompt: Prompt, filename: str) -> str:

    for attempt in range(1, 6):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=prompt,
                max_tokens=1500,
                temperature=0.6,
            )

            text = completion.choices[0].message.content.strip()

            prompt.append(completion.choices[0].message)

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    {"messages": prompt},
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            used = completion.usage.total_tokens
            remain = max(0, max_token - used)

            return f"{text}\n\n_(осталось {remain} токенов)_"

        except Exception as e:
            logging.error(f"OpenAI error ({attempt}/5): {e}")
            time.sleep(2)

    return "⚠️ OpenAI временно недоступен. Попробуй позже."


# ==============================
# TELEGRAM OUTPUT
# ==============================

async def process_and_send_mess(event, answer: str):

    max_length = 4000

    for i in range(0, len(answer), max_length):
        await event.reply(answer[i:i + max_length])
