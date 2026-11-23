from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import FastAPI
from fastapi import Request as FastAPIRequest
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.collectors.craigslist import parse_search_results
from app.collectors.types import NormalizedListing
from app.config import Settings

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


@app.get("/")
def dashboard(request: FastAPIRequest):
    error = None
    try:
        listings = load_preview_listings()
    except (OSError, TimeoutError, ValueError) as exc:
        listings = []
        error = f"Craigslist could not be refreshed: {exc}"
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"listings": listings, "error": error},
    )


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gear-hound"}
