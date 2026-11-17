"""Exact money arithmetic: no floats, no silent rounding."""

from decimal import Decimal

import pytest

from apps.common.money import (
    AmountOverflow,
    CurrencyMismatch,
    InvalidPrecision,
    Money,
    convert,
    parse_rate,
)


def test_parse_keeps_minor_units_exact() -> None:
    money = Money.parse("1250.50", "USD")
    assert money.amount_minor == 125050
    assert money.currency == "USD"
    assert money.minor_unit == 2


def test_parse_normalizes_currency_case() -> None:
    assert Money.parse("1.00", "usd").currency == "USD"


def test_parse_accepts_integer_and_leading_decimal() -> None:
    assert Money.parse("42", "USD").amount_minor == 4200
    assert Money.parse("0.5", "USD").amount_minor == 50
    assert Money.parse("-0.05", "USD").amount_minor == -5


def test_parse_accepts_zero_decimal_currency() -> None:
    money = Money.parse("4100", "KHR", minor_unit=0)
    assert money.amount_minor == 4100
    assert money.serialize() == "4100"


def test_parse_rejects_extra_precision() -> None:
    with pytest.raises(InvalidPrecision):
        Money.parse("0.005", "USD")


def test_parse_rejects_malformed_input() -> None:
    for value in ("", " ", "1,250.50", "1e3", "NaN", "Infinity", "--1.00", "1.2.3"):
        with pytest.raises(ValueError):
            Money.parse(value, "USD")


def test_parse_rejects_non_string_input() -> None:
    with pytest.raises(TypeError):
        Money.parse(12.5, "USD")  # type: ignore[arg-type]


def test_parse_rejects_amounts_above_product_limit() -> None:
    with pytest.raises(AmountOverflow):
        Money(10**15 + 1, "USD", 2)


def test_add_different_currencies_raises() -> None:
    with pytest.raises(CurrencyMismatch):
        Money.parse("1.00", "USD") + Money.parse("1.00", "KHR")


def test_add_different_minor_units_raises() -> None:
    with pytest.raises(CurrencyMismatch):
        Money(100, "USD", 2) + Money(100, "USD", 0)


def test_add_and_subtract_are_exact() -> None:
    total = Money.parse("0.10", "USD") + Money.parse("0.20", "USD")
    assert total.amount_minor == 30
    assert total.serialize() == "0.30"
    assert (total - Money.parse("0.30", "USD")).amount_minor == 0


def test_negation_roundtrips() -> None:
    money = Money.parse("1250.50", "USD")
    negated = -money
    assert negated.serialize() == "-1250.50"
    assert -negated == money


def test_serialize_roundtrips() -> None:
    money = Money(-5, "USD", 2)
    assert money.serialize() == "-0.05"
    assert Money.parse(money.serialize(), "USD") == money


def test_format_is_canonical() -> None:
    assert Money.parse("1250.50", "USD").format("en-US") == "1,250.50 USD"
    assert Money.parse("-1250.50", "USD").format() == "-1,250.50 USD"
    assert Money.parse("0", "USD").format() == "0.00 USD"


def test_convert_rounds_half_up_once() -> None:
    result = convert(Money.parse("100.00", "USD"), Decimal("4100"), "KHR")
    assert result.amount_minor == 41_000_000
    assert result.currency == "KHR"


def test_convert_half_up_at_exact_boundary() -> None:
    result = convert(Money.parse("1.00", "USD"), Decimal("1.005"), "USD")
    assert result.amount_minor == 101


def test_convert_keeps_negative_direction() -> None:
    result = convert(Money.parse("-100.00", "USD"), Decimal("4100"), "KHR")
    assert result.amount_minor == -41_000_000


def test_convert_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        convert(Money.parse("1.00", "USD"), Decimal("0"), "KHR")


def test_parse_rate_accepts_positive_decimal() -> None:
    assert parse_rate("4100.0000000001") == Decimal("4100.0000000001")


def test_parse_rate_rejects_invalid_values() -> None:
    for value in ("0", "-1", "NaN", "Infinity", "1.00000000001"):
        with pytest.raises(ValueError):
            parse_rate(value)
    with pytest.raises(TypeError):
        parse_rate(4100)  # type: ignore[arg-type]


def test_money_rejects_invalid_metadata() -> None:
    with pytest.raises(ValueError):
        Money(1, "US", 2)
    with pytest.raises(ValueError):
        Money(1, "USD", -1)
    with pytest.raises(TypeError):
        Money(1.5, "USD", 2)  # type: ignore[arg-type]
