import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from __version__ import __version__
from src.bot import bot

BOT_NAME = "Dushnilla"

try:
    BOT_VERSION = __version__
except:
    BOT_VERSION = "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(bot())
        logging.info("Bot task started")
    except Exception as e:
        logging.critical(f"Bot startup error: {e}")
        raise e

    yield

    logging.info("Application shutting down")


app = FastAPI(lifespan=lifespan, title=BOT_NAME)


@app.get("/")
def root():
    return f"{BOT_NAME} {BOT_VERSION} is running"


@app.get("/health")
def health():
    return "ok"


