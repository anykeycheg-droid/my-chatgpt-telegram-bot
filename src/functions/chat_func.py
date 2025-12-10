import json
import logging
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from openai import OpenAI
from telethon.events import NewMessage

from utils.utils import (
    model,
    max_token,
    read_existing_conversation,
    num_tokens_from_messages,
    sys_mess,
)

from functions.additional_func import search as web_search
from rag.search import search as rag_search

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

FILE_REQUEST_WORDS = {
    "скинь",
    "пришли",
    "перешли",
    "дай файл",
    "отправь файл",
    "дай документ",
    "пришли документ",
    "перешли документ",
    "скинь памятку",
    "выдай документ",
    "pdf",
}


BASE_PROJECT_DIR = Path(__file__).resolve().parents[2]


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
    return t not in trash


def is_affirmative(text: str) -> bool:
    return any(w in text.lower() for w in YES_WORDS)


def is_negative(text: str) -> bool:
    return any(w in text.lower() for w in NO_WORDS)


def request_documents(text: str) -> bool:
    text = text.lower()
    return any(patt in text for patt in FILE_REQUEST_WORDS)


# ===============================================================
# RAG
# ===============================================================

def _format_rag_chunks(
    chunks: List[Dict[str, Any]],
    max_sources: int = 3,
    max_chars: int = 2500,
) -> Tuple[str, List[Dict[str, Any]]]:

    if not chunks:
        return "", []

    lines: List[str] = []
    sources: List[Dict[str, Any]] = []
    used = set()
    total_len = 0

    for rank, ch in enumerate(chunks[:max_sources], start=1):
        text = (ch.get("text") or "").strip()
        if not text:
            continue

        source_file = ch.get("source_file") or ch.get("source")
        page = ch.get("page")

        snippet = text[:800]
        header = f"[{rank}] Источник: {source_file}"
        if page:
            header += f", стр. {page}"

        block = f"{header}\n{snippet}"

        if total_len + len(block) > max_chars:
            break

        lines.append(block)
        total_len += len(block)

        key = (source_file, page)
        if key not in used:
            used.add(key)
            sources.append(
                {
                    "source_file": source_file,
                    "page": page,
                }
            )

    return "\n\n---\n\n".join(lines), sources


def _build_sources_hint(sources: List[Dict[str, Any]]) -> str:
    if not sources:
        return ""

    lines = []
    for s in sources:
        name = s.get("source_file") or "внутренний документ"
        page = s.get("page")
        if page:
            name += f", стр. {page}"
        lines.append(f"- {name}")

    return "\n".join(lines)


def try_rag(query: str) -> Optional[Dict[str, Any]]:
    try:
        chunks = rag_search(query)

        if not chunks:
            return None

        formatted, sources = _format_rag_chunks(chunks)
        if not formatted:
            return None

        return {
            "formatted": formatted,
            "sources": sources,
        }

    except Exception:
        logging.exception("RAG SEARCH ERROR")
        return None


# ===============================================================
# CHAT
# ===============================================================

async def start_and_check(event: NewMessage, message: str, chat_id: int):

    session, filename, prompt = read_existing_conversation(str(chat_id))

    if not any(m["role"] == "system" for m in prompt):
        prompt.insert(0, {"role": "system", "content": sys_mess})

    text = message.strip()

    # ===================================================
    # SEND DOCUMENT REQUEST
    # ===================================================

    if request_documents(text):

        sources = session.get("last_rag_sources", [])

        if not sources:
            return filename, [
                {
                    "role": "assistant",
                    "content": "У меня ещё нет контекста, из какого документа отправлять файл. Задайте вопрос сначала.",
                }
            ]

        attachments = []
        for s in sources:
            rel_path = s.get("source_file")
            if not rel_path:
                continue

            full_path = BASE_PROJECT_DIR / rel_path
            if full_path.exists():
                attachments.append(full_path)

        if not attachments:
            return filename, [
                {
                    "role": "assistant",
                    "content": "Не удалось найти файлы документов на сервере.",
                }
            ]

        # Отправляем файлы
        for f in attachments:
            await event.client.send_file(
                chat_id,
                file=f,
                caption=f"Источник: {f.name}",
            )

        return filename, []


    # ===================================================
    # NORMAL QUESTION
    # ===================================================

    rag_payload = try_rag(text)

    if rag_payload:

        rag_text = rag_payload["formatted"]
        rag_sources = rag_payload["sources"]

        session["state"] = None
        session["last_rag_sources"] = rag_sources

        sources_hint = _build_sources_hint(rag_sources)

        system_content = (
            "Ты корпоративный ассистент сети «Четыре Лапы».\n"
            "Отвечай строго только на базе информации ниже.\n\n"
            "=== ВНУТРЕННЯЯ БАЗА ===\n"
            f"{rag_text}\n"
            "=== КОНЕЦ ===\n\n"
        )

        if sources_hint:
            system_content += (
                "В конце ответа добавь:\n"
                "📚 Источники:\n"
                f"{sources_hint}"
            )

        prompt.insert(1, {"role": "system", "content": system_content})
        prompt.append({"role": "user", "content": text})

    else:
        session["state"] = WAIT_WEB_CONFIRM_STATE
        session["last_rag_query"] = text

        prompt.append(
            {
                "role": "assistant",
                "content": (
                    "Во внутренней базе знаний нет точной информации по этому вопросу.\n"
                    "Искать ответ в интернете?"
                ),
            }
        )

        save_session(filename, session, prompt)
        return filename, prompt

    prompt = trim_prompt_window(prompt)

    tokens = num_tokens_from_messages(prompt)

    if tokens > max_token - 500:
        await create_summary_and_reset(prompt, filename)
        session, filename, prompt = read_existing_conversation(str(chat_id))

        if not any(m["role"] == "system" for m in prompt):
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
                "content": "Сожми диалог в краткое резюме из 3–5 предложений.",
            },
            {"role": "user", "content": json.dumps(dialog_only, ensure_ascii=False)},
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
# SAVE
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
