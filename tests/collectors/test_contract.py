from app.collectors.types import CollectionResult, NormalizedListing


def test_collection_result_preserves_partial_source_results() -> None:
    listing = NormalizedListing(
        source="craigslist",
        source_listing_id="8001021969",
        title="FSOT oddball synth",
        price_cents=None,
        url="https://example.test/listing",
        location="Austin",
        source_category="electronics",
        image_url=None,
        raw_metadata={"trade": True},
    )

    result = CollectionResult(
        source="craigslist",
        listings=[listing],
        complete=False,
        error="Second results page failed",
    )

    assert result.listings == [listing]
    assert result.complete is False
    assert result.error == "Second results page failed"
