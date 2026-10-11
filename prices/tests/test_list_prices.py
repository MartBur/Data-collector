from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from prices.list_prices import list_prices
from prices.models import PriceObservation, Product, Shop, ShopPage


class ListPriceTests(TestCase):
    def _product(self, name: str = "Shampoo") -> Product:
        return Product.objects.create(name=name)

    def _page(self, product: Product, shop: str, url: str) -> ShopPage:
        return ShopPage.objects.create(product=product, shop=shop, url=url)

    def _observation(
        self,
        page: ShopPage,
        amount: str,
        observed_date: date,
    ) -> PriceObservation:
        return PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal(amount),
            observed_date=observed_date,
        )

    def test_today_minimum_keeps_only_the_cheapest_shop(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")
        self._observation(rossmann, "19.99", today)
        self._observation(doz, "24.00", today)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("19.99"))
        self.assertEqual(
            summary["shops"],
            [{"label": "Rossmann", "url": rossmann.url}],
        )

    def test_tied_today_shops_follow_page_pk_order(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")
        gemini = self._page(product, Shop.GEMINI, "https://gemini.pl/p/1")
        self._observation(rossmann, "19.99", today)
        self._observation(doz, "19.99", today)
        self._observation(gemini, "24.00", today)

        summary = list_prices([product], today)[product.pk]

        self.assertLess(rossmann.pk, doz.pk)
        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("19.99"))
        self.assertEqual(
            summary["shops"],
            [
                {"label": "Rossmann", "url": rossmann.url},
                {"label": "DOZ", "url": doz.url},
            ],
        )

    def test_yesterday_fills_in_when_today_is_empty(self) -> None:
        today = date(2026, 10, 10)
        yesterday = today - timedelta(days=1)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        self._observation(rossmann, "10.00", yesterday)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "yesterday")
        self.assertEqual(summary["amount"], Decimal("10.00"))
        self.assertEqual(
            summary["shops"],
            [{"label": "Rossmann", "url": rossmann.url}],
        )
        self.assertFalse(summary["matches_lowest_stored"])

    def test_price_older_than_yesterday_is_absent(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")
        self._observation(doz, "8.00", today - timedelta(days=3))

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "none")
        self.assertIsNone(summary["amount"])
        self.assertEqual(summary["shops"], [])
        self.assertFalse(summary["matches_lowest_stored"])

    def test_older_daily_price_is_not_a_historical_match(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        self._observation(rossmann, "15.00", date(2026, 9, 15))
        self._observation(rossmann, "19.99", today)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("19.99"))
        self.assertFalse(summary["matches_lowest_stored"])

    def test_today_matches_when_no_stored_daily_price_is_lower(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        gemini = self._page(product, Shop.GEMINI, "https://gemini.pl/p/1")
        self._observation(gemini, "8.00", today)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("8.00"))
        self.assertTrue(summary["matches_lowest_stored"])

    def test_superseded_same_day_amount_is_not_the_stored_low(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        self._observation(rossmann, "5.00", today)
        self._observation(rossmann, "19.99", today)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("19.99"))
        self.assertTrue(summary["matches_lowest_stored"])

    def test_low_older_than_thirty_days_blocks_a_match(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/1",
        )
        self._observation(rossmann, "10.00", today - timedelta(days=31))
        self._observation(rossmann, "19.99", today)

        summary = list_prices([product], today)[product.pk]

        self.assertEqual(summary["day"], "today")
        self.assertEqual(summary["amount"], Decimal("19.99"))
        self.assertFalse(summary["matches_lowest_stored"])

    def test_product_without_observations_is_still_listed(self) -> None:
        today = date(2026, 10, 10)
        priced = self._product("Priced")
        empty = self._product("Empty")
        page = self._page(priced, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._observation(page, "19.99", today)

        summaries = list_prices([priced, empty], today)

        self.assertEqual(set(summaries), {priced.pk, empty.pk})
        self.assertEqual(summaries[priced.pk]["amount"], Decimal("19.99"))
        self.assertEqual(summaries[empty.pk]["day"], "none")
        self.assertIsNone(summaries[empty.pk]["amount"])
        self.assertEqual(summaries[empty.pk]["shops"], [])
        self.assertFalse(summaries[empty.pk]["matches_lowest_stored"])
