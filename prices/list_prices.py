from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, TypedDict

from prices.models import PriceObservation, Product, ShopPage


class ShopOffer(TypedDict):
    label: str
    url: str


class ListPrice(TypedDict):
    amount: Decimal | None
    day: Literal["today", "yesterday", "none"]
    shops: list[ShopOffer]
    matches_lowest_stored: bool


def list_prices(products: list[Product], today: date) -> dict[int, ListPrice]:
    """Return each product's today-or-yesterday amount, tied shops, and low flag."""
    summaries: dict[int, ListPrice] = {}
    if not products:
        return summaries
    product_ids = [product.pk for product in products]
    pages_by_product, daily = _latest_daily_amounts(product_ids)
    yesterday = today - timedelta(days=1)
    for product in products:
        summaries[product.pk] = _list_price(
            pages_by_product[product.pk],
            daily,
            today,
            yesterday,
        )
    return summaries


def _latest_daily_amounts(
    product_ids: list[int],
) -> tuple[dict[int, list[ShopPage]], dict[tuple[int, date], Decimal]]:
    """Return each page's latest amount on each stored date.

    The first row for a page and date wins. Rows are ordered like
    ``price_on_date``: newest ``recorded_at``, then highest id.
    Pages for a product stay in pk order.
    """
    pages_by_product: dict[int, list[ShopPage]] = {
        product_id: [] for product_id in product_ids
    }
    daily: dict[tuple[int, date], Decimal] = {}
    seen_pages: set[int] = set()
    observations = (
        PriceObservation.objects.filter(shop_page__product_id__in=product_ids)
        .select_related("shop_page")
        .order_by("shop_page_id", "observed_date", "-recorded_at", "-pk")
    )
    for observation in observations:
        page = observation.shop_page
        key = (page.pk, observation.observed_date)
        if key not in daily:
            daily[key] = observation.amount
        if page.pk not in seen_pages:
            seen_pages.add(page.pk)
            pages_by_product[page.product_id].append(page)
    return pages_by_product, daily


def _list_price(
    pages: list[ShopPage],
    daily: dict[tuple[int, date], Decimal],
    today: date,
    yesterday: date,
) -> ListPrice:
    """Return one product's summary for the injected today."""
    today_amount, today_shops = _tied_offers(pages, daily, today)
    if today_amount is not None:
        return {
            "amount": today_amount,
            "day": "today",
            "shops": today_shops,
            "matches_lowest_stored": _matches_lowest_stored(
                today_amount,
                pages,
                daily,
            ),
        }
    yesterday_amount, yesterday_shops = _tied_offers(pages, daily, yesterday)
    if yesterday_amount is not None:
        return {
            "amount": yesterday_amount,
            "day": "yesterday",
            "shops": yesterday_shops,
            "matches_lowest_stored": False,
        }
    return {
        "amount": None,
        "day": "none",
        "shops": [],
        "matches_lowest_stored": False,
    }


def _tied_offers(
    pages: list[ShopPage],
    daily: dict[tuple[int, date], Decimal],
    observed_date: date,
) -> tuple[Decimal | None, list[ShopOffer]]:
    """Return the minimum price on this date and every shop tied for it."""
    priced: list[tuple[ShopPage, Decimal]] = []
    for page in pages:
        amount = daily.get((page.pk, observed_date))
        if amount is not None:
            priced.append((page, amount))
    if not priced:
        return None, []
    lowest = min(amount for _page, amount in priced)
    shops: list[ShopOffer] = [
        {"label": page.get_shop_display(), "url": page.url}
        for page, amount in priced
        if amount == lowest
    ]
    return lowest, shops


def _matches_lowest_stored(
    amount: Decimal,
    pages: list[ShopPage],
    daily: dict[tuple[int, date], Decimal],
) -> bool:
    """Return True when this amount equals the lowest stored daily price."""
    page_ids = {page.pk for page in pages}
    lowest = min(
        stored
        for (page_id, _observed_date), stored in daily.items()
        if page_id in page_ids
    )
    return amount == lowest
