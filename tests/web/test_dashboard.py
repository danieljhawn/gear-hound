import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.collectors.types import NormalizedListing
from app.models import Base


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
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main_module, "load_preview_listings", lambda: [listing], raising=False)
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine)

    response = TestClient(main_module.app).get("/")

    assert response.status_code == 200
    assert '<link rel="stylesheet" href="/static/css/app.css">' in response.text
    assert "Gear Hound" in response.text
    assert "Fender Fat Strat" in response.text
    assert "$390" in response.text
    assert "Austin" in response.text
    assert "https://images.example/fender.jpg" in response.text


def test_favorite_and_ignore_actions_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    listing = NormalizedListing(
        source="craigslist",
        source_listing_id="abc123",
        title="Fender Fat Strat",
        price_cents=39000,
        url="https://example.test/abc123",
        location="Austin",
        source_category="musical-instruments",
        image_url=None,
        raw_metadata={"category": "Guitar", "is_trade": False},
    )
    monkeypatch.setattr(main_module, "load_preview_listings", lambda: [listing])
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine, raising=False)
    client = TestClient(main_module.app)

    initial = client.get("/")
    assert "Favorite" in initial.text
    assert "Ignore" in initial.text

    favorite = client.post(
        "/listings/state",
        data={"source": "craigslist", "source_listing_id": "abc123", "state": "interested"},
        follow_redirects=False,
    )
    assert favorite.status_code == 303
    favorited = client.get("/")
    assert 'class="card interested"' in favorited.text
    assert "Unfavorite" in favorited.text

    ignored = client.post(
        "/listings/state",
        data={"source": "craigslist", "source_listing_id": "abc123", "state": "hidden"},
        follow_redirects=False,
    )
    assert ignored.status_code == 303
    assert "Fender Fat Strat" not in client.get("/").text
