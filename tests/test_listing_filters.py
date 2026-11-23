from datetime import UTC, datetime, timedelta

import pytest

from app.collectors.types import NormalizedListing
from app.services.listing_filters import ListingCard, ListingFilters, filter_and_sort_cards


def card(
    listing_id: str,
    *,
    source: str = "craigslist",
    category: str = "Bass",
    state: str = "normal",
    price_cents: int | None = 10000,
    first_seen_at: datetime | None = None,
    title: str | None = None,
) -> ListingCard:
    return {
        "listing": NormalizedListing(
            source=source,
            source_listing_id=listing_id,
            title=title or listing_id,
            price_cents=price_cents,
            url=f"https://example.test/{listing_id}",
            location="Austin",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": category, "is_trade": False},
        ),
        "state": state,
        "first_seen_at": first_seen_at,
    }


def test_combines_source_category_and_state_filters() -> None:
    cards = [
        card("wanted", source="craigslist", category="Bass", state="interested"),
        card("wrong-state", source="craigslist", category="Bass", state="normal"),
        card("wrong-category", source="craigslist", category="Effects", state="interested"),
        card("wrong-source", source="guitar-center", category="Bass", state="interested"),
    ]

    result = filter_and_sort_cards(
        cards,
        ListingFilters(source="craigslist", category="Bass", state="interested"),
    )

    assert [item["listing"].source_listing_id for item in result] == ["wanted"]


def test_filters_by_first_seen_age() -> None:
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    cards = [
        card("recent", first_seen_at=now - timedelta(hours=12)),
        card("old", first_seen_at=now - timedelta(days=4)),
        card("unknown", first_seen_at=None),
    ]

    result = filter_and_sort_cards(cards, ListingFilters(age_days=1), now=now)

    assert [item["listing"].source_listing_id for item in result] == ["recent"]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("newest", ["high", "low", "trade"]),
        ("oldest", ["low", "high", "trade"]),
        ("price_asc", ["low", "high", "trade"]),
        ("price_desc", ["high", "low", "trade"]),
        ("title", ["trade", "high", "low"]),
    ],
)
def test_sorts_cards(sort: str, expected: list[str]) -> None:
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    cards = [
        card("high", price_cents=45000, first_seen_at=now, title="Beta Bass"),
        card("trade", price_cents=None, first_seen_at=None, title="Alpha Trade"),
        card("low", price_cents=10000, first_seen_at=now - timedelta(days=2), title="Gamma Pedal"),
    ]

    result = filter_and_sort_cards(cards, ListingFilters(sort=sort))  # type: ignore[arg-type]

    assert [item["listing"].source_listing_id for item in result] == expected


def test_keyword_terms_match_independently_across_title_and_location() -> None:
    cards = [
        card("match", title="Fender Jazz Bass"),
        card("missing-term", title="Fender Stratocaster"),
    ]

    result = filter_and_sort_cards(cards, ListingFilters(q="bass fender"))

    assert [item["listing"].source_listing_id for item in result] == ["match"]


def test_max_price_keeps_unpriced_trade_but_min_price_excludes_it() -> None:
    trade = card("trade", price_cents=None)

    under_max = filter_and_sort_cards([trade], ListingFilters(max_price=500))
    over_min = filter_and_sort_cards([trade], ListingFilters(min_price=1))

    assert [item["listing"].source_listing_id for item in under_max] == ["trade"]
    assert over_min == []
