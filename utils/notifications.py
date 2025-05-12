import aiohttp
from enum import StrEnum

from loguru import logger

from config import settings


class ParseMode(StrEnum):
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"
    MARKDOWN_V2 = "MarkdownV2"


class TGBotAPI:
    COMMON_HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/"
        "537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }

    def __init__(self, token: str | None = None):
        self._token = token or settings.TELEGRAM_BOT_TOKEN
        if not self._token:
            raise ValueError("Telegram bot token is not configured.")
        self._base_url = f"https://api.telegram.org/bot{self._token}"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: dict | None = None,
        params: dict | None = None,
        data: dict | None = None,
    ) -> aiohttp.ClientResponse | None:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method=method,
                    url=self._base_url + endpoint,
                    headers=headers or self.COMMON_HEADERS,
                    params=params,
                    data=data,
                    ssl=False,
                ) as response:
                    response.raise_for_status()
                    logger.debug(f"Telegram API request to {endpoint} successful.")
                    return response
            except aiohttp.ClientResponseError as e:
                logger.error(
                    f"Telegram API HTTP error: {e.status} {e.message} for {method} {endpoint}"
                )
            except aiohttp.ClientError as e:
                logger.error(f"Telegram API client error: {e} for {method} {endpoint}")
            except Exception:
                logger.exception(
                    f"Unexpected error during Telegram API request to {endpoint}"
                )
            return None

    async def send_message(
        self, chat_id: int | str, text: str, parse_mode: ParseMode | None = None
    ):
        if not chat_id:
            logger.warning("Telegram chat_id is not configured, cannot send message.")
            return

        max_length = 4096
        if len(text) > max_length:
            text = text[: max_length - 4] + "\\n..."
            logger.warning("Message text truncated due to Telegram length limits.")

        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode.value

        await self._make_request(method="POST", endpoint="/sendMessage", data=data)
