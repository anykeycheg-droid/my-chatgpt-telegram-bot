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

from functions.additional_func import search

client = OpenAI()

Prompt = List[dict]


# ===============================================================
# SETTINGS
# ===============================================================

WINDOW_SIZE = 12
SUMMARY_MAX_TOKENS = 300
RESPONSE_MAX_TOKENS = 800

WAIT_WEB_CONFIRM_STATE = "__WAIT_WEB_SEARCH_CONFIRM__"

YES_WORDS = {"да", "давай", "ага", "ищи", "найди", "ок"}
NO_WORDS = {"нет", "не надо", "не нужно"}

# ===============================================================
# HELPERS
# ===============================================================

def trim_prompt_window(prompt: Prompt) -> Prompt:
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
        "ок", "ага", "понял", "поняла", "спасибо", "окей", "хорошо", "ясно"
    }

    t = text.lower().strip()
    if t in trash:
        return False

    return True


def is_affirmative(text: str) -> bool:
    return any(w in text.lower() for w in YES_WORDS)


def is_negative(text: str) -> bool:
    return any(w in text.lower() for w in NO_WORDS)


# ===============================================================
# ALWAYS TRY RAG FIRST
# ===============================================================

def try_rag(query: str) -> str | None:
    try:
        return search(query)
    except Exception:
        logging.exception("RAG SEARCH ERROR")
        return None


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

    text = message.strip()

    # ===================================================
    # CASE 1 — ожидаем подтверждение web search
    # ===================================================

    if session.get("state") == WAIT_WEB_CONFIRM_STATE:

        if is_affirmative(text):
            session["state"] = None

            web_result = await search(session.get("last_rag_query", text))

            prompt.append({
                "role": "assistant",
                "content": f"🌐 Вот результаты поиска в интернете:\n\n{web_result}"
            })

            save_session(filename, session, prompt)
            return filename, prompt

        elif is_negative(text):
            session["state"] = None

            prompt.append({
                "role": "assistant",
                "content": "Хорошо, интернет-поиск выполнять не буду."
            })

            save_session(filename, session, prompt)
            return filename, prompt

        else:
            prompt.append({
                "role": "assistant",
                "content": "Пожалуйста, ответьте: искать информацию в интернете — да или нет?"
            })

            save_session(filename, session, prompt)
            return filename, prompt


    # ===================================================
    # CASE 2 — NORMAL QUESTION → ALWAYS TRY RAG
    # ===================================================

    rag_result = try_rag(text)

    if rag_result:
        prompt.insert(1, {
            "role": "system",
            "content":
                "Ты корпоративный ассистент сети «Четыре Лапы».\n"
                "Отвечай строго ТОЛЬКО используя информацию ниже. "
                "Не придумывай.\n\n"
                "=== ВНУТРЕННЯЯ БАЗА ===\n"
                f"{rag_result}\n"
                "=== КОНЕЦ ==="
        })

        prompt.append({"role": "user", "content": text})

    else:
        # RAG ничего не дал → спрашиваем пользоваться ли интернетом
        session["state"] = WAIT_WEB_CONFIRM_STATE
        session["last_rag_query"] = text

        prompt.append({
            "role": "assistant",
            "content":
                "Во внутренней базе знаний компании нет точной информации "
                "по этому вопросу.\n\n"
                "Я могу попробовать найти ответ в интернете.\n"
                "Искать информацию?"
        })

        save_session(filename, session, prompt)
        return filename, prompt

    prompt = trim_prompt_window(prompt)

    tokens = num_tokens_from_messages(prompt)

    if tokens > max_token - 500:
        await create_summary_and_reset(prompt, filename)
        session, filename, prompt = read_existing_conversation(str(chat_id))
        prompt.insert(0, {"role": "system", "content": sys_mess})
        prompt.append({"role": "user", "content": text})

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

        save_session(filename, {"messages": new_prompt}, new_prompt)

    except Exception as e:
        logging.error(f"SUMMARY ERROR: {e}")


# ===============================================================
# FILE SAVE
# ===============================================================

def save_session(filename: str, session: dict, prompt: Prompt):

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    **session,
                    "messages": prompt,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        logging.error(f"SAVE SESSION ERROR: {e}")


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
                temperature=0.2,
            )

            message = completion.choices[0].message

            if should_keep_message(message.content):
                prompt.append({
                    "role": message.role,
                    "content": message.content,
                })

            save_session(filename, {}, prompt)

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
