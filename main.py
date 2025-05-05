import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

import aiocron
from database.uow.mldb import init_db
from parsers.yandex_tv_parser import parse_yandex_schedule


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

    logger.info("Запуск первичной задачи парсинга в фоне...")
    initial_parse_task = asyncio.create_task(parse_yandex_schedule())
    

    logger.info("Запуск планировщика задач aiocron...")
    

    logger.info("Приложение успешно запущено.")

    yield

    
    logger.info("Начинаю корректную остановку...")

    
    if initial_parse_task and not initial_parse_task.done():
        logger.info("Отмена первоначальной задачи парсинга...")
        initial_parse_task.cancel()
        try:
            await initial_parse_task
        except asyncio.CancelledError:
            logger.info("Первоначальная задача парсинга отменена.")
        except Exception as e:
            logger.error(f"Ошибка при отмене первоначальной задачи: {e}")

    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if tasks:
        logger.info(f"Отмена {len(tasks)} фоновых задач (включая aiocron)...")
        for task in tasks:
            task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        cancelled_count = sum(1 for r in results if isinstance(r, asyncio.CancelledError))
        error_count = sum(1 for r in results if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError))
        logger.info(f"Фоновые задачи завершены. Отменено: {cancelled_count}, Ошибки: {error_count}")
        for i, result in enumerate(results):
             if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                 task_name = tasks[i].get_name() if hasattr(tasks[i], 'get_name') else f"Task-{i}"
                 logger.error(f"Ошибка в фоновой задаче '{task_name}': {result}")
    else:
        logger.info("Нет активных фоновых задач для отмены.")
    logger.info("Приложение корректно остановлено.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
