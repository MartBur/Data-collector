import json
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from prices.models import Shop
from prices.recording import normalize_pln

_ROSSMANN_PRICE = re.compile(
    r'data-testid="product-price">\s*'
    r'<span[^>]*>\s*(\d+)\s*</span>\s*'
    r'<span[^>]*>\s*,(\d+)',
    re.DOTALL,
)
_DOZ_PRICE = re.compile(
    r'class="product-card-price-box">.*?class="price">\s*(\d+),(\d+)\s*zł',
    re.DOTALL,
)
_SUPERPHARM_JSON_LD = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_GEMINI_PRICE = re.compile(
    r'<meta name="product:price:amount" content="(\d+\.\d+)"',
)


def _positive_pln(value: object) -> Decimal | None:
    """Return a positive two-decimal PLN amount, or nothing when unusable."""
    try:
        return normalize_pln(Decimal(str(value)))
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


def _from_parts(whole: str, fraction: str) -> Decimal | None:
    """Return a two-decimal PLN amount, or nothing when it cannot be stored."""
    return _positive_pln(f"{whole}.{fraction}")


def read_rossmann_price(html: str) -> Decimal | None:
    """Return the current Rossmann selling price, ignoring the unit price."""
    match = _ROSSMANN_PRICE.search(html)
    if match is None:
        return None
    return _from_parts(match.group(1), match.group(2))


def read_doz_price(html: str) -> Decimal | None:
    """Return the DOZ product price, ignoring delivery amounts."""
    match = _DOZ_PRICE.search(html)
    if match is None:
        return None
    return _from_parts(match.group(1), match.group(2))


def _offer_price(node: object) -> Decimal | None:
    """Return the selling price of a schema.org Product, ignoring other offers."""
    if isinstance(node, dict):
        if node.get("@type") == "Product":
            offers = node.get("offers")
            if isinstance(offers, dict) and "price" in offers:
                return _positive_pln(offers["price"])
            if isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict) and "price" in offer:
                        amount = _positive_pln(offer["price"])
                        if amount is not None:
                            return amount
        for value in node.values():
            found = _offer_price(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _offer_price(item)
            if found is not None:
                return found
    return None


def read_superpharm_price(html: str) -> Decimal | None:
    """Return this page's selling price, not another capacity shown beside it."""
    for match in _SUPERPHARM_JSON_LD.finditer(html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        price = _offer_price(data)
        if price is not None:
            return price
    return None


def read_gemini_price(html: str) -> Decimal | None:
    """Return the Gemini selling price from the product price meta tag."""
    match = _GEMINI_PRICE.search(html)
    if match is None:
        return None
    whole, fraction = match.group(1).split(".")
    return _from_parts(whole, fraction)


_READERS: dict[str, Callable[[str], Decimal | None]] = {
    Shop.ROSSMANN: read_rossmann_price,
    Shop.DOZ: read_doz_price,
    Shop.SUPERPHARM: read_superpharm_price,
    Shop.GEMINI: read_gemini_price,
}


def read_shop_price(shop: str, html: str) -> Decimal | None:
    """Return the promo price for one shop's saved page, or nothing."""
    reader = _READERS.get(shop)
    if reader is None:
        return None
    return reader(html)
