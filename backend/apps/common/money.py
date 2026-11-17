"""Exact money value object.

Money is stored as an integer number of minor units plus an ISO-4217 currency code. Python
``Decimal`` is used only at the boundary (parsing, formatting, conversion); arithmetic on stored
amounts is integer addition, so it can never drift. See ADR-0002 and ACCOUNTING_RULES.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

#: Product cap from SECURITY.md. Well inside BIGINT, and small enough that multiplying by a
#: plausible rate cannot overflow a BIGINT before the result is validated.
MAX_ABS_AMOUNT_MINOR = 10**15

#: Rates are NUMERIC(20,10): at most 10 decimal places and less than 10**10.
MAX_RATE = Decimal(10) ** 10
RATE_QUANTUM = Decimal("1E-10")

_DECIMAL_INPUT = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


class CurrencyMismatch(ValueError):
    """Two amounts in different currencies (or precisions) were combined."""


class InvalidPrecision(ValueError):
    """The input carries more decimal places than the currency allows."""


class AmountOverflow(ValueError):
    """The amount exceeds the product cap or the storage range."""


class InvalidRate(ValueError):
    """The exchange rate is not a positive, representable decimal."""


def _require_decimal_string(value: object, *, what: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a decimal string, got {type(value).__name__}")
    if not _DECIMAL_INPUT.match(value):
        raise ValueError(f"{what} must be a plain decimal string without exponent or grouping")
    return value


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount in one currency.

    ``minor_unit`` comes from the currency registry, never from the caller's guess. Equality
    includes currency and precision, so ``Money(100, "USD", 2) != Money(100, "USD", 0)``.
    """

    amount_minor: int
    currency: str
    minor_unit: int

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError("amount_minor must be an int")
        if abs(self.amount_minor) > MAX_ABS_AMOUNT_MINOR:
            raise AmountOverflow(
                f"amount exceeds the {MAX_ABS_AMOUNT_MINOR} minor-unit product limit"
            )
        if not isinstance(self.currency, str):
            raise TypeError("currency must be a string")
        code = self.currency.strip().upper()
        if not _CURRENCY_CODE.match(code):
            raise ValueError("currency must be a three-letter ISO-4217 code")
        if isinstance(self.minor_unit, bool) or not isinstance(self.minor_unit, int):
            raise TypeError("minor_unit must be an int")
        if not 0 <= self.minor_unit <= 6:
            raise ValueError("minor_unit must be between 0 and 6")
        object.__setattr__(self, "currency", code)

    @classmethod
    def parse(cls, value: str, currency: str, minor_unit: int = 2) -> Money:
        """Parse a decimal string without silently rounding.

        ``0.005`` in a 2-decimal currency is rejected, not rounded to ``0.01``.
        """
        text = _require_decimal_string(value, what="amount")
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:  # pragma: no cover - regex already guards this
            raise ValueError("amount is not a decimal number") from exc

        scaled = decimal_value.scaleb(minor_unit)
        if scaled != scaled.to_integral_value():
            raise InvalidPrecision(
                f"{text} has more than {minor_unit} decimal places for {currency.upper()}"
            )
        return cls(int(scaled), currency, minor_unit)

    def serialize(self) -> str:
        """Canonical decimal string with exactly ``minor_unit`` places. No grouping."""
        sign = "-" if self.amount_minor < 0 else ""
        digits = str(abs(self.amount_minor)).rjust(self.minor_unit + 1, "0")
        if self.minor_unit == 0:
            return f"{sign}{digits}"
        return f"{sign}{digits[: -self.minor_unit]}.{digits[-self.minor_unit :]}"

    def format(self, locale: str = "en-US") -> str:
        """Human display, e.g. ``1,250.50 USD``. V1 ships English grouping only."""
        if locale.replace("_", "-") != "en-US":
            raise ValueError(f"unsupported locale for money formatting: {locale}")
        magnitude = format(
            Decimal(abs(self.amount_minor)).scaleb(-self.minor_unit),
            f",.{self.minor_unit}f",
        )
        sign = "-" if self.amount_minor < 0 else ""
        return f"{sign}{magnitude} {self.currency}"

    def _require_same(self, other: Money) -> None:
        if self.currency != other.currency or self.minor_unit != other.minor_unit:
            raise CurrencyMismatch(
                f"cannot combine {self.currency} ({self.minor_unit} dp) with "
                f"{other.currency} ({other.minor_unit} dp)"
            )

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same(other)
        return Money(self.amount_minor + other.amount_minor, self.currency, self.minor_unit)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same(other)
        return Money(self.amount_minor - other.amount_minor, self.currency, self.minor_unit)

    def __neg__(self) -> Money:
        return Money(-self.amount_minor, self.currency, self.minor_unit)

    def __bool__(self) -> bool:
        return self.amount_minor != 0


def parse_rate(value: str) -> Decimal:
    """Validate an exchange rate for storage as NUMERIC(20,10).

    Extra precision is rejected: rounding a rate would change the money it produces.
    """
    text = _require_decimal_string(value, what="rate")
    rate = Decimal(text)
    if not rate.is_finite() or rate <= 0:
        raise InvalidRate("rate must be a finite positive decimal")
    if rate >= MAX_RATE:
        raise InvalidRate("rate is outside the NUMERIC(20,10) range")
    if rate != rate.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP):
        raise InvalidRate("rate has more than 10 decimal places")
    return rate


def convert(
    amount: Money,
    rate: Decimal,
    target_currency: str,
    target_minor_unit: int = 2,
) -> Money:
    """Convert at an explicit rate, rounding half-up exactly once at the target precision.

    ``rate`` is destination major units per one source major unit. The intermediate product keeps
    full precision; only the final target amount is quantized.
    """
    if not isinstance(rate, Decimal):
        raise TypeError("rate must be a Decimal")
    if not rate.is_finite() or rate <= 0:
        raise InvalidRate("rate must be a finite positive decimal")

    major = Decimal(amount.amount_minor).scaleb(-amount.minor_unit)
    quantum = Decimal(1).scaleb(-target_minor_unit)
    converted = (major * rate).quantize(quantum, rounding=ROUND_HALF_UP)
    return Money(int(converted.scaleb(target_minor_unit)), target_currency, target_minor_unit)
