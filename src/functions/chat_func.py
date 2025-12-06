import asyncio
import json
import logging
from typing import List, Tuple

import openai
from openai.error import APIConnectionError
from telethon.events import NewMessage

from src.utils import LOG_PATH, model, max_token, sys_mess, read_existing_conversation, num_tokens_from_messages

Prompt = List[dict]

async def over_token(num_tokens: int, event: NewMessage, prompt: Prompt, filename: str):
    await event.reply(f"Разговор слишком длинный ({num_tokens} токенов), начинаю новый! 😅")
    prompt.append({"role": "user", "content": "Кратко перескажи весь предыдущий разговор"})
    try:
        completion = openai.ChatCompletion.create(model=model, messages=prompt[:10])
        summary = completion.choices[0].message.content
        new_prompt = sys_mess + [{"role": "system", "content": f"Краткое резюме прошлой беседы: {summary}"}]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"messages": new_prompt}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка суммаризации: {e}")

async def start_and_check(event: NewMessage, message: str, chat_id: int) -> Tuple[str, Prompt]:
    file_num, filename, prompt = await read_existing_conversation(chat_id)
    prompt.append({"role": "user", "content": message})
    
    while True:
        tokens = num_tokens_from_messages(prompt, model)
        if tokens > max_token - 1000:
            file_num += 1
            with open(f"{LOG_PATH}chats/session/{chat_id}.json", "w") as f:
                json.dump({"session": file_num}, f)
            await over_token(tokens, event, prompt, filename)
            _, filename, prompt = await read_existing_conversation(chat_id)
            prompt.append({"role": "user", "content": message})
        else:
            break
    return filename, prompt

def get_openai_response(prompt: Prompt, filename: str) -> str:
    trial = 0
    while trial < 5:
        try:
            completion = openai.ChatCompletion.create(
                model=model,  # o4-mini (работает в 0.28.1 через fallback)
                messages=prompt,
                max_tokens=1500,
                temperature=0.8,
            )
            text = completion.choices[0].message.content.strip()
            prompt.append(completion.choices[0].message)  # Добавляем ответ в историю
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({"messages": prompt}, f, ensure_ascii=False, indent=4)
            
            used = completion.usage.total_tokens
            left = max_token - used
            return f"{text}\n\n__({left} токенов осталось)__"
            
        except APIConnectionError:
            trial += 1
            if trial >= 5:
                return "🔌 Проблемы с соединением... Попробуй через минуту"
        except Exception as e:
            logging.error(f"OpenAI error: {e}")
            return "Ой, OpenAI сейчас подтормаживает... Попробуй ещё раз через минуту 😏"

async def process_and_send_mess(event, text: str, limit=500) -> None:
    from src.utils import split_text  # Импорт внутри, чтобы избежать циклических
    text_lst = text.split("```")
    cur_limit = 4096
    for idx, part in enumerate(text_lst):
        if idx % 2 == 0:
            mess_gen = split_text(part, cur_limit)
            for mess in mess_gen:
                await event.client.send_message(
                    event.chat_id, mess, background=True, silent=True
                )
                await asyncio.sleep(1)
        else:
            mess_gen = split_text(part, cur_limit, prefix="```\n", suffix="\n```")
            for mess in mess_gen:
                await event.client.send_message(
                    event.chat_id, mess, background=True, silent=True
                )
                await asyncio.sleep(1)