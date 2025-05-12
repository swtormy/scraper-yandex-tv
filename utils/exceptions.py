class ParserCriticalError(Exception):
    """Базовый класс для критических ошибок парсера."""

    pass


class SKKeyFetchError(ParserCriticalError):
    """Ошибка получения X-TV-SK ключа."""

    pass
