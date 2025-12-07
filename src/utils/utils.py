import os
import json
import pytz
import tiktoken
from datetime import datetime
from typing import List


# =====================
# BASE PATHS
# =====================

LOG_PATH = "logs"
CHATS_PATH = f"{LOG_PATH}/chats"
HISTORY_PATH = f"{CHATS_PATH}/history"
SESSION_PATH = f"{CHATS_PATH}/session"
MEDIA_PATH = f"{LOG_PATH}/media"


def create_initial_folders():
    """
    Create required working directories
    """
    for path in [
        LOG_PATH,
        CHATS_PATH,
        HISTORY_PATH,
        SESSION_PATH,
        MEDIA_PATH,
    ]:
        os.makedirs(path, exist_ok=True)


create_initial_folders()


# =====================
# GENERAL
# =====================

BOT_NAME = "Dushnilla"


# =====================
# TIME
# =====================

def get_date_time(zone: str | None = None) -> str:
    timezone_name = zone or os.getenv("TIMEZONE", "Europe/Moscow")
    try:
        timezone = pytz.timezone(timezone_name)
    except Exception:
        timezone = pytz.timezone("Europe/Moscow")

    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")


# =====================
# TEXT UTILS
# =====================

def split_text(text: str, limit: int, prefix: str = "", suffix: str = "") -> List[str]:
    if not text:
        return [""]

    parts = []
    buffer = ""

    for line in text.splitlines(True):
        if len(buffer) + len(line) > limit:
            parts.append(f"{prefix}{buffer}{suffix}")
            buffer = line
        else:
            buffer += line

    if buffer:
        parts.append(f"{prefix}{buffer}{suffix}")

    return parts


# =====================
# TOKEN COUNT
# =====================

def num_tokens_from_messages(messages, model="gpt-4o-mini") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0
    for msg in messages:
        num_tokens += tokens_per_message
        for key, value in msg.items():
            num_tokens += len(encoding.encode(str(value)))
            if key == "name":
                num_tokens += tokens_per_name

    num_tokens += 3
    return num_tokens


# =====================
# DIALOG HISTORY
# =====================

async def read_existing_conversation(chat_id: int, clear=False):
    """
    Load or initialize session history
    """

    session_file = f"{SESSION_PATH}/{chat_id}.json"

    if os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        session_num = session_data.get("session", 0)
        filename = f"{CHATS_PATH}/chat_{chat_id}_{session_num}.json"

        if clear:
            session_num += 1
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump({"session": session_num}, f)

            filename = f"{CHATS_PATH}/chat_{chat_id}_{session_num}.json"
            return session_num, filename, []

        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                history = json.load(f).get("messages", [])
        else:
            history = []

        return session_num, filename, history

    else:
        os.makedirs(os.path.dirname(session_file), exist_ok=True)

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump({"session": 0}, f)

        filename = f"{CHATS_PATH}/chat_{chat_id}_0.json"
        return 0, filename, []
