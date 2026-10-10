from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from prices.models import PriceObservation, Product, ShopPage

WINDOW_LENGTH: int = 30


class ShopRow(TypedDict):
    label: str
    url: str
    today_amount: Decimal | None
    cheapest: bool


class ShopSeries(TypedDict):
    label: str
    amounts: list[Decimal | None]


class CardFigures(TypedDict):
    dates: list[date]
    shops: list[ShopRow]
    series: list[ShopSeries]
    lowest_recorded: Decimal | None


def card_figures(product: Product, today: date) -> CardFigures:
    """Return one product's shop rows, 30-day series, and lowest recorded price."""
    dates = _window_dates(today)
    pages = list(product.shop_pages.order_by("pk"))
    daily = _latest_daily_amounts(pages)
    present_today: list[Decimal] = []
    for page in pages:
        amount = daily.get((page.pk, today))
        if amount is not None:
            present_today.append(amount)
    lowest_today = min(present_today) if present_today else None
    shops: list[ShopRow] = []
    series: list[ShopSeries] = []
    for page in pages:
        label = page.get_shop_display()
        today_amount = daily.get((page.pk, today))
        shops.append(
            {
                "label": label,
                "url": page.url,
                "today_amount": today_amount,
                "cheapest": today_amount is not None and today_amount == lowest_today,
            }
        )
        series.append(
            {
                "label": label,
                "amounts": [daily.get((page.pk, day)) for day in dates],
            }
        )
    lowest_recorded = min(daily.values()) if daily else None
    return {
        "dates": dates,
        "shops": shops,
        "series": series,
        "lowest_recorded": lowest_recorded,
    }


def _window_dates(today: date) -> list[date]:
    """Return the 30 calendar dates ending on today, oldest first."""
    start = today - timedelta(days=WINDOW_LENGTH - 1)
    return [start + timedelta(days=offset) for offset in range(WINDOW_LENGTH)]


def _latest_daily_amounts(
    pages: list[ShopPage],
) -> dict[tuple[int, date], Decimal]:
    """Return each page's latest amount on each stored date.

    The first row for a page and date wins. Rows are ordered like
    ``price_on_date``: newest ``recorded_at``, then highest id.
    """
    if not pages:
        return {}
    observations = PriceObservation.objects.filter(shop_page__in=pages).order_by(
        "shop_page_id",
        "observed_date",
        "-recorded_at",
        "-pk",
    )
    latest: dict[tuple[int, date], Decimal] = {}
    for observation in observations:
        key = (observation.shop_page_id, observation.observed_date)
        if key not in latest:
            latest[key] = observation.amount
    return latest
