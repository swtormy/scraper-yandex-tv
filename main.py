import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

import aiocron
from database.uow.mldb import init_db
from parsers.yandex_tv_parser import parse_yandex_schedule
from config import settings
from utils.notifications import TGBotAPI


@aiocron.crontab("*/5 * * * *")
async def scheduled_parsing_job():

    logger.info("Запуск запланированной задачи парсинга...")
    try:
        await parse_yandex_schedule()
        logger.info("Задача парсинга успешно завершена.")
    except Exception as e:
        logger.exception("Ошибка во время выполнения задачи парсинга: {}", e)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Инициализация приложения...")
    await init_db()
    logger.info("База данных инициализирована.")

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            notifier = TGBotAPI()
            await notifier.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text="📺 Yandex TV Parser запущен!",
                parse_mode=None,
            )
            logger.info("Сообщение о старте приложения отправлено в Telegram.")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о старте в Telegram: {e}")

    logger.info("Приложение успешно запущено.")

    yield

    logger.info("Приложение корректно остановлено.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
