import os
import json
import pytz
import tiktoken
from datetime import datetime
from typing import List

# =====================
# PATH SETTINGS
# =====================

LOG_PATH = "logs/"

CHATS_PATH = f"{LOG_PATH}chats"
HISTORY_PATH = f"{LOG_PATH}chats/history"
SESSION_PATH = f"{LOG_PATH}chats/session"
MEDIA_PATH = f"{LOG_PATH}media"

os.makedirs(CHATS_PATH, exist_ok=True)
os.makedirs(HISTORY_PATH, exist_ok=True)
os.makedirs(SESSION_PATH, exist_ok=True)
os.makedirs(MEDIA_PATH, exist_ok=True)

# =====================
# GENERAL SETTINGS
# =====================

BOT_NAME = "Dushnilla"

VIETNAMESE_WORDS = [
    "xin",
    "chao",
    "cam",
    "on",
    "toi",
    "ban",
    "viet",
    "nam",
]

# =====================
# TIME
# =====================

def get_date_time(zone: str | None = None) -> str:
    tz_name = zone or os.getenv("TIMEZONE", "Europe/Moscow")
    try:
        timezone = pytz.timezone(tz_name)
    except Exception:
        timezone = pytz.timezone("Europe/Moscow")
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")


# =====================
# LOGGING INIT
# =====================

def initialize_logging():
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    logging.info("Logging initialized")


# =====================
# TEXT UTILS
# =====================

def split_text(
    text: str,
    limit: int,
    prefix: str = "",
    suffix: str = ""
) -> List[str]:

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
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name

    num_tokens += 3
    return num_tokens


# =====================
# DIALOG HISTORY
# =====================

async def read_existing_conversation(chat_id: int, clear=False):
    """
    Loads or initializes chat history
    """
    session_file = f"{SESSION_PATH}/{chat_id}.json"

    if os.path.exists(session_file):
        with open(session_file) as f:
            session_data = json.load(f)

        session_num = session_data.get("session", 0)

        filename = f"{LOG_PATH}chats/chat_{chat_id}_{session_num}.json"

        if clear:
            session_num += 1

            with open(session_file, "w") as f:
                json.dump({"session": session_num}, f)

            filename = f"{LOG_PATH}chats/chat_{chat_id}_{session_num}.json"
            return session_num, filename, []

        try:
            with open(filename) as f:
                history = json.load(f).get("messages", [])
        except FileNotFoundError:
            history = []

        return session_num, filename, history

    else:
        os.makedirs(os.path.dirname(session_file), exist_ok=True)

        with open(session_file, "w") as f:
            json.dump({"session": 0}, f)

        filename = f"{LOG_PATH}chats/chat_{chat_id}_0.json"
        return 0, filename, []

def create_initial_folders():
    """
    Ensure all required directories exist
    """
    paths = [
        LOG_PATH,
        f"{LOG_PATH}chats/",
        f"{LOG_PATH}chats/session/",
        f"{LOG_PATH}images/",
    ]

    for path in paths:
        os.makedirs(path, exist_ok=True)
