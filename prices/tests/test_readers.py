from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from prices.models import Shop
from prices.readers import (
    read_doz_price,
    read_gemini_price,
    read_rossmann_price,
    read_superpharm_price,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ShopReaderTests(TestCase):
    def test_rossmann_fixture_is_the_current_price(self) -> None:
        self.assertEqual(read_rossmann_price(_html("rossmann.html")), Decimal("5.39"))

    def test_doz_fixture_ignores_delivery(self) -> None:
        self.assertEqual(read_doz_price(_html("doz.html")), Decimal("10.49"))

    def test_superpharm_fixture_is_this_pages_price_not_another_capacity(self) -> None:
        self.assertEqual(read_superpharm_price(_html("superpharm.html")), Decimal("35.99"))

    def test_gemini_fixture_is_the_selling_price(self) -> None:
        self.assertEqual(read_gemini_price(_html("gemini.html")), Decimal("10.49"))

    def test_page_with_no_selling_price_returns_nothing(self) -> None:
        html = _html("no-price.html")
        self.assertIsNone(read_rossmann_price(html))
        self.assertIsNone(read_doz_price(html))
        self.assertIsNone(read_superpharm_price(html))
        self.assertIsNone(read_gemini_price(html))

    def test_each_shop_reader_is_reachable_by_shop_code(self) -> None:
        from prices.readers import read_shop_price

        self.assertEqual(
            read_shop_price(Shop.ROSSMANN, _html("rossmann.html")),
            Decimal("5.39"),
        )
        self.assertEqual(read_shop_price(Shop.DOZ, _html("doz.html")), Decimal("10.49"))
        self.assertEqual(
            read_shop_price(Shop.SUPERPHARM, _html("superpharm.html")),
            Decimal("35.99"),
        )
        self.assertEqual(
            read_shop_price(Shop.GEMINI, _html("gemini.html")),
            Decimal("10.49"),
        )
