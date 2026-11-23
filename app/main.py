from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import FastAPI, Form, HTTPException
from fastapi import Request as FastAPIRequest
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.collectors.craigslist import parse_search_results
from app.collectors.types import NormalizedListing
from app.config import Settings
from app.db import create_database_engine
from app.services.listing_filters import ListingCard, ListingFilters, filter_and_sort_cards
from app.services.listing_state import (
    get_listing_first_seen,
    get_listing_states,
    set_listing_state,
    sync_listings,
)

BASE_DIR = Path(__file__).parent
CRAIGSLIST_SEARCH_URL = (
    "https://www.craigslist.org/search/area/austin?cat=msa&max_price=500&sort=date"
)

app = FastAPI(title="Gear Hound")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@lru_cache(maxsize=1)
def load_preview_listings() -> list[NormalizedListing]:
    settings = Settings()
    request = Request(CRAIGSLIST_SEARCH_URL, headers={"User-Agent": "GearHound/0.1"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    return parse_search_results(html, max_price_cents=settings.max_price * 100)


@lru_cache(maxsize=1)
def get_app_engine() -> Engine:
    return create_database_engine(Settings().database_url)


def parse_optional_nonnegative_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


@app.get("/")
def dashboard(
    request: FastAPIRequest,
    q: str = "",
    min_price: str = "",
    max_price: str = "",
    age_days: str = "",
    source: str = "all",
    category: str = "all",
    state: str = "all",
    sort: str = "newest",
):
    valid_sorts = {"newest", "oldest", "price_asc", "price_desc", "title"}
    selected_sort = sort if sort in valid_sorts else "newest"
    filters = ListingFilters(
        q=q,
        min_price=parse_optional_nonnegative_int(min_price),
        max_price=parse_optional_nonnegative_int(max_price),
        age_days=parse_optional_nonnegative_int(age_days),
        source=source,
        category=category,
        state=state,
        sort=selected_sort,  # type: ignore[arg-type]
    )
    error = None
    cards: list[ListingCard] = []
    source_options: list[tuple[str, str]] = []
    category_options: list[str] = []
    total_visible = 0
    try:
        listings = load_preview_listings()
        with Session(get_app_engine()) as session:
            sync_listings(session, listings)
            states = get_listing_states(session, listings)
            first_seen = get_listing_first_seen(session, listings)
        cards = [
            {
                "listing": listing,
                "state": states[(listing.source, listing.source_listing_id)],
                "first_seen_at": first_seen.get((listing.source, listing.source_listing_id)),
            }
            for listing in listings
            if states[(listing.source, listing.source_listing_id)] != "hidden"
        ]
        total_visible = len(cards)
        source_labels = {"craigslist": "Craigslist", "guitar-center": "Guitar Center"}
        source_options = [
            (value, source_labels.get(value, value.replace("-", " ").title()))
            for value in sorted({card["listing"].source for card in cards})
        ]
        category_options = sorted(
            {
                str(card["listing"].raw_metadata.get("category") or "Other/Oddball")
                for card in cards
            }
        )
        cards = filter_and_sort_cards(cards, filters)
    except (OSError, TimeoutError, ValueError) as exc:
        error = f"Craigslist could not be refreshed: {exc}"
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "cards": cards,
            "error": error,
            "filters": filters,
            "source_options": source_options,
            "category_options": category_options,
            "total_visible": total_visible,
        },
    )


@app.post("/listings/state")
def update_listing_state(
    source: str = Form(),
    source_listing_id: str = Form(),
    state: str = Form(),
    return_to: str = Form("/"),
) -> RedirectResponse:
    try:
        with Session(get_app_engine()) as session:
            set_listing_state(session, source, source_listing_id, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    safe_return = return_to if return_to.startswith("/") and not return_to.startswith("//") else "/"
    return RedirectResponse(url=safe_return, status_code=303)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gear-hound"}
