import logging
from datetime import datetime

from openai import OpenAI, APIError, RateLimitError, APIConnectionError

from src.utils import (
    LOG_PATH,
    read_existing_conversation,
    num_tokens_from_messages,
)

# =====================
# OPENAI CONFIG
# =====================

# Модель
MODEL = "gpt-4o-mini"

# Максимум токенов в истории
MAX_TOKENS = 12000

# Системное сообщение
SYSTEM_MESSAGE = (
    "Ты — помощник для сотрудников сети зоомагазинов «Четыре Лапы».\n"
    "Говоришь строго на русском языке.\n"
    "Ты дружелюбный, понятный и немного с юмором.\n"
    "Всегда стараешься помогать максимально практично и по делу.\n\n"
    "Ты знаешь сегодняшнюю дату: "
    + datetime.now().strftime("%d.%m.%Y")
)

# =====================
# CLIENT
# =====================

client = OpenAI()


# =====================
# CORE FUNCTIONS
# =====================

async def start_and_check(chat_id: int, clear: bool = False):
    """
    Загружает или очищает историю чата
    """
    session_num, filename, history = await read_existing_conversation(
        chat_id=chat_id,
        clear=clear
    )
    return filename, history


async def get_openai_response(messages: list[dict]) -> str:
    """
    Отправка запроса в OpenAI и получение ответа
    """

    try:
        messages_with_system = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            *messages
        ]

        # Контроль чрезмерной истории
        tokens = num_tokens_from_messages(messages_with_system, MODEL)
        if tokens > MAX_TOKENS:
            messages_with_system = messages_with_system[-20:]

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages_with_system,
            temperature=0.7,
        )

        text = response.choices[0].message.content.strip()
        return text

    except RateLimitError:
        logging.error("OpenAI RateLimit")
        return "Слишком много запросов к ИИ. Немного подожди и попробуй ещё раз."

    except APIConnectionError:
        logging.error("OpenAI Connection error")
        return "Не удалось подключиться к сервису ИИ. Попробуй немного позже."

    except APIError as e:
        logging.error(f"OpenAI API error: {e}")
        return "Произошла ошибка при работе с ИИ."

    except Exception as e:
        logging.exception("Unexpected error while calling OpenAI")
        return "Что-то пошло не так при обращении к ИИ."
