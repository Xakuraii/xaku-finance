"""Properties that must hold for every amount we can store."""

from hypothesis import given
from hypothesis import strategies as st

from apps.common.money import Money

MINOR_LIMIT = 10**15


@given(st.integers(min_value=-MINOR_LIMIT, max_value=MINOR_LIMIT))
def test_roundtrip_minor_units(value: int) -> None:
    money = Money(value, "USD", 2)
    assert Money.parse(money.serialize(), "USD").amount_minor == value


@given(
    st.integers(min_value=-MINOR_LIMIT, max_value=MINOR_LIMIT),
    st.integers(min_value=-MINOR_LIMIT, max_value=MINOR_LIMIT),
)
def test_addition_then_subtraction_is_identity(left: int, right: int) -> None:
    a = Money(left, "USD", 2)
    b = Money(right, "USD", 2)
    if abs(left + right) > MINOR_LIMIT:
        return
    assert (a + b) - b == a


@given(st.integers(min_value=-MINOR_LIMIT, max_value=MINOR_LIMIT))
def test_negation_is_involutive(value: int) -> None:
    money = Money(value, "USD", 2)
    once = -money
    twice = -once
    assert twice == money
