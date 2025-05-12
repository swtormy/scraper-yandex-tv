import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Optional
from pathlib import Path

import aiohttp
from loguru import logger
from pydantic import ValidationError
from tqdm.asyncio import tqdm

from config import settings
from database.uow.mldb import MldbUow
from .schemas import EventModel
from utils.error_handling import handle_critical_error
from utils.exceptions import SKKeyFetchError

BASE_URL = "https://tv.yandex.ru/api/213"
CHUNK_URL = "https://tv.yandex.ru/api/213/main/chunk"
SK_URL = "https://tv.yandex.ru/api/sk"

SK_FILE_PATH = Path(__file__).resolve().parent.parent / "sk_key.txt"


def _load_sk_from_file() -> Optional[str]:
    if SK_FILE_PATH.exists():
        try:
            with open(SK_FILE_PATH, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    logger.info(f"X-TV-SK ключ загружен из файла: {key}...")
                    return key
                else:
                    logger.warning(f"Файл {SK_FILE_PATH} пуст.")
                    return None
        except Exception as e:
            logger.error(f"Ошибка чтения файла {SK_FILE_PATH}: {e}")
            return None
    else:
        logger.info(f"Файл {SK_FILE_PATH} не найден.")
        return None


def _save_sk_to_file(sk_key: str) -> None:
    try:
        with open(SK_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(sk_key)
        logger.info(f"Новый X-TV-SK ключ сохранен в {SK_FILE_PATH}: {sk_key[:10]}...")
    except Exception as e:
        logger.error(f"Ошибка сохранения X-TV-SK ключа в файл {SK_FILE_PATH}: {e}")


async def _fetch_sk_key(
    session: aiohttp.ClientSession,
    cookies: Dict[str, str],
    base_headers: Dict[str, str],
) -> Optional[str]:
    """Получает ключ X-TV-SK с сервера Яндекс.ТВ."""
    logger.info("Запрос ключа X-TV-SK...")
    try:
        request_headers = base_headers.copy()
        if cookies:
            request_headers["Cookie"] = "; ".join(
                [f"{k}={v}" for k, v in cookies.items()]
            )

        async with session.get(SK_URL, headers=request_headers, ssl=False) as response:
            response.raise_for_status()
            data = await response.json()
            sk_key_value = data.get("sk", {}).get("key")
            if sk_key_value:
                logger.info(f"Успешно получен X-TV-SK ключ: {sk_key_value[:10]}...")
                return sk_key_value
            else:
                logger.error("Ключ 'sk.key' не найден в ответе от /api/sk.")
                logger.debug(f"Полный ответ от /api/sk: {data}")
                return None
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP ошибка при запросе X-TV-SK ключа: {e.status} {e.message}")
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе X-TV-SK ключа: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON при запросе X-TV-SK ключа: {e}")
    except Exception as e:
        logger.exception("Неожиданная ошибка при запросе X-TV-SK ключа.")
    return None


async def _fetch_schedule_page(
    session: aiohttp.ClientSession, url: str, params: dict, headers: dict
) -> dict | None:
    """Вспомогательная функция для получения одной страницы расписания."""
    try:
        async with session.get(
            url, params=params, headers=headers, ssl=False
        ) as response:
            response.raise_for_status()
            raw_text = await response.text()

            data = json.loads(raw_text)
            logger.debug(f"Успешно получен ответ от {response.url}")
            return data
    except aiohttp.ClientResponseError as e:
        logger.error(
            f"HTTP ошибка при запросе к {url} с параметрами {params}: {e.status} {e.message}"
        )
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе к {url}: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON от {url}: {e}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при запросе к {url}: {e}")
    return None


def _parse_event_data(event_dict: dict, channel_title: str) -> Optional[Dict]:
    """Извлекает и преобразует данные одного события для сохранения в БД."""
    try:
        event = EventModel.model_validate(event_dict)

        start_time_aware: datetime = datetime.fromisoformat(event.start)
        end_time_aware: datetime = datetime.fromisoformat(event.finish)

        start_time_naive: datetime = start_time_aware.replace(tzinfo=None)
        end_time_naive: datetime = end_time_aware.replace(tzinfo=None)

        start_time_utc: datetime = start_time_aware.astimezone(ZoneInfo("UTC"))
        end_time_utc: datetime = end_time_aware.astimezone(ZoneInfo("UTC"))

        program_id = event.program.id if event.program else None
        program_title = event.program.title if event.program else None
        program_type = (
            event.program.type.name if event.program and event.program.type else None
        )

        episode_id = event.episode.id if event.episode else None
        episode_title = event.episode.title if event.episode else None

        return {
            "event_id": event.id,
            "channel_title": channel_title,
            "event_title": event.title,
            "start_time": start_time_naive,
            "end_time": end_time_naive,
            "start_time_utc": start_time_utc,
            "end_time_utc": end_time_utc,
            "program_id": program_id,
            "program_title": program_title,
            "episode_id": episode_id,
            "episode_title": episode_title,
            "program_type": program_type,
            "is_live": event.live,
            "has_reminder": event.hasReminder,
            "has_started": event.hasStarted,
            "has_finished": event.hasFinished,
            "is_now": event.isNow,
        }
    except ValidationError as e:
        logger.warning(
            f"Ошибка валидации Pydantic для события: {e}. Данные: {event_dict}"
        )
    except KeyError as e:
        logger.warning(
            f"Отсутствует обязательное поле '{e}' в данных события: {event_dict.get('id', '?')}"
        )
    except ValueError as e:
        logger.warning(
            f"Ошибка преобразования данных для события {event_dict.get('id', '?')}: {e}"
        )
    except Exception as e:
        logger.exception(
            f"Неожиданная ошибка при парсинге события {event_dict.get('id', '?')}: {e}"
        )
    return None


@handle_critical_error()
async def parse_yandex_schedule():
    """
    Основная функция для парсинга расписания Яндекс.Телепрограммы за 5 дней
    и сохранения/обновления данных в БД с использованием bulk upsert.
    """
    logger.info("Начало парсинга расписания Яндекс.ТВ...")

    cookie_i = settings.YANDEX_TV_COOKIE_I
    x_tv_sk_current = _load_sk_from_file()
    if not x_tv_sk_current:
        x_tv_sk_current = settings.YANDEX_TV_X_SK

    if not cookie_i or not x_tv_sk_current:
        logger.error(
            "Не заданы кука YANDEX_TV_COOKIE_I и/или X-TV-SK (ни в файле, ни в окружении). Прерывание парсинга."
        )
        return

    initial_cookies_dict = {"i": cookie_i}
    initial_headers_dict = {
        "X-Requested-With": "XMLHttpRequest",
        "X-TV-SK": x_tv_sk_current,
    }

    async with aiohttp.ClientSession() as session:
        new_sk_key = await _fetch_sk_key(
            session, initial_cookies_dict, initial_headers_dict
        )

        if not new_sk_key:
            raise SKKeyFetchError("Не удалось получить актуальный X-TV-SK ключ. Прерывание парсинга.")

        if new_sk_key != x_tv_sk_current:
            _save_sk_to_file(new_sk_key)
            x_tv_sk_current = new_sk_key

        working_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-TV-SK": x_tv_sk_current,
            "Cookie": f"i={cookie_i}",
        }

        today = datetime.now(timezone.utc).date()
        all_parsed_events_for_upsert = []
        raw_events_for_logging = []

        i = 0
        while True:
            target_date = today + timedelta(days=i)
            target_date_str = target_date.strftime("%Y-%m-%d")

            base_params = {
                "date": target_date_str,
                "grid": "sport",
                "period": "all-day",
            }

            initial_data = await _fetch_schedule_page(
                session, BASE_URL, base_params, working_headers
            )

            if initial_data is None:
                logger.warning(
                    f"Не удалось получить данные для {target_date_str}. Прекращаем парсинг следующих дней."
                )
                break

            day_schedules = list(initial_data["schedule"]["schedules"])
            schedule_map = initial_data["schedule"].get("scheduleMap", [])

            if len(schedule_map) > 1:
                for chunk_info_raw in schedule_map[1:]:
                    try:
                        chunk_info = {
                            "id": int(chunk_info_raw["id"]),
                            "offset": int(chunk_info_raw["offset"]),
                            "limit": int(chunk_info_raw["limit"]),
                        }
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(
                            f"Некорректная структура chunk_info для {target_date_str}: {chunk_info_raw}, ошибка: {e}"
                        )
                        continue

                    chunk_params = {
                        "date": target_date_str,
                        "grid": "sport",
                        "period": "all-day",
                        "page": chunk_info["id"],
                        "offset": chunk_info["offset"],
                        "limit": chunk_info["limit"],
                    }
                    chunk_data = await _fetch_schedule_page(
                        session, CHUNK_URL, chunk_params, working_headers
                    )
                    if chunk_data and "schedules" in chunk_data:
                        day_schedules.extend(chunk_data["schedules"])
                    else:
                        logger.warning(
                            f"Не удалось получить данные чанка page={chunk_info['id']} для {target_date_str}"
                        )

            day_event_count = 0
            for sch_item in day_schedules:
                channel_info = sch_item.get("channel")
                if not channel_info or not channel_info.get("title"):
                    logger.debug("Пропуск расписания без информации о канале.")
                    continue
                channel_title = channel_info["title"]

                for event_dict in sch_item.get("events", []):
                    raw_events_for_logging.append(event_dict)
                    parsed_data = _parse_event_data(event_dict, channel_title)
                    if parsed_data:
                        all_parsed_events_for_upsert.append(parsed_data)
                        day_event_count += 1

            logger.info(
                f"Парсинг за {target_date_str}: Найдено {day_event_count} событий."
            )

            if day_event_count == 0:
                logger.info(
                    f"Не найдено событий для {target_date_str}. Прекращаем парсинг следующих дней."
                )
                break

            await asyncio.sleep(1)
            i += 1

    total_events = len(all_parsed_events_for_upsert)
    logger.info(
        f"Всего собрано {total_events} событий. Выполняю дедупликацию по event_id..."
    )

    unique_events_map = {}
    for event_data in all_parsed_events_for_upsert:
        event_id = event_data.get("event_id")
        if event_id:
            unique_events_map[event_id] = event_data

    deduplicated_events = list(unique_events_map.values())
    final_event_count = len(deduplicated_events)
    if total_events != final_event_count:
        logger.info(
            f"После дедупликации осталось {final_event_count} уникальных событий (удалено {total_events - final_event_count})."
        )
    else:
        logger.info("Дубликатов не найдено.")

    log_file_path = os.path.join("logs", "parsed_events_raw.json")
    try:
        os.makedirs("logs", exist_ok=True)
        with open(log_file_path, "w", encoding="utf-8") as f:
            json.dump(raw_events_for_logging, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Сырые словари {len(raw_events_for_logging)} событий сохранены в {log_file_path}"
        )
    except Exception as save_err:
        logger.error(
            f"Не удалось сохранить сырые события в {log_file_path}: {save_err}"
        )

    if not deduplicated_events:
        logger.info("Нет событий для сохранения в БД.")
        return

    uow = MldbUow()
    batch_size = 50
    try:
        async with uow:
            logger.info(
                f"Начинаю сохранение/обновление {final_event_count} событий в БД..."
            )
            pbar = tqdm(
                total=final_event_count, desc="Сохранение в БД", unit=" событий"
            )
            for i in range(0, final_event_count, batch_size):
                batch = deduplicated_events[i : i + batch_size]
                if not batch:
                    continue

                try:
                    await uow.tv_schedule.bulk_upsert(batch)
                    pbar.update(len(batch))
                except Exception as batch_err:
                    pbar.close()
                    logger.error(
                        f"Ошибка при обработке батча начиная с индекса {i}: {batch_err}"
                    )
                    logger.debug(f"Данные батча с ошибкой: {batch}")
                    raise
            pbar.close()
            logger.info(
                f"Все батчи ({final_event_count} событий) подготовлены. Попытка выполнить commit..."
            )
            await uow.commit()
            logger.success(
                f"Commit выполнен успешно. {final_event_count} событий сохранено/обновлено."
            )

    except Exception as e:
        logger.exception(f"Ошибка во время обработки данных или commit: {e}")
        try:
            await uow.rollback()
            logger.warning("Транзакция БД отменена из-за ошибки.")
        except Exception as rb_err:
            logger.error(f"Ошибка при попытке отката транзакции: {rb_err}")

    logger.info("Парсинг и сохранение расписания Яндекс.ТВ завершены.")
