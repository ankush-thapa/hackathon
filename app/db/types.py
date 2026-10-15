from sqlalchemy import BigInteger, DateTime
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement

# BIGINT UNSIGNED on MySQL, plain BIGINT elsewhere (SQLite in tests).
UnsignedBigInt = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")

# DATETIME(3) on MySQL.
DateTime3 = DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")


class now_ms(FunctionElement):
    """DEFAULT CURRENT_TIMESTAMP(3)"""

    type = DateTime()
    inherit_cache = True


class now_ms_on_update(FunctionElement):
    """DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) (MySQL only)"""

    type = DateTime()
    inherit_cache = True


@compiles(now_ms)
def _now_ms_default(element, compiler, **kw):
    return "CURRENT_TIMESTAMP"


@compiles(now_ms, "mysql")
def _now_ms_mysql(element, compiler, **kw):
    return "CURRENT_TIMESTAMP(3)"


@compiles(now_ms_on_update)
def _upd_default(element, compiler, **kw):
    return "CURRENT_TIMESTAMP"


@compiles(now_ms_on_update, "mysql")
def _upd_mysql(element, compiler, **kw):
    return "CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"
