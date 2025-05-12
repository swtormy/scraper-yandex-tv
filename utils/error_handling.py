import functools
import traceback

from loguru import logger

from config import settings
from utils.notifications import TGBotAPI, ParseMode


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

                error_message = (
                    f"🚨 *CRITICAL ERROR* in `{func.__name__}` 🚨\\n\\n"
                    f"*Error Type:* `{type(e).__name__}`\\n"
                    f"*Message:* `{str(e)}`\\n\\n"
                    f"*Traceback (last 15 lines):*\\n"
                    f"```\n{traceback_str}\n```"
                )

                tg_token = settings.TELEGRAM_BOT_TOKEN
                tg_chat_id = settings.TELEGRAM_CHAT_ID

                if tg_token and tg_chat_id:
                    try:
                        notifier = TGBotAPI(token=tg_token)
                        await notifier.send_message(
                            chat_id=tg_chat_id,
                            text=error_message,
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
