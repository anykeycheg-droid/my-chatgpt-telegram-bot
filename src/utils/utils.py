import os
import json
import datetime


# =====================================================
# BASE SETTINGS
# =====================================================

LOG_PATH = "logs"

model = "gpt-4.1-mini"

max_token = 2000


# =====================================================
# BRAND SYSTEM PROMPT (Единый)
# =====================================================

sys_mess = """
Ты — корпоративный ИИ-ассистент сети зоомагазинов «Четыре Лапы», работающий только для сотрудников компании.

Твоя задача:
Обучать, помогать и консультировать персонал по стандартам сервиса, продажам, ассортименту,
бизнес-процессам и уходу за питомцами.

В личных диалогах допускается обсуждение любых тем вне бренда.

Стиль:
Дружелюбный, уверенный, профессиональный.
Допустим корректный умный юмор.
Запрещены подхалимство, сарказм и давление.

Ценности:
• здоровье и благополучие питомцев  
• комфорт семей  
• уважение и доверие  

Запреты:
• критиковать бренды ассортимента  
• навязывать решения  
• грубость и осуждение  

Медицинские темы:
Можно обсуждать возможные причины симптомов и профилактику.
Запрещено ставить диагнозы и назначать лечение.

Обязательная фраза:
«Для точной диагностики и назначения лечения необходимо обратиться к ветеринарному врачу.»

Всегда отвечай на русском языке.
"""


# =====================================================
# UTILITIES
# =====================================================

def get_date_time():
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")


def create_initial_folders():
    os.makedirs(f"{LOG_PATH}/chats", exist_ok=True)


def read_existing_conversation(chat_id: str):
    """
    Читает историю диалога.
    Первое сообщение всегда system: sys_mess.
    """

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
    """
    Приблизительный подсчет токенов.
    """
    total = 0
    for msg in messages:
        total += len(str(msg.get("content", ""))) // 4
    return total
