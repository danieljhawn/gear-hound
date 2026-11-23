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
from app.services.listing_state import get_listing_states, set_listing_state, sync_listings

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


@app.get("/")
def dashboard(request: FastAPIRequest):
    error = None
    cards: list[dict[str, object]] = []
    try:
        listings = load_preview_listings()
        with Session(get_app_engine()) as session:
            sync_listings(session, listings)
            states = get_listing_states(session, listings)
        cards = [
            {"listing": listing, "state": states[(listing.source, listing.source_listing_id)]}
            for listing in listings
            if states[(listing.source, listing.source_listing_id)] != "hidden"
        ]
    except (OSError, TimeoutError, ValueError) as exc:
        error = f"Craigslist could not be refreshed: {exc}"
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"cards": cards, "error": error},
    )


@app.post("/listings/state")
def update_listing_state(
    source: str = Form(),
    source_listing_id: str = Form(),
    state: str = Form(),
) -> RedirectResponse:
    try:
        with Session(get_app_engine()) as session:
            set_listing_state(session, source, source_listing_id, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url="/", status_code=303)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gear-hound"}
