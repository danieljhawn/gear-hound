import pytest

from app.services.filtering import should_keep_listing


@pytest.mark.parametrize(
    ("title", "price_cents", "is_trade", "expected"),
    [
        ("Korg synth", 50000, False, True),
        ("Korg synth", 50001, False, False),
        ("Korg synth", None, False, False),
        ("FSOT Korg synth for bass", None, True, True),
        ("FSOT Korg synth", 90000, True, True),
        ("FSOT hi-hat cymbals", None, True, False),
    ],
)
def test_listing_filter_applies_price_ceiling_without_losing_trade_only_ads(
    title: str, price_cents: int | None, is_trade: bool, expected: bool
) -> None:
    assert (
        should_keep_listing(
            title=title,
            price_cents=price_cents,
            is_trade=is_trade,
            max_price_cents=50000,
        )
        is expected
    )
