import re
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.utils import timezone

from prices.models import PriceObservation, Product, Shop, ShopPage
from prices.recording_clock import mark_recording_finished

PASSWORD: str = "correct-horse"
_HOME_CAPTIONS: tuple[str, str, str, str] = (
    "All products",
    "Favourites",
    "Historical lowest today",
    "Lowest price today",
)
_TAGS: re.Pattern[str] = re.compile(r"<[^>]+>")
_WHITESPACE: re.Pattern[str] = re.compile(r"\s+")


def _slice_table(body: str, caption: str) -> str:
    """Return one home table from its caption through the end of that table."""
    start = body.index(f"<caption>{caption}</caption>")
    end = body.index("</table>", start)
    return body[start:end]


def _visible_text(html: str) -> str:
    """Return markup text with tags removed and whitespace collapsed."""
    return _WHITESPACE.sub(" ", _TAGS.sub("", html)).strip()


class HomeTests(TestCase):
    def _user(self, username: str, *, is_staff: bool = False) -> AbstractUser:
        user = get_user_model().objects.create_user(
            username=username,
            password=PASSWORD,
        )
        if is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        return user

    def _login(self, *, is_staff: bool = False) -> AbstractUser:
        user = self._user("ada", is_staff=is_staff)
        self.client.force_login(user)
        return user

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

    def _home_body(self) -> str:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_non_staff_sees_casefold_order_and_can_open_a_card(self) -> None:
        later = Product.objects.create(name="Zebra")
        earlier = Product.objects.create(name="apple")
        self.assertLess(later.pk, earlier.pk)
        self.assertLess(earlier.name.casefold(), later.name.casefold())
        user = self._login()
        self.assertFalse(user.is_staff)

        body = self._home_body()

        earlier_link = f'href="/products/{earlier.pk}/">apple'
        later_link = f'href="/products/{later.pk}/">Zebra'
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")
        self.assertLess(all_products.index(earlier_link), all_products.index(later_link))
        self.assertLess(lowest.index(earlier_link), lowest.index(later_link))
        match = re.search(r'href="(/products/\d+/)"', all_products)
        self.assertIsNotNone(match)
        assert match is not None
        opened = self.client.get(match.group(1))
        self.assertEqual(opened.status_code, 200)
        self.assertContains(opened, "apple")

    def test_today_amount_on_all_products_omits_the_shop(self) -> None:
        product = Product.objects.create(name="Alpecin")
        page = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/alpecin",
        )
        self._observation(page, "19.99", timezone.localdate())
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")

        self.assertIn("19.99 PLN", all_products)
        self.assertNotIn("Rossmann", all_products)
        self.assertNotIn('target="_blank"', all_products)
        self.assertIn(
            f'href="/products/{product.pk}/">Alpecin</a>',
            all_products,
        )
        self.assertIn("19.99 PLN at Rossmann", _visible_text(lowest))
        self.assertIn(
            'href="https://www.rossmann.pl/p/alpecin" target="_blank" rel="noopener noreferrer">Rossmann</a>',
            lowest,
        )
        self.assertNotRegex(lowest, r"<a[^>]*>[^<]*19\.99")

    def test_tied_shops_follow_page_order_without_a_higher_shop(self) -> None:
        today = timezone.localdate()
        product = Product.objects.create(name="Citrus")
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/citrus",
        )
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/citrus")
        gemini = self._page(product, Shop.GEMINI, "https://gemini.pl/p/citrus")
        self.assertLess(rossmann.pk, doz.pk)
        self._observation(rossmann, "19.99", today)
        self._observation(doz, "19.99", today)
        self._observation(gemini, "24.00", today)
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")

        self.assertIn("19.99 PLN", all_products)
        self.assertNotIn("Rossmann", all_products)
        self.assertNotIn("DOZ", all_products)
        self.assertNotIn("Gemini", all_products)
        self.assertNotIn("24.00", all_products)
        self.assertIn("19.99 PLN at Rossmann", _visible_text(lowest))
        self.assertIn("19.99 PLN at DOZ", _visible_text(lowest))
        self.assertNotIn(" and ", _visible_text(lowest))
        self.assertNotIn("Gemini", lowest)
        self.assertNotIn("24.00", lowest)
        self.assertEqual(
            lowest.count(f'href="/products/{product.pk}/">Citrus</a>'),
            2,
        )
        self.assertIn(
            'href="https://www.rossmann.pl/p/citrus" target="_blank" rel="noopener noreferrer">Rossmann</a>',
            lowest,
        )
        self.assertIn(
            'href="https://www.doz.pl/p/citrus" target="_blank" rel="noopener noreferrer">DOZ</a>',
            lowest,
        )
        self.assertLess(lowest.index(">Rossmann</a>"), lowest.index(">DOZ</a>"))

    def test_manual_shampoo_today_is_15_at_rossmann_and_doz(self) -> None:
        today = timezone.localdate()
        product = Product.objects.create(name="Manual shampoo")
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/manual-shampoo",
        )
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/manual-shampoo")
        self.assertLess(rossmann.pk, doz.pk)
        self._observation(rossmann, "15.00", today)
        self._observation(doz, "15.00", today)
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")

        self.assertIn("Manual shampoo", all_products)
        self.assertIn("15.00 PLN", all_products)
        self.assertNotIn("Rossmann", all_products)
        self.assertNotIn("DOZ", all_products)
        self.assertIn("15.00 PLN at Rossmann", _visible_text(lowest))
        self.assertIn("15.00 PLN at DOZ", _visible_text(lowest))
        self.assertNotIn(" and ", _visible_text(lowest))
        self.assertEqual(
            lowest.count(f'href="/products/{product.pk}/">Manual shampoo</a>'),
            2,
        )
        self.assertIn("+", lowest)
        self.assertIn("|", lowest)
        self.assertIn(
            'href="https://www.rossmann.pl/p/manual-shampoo" target="_blank" rel="noopener noreferrer">Rossmann</a>',
            lowest,
        )
        self.assertIn(
            'href="https://www.doz.pl/p/manual-shampoo" target="_blank" rel="noopener noreferrer">DOZ</a>',
            lowest,
        )
        self.assertLess(lowest.index(">Rossmann</a>"), lowest.index(">DOZ</a>"))

    def test_yesterday_is_labeled_yesterday_and_is_not_historical(self) -> None:
        product = Product.objects.create(name="Dawn")
        page = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/dawn",
        )
        self._observation(page, "10.00", timezone.localdate() - timedelta(days=1))
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")
        historical = _slice_table(body, "Historical lowest today")

        self.assertIn("10.00 PLN yesterday", all_products)
        self.assertNotIn("Rossmann", all_products)
        self.assertIn("10.00 PLN at Rossmann yesterday", _visible_text(lowest))
        self.assertNotIn("Dawn", historical)

    def test_price_older_than_yesterday_is_no_price(self) -> None:
        product = Product.objects.create(name="Gap")
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/gap")
        self._observation(page, "8.00", timezone.localdate() - timedelta(days=3))
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")
        historical = _slice_table(body, "Historical lowest today")

        self.assertIn("Gap", all_products)
        self.assertIn("No price", all_products)
        self.assertNotIn("8.00", all_products)
        self.assertIn("Gap", lowest)
        self.assertIn("No price", lowest)
        self.assertNotIn("8.00", lowest)
        self.assertNotIn("Gap", historical)

    def test_low_older_than_thirty_days_is_not_historical(self) -> None:
        today = timezone.localdate()
        product = Product.objects.create(name="Aged")
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/aged")
        self._observation(page, "15.00", today - timedelta(days=31))
        self._observation(page, "19.99", today)
        self._login()

        body = self._home_body()
        all_products = _slice_table(body, "All products")
        lowest = _slice_table(body, "Lowest price today")
        historical = _slice_table(body, "Historical lowest today")

        self.assertIn("Aged", all_products)
        self.assertIn("19.99 PLN", all_products)
        self.assertNotIn("15.00", all_products)
        self.assertIn("Aged", lowest)
        self.assertIn("19.99 PLN at Rossmann", _visible_text(lowest))
        self.assertNotIn("15.00", lowest)
        self.assertNotIn("Aged", historical)

    def test_historical_lowest_today_shows_the_stored_low(self) -> None:
        product = Product.objects.create(name="Nizoral")
        page = self._page(product, Shop.GEMINI, "https://gemini.pl/p/nizoral")
        self._observation(page, "8.00", timezone.localdate())
        self._login()

        historical = _slice_table(self._home_body(), "Historical lowest today")

        self.assertIn("Nizoral", historical)
        self.assertIn("8.00 PLN at Gemini", _visible_text(historical))
        self.assertIn(
            'href="https://gemini.pl/p/nizoral" target="_blank" rel="noopener noreferrer">Gemini</a>',
            historical,
        )

    def test_creme_at_1_today_is_in_historical_lowest(self) -> None:
        today = timezone.localdate()
        product = Product.objects.create(name="Creme")
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/creme",
        )
        self._observation(rossmann, "1.00", today)
        self._login()

        body = self._home_body()
        historical = _slice_table(body, "Historical lowest today")
        all_products = _slice_table(body, "All products")

        self.assertIn("Creme", historical)
        self.assertIn("1.00 PLN at Rossmann", _visible_text(historical))
        self.assertIn(
            'href="https://www.rossmann.pl/p/creme" target="_blank" rel="noopener noreferrer">Rossmann</a>',
            historical,
        )
        self.assertIn(
            f'href="/products/{product.pk}/">Creme</a>',
            historical,
        )
        self.assertIn("1.00 PLN", all_products)
        self.assertNotIn("Rossmann", all_products)

    def test_favourites_is_one_empty_row_when_products_exist(self) -> None:
        product = Product.objects.create(name="Alpecin")
        self._login()

        body = self._home_body()
        favourites = _slice_table(body, "Favourites")

        self.assertIn("<caption>Favourites</caption>", favourites)
        self.assertIn('<td class="ascii-cell ascii-title" colspan="3">Favourites</td>', favourites)
        self.assertIn("<td class=\"ascii-cell\">_</td>", favourites)
        self.assertIn('class="home-cross-joint" aria-hidden="true">+</div>', body)
        self.assertIn("+", favourites)
        self.assertIn("|", favourites)
        self.assertIn("-", favourites)
        self.assertNotRegex(favourites, r"/products/\d+/")
        self.assertNotIn("Alpecin", favourites)
        self.assertIn(
            f'href="/products/{product.pk}/">Alpecin</a>',
            _slice_table(body, "All products"),
        )

    def test_empty_catalog_shows_username_and_sign_out_without_product_links(
        self,
    ) -> None:
        self._login()

        body = self._home_body()

        self.assertIn("ada", body)
        self.assertIn("Sign out", body)
        self.assertIn('action="/accounts/logout/"', body)
        self.assertNotRegex(body, r"/products/\d+/")
        positions = [body.index(f"<caption>{caption}</caption>") for caption in _HOME_CAPTIONS]
        self.assertEqual(positions, sorted(positions))
        for caption in _HOME_CAPTIONS:
            table = _slice_table(body, caption)
            self.assertIn(f"<caption>{caption}</caption>", table)
            self.assertIn(
                f'<td class="ascii-cell ascii-title" colspan="3">{caption}</td>',
                table,
            )
            self.assertIn("<td class=\"ascii-cell\">_</td>", table)
            self.assertNotRegex(table, r"/products/\d+/")
        self.assertIn('class="home-cross-joint" aria-hidden="true">+</div>', body)

    def test_staff_still_sees_the_add_product_link(self) -> None:
        self._login(is_staff=True)

        body = self._home_body()

        self.assertIn("ada", body)
        self.assertIn("Sign out", body)
        self.assertIn('action="/accounts/logout/"', body)
        self.assertIn("Add a tracked product", body)
        self.assertIn('href="/products/add/"', body)
        self.assertIn("Tracked products", body)
        self.assertIn('href="/products/"', body)
        self.assertNotRegex(body, r"/products/\d+/")
        for caption in _HOME_CAPTIONS:
            table = _slice_table(body, caption)
            self.assertIn(f"<caption>{caption}</caption>", table)
            self.assertIn("<td class=\"ascii-cell\">_</td>", table)
            self.assertNotRegex(table, r"/products/\d+/")

    def test_last_update_is_none_without_a_recording_run(self) -> None:
        self._login()

        body = self._home_body()

        self.assertIn("<strong>Last price update: none - Warsaw time</strong>", body)
        self.assertLess(
            body.index("Last price update: none - Warsaw time"),
            body.index("<caption>All products</caption>"),
        )

    def test_last_update_formats_an_aware_finish_in_warsaw(self) -> None:
        self._login()
        mark_recording_finished(
            datetime(2026, 10, 12, 6, 0, tzinfo=datetime_timezone.utc)
        )

        body = self._home_body()

        self.assertIn("Last price update: 12.10.2026 08:00 - Warsaw time", body)
        self.assertNotIn("Last price update: none - Warsaw time", body)

    def test_home_button_is_on_every_page(self) -> None:
        login = self.client.get("/accounts/login/")
        self.assertContains(login, '<a href="/">Home</a>')
        self._login(is_staff=True)
        product = Product.objects.create(name="Home button shampoo")
        page = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/p/home-button",
        )
        PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal("19.99"),
            observed_date=timezone.localdate(),
        )
        addresses = (
            "/",
            "/products/",
            "/products/add/",
            f"/products/{product.pk}/",
            f"/products/{product.pk}/change/",
        )
        for address in addresses:
            response = self.client.get(address)
            self.assertEqual(response.status_code, 200, address)
            self.assertContains(response, '<a href="/">Home</a>')
        confirm = self.client.post(f"/products/{product.pk}/remove/")
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, '<a href="/">Home</a>')
        self.assertContains(confirm, "Confirm removal")
