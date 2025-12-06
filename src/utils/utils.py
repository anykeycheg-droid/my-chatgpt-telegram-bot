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


def get_date_time():
    tz_name = os.getenv("TIMEZONE", "Europe/Moscow")

    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("Europe/Moscow")

    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
