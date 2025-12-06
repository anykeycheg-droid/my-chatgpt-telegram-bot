import os
import logging
from telethon import events
from src.functions.additional_func import (
    bash,
    search,
    generate_image,
    analyze_image_with_gpt,
)
from src.functions.chat_func import process_and_send_mess, start_and_check, get_openai_response
from src.utils import get_date_time



create_initial_folders()

@events.register(events.NewMessage)
async def universal_handler(event):
    # Не реагируем на свои сообщения
    if event.out:
        return

        # ==== 1. Если прилетело медиа (фото, документ и т.п.) ====
    if getattr(event.message, "media", None):
        try:
            # Скачиваем байты файла
            media_bytes = await event.client.download_media(event.message, file=bytes)

            if media_bytes:
                # Отзеркалить файл обратно в чат (чтобы было видно, что дошло)
                await event.client.send_file(
                    event.chat_id,
                    media_bytes,
                    caption="✅ Файл принят, думаю над ним...",
                )

                caption = (event.message.message or "").strip()
                answer = await analyze_image_with_gpt(media_bytes, caption or None)
                await event.reply(answer)
            else:
                await event.reply("Я получил файл, но не смог его скачать 😔")

        except Exception as e:
            logging.exception("Ошибка при обработке media в universal_handler")
            await event.reply("Не получилось обработать файл 😔")

        raise events.StopPropagation

    # ==== 2. Обычный текст ====
    text = (event.message.message or "").strip()
    if not text:
        return

    text_lower = text.lower()
    is_private = event.is_private

    # Команды, у которых есть отдельные хендлеры — пропускаем
    if text_lower.startswith(("/search", "/bash", "/clear", "/img", "/today")):
        return

    # В группах отвечаем только если есть триггер-слово
    triggered = any(word in text_lower for word in TRIGGERS)
    if not is_private and not triggered:
        return

    # Убираем триггер-слово из начала сообщения (в группах)
    clean_text = text
    if not is_private:
        pattern = r"^(?:" + "|".join(TRIGGERS) + r")\s*[:,\\-–— ]*"
        clean_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        if not clean_text:
            clean_text = text

    try:
        # Показываем "печатает"
        await event.client(
            SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction(),
            )
        )

        # История + запрос к OpenAI
        filename, prompt = await start_and_check(event, clean_text, event.chat_id)
        response = get_openai_response(prompt, filename)

        # Отправляем ответ (с разбиением на части и т.п.)
        await process_and_send_mess(event, response)
     
    except Exception as e:
        logging.error(f"Ошибка в universal_handler: {e}")
        await event.reply("Ой, что-то сломалось… Попробуй ещё разок")

    raise events.StopPropagation

# Команды
@events.register(events.NewMessage(pattern="/search"))
async def search_handler(event):
    await search(event)
    raise events.StopPropagation

@events.register(events.NewMessage(pattern="/bash"))
async def bash_handler(event):
    await bash(event)
    raise events.StopPropagation

@events.register(events.NewMessage(pattern="/clear"))
async def clear_handler(event):
    await bash(event)
    raise events.StopPropagation
    
    
@events.register(events.NewMessage(pattern="/img"))
async def img_handler(event):
    await generate_image(event)
    raise events.StopPropagation


@events.register(events.NewMessage(pattern="/today"))
async def today_handler(event):
    await event.reply(f"📅 Сейчас: {get_date_time()}")
    raise events.StopPropagation