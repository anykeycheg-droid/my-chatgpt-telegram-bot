import os
import json
import datetime

# =====================================================
# Общие настройки
# =====================================================

LOG_PATH = "logs"

model = "gpt-4.1-mini"

max_token = 2000


# =====================================================
# SYSTEM PROMPT
# =====================================================

sys_mess = """
Ты — помощник для сотрудников сети зоомагазинов «ЧЕТЫРЕ ЛАПЫ».

Отвечай только на русском языке.

Всегда будь вежлив, полезен и ориентирован на решение рабочих задач.

Текущая дата учитывается при ответах.
"""


# =====================================================
# Утилиты
# =====================================================

def get_date_time():
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")


def create_initial_folders():
    os.makedirs(f"{LOG_PATH}/chats", exist_ok=True)


def read_existing_conversation(chat_id: str):
    create_initial_folders()

    filename = f"{LOG_PATH}/chats/{chat_id}.json"

    try:
        with open(filename, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("session", 0), filename, data.get("messages", [])

    except FileNotFoundError:
        prompt = [{"role": "system", "content": sys_mess}]
        session = 0

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"session": session, "messages": prompt},
                f,
                ensure_ascii=False,
                indent=2
            )

        return session, filename, prompt


def num_tokens_from_messages(messages: list):
    total = 0
    for msg in messages:
        total += len(str(msg.get("content", ""))) // 4
    return total
