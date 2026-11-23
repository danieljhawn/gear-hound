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

    response = TestClient(main_module.app).get("/?min_price=&max_price=&age_days=")

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


def test_state_action_returns_to_active_filters(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine)
    client = TestClient(main_module.app)
    client.get("/")

    response = client.post(
        "/listings/state",
        data={
            "source": "craigslist",
            "source_listing_id": "abc123",
            "state": "interested",
            "return_to": "/?q=fender&sort=price_desc",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?q=fender&sort=price_desc"


def test_state_action_rejects_external_return_url(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine)
    client = TestClient(main_module.app)
    client.get("/")

    response = client.post(
        "/listings/state",
        data={
            "source": "craigslist",
            "source_listing_id": "abc123",
            "state": "interested",
            "return_to": "https://evil.example/",
        },
        follow_redirects=False,
    )

    assert response.headers["location"] == "/"


def test_combines_keyword_and_price_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    listings = [
        NormalizedListing(
            source="craigslist",
            source_listing_id="bass-1",
            title="Fender Jazz Bass",
            price_cents=45000,
            url="https://example.test/bass-1",
            location="Austin",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": "Bass", "is_trade": False},
        ),
        NormalizedListing(
            source="craigslist",
            source_listing_id="bass-2",
            title="Squier Bass Guitar",
            price_cents=20000,
            url="https://example.test/bass-2",
            location="Round Rock",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": "Bass", "is_trade": False},
        ),
        NormalizedListing(
            source="craigslist",
            source_listing_id="synth-1",
            title="Korg Synth",
            price_cents=30000,
            url="https://example.test/synth-1",
            location="Austin",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": "Synths/Keys", "is_trade": False},
        ),
    ]
    monkeypatch.setattr(main_module, "load_preview_listings", lambda: listings)
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine)

    response = TestClient(main_module.app).get("/?q=bass&min_price=300&max_price=500")

    assert response.status_code == 200
    assert "Fender Jazz Bass" in response.text
    assert "Squier Bass Guitar" not in response.text
    assert "Korg Synth" not in response.text
    assert 'value="bass"' in response.text
    assert 'value="300"' in response.text
    assert 'value="500"' in response.text


def test_filter_controls_retain_query_and_sort_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    listings = [
        NormalizedListing(
            source="craigslist",
            source_listing_id="cheap",
            title="Cheap Bass",
            price_cents=10000,
            url="https://example.test/cheap",
            location="Austin",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": "Bass", "is_trade": False},
        ),
        NormalizedListing(
            source="craigslist",
            source_listing_id="expensive",
            title="Expensive Bass",
            price_cents=40000,
            url="https://example.test/expensive",
            location="Austin",
            source_category="musical-instruments",
            image_url=None,
            raw_metadata={"category": "Bass", "is_trade": False},
        ),
    ]
    monkeypatch.setattr(main_module, "load_preview_listings", lambda: listings)
    monkeypatch.setattr(main_module, "get_app_engine", lambda: engine)

    response = TestClient(main_module.app).get(
        "/?age_days=7&source=craigslist&category=Bass&state=normal&sort=price_desc"
    )

    assert response.status_code == 200
    assert '<option value="7" selected>7 days</option>' in response.text
    assert '<option value="craigslist" selected>Craigslist</option>' in response.text
    assert '<option value="Bass" selected>Bass</option>' in response.text
    assert '<option value="normal" selected>Not favorited</option>' in response.text
    assert '<option value="price_desc" selected>Price: high to low</option>' in response.text
    assert response.text.index("Expensive Bass") < response.text.index("Cheap Bass")
