from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from prices.card import card_figures
from prices.models import PriceObservation, Product, Shop, ShopPage


class CardFigureTests(TestCase):
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

    def test_window_is_thirty_dates_ending_today(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._observation(page, "12.50", today - timedelta(days=30))
        self._observation(page, "19.99", today - timedelta(days=29))

        figures = card_figures(product, today)

        self.assertEqual(len(figures["dates"]), 30)
        self.assertEqual(figures["dates"][0], date(2026, 9, 11))
        self.assertEqual(figures["dates"][-1], today)
        self.assertNotIn(date(2026, 9, 10), figures["dates"])
        self.assertEqual(figures["series"][0]["amounts"][0], Decimal("19.99"))
        self.assertNotIn(Decimal("12.50"), figures["series"][0]["amounts"])

    def test_gap_day_is_empty_between_priced_days(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        priced_before = date(2026, 10, 8)
        gap = date(2026, 10, 9)
        self._observation(page, "18.00", priced_before)
        self._observation(page, "19.99", today)

        figures = card_figures(product, today)
        amounts = figures["series"][0]["amounts"]
        dates = figures["dates"]

        self.assertEqual(amounts[dates.index(priced_before)], Decimal("18.00"))
        self.assertIsNone(amounts[dates.index(gap)])
        self.assertEqual(amounts[dates.index(today)], Decimal("19.99"))

    def test_every_shop_tied_for_today_is_cheapest(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")
        self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._page(product, Shop.GEMINI, "https://gemini.pl/p/1")
        pages = list(product.shop_pages.order_by("pk"))
        self._observation(pages[0], "19.99", today)
        self._observation(pages[1], "19.99", today)
        self._observation(pages[2], "24.00", today)

        figures = card_figures(product, today)

        self.assertEqual(
            [shop["label"] for shop in figures["shops"]],
            ["DOZ", "Rossmann", "Gemini"],
        )
        self.assertEqual(
            [shop["cheapest"] for shop in figures["shops"]],
            [True, True, False],
        )
        self.assertEqual(
            [shop["today_amount"] for shop in figures["shops"]],
            [Decimal("19.99"), Decimal("19.99"), Decimal("24.00")],
        )

    def test_shop_with_no_price_today_is_not_cheapest(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        priced = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        missing = self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")
        self._observation(priced, "19.99", today)

        figures = card_figures(product, today)
        by_label = {shop["label"]: shop for shop in figures["shops"]}

        self.assertEqual(by_label["Rossmann"]["today_amount"], Decimal("19.99"))
        self.assertTrue(by_label["Rossmann"]["cheapest"])
        self.assertIsNone(by_label["DOZ"]["today_amount"])
        self.assertFalse(by_label["DOZ"]["cheapest"])
        self.assertEqual(by_label["DOZ"]["url"], missing.url)

    def test_lowest_recorded_includes_a_price_outside_the_window(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._observation(page, "10.00", date(2026, 8, 1))
        self._observation(page, "18.00", date(2026, 10, 1))
        self._observation(page, "19.99", today)

        figures = card_figures(product, today)

        self.assertEqual(figures["lowest_recorded"], Decimal("10.00"))
        self.assertNotIn(date(2026, 8, 1), figures["dates"])

    def test_same_day_replacement_is_the_daily_price(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._observation(page, "5.00", today)
        self._observation(page, "19.99", today)
        self._observation(page, "22.00", date(2026, 10, 1))

        figures = card_figures(product, today)

        self.assertEqual(figures["shops"][0]["today_amount"], Decimal("19.99"))
        self.assertEqual(figures["lowest_recorded"], Decimal("19.99"))
        self.assertNotEqual(figures["lowest_recorded"], Decimal("5.00"))

    def test_product_with_no_observations_has_no_low_and_no_cheapest(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()
        self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/1")
        self._page(product, Shop.DOZ, "https://www.doz.pl/p/1")

        figures = card_figures(product, today)

        self.assertIsNone(figures["lowest_recorded"])
        self.assertEqual(len(figures["dates"]), 30)
        self.assertEqual(len(figures["shops"]), 2)
        self.assertTrue(all(shop["today_amount"] is None for shop in figures["shops"]))
        self.assertTrue(all(not shop["cheapest"] for shop in figures["shops"]))
        for shop in figures["series"]:
            self.assertEqual(len(shop["amounts"]), 30)
            self.assertTrue(all(amount is None for amount in shop["amounts"]))

    def test_product_with_no_shop_pages_has_an_empty_card(self) -> None:
        today = date(2026, 10, 10)
        product = self._product()

        figures = card_figures(product, today)

        self.assertEqual(figures["shops"], [])
        self.assertEqual(figures["series"], [])
        self.assertEqual(len(figures["dates"]), 30)
        self.assertIsNone(figures["lowest_recorded"])
