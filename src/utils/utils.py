import os
import datetime

# =====================================================
# Общие настройки
# =====================================================

LOG_PATH = "logs"

# Модель для OpenAI
model = "gpt-4.1-mini"

# Максимальный размер ответа
max_token = 2000


# =====================================================
# Системное сообщение для ChatGPT
# =====================================================

sys_mess = """
Ты — помощник для сотрудников сети зоомагазинов «4 ЛАПЫ».

Твои задачи:
- Помогать по работе магазина.
- Подсказывать по товарам и сервисам.
- Помогать с регламентами, обучением и стандартами обслуживания.
- Отвечать только на русском языке.
- Текущая дата должна учитываться при ответах.

Стиль общения:
Дружелюбный, рабочий, с лёгким юмором и подколами, но всегда на результат.
"""


# =====================================================
# Утилиты
# =====================================================

def get_date_time() -> str:
    """Возвращает текущую дату и время."""
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")


def create_initial_folders():
    """
    Создает необходимые папки при старте приложения.
    """
    os.makedirs(LOG_PATH, exist_ok=True)


def read_existing_conversation(filename: str) -> list:
    """
    Читает историю диалога из файла.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [{"role": "user", "content": line.strip()} for line in lines]
    except FileNotFoundError:
        return []


def num_tokens_from_messages(messages: list) -> int:
    """
    Простейшая оценка токенов (примерная).
    """
    total = 0
    for msg in messages:
        total += len(str(msg.get("content", ""))) // 4
    return total
