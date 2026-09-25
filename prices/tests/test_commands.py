from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from prices.collect import (
    MAX_RESPONSE_BYTES,
    FetchFailed,
    _SameHostRedirectHandler,
    _read_limited,
    fetch_html,
)
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
        def fake_fetch(url: str, _shop: str) -> str:
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
        def fail_rossmann(url: str, _shop: str) -> str:
            if "rossmann" in url:
                raise FetchFailed("timed out")
            return DOZ_HTML

        with patch("prices.collect.fetch_html", side_effect=fail_rossmann) as fetch:
            PriceObservation.objects.create(
                shop_page=self.rossmann,
                amount=Decimal("10.00"),
                observed_date=self.today,
            )
            out = StringIO()
            call_command("record_prices", stdout=out)

        rossmann_calls = [
            call for call in fetch.call_args_list if "rossmann" in call.args[0]
        ]
        self.assertEqual(len(rossmann_calls), 2)

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
        def rossmann_only(url: str, _shop: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=rossmann_only):
            out = StringIO()
            call_command("record_rossmann_prices", stdout=out)

        self.assertIn("stored", out.getvalue())
        self.assertEqual(self._observations(self.rossmann), 1)
        self.assertEqual(self._observations(self.doz), 0)

    def test_rossmann_command_skips_an_unchanged_price(self) -> None:
        def rossmann_only(url: str, _shop: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=rossmann_only):
            first = StringIO()
            call_command("record_rossmann_prices", stdout=first)
            second = StringIO()
            call_command("record_rossmann_prices", stdout=second)

        self.assertIn("stored", first.getvalue())
        self.assertIn("unchanged", second.getvalue())
        self.assertEqual(self._observations(self.rossmann), 1)
        self.assertEqual(self._observations(self.doz), 0)

    def test_rossmann_command_leaves_a_gap_after_one_retry(self) -> None:
        def fail_rossmann(url: str, _shop: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            raise FetchFailed("timed out")

        with patch("prices.collect.fetch_html", side_effect=fail_rossmann) as fetch:
            out = StringIO()
            call_command("record_rossmann_prices", stdout=out)

        self.assertEqual(fetch.call_count, 2)
        self.assertIn("gap", out.getvalue())
        self.assertEqual(self._observations(self.rossmann), 0)
        self.assertEqual(self._observations(self.doz), 0)

    def test_rejected_amount_leaves_a_gap_and_records_the_other_shop(self) -> None:
        def fake_fetch(url: str, _shop: str) -> str:
            return ROSSMANN_HTML if "rossmann" in url else DOZ_HTML

        def fake_read(shop: str, html: str) -> Decimal | None:
            if shop == Shop.ROSSMANN:
                return Decimal("-1.00")
            return Decimal("19.00")

        with (
            patch("prices.collect.fetch_html", side_effect=fake_fetch),
            patch("prices.collect.read_shop_price", side_effect=fake_read),
        ):
            out = StringIO()
            call_command("record_prices", stdout=out)

        self.assertIn("gap", out.getvalue())
        self.assertIn("stored", out.getvalue())
        self.assertEqual(self._observations(self.rossmann), 0)
        self.assertEqual(self._observations(self.doz), 1)


class ShopFetchTests(TestCase):
    def test_fetch_rejects_http_and_a_foreign_host(self) -> None:
        with self.assertRaises(FetchFailed):
            fetch_html("http://www.rossmann.pl/product/1", Shop.ROSSMANN)
        with self.assertRaises(FetchFailed):
            fetch_html("https://www.doz.pl/product/1", Shop.ROSSMANN)

    def test_redirect_rejects_a_foreign_host(self) -> None:
        handler = _SameHostRedirectHandler(Shop.ROSSMANN)
        with self.assertRaises(FetchFailed):
            handler.redirect_request(
                urllib_request(),
                _Response(),
                302,
                "Found",
                _Headers(),
                "https://www.doz.pl/product/1",
            )

    def test_oversized_response_is_rejected(self) -> None:
        payload = b"x" * (MAX_RESPONSE_BYTES + 1)
        with self.assertRaises(FetchFailed):
            _read_limited(_OversizedResponse(payload), MAX_RESPONSE_BYTES)


def urllib_request() -> object:
    from urllib.request import Request

    return Request("https://www.rossmann.pl/product/1")


class _Response:
    pass


class _OversizedResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload: bytes = payload

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.payload
        return self.payload[:size]


class _Headers:
    pass
