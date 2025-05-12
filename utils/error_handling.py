import functools
import traceback
import re

from loguru import logger

from config import settings
from utils.notifications import TGBotAPI, ParseMode


def escape_markdown_v2(text: str) -> str:
    escape_chars = r"[_*\[\]()~`>#+-=|{}.!]"
    return re.sub(escape_chars, r"\\1", text)


def handle_critical_error():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Critical error in {func.__name__}: {e}")

                tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
                traceback_str = "".join(tb_lines[-15:])

                func_name_escaped = escape_markdown_v2(func.__name__)
                error_type_escaped = escape_markdown_v2(type(e).__name__)
                error_message_escaped = escape_markdown_v2(str(e))
                traceback_escaped = escape_markdown_v2(traceback_str)

                error_message_tg = (
                    f"🚨 *CRITICAL ERROR* in `{func_name_escaped}` 🚨\\n\\n"
                    f"*Error Type:* `{error_type_escaped}`\\n"
                    f"*Message:* `{error_message_escaped}`\\n\\n"
                    f"*Traceback (last 15 lines):*\\n"
                    f"```\n{traceback_escaped}\n```"
                )

                tg_token = settings.TELEGRAM_BOT_TOKEN
                tg_chat_id = settings.TELEGRAM_CHAT_ID

                if tg_token and tg_chat_id:
                    try:
                        notifier = TGBotAPI(token=tg_token)
                        await notifier.send_message(
                            chat_id=tg_chat_id,
                            text=error_message_tg,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        logger.info(
                            f"Sent critical error notification for {func.__name__} to Telegram."
                        )
                    except Exception as notify_err:
                        logger.error(
                            f"Failed to send Telegram notification: {notify_err}"
                        )
                else:
                    logger.warning(
                        "Telegram token or chat ID not configured. Skipping notification."
                    )

                raise e

        return wrapper

    return decorator
