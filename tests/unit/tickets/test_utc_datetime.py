from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import sqlite

from app.domain.types import UtcDateTime

DIALECT = sqlite.dialect()


def test_utc_datetime_converts_to_utc_rejects_naive_and_reads_aware():
    """SPEC-TKT-14 · TC-TKT-14d"""
    column_type = UtcDateTime()
    plus_three = timezone(timedelta(hours=3))

    stored = column_type.process_bind_param(datetime(2026, 1, 1, 12, 0, tzinfo=plus_three), DIALECT)
    with pytest.raises(ValueError):
        column_type.process_bind_param(datetime(2026, 1, 1, 12, 0), DIALECT)
    read = column_type.process_result_value(datetime(2026, 1, 1, 9, 0), DIALECT)

    assert stored == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert read == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert read.tzinfo is UTC
