from datetime import UTC, date, datetime

import pytest

from apps.common.periods import DateRange, days_remaining, resolve_period, utc_bounds


def test_month_bounds_are_local_and_inclusive() -> None:
    period = resolve_period(
        period="calendar_month", timezone="Asia/Phnom_Penh", anchor=date(2026, 11, 17)
    )
    assert (period.start, period.end) == (date(2026, 11, 1), date(2026, 11, 30))
    assert period.timezone == "Asia/Phnom_Penh"
    assert period.resolved_from == "calendar_month"


def test_month_end_handles_february() -> None:
    period = resolve_period(period="calendar_month", timezone="UTC", anchor=date(2024, 2, 10))
    assert period.end == date(2024, 2, 29)


def test_week_respects_week_start() -> None:
    monday = resolve_period(
        period="calendar_week", timezone="UTC", anchor=date(2026, 11, 17), week_start=1
    )
    assert (monday.start, monday.end) == (date(2026, 11, 16), date(2026, 11, 22))

    sunday = resolve_period(
        period="calendar_week", timezone="UTC", anchor=date(2026, 11, 17), week_start=7
    )
    assert (sunday.start, sunday.end) == (date(2026, 11, 15), date(2026, 11, 21))


def test_year_bounds() -> None:
    period = resolve_period(period="calendar_year", timezone="UTC", anchor=date(2026, 6, 1))
    assert (period.start, period.end) == (date(2026, 1, 1), date(2026, 12, 31))


def test_unknown_period_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_period(period="fortnight", timezone="UTC")


def test_unknown_timezone_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_period(period="calendar_month", timezone="Mars/Olympus_Mons")


def test_custom_requires_both_dates() -> None:
    with pytest.raises(ValueError):
        resolve_period(period="custom", timezone="UTC", start=date(2026, 11, 1))
    with pytest.raises(ValueError):
        resolve_period(period="custom", timezone="UTC", end=date(2026, 11, 30))


def test_custom_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        resolve_period(
            period="custom",
            timezone="UTC",
            start=date(2026, 11, 30),
            end=date(2026, 11, 1),
        )


def test_custom_is_inclusive() -> None:
    period = resolve_period(
        period="custom", timezone="UTC", start=date(2026, 11, 1), end=date(2026, 11, 30)
    )
    assert (period.start, period.end, period.resolved_from) == (
        date(2026, 11, 1),
        date(2026, 11, 30),
        "custom",
    )


def test_days_remaining_is_inclusive() -> None:
    period = resolve_period(period="calendar_month", timezone="UTC", anchor=date(2026, 11, 17))
    assert days_remaining(period, date(2026, 11, 17)) == 14
    assert days_remaining(period, date(2026, 11, 30)) == 1
    assert days_remaining(period, date(2026, 10, 31)) == 0
    assert days_remaining(period, date(2026, 12, 1)) == 0


def test_days_remaining_rejects_naive_datetime() -> None:
    period = resolve_period(period="calendar_month", timezone="UTC", anchor=date(2026, 11, 17))
    with pytest.raises(TypeError):
        days_remaining(period, datetime(2026, 11, 17))  # type: ignore[arg-type]


def test_first_local_day_not_previous_utc_day() -> None:
    period = resolve_period(
        period="calendar_month", timezone="Asia/Phnom_Penh", anchor=date(2026, 11, 1)
    )
    start_utc, end_utc = utc_bounds(period)
    assert start_utc == datetime(2026, 10, 31, 17, 0, tzinfo=UTC)
    assert end_utc == datetime(2026, 11, 30, 16, 59, 59, 999999, tzinfo=UTC)


def test_dst_boundary_month() -> None:
    # US DST ends on 2026-11-01. The start is EDT (UTC-4); the end is EST (UTC-5).
    period = resolve_period(
        period="calendar_month", timezone="America/New_York", anchor=date(2026, 11, 10)
    )
    start_utc, end_utc = utc_bounds(period)
    assert start_utc == datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
    assert end_utc == datetime(2026, 12, 1, 4, 59, 59, 999999, tzinfo=UTC)


def test_date_range_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError):
        DateRange(
            start=date(2026, 11, 30),
            end=date(2026, 11, 1),
            timezone="UTC",
            resolved_from="custom",
        )
