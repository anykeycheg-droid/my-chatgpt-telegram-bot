import json
import logging
import time
from typing import List, Tuple

from openai import OpenAI
from telethon.events import NewMessage

from utils.utils import (
    model,
    max_token,
    read_existing_conversation,
    num_tokens_from_messages,
    sys_mess,
)

client = OpenAI()

Prompt = List[dict]


# ===============================================================
# SETTINGS
# ===============================================================

WINDOW_SIZE = 12
SUMMARY_MAX_TOKENS = 300
RESPONSE_MAX_TOKENS = 1500


# ===============================================================
# HELPERS
# ===============================================================

def trim_prompt_window(prompt: Prompt) -> Prompt:
    """
    Оставляет только последние WINDOW_SIZE сообщений в prompt
    + сохраняет все system-сообщения
    """

    system_msgs = [m for m in prompt if m["role"] == "system"]
    dialog_msgs = [m for m in prompt if m["role"] != "system"]

    if len(dialog_msgs) <= WINDOW_SIZE:
        return prompt

    dialog_msgs = dialog_msgs[-WINDOW_SIZE:]

    return system_msgs + dialog_msgs


def should_keep_message(text: str) -> bool:
    if not text:
        return False

    trash = {
        "ок",
        "ага",
        "понял",
        "поняла",
        "спасибо",
        "окей",
        "хорошо",
        "ясно",
    }

    t = text.lower().strip()
    if t in trash:
        return False

    return True


# ===============================================================
# CHAT FLOW
# ===============================================================

async def start_and_check(
    event: NewMessage,
    message: str,
    chat_id: int,
) -> Tuple[str, Prompt]:

    session, filename, prompt = read_existing_conversation(str(chat_id))

    if not any(m["role"] == "system" for m in prompt):
        prompt.insert(0, {"role": "system", "content": sys_mess})

    if should_keep_message(message):
        prompt.append({"role": "user", "content": message})

    prompt = trim_prompt_window(prompt)

    tokens = num_tokens_from_messages(prompt)

    if tokens > max_token - 700:
        await create_summary_and_reset(prompt, filename)
        session, filename, prompt = read_existing_conversation(str(chat_id))

        prompt.insert(0, {"role": "system", "content": sys_mess})
        prompt.append({"role": "user", "content": message})

    return filename, prompt


# ===============================================================
# SUMMARY
# ===============================================================

async def create_summary_and_reset(prompt: Prompt, filename: str):

    try:
        dialog_only = [m for m in prompt if m["role"] != "system"]

        summary_prompt = [
            {
                "role": "system",
                "content":
                    "Ты сжимаешь диалоги. "
                    "Создай краткое резюме беседы в 3–5 предложениях "
                    "по-русски, только по ключевым фактам.",
            },
            {
                "role": "user",
                "content": json.dumps(dialog_only, ensure_ascii=False),
            }
        ]

        completion = client.chat.completions.create(
            model=model,
            messages=summary_prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=0.2,
        )

        summary = completion.choices[0].message.content.strip()

        new_prompt = [
            {"role": "system", "content": sys_mess},
            {"role": "system", "content": f"Резюме прошлого диалога: {summary}"},
        ]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"messages": new_prompt},
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception as e:
        logging.error(f"SUMMARY ERROR: {e}")


# ===============================================================
# OPENAI RESPONSE
# ===============================================================

async def get_openai_response(prompt: Prompt, filename: str) -> str:

    for attempt in range(5):
        try:
            prompt = trim_prompt_window(prompt)

            completion = client.chat.completions.create(
                model=model,
                messages=prompt,
                max_tokens=RESPONSE_MAX_TOKENS,
                temperature=0.6,
            )

            message = completion.choices[0].message

            if should_keep_message(message.content):
                prompt.append({
                    "role": message.role,
                    "content": message.content,
                })

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    {"messages": prompt},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            return message.content.strip()

        except Exception as e:
            logging.error(f"OpenAI error {attempt + 1}/5: {e}")
            time.sleep(2)

    return "⚠️ OpenAI временно недоступен. Попробуй позже."


# ===============================================================
# TELEGRAM OUTPUT
# ===============================================================

async def process_and_send_mess(event, answer: str):

    max_length = 4000

    for i in range(0, len(answer), max_length):
        await event.reply(answer[i:i + max_length])
