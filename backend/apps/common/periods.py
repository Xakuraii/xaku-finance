"""Financial period resolution in the workspace timezone.

Periods are calendar concepts: a month starts at 00:00 local time and ends at 23:59:59.999999 local
time, then converts to UTC for querying. Using UTC boundaries instead would put a transaction made
at 00:30 on the first of the month into the previous month. See ACCOUNTING_RULES.md 4.3.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PeriodName = Literal["calendar_month", "calendar_week", "calendar_year", "custom"]

PERIOD_NAMES: frozenset[str] = frozenset(
    {"calendar_month", "calendar_week", "calendar_year", "custom"}
)


def _zone(name: str) -> ZoneInfo:
    if not isinstance(name, str) or not name:
        raise ValueError("timezone must be an IANA zone name")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown timezone: {name}") from exc


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive local date range with the timezone it was resolved in."""

    start: date
    end: date
    timezone: str
    resolved_from: str

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise TypeError("DateRange bounds must be dates")
        if isinstance(self.start, datetime) or isinstance(self.end, datetime):
            raise TypeError("DateRange bounds must be dates, not datetimes")
        if self.end < self.start:
            raise ValueError("DateRange end must not be before start")
        _zone(self.timezone)
        if self.resolved_from not in PERIOD_NAMES:
            raise ValueError(f"unknown period source: {self.resolved_from}")


def resolve_period(
    *,
    period: str,
    timezone: str,
    anchor: date | None = None,
    start: date | None = None,
    end: date | None = None,
    week_start: int = 1,
) -> DateRange:
    """Resolve a named or custom period.

    ``week_start`` uses ISO numbering: 1 = Monday ... 7 = Sunday. For named periods the anchor
    defaults to "today" in the workspace timezone; custom periods ignore it.
    """
    if period not in PERIOD_NAMES:
        raise ValueError(f"unknown period: {period}")
    zone = _zone(timezone)

    if period == "custom":
        if start is None or end is None:
            raise ValueError("custom periods require both start and end")
        if anchor is not None:
            raise ValueError("custom periods do not accept an anchor")
        return DateRange(start=start, end=end, timezone=timezone, resolved_from="custom")

    if start is not None or end is not None:
        raise ValueError(f"{period} periods do not accept explicit start/end")
    if not 1 <= week_start <= 7:
        raise ValueError("week_start must be between 1 (Monday) and 7 (Sunday)")

    local_today = anchor if anchor is not None else datetime.now(zone).date()
    if isinstance(local_today, datetime):
        raise TypeError("anchor must be a date, not a datetime")

    if period == "calendar_month":
        first = local_today.replace(day=1)
        last = local_today.replace(day=calendar.monthrange(local_today.year, local_today.month)[1])
    elif period == "calendar_year":
        first = local_today.replace(month=1, day=1)
        last = local_today.replace(month=12, day=31)
    else:  # calendar_week
        first = local_today - timedelta(days=(local_today.isoweekday() - week_start) % 7)
        last = first + timedelta(days=6)

    return DateRange(start=first, end=last, timezone=timezone, resolved_from=period)


def days_remaining(period: DateRange, today: date) -> int:
    """Inclusive days from ``today`` through ``period.end``; 0 outside the period."""
    if isinstance(today, datetime):
        raise TypeError("today must be a date; convert timestamps in the service layer")
    if not isinstance(today, date):
        raise TypeError("today must be a date")
    if today < period.start or today > period.end:
        return 0
    return (period.end - today).days + 1


def utc_bounds(period: DateRange) -> tuple[datetime, datetime]:
    """Convert the inclusive local range to inclusive UTC bounds."""
    zone = _zone(period.timezone)
    start_local = datetime.combine(period.start, time.min, tzinfo=zone)
    end_local = datetime.combine(period.end, time.max, tzinfo=zone)
    return (
        start_local.astimezone(UTC),
        end_local.astimezone(UTC),
    )
