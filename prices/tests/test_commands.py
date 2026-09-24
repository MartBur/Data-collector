from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from prices.collect import FetchFailed
from prices.models import PriceObservation, Product, Shop, ShopPage


ROSSMANN_HTML = (
    '<span data-testid="product-price"><span>12</span><span>,50</span></span>'
)
DOZ_HTML = (
    '<div class="product-card-price-box"><div class="price">19,00 zł</div></div>'
)


class RecordCommandTests(TestCase):
    def setUp(self) -> None:
        product = Product.objects.create(name="Shampoo")
        self.rossmann: ShopPage = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        self.doz: ShopPage = ShopPage.objects.create(
            product=product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/product/1",
        )
        self.today = timezone.localdate()

    def _observations(self, page: ShopPage) -> int:
        return PriceObservation.objects.filter(
            shop_page=page,
            observed_date=self.today,
        ).count()

    def test_record_prices_stores_a_change_then_skips_the_same_amount(self) -> None:
        def fake_fetch(url: str) -> str:
            if "rossmann" in url:
                return ROSSMANN_HTML
            return DOZ_HTML

        with patch("prices.collect.fetch_html", side_effect=fake_fetch):
            first = StringIO()
            call_command("record_prices", stdout=first)
            second = StringIO()
            call_command("record_prices", stdout=second)

        self.assertIn("stored", first.getvalue())
        self.assertNotIn("unchanged", first.getvalue())
        self.assertIn("unchanged", second.getvalue())
        self.assertNotIn("stored", second.getvalue())
        self.assertEqual(self._observations(self.rossmann), 1)
        self.assertEqual(self._observations(self.doz), 1)
        self.assertEqual(
            self.rossmann.observations.get(observed_date=self.today).amount,
            Decimal("12.50"),
        )
        self.assertEqual(
            self.doz.observations.get(observed_date=self.today).amount,
            Decimal("19.00"),
        )

    def test_failed_retry_keeps_an_earlier_row_and_stores_the_other_shop(self) -> None:
        def fail_rossmann(url: str) -> str:
            if "rossmann" in url:
                raise FetchFailed("timed out")
            return DOZ_HTML

        with patch("prices.collect.fetch_html", side_effect=fail_rossmann):
            PriceObservation.objects.create(
                shop_page=self.rossmann,
                amount=Decimal("10.00"),
                observed_date=self.today,
            )
            out = StringIO()
            call_command("record_prices", stdout=out)

        self.assertIn("gap", out.getvalue())
        self.assertIn("stored", out.getvalue())
        self.assertEqual(self._observations(self.rossmann), 1)
        self.assertEqual(
            self.rossmann.observations.get(observed_date=self.today).amount,
            Decimal("10.00"),
        )
        self.assertEqual(self._observations(self.doz), 1)
        self.assertEqual(
            self.doz.observations.get(observed_date=self.today).amount,
            Decimal("19.00"),
        )

    def test_rossmann_command_leaves_other_shops_untouched(self) -> None:
        def rossmann_only(url: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=rossmann_only):
            out = StringIO()
            call_command("record_rossmann_prices", stdout=out)

        self.assertIn("stored", out.getvalue())
        self.assertEqual(self._observations(self.rossmann), 1)
        self.assertEqual(self._observations(self.doz), 0)
