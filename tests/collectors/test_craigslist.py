from pathlib import Path

from app.collectors.craigslist import parse_search_results


def test_parse_search_results_normalizes_and_filters_static_cards() -> None:
    fixture = Path("tests/fixtures/craigslist/search.html").read_text(encoding="utf-8")

    listings = parse_search_results(fixture, max_price_cents=50000)

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "craigslist"
    assert listing.source_listing_id == "abc123"
    assert listing.title == "Fender Standard Fat Strat MIM HSS"
    assert listing.price_cents == 39000
    assert listing.location == "Austin"
    assert listing.image_url == "https://images.example/fender.jpg"
    assert listing.url.endswith("/abc123")
