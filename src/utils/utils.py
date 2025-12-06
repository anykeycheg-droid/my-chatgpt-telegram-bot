import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Generator, List, Optional, Tuple

import coloredlogs
import pytz
import tiktoken
from dotenv import load_dotenv
from telethon.errors.rpcerrorlist import PeerIdInvalidError
from telethon.events import NewMessage
from telethon.tl.types import (
    SendMessageChooseContactAction,
    SendMessageChooseStickerAction,
    SendMessageGamePlayAction,
    SendMessageGeoLocationAction,
    SendMessageRecordAudioAction,
    SendMessageRecordRoundAction,
    SendMessageRecordVideoAction,
)

load_dotenv()

# Prompt typehint
Prompt = List[dict]

# Имя бота
BOT_NAME = "Душнилла"

# Главный промпт — Душнилла на русском (мультимодальный)
SYS_MESS = [
    {
        "role": "system",
        "content": """
Ты — очень умный, слегка ироничный и заботливый помощник по имени Душнилла.
Всегда отвечай ТОЛЬКО на русском языке, даже если вопрос на другом языке.
Говори живо, по-дружески, можешь использовать эмодзи, но не переборщи.
Если тебя зовут по имени — отвечай сразу, без лишних слов.
Ты любишь подушнить, но с теплом и заботой.
Можешь анализировать изображения: описывай их подробно, если пользователь присылает фото.
Никогда не пиши, что ты ИИ или что у тебя нет доступа к чему-то. Просто помогай.
        """.strip()
    }
]

# Основной промпт для всех чатов
sys_mess = SYS_MESS

# Для совместимости со старым кодом (не удаляй!)
VIETNAMESE_WORDS = "áàảãạăắằẳẵặâấầẩẫậÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬéèẻẽẹêếềểễệÉÈẺẼẸÊẾỀỂỄỆóòỏõọôốồổỗộơớờởỡợÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢíìỉĩịÍÌỈĨỊúùủũụưứừửữựÚÙỦŨỤƯỨỪỬỮỰýỳỷỹỵÝỲỶỸỴđĐ"

LOG_PATH = "logs/"

RANDOM_ACTION = [
    SendMessageRecordVideoAction(),
    SendMessageRecordRoundAction(),
    SendMessageRecordAudioAction(),
    SendMessageGeoLocationAction(),
    SendMessageGamePlayAction(),
    SendMessageChooseStickerAction(),
    SendMessageChooseContactAction(),
]

# Доступ — только для указанных ID (если пусто — всем)
ALLOW_USERS = eval(os.getenv("ALLOW_USERS", "[]"))

# Самая мощная и дешёвая мультимодальная модель (gpt-4o-mini — точно работает с фото/голосом)
model = "gpt-4o-mini"
max_token = 128000

def initialize_logging() -> io.StringIO:
    coloredlogs.install()
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    console_out = io.StringIO()
    console_handler = logging.getLogger("root").handlers[0]
    console_handler.stream = console_out
    return console_out

def create_initial_folders() -> None:
    for folder in [f"{LOG_PATH}chats", f"{LOG_PATH}chats/history", f"{LOG_PATH}chats/session"]:
        os.makedirs(folder, exist_ok=True)

def get_date_time(zone="Asia/Ho_Chi_Minh"):
    timezone = pytz.timezone(zone)
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

async def read_existing_conversation(chat_id: int) -> Tuple[int, str, Prompt]:
    try:
        with open(f"{LOG_PATH}chats/session/{chat_id}.json", "r", encoding="utf-8") as f:
            file_num = json.load(f)["session"]
    except:
        file_num = 1
        os.makedirs(f"{LOG_PATH}chats/session", exist_ok=True)
        with open(f"{LOG_PATH}chats/session/{chat_id}.json", "w", encoding="utf-8") as f:
            json.dump({"session": 1}, f)

    filename = f"{LOG_PATH}chats/history/{chat_id}_{file_num}.json"
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"messages": sys_mess}, f, ensure_ascii=False, indent=4)

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompt = data.get("messages", sys_mess)
    return file_num, filename, prompt

def num_tokens_from_messages(messages: Prompt, model: str = "gpt-4o-mini") -> int:
    """Обновлённая версия для gpt-4o-mini"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = 0
    for msg in messages:
        tokens += 4
        for key, value in msg.items():
            if isinstance(value, str):
                tokens += len(encoding.encode(value))
            elif isinstance(value, list):  # Для изображений
                tokens += sum(len(encoding.encode(str(item))) for item in value if isinstance(item, dict))
            if key == "name":
                tokens -= 1
    tokens += 3
    return tokens

def split_text(text: str, limit=4000, prefix="", suffix="") -> Generator[str, None, None]:
    if len(text) <= limit:
        yield f"{prefix}{text}{suffix}"
        return
    parts = re.split(r'(\n\n|\.\s|\?\s|\!\s)', text)
    current = ""
    for part in parts:
        if len(current) + len(part) < limit:
            current += part
        else:
            if current.strip():
                yield f"{prefix}{current.strip()}{suffix}"
            current = part
    if current.strip():
        yield f"{prefix}{current.strip()}{suffix}"

def terminal_html() -> str:
    return """
        <html>
        <head>
            <title>Terminal</title>
            <script>
                function sendCommand() {
                    const command = document.getElementById("command").value;
                    fetch("/terminal/run", {
                        method: "POST",
                        body: JSON.stringify({command: command}),
                        headers: {
                            "Content-Type": "application/json"
                        }
                    })
                    .then(response => response.text())
                    .then(data => {
                        document.getElementById("output").innerHTML += data + "<br>";
                    });
                    document.getElementById("command").value = "";
                }
            </script>
        </head>
        <body>
            <div id="output"></div>
            <input type="text" id="command" onkeydown="if (event.keyCode == 13) sendCommand()">
            <button onclick="sendCommand()">Run</button>
        </body>
        </html>
    """