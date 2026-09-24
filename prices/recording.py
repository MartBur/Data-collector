from datetime import date
from decimal import Decimal
from enum import Enum

from django.db import connection, transaction

from prices.models import PriceObservation, ShopPage

PLN_QUANTUM = Decimal("0.01")


class RecordOutcome(Enum):
    STORED = "stored"
    UNCHANGED = "unchanged"


def _as_pln(amount: Decimal) -> Decimal:
    """Return the amount as a two-decimal PLN value."""
    return amount.quantize(PLN_QUANTUM)


def latest_observation(
    shop_page: ShopPage,
    observed_date: date,
) -> PriceObservation | None:
    """Return the newest stored observation for this page on this date."""
    return (
        PriceObservation.objects.filter(
            shop_page=shop_page,
            observed_date=observed_date,
        )
        .order_by("-recorded_at", "-pk")
        .first()
    )


def price_on_date(shop_page: ShopPage, observed_date: date) -> Decimal | None:
    """Return the latest amount stored for this page on this date, or nothing."""
    observation = latest_observation(shop_page, observed_date)
    if observation is None:
        return None
    return observation.amount


def record_price(
    shop_page: ShopPage,
    amount: Decimal,
    observed_date: date,
) -> RecordOutcome:
    """Store the first amount for this date, and a later one only when it changes."""
    normalized = _as_pln(amount)
    with transaction.atomic():
        locked_page = shop_page
        if connection.features.has_select_for_update:
            locked_page = ShopPage.objects.select_for_update().get(pk=shop_page.pk)
        latest = latest_observation(locked_page, observed_date)
        if latest is not None and latest.amount == normalized:
            return RecordOutcome.UNCHANGED
        PriceObservation.objects.create(
            shop_page=locked_page,
            amount=normalized,
            observed_date=observed_date,
        )
    return RecordOutcome.STORED
