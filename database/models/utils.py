from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.types import DateTime
from sqlalchemy.ext.compiler import compiles


class utcnow(FunctionElement):
    type = DateTime
    inherit_cache = True


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kwargs):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"
