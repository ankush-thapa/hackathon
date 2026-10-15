from sqlalchemy import BigInteger, Column, DateTime, FetchedValue
from sqlalchemy.dialects.mysql import BIGINT, DATETIME
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


USER_ID_TYPE = BigInteger().with_variant(BIGINT(unsigned=True), "mysql")
DATETIME_MILLISECONDS = DateTime().with_variant(DATETIME(fsp=3), "mysql")
MYSQL_TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class _CurrentTimestamp(FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(_CurrentTimestamp)
def _current_timestamp(element, compiler, **kwargs):
    return "CURRENT_TIMESTAMP"


@compiles(_CurrentTimestamp, "mysql")
def _mysql_current_timestamp(element, compiler, **kwargs):
    return "CURRENT_TIMESTAMP(3)"


class _UpdatedTimestamp(FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(_UpdatedTimestamp)
def _updated_timestamp(element, compiler, **kwargs):
    return "CURRENT_TIMESTAMP"


@compiles(_UpdatedTimestamp, "mysql")
def _mysql_updated_timestamp(element, compiler, **kwargs):
    # MySQL requires ON UPDATE in the server default; server_onupdate alone
    # only tells SQLAlchemy that the database generates the value.
    return "CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"


class TimestampMixin:
    created_at = Column(
        DATETIME_MILLISECONDS, nullable=False, server_default=_CurrentTimestamp()
    )
    updated_at = Column(
        DATETIME_MILLISECONDS,
        nullable=False,
        server_default=_UpdatedTimestamp(),
        server_onupdate=FetchedValue(),
    )
