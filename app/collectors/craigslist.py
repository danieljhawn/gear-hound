import json
import re
from decimal import Decimal
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.collectors.types import NormalizedListing
from app.services.classifier import classify_title
from app.services.filtering import should_keep_listing

TRADE_PATTERN = re.compile(
    r"\b(?:fsot|wttf?|for sale or trade|trade for|consider trades)\b", re.IGNORECASE
)


def _price_to_cents(value: str) -> int | None:
    cleaned = re.sub(r"[^0-9.]", "", value)
    if not cleaned:
        return None
    return int(Decimal(cleaned) * 100)


def parse_search_results(html: str, *, max_price_cents: int) -> list[NormalizedListing]:
    soup = BeautifulSoup(html, "html.parser")
    image_by_title: dict[str, str] = {}
    data_script = soup.select_one("#ld_searchpage_results")
    if data_script and data_script.string:
        data = json.loads(data_script.string)
        for element in data.get("itemListElement", []):
            item = element.get("item", {})
            images = item.get("image") or []
            if item.get("name") and images:
                image_by_title[item["name"]] = images[0]

    listings: list[NormalizedListing] = []
    for card in soup.select("li.cl-static-search-result"):
        link = card.select_one("a[href]")
        title_element = card.select_one(".title")
        if link is None or title_element is None:
            continue
        title = title_element.get_text(" ", strip=True)
        price_element = card.select_one(".price")
        price_cents = _price_to_cents(price_element.get_text(strip=True)) if price_element else None
        is_trade = bool(TRADE_PATTERN.search(title))
        if not should_keep_listing(
            title=title,
            price_cents=price_cents,
            is_trade=is_trade,
            max_price_cents=max_price_cents,
        ):
            continue
        url = str(link["href"])
        location_element = card.select_one(".location")
        location = location_element.get_text(" ", strip=True) if location_element else None
        source_id = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        listings.append(
            NormalizedListing(
                source="craigslist",
                source_listing_id=source_id,
                title=title,
                price_cents=price_cents,
                url=url,
                location=location,
                source_category="musical-instruments",
                image_url=image_by_title.get(title),
                raw_metadata={"is_trade": is_trade, "category": classify_title(title)},
            )
        )
    return listings
