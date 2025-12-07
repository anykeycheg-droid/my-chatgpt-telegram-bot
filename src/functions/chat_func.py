import logging
import datetime

from openai import OpenAI
from telethon.events import NewMessage

from src.utils import (
    model,
    max_token,
    sys_mess,
    read_existing_conversation,
    save_dialogue,
)

client = OpenAI()


# ======================================================
# START / CHECK FUNCTION
# ======================================================

async def start_and_check(
    event: NewMessage,
    user_text: str = ""
):
    """
    Предобработка входящего сообщения
    """

    filename = f"dialog_{event.sender_id}.json"

    if not user_text:
        user_text = event.raw_text or ""

    return filename, user_text.strip()


# ======================================================
# CORE AI RESPONSE FUNCTION
# ======================================================

async def get_openai_response(
    prompt: str,
    filename: str,
) -> str:
    """
    Запрос к OpenAI (основной ответ бота)
    """

    today = datetime.datetime.now().strftime("%d.%m.%Y")

    conversation = read_existing_conversation(filename)

    # Системное сообщение (роль бота)
    system_prompt = (
        f"{sys_mess}\n\n"
        f"Сегодняшняя дата: {today}.\n"
        "Ты помощник сотрудников сети зоомагазинов «4 лапы».\n"
        "Отвечай всегда на русском.\n"
        "Манера общения — дружелюбная, результативная, "
        "иногда с лёгкими шутками или подколами.\n"
        "Ты помогаешь в работе: товар, клиенты, инструкции, стандарты сервиса.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    for msg in conversation:
        messages.append(
            {
                "role": msg["role"],
                "content": str(msg["content"]),
            }
        )

    messages.append(
        {"role": "user", "content": prompt}
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_token,
        )

        answer = response.choices[0].message.content.strip()

        save_dialogue(
            filename=filename,
            user_message=prompt,
            assistant_message=answer,
        )

        return answer

    except Exception as err:
        logging.error(f"OpenAI API error: {err}")
        return (
            "⚡ Сейчас сервис ИИ временно недоступен.\n"
            "Попробуй чуть позже — я скоро вернусь в строй 😉"
        )


# ======================================================
# FULL MESSAGE PIPELINE
# ======================================================

async def process_and_send_mess(
    event: NewMessage,
    filename: str,
    prompt: str,
):
    """
    Полный цикл обработки сообщения и ответа пользователю
    """

    answer = await get_openai_response(
        prompt=prompt,
        filename=filename,
    )

    await event.respond(answer)
