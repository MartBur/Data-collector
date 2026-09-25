from datetime import date
from decimal import Decimal

from django.test import TestCase

from prices.models import PriceObservation, Product, Shop, ShopPage
from prices.recording import RecordOutcome, price_on_date, record_price


class RecordingTests(TestCase):
    def setUp(self) -> None:
        product = Product.objects.create(name="Shampoo")
        self.page: ShopPage = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        self.monday: date = date(2026, 9, 21)
        self.tuesday: date = date(2026, 9, 22)

    def test_first_read_of_a_date_is_stored(self) -> None:
        outcome = record_price(self.page, Decimal("10.00"), self.monday)
        self.assertEqual(outcome, RecordOutcome.STORED)
        self.assertEqual(self.page.observations.count(), 1)
        self.assertEqual(price_on_date(self.page, self.monday), Decimal("10.00"))

    def test_same_day_unchanged_amount_is_skipped(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        outcome = record_price(self.page, Decimal("10.00"), self.monday)
        self.assertEqual(outcome, RecordOutcome.UNCHANGED)
        self.assertEqual(self.page.observations.count(), 1)

    def test_same_day_changed_amount_is_stored(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        outcome = record_price(self.page, Decimal("12.00"), self.monday)
        self.assertEqual(outcome, RecordOutcome.STORED)
        self.assertEqual(self.page.observations.count(), 2)
        self.assertEqual(price_on_date(self.page, self.monday), Decimal("12.00"))

    def test_latest_of_day_is_the_reported_price(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        record_price(self.page, Decimal("12.00"), self.monday)
        record_price(self.page, Decimal("11.50"), self.monday)
        self.assertEqual(price_on_date(self.page, self.monday), Decimal("11.50"))

    def test_date_with_no_row_has_no_price(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        self.assertIsNone(price_on_date(self.page, self.tuesday))

    def test_next_day_stores_an_equal_amount(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        outcome = record_price(self.page, Decimal("10.00"), self.tuesday)
        self.assertEqual(outcome, RecordOutcome.STORED)
        self.assertEqual(
            PriceObservation.objects.filter(observed_date=self.tuesday).count(),
            1,
        )
        self.assertEqual(price_on_date(self.page, self.tuesday), Decimal("10.00"))
        self.assertEqual(price_on_date(self.page, self.monday), Decimal("10.00"))

    def test_non_positive_amount_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            record_price(self.page, Decimal("-1.00"), self.monday)
        self.assertEqual(self.page.observations.count(), 0)

    def test_later_tuesday_read_of_the_same_amount_adds_no_row(self) -> None:
        record_price(self.page, Decimal("10.00"), self.monday)
        record_price(self.page, Decimal("10.00"), self.tuesday)
        outcome = record_price(self.page, Decimal("10.00"), self.tuesday)
        self.assertEqual(outcome, RecordOutcome.UNCHANGED)
        self.assertEqual(
            PriceObservation.objects.filter(observed_date=self.tuesday).count(),
            1,
        )
