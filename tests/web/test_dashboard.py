import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.collectors.types import NormalizedListing


def test_dashboard_renders_listing_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    listing = NormalizedListing(
        source="craigslist",
        source_listing_id="abc123",
        title="Fender Fat Strat",
        price_cents=39000,
        url="https://example.test/abc123",
        location="Austin",
        source_category="musical-instruments",
        image_url="https://images.example/fender.jpg",
        raw_metadata={"category": "Guitar", "is_trade": False},
    )
    monkeypatch.setattr(main_module, "load_preview_listings", lambda: [listing], raising=False)

    response = TestClient(main_module.app).get("/")

    assert response.status_code == 200
    assert "Gear Hound" in response.text
    assert "Fender Fat Strat" in response.text
    assert "$390" in response.text
    assert "Austin" in response.text
    assert "https://images.example/fender.jpg" in response.text
