import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from __version__ import __version__
from bot import bot

# ===================
# Basic App Settings
# ===================

BOT_NAME = "Dushnilla — ассистент сети «Четыре Лапы»"

try:
    BOT_VERSION = __version__
except Exception:
    BOT_VERSION = "unknown"

# ===================
# Logging
# ===================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("main")

# ===================
# App lifecycle
# ===================

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None

    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(bot())
        logger.info("✅ Bot background task started")
    except Exception as e:
        logger.exception("❌ Fatal error while starting bot")
        raise e

    yield

    if task:
        task.cancel()
        logger.info("🛑 Bot task cancelled")

    logger.info("🧹 Application shutdown completed")

# ===================
# FastAPI app
# ===================

app = FastAPI(
    title=BOT_NAME,
    version=BOT_VERSION,
    lifespan=lifespan
)

# ===================
# Routes
# ===================

@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "service": BOT_NAME,
        "version": BOT_VERSION,
        "status": "running"
    }


@app.get("/health", response_class=JSONResponse)
async def health():
    return {
        "status": "ok"
    }
