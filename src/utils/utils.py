import os
import pytz
from datetime import datetime

LOG_PATH = "logs/"

def create_initial_folders():
    for folder in [
        f"{LOG_PATH}chats",
        f"{LOG_PATH}chats/history",
        f"{LOG_PATH}chats/session",
        f"{LOG_PATH}media"
    ]:
        os.makedirs(folder, exist_ok=True)


def get_date_time(zone: str | None = None) -> str:
    """
    Возвращает текущую дату/время.
    Если передан zone — используем её.
    Если нет — берём TIMEZONE из переменных окружения
    (по умолчанию Europe/Moscow).
    """
    tz_name = zone or os.getenv("TIMEZONE", "Europe/Moscow")
    try:
        timezone = pytz.timezone(tz_name)
    except Exception:
        timezone = pytz.timezone("Europe/Moscow")
    return datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")


BOT_NAME = "Dushnilla"