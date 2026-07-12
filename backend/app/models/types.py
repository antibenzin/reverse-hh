"""SQLAlchemy column types shared across models."""

from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, TypeDecorator, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY


def sa_enum(enum_class: type[PyEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_class,
        name=name,
        values_callable=lambda obj: [member.value for member in obj],
        native_enum=False,
        validate_strings=True,
    )


class UuidArray(TypeDecorator[list[uuid.UUID] | None]):
    """PostgreSQL UUID[]; JSON string list in SQLite tests."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Uuid(as_uuid=True)))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return [str(item) for item in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [uuid.UUID(item) if isinstance(item, str) else item for item in value]
