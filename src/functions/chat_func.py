import asyncio
import json
import logging
import time
from typing import List, Tuple

from openai import OpenAI
from telethon.events import NewMessage

from src.utils import (
    LOG_PATH,
    read_existing_conversation,
    num_tokens_from_messages,
)


# ============ OpenAI CONFIG ============

client = OpenAI()

model = "gpt-4o-mini"
max_token = 16000

sys_mess = {
    "role": "system",
    "content": """
Ты — корпоративный AI-ассистент сети зоомагазинов «4 Лапы».

Всегда общайся НА РУССКОМ ЯЗЫКЕ.
Ты помогаешь сотрудникам:
• с продажами
• подбором кормов и товаров
• консультированием клиентов
• обучением персонала
• стандартами сервиса
• внутренними вопросами магазина

Ты знаешь, что сегодня текущая дата должна выводиться корректно.

Твой стиль:
— дружелюбный
— уверенный
— с лёгким юмором и подколами
— ориентирован на результат
— объясняешь понятно и по делу

Ты никогда не говоришь, что ты GPT-3.5 или старая модель.
Ты всегда представляешься как AI-ассистент сети «4 Лапы».

Ты НИКОГДА не упоминаешь версии моделей.
"""
}


Prompt = List[dict]


# ===============================
# LONG CHAT COMPRESSION
# ===============================

async def over_token(
    num_tokens: int,
    event: NewMessage,
    prompt: Prompt,
    filename: str,
):
    await event.reply(
        f"История диалога слишком длинная " 
        f"({num_tokens} токенов). " 
        f"Начинаю новый контекст 👋"
    )

    prompt.append(
        {
            "role": "user",
            "content": "Кратко перескажи весь предыдущий разговор"
        }
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=prompt[:10],
            max_tokens=500,
            temperature=0.5
        )

        summary = completion.choices[0].message.content

        new_prompt = [
            sys_mess,
            {
                "role": "system",
                "content": f"Краткое резюме диалога: {summary}"
            },
        ]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"messages": new_prompt},
                f,
                ensure_ascii=False,
                indent=4,
            )

    except Exception:
        logging.exception("Ошибка суммаризации диалога")


# ====================================
# DIALOG MANAGER
# ====================================

async def start_and_check(
    event: NewMessage,
    message: str,
    chat_id: int,
    clear: bool = False
) -> Tuple[str, Prompt]:

    file_num, filename, prompt = await read_existing_conversation(
        chat_id,
        clear=clear
    )

    if message:
        prompt.append(
            {
                "role": "user",
                "content": message,
            }
        )

    while True:
        tokens = num_tokens_from_messages(prompt, model)

        if tokens > max_token - 1000:
            file_num += 1

            with open(
                f"{LOG_PATH}chats/session/{chat_id}.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump({"session": file_num}, f)

            await over_token(tokens, event, prompt, filename)

            _, filename, prompt = await read_existing_conversation(chat_id)
            prompt.append({"role": "user", "content": message})

        else:
            break

    return filename, prompt


# ====================================
# OPENAI REQUEST
# ====================================

def get_openai_response(prompt: Prompt, filename: str) -> str:
    trial = 0

    while trial < 5:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=0.8,
                max_tokens=1500,
            )

            message = completion.choices[0].message
            text = message.content.strip()

            # ✅ СОХРАНЯЕМ ТОЛЬКО СЛОВАРЬ, А НЕ SDK ОБЪЕКТ
            prompt.append({
                "role": message.role,
                "content": message.content
            })

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    {"messages": prompt},
                    f,
                    ensure_ascii=False,
                    indent=4,
                )

            used = completion.usage.total_tokens
            remain = max(0, max_token - used)

            return f"{text}\n\n__(осталось {remain} токенов)__"

        except Exception as e:
            trial += 1
            logging.error(f"OpenAI error ({trial}/5): {e}")
            time.sleep(2)

    return "⚠ OpenAI временно недоступен. Попробуй позже."



# ====================================
# TELEGRAM SEND UTIL
# ====================================

async def process_and_send_mess(
    event,
    text: str,
    limit: int = 500
) -> None:

    from src.utils import split_text

    parts = text.split("```")

    for idx, part in enumerate(parts):
        # обычный текст
        if idx % 2 == 0:
            for msg in split_text(part, limit):
                await event.client.send_message(
                    event.chat_id,
                    msg,
                    background=True,
                    silent=True,
                )
                await asyncio.sleep(1)

        # блок кода
        else:
            for msg in split_text(
                part,
                limit,
                prefix="```\n",
                suffix="\n```",
            ):
                await event.client.send_message(
                    event.chat_id,
                    msg,
                    background=True,
                    silent=True,
                )
                await asyncio.sleep(1)
