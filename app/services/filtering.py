from app.services.classifier import classify_title


def should_keep_listing(
    *,
    title: str,
    price_cents: int | None,
    is_trade: bool,
    max_price_cents: int,
) -> bool:
    if classify_title(title) is None:
        return False
    if is_trade:
        return True
    return price_cents is not None and 0 <= price_cents <= max_price_cents
