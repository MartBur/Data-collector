import re
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from prices.card import card_figures
from prices.models import PriceObservation, Product, Shop, ShopPage

PASSWORD: str = "correct-horse"


class ProductCardTests(TestCase):
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

    def _product(self, name: str = "Alpecin") -> Product:
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

    def _open(self, product: Product) -> HttpResponse:
        return self.client.get(f"/products/{product.pk}/")

    def _rows(self, html: str) -> list[str]:
        """Return each shop row's inner HTML, in page order."""
        return [chunk.split("</li>", 1)[0] for chunk in html.split("<li>")[1:]]

    def _points(self, html: str) -> list[tuple[str, str, str, str]]:
        """Return plotted points as x, y, date, and amount."""
        return re.findall(
            r'cx="([0-9.]+)" cy="([0-9.]+)"[^>]*'
            r'data-date="([^"]+)" data-amount="([^"]+)"',
            html,
        )

    def _slots(self, html: str) -> list[str]:
        """Return the x position of each date slot, oldest first."""
        return re.findall(r'data-slot="\d+" x1="([0-9.]+)"', html)

    def _lines(self, html: str) -> list[str]:
        """Return each shop line element, including its priced-day titles."""
        return re.findall(r"<polyline\b.*?</polyline>", html, flags=re.DOTALL)

    def test_anonymous_get_redirects_to_sign_in(self) -> None:
        product = self._product()
        response = self.client.get(f"/products/{product.pk}/")
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/products/{product.pk}/",
        )

    def test_non_staff_get_returns_the_card(self) -> None:
        product = self._product()
        user = self._login()
        self.assertFalse(user.is_staff)
        response = self._open(product)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpecin")
        self.assertEqual(
            reverse("prices:product_card", kwargs={"pk": product.pk}),
            f"/products/{product.pk}/",
        )

    def test_unknown_id_is_not_found(self) -> None:
        self._login()
        response = self.client.get("/products/999999/")
        self.assertEqual(response.status_code, 404)

    def test_card_states_today_price_ties_missing_price_and_low(self) -> None:
        today = timezone.localdate()
        older = today - timedelta(days=5)
        low_day = today - timedelta(days=40)
        product = self._product()
        doz = self._page(product, Shop.DOZ, "https://www.doz.pl/p/alpecin")
        rossmann = self._page(
            product,
            Shop.ROSSMANN,
            "https://www.rossmann.pl/p/alpecin",
        )
        gemini = self._page(product, Shop.GEMINI, "https://gemini.pl/p/alpecin")
        self._page(
            product,
            Shop.SUPERPHARM,
            "https://www.superpharm.pl/p/alpecin",
        )
        self._observation(doz, "10.00", low_day)
        self._observation(doz, "19.99", today)
        self._observation(rossmann, "19.99", today)
        self._observation(gemini, "18.00", older)
        self._observation(gemini, "24.00", today)
        self._login()

        response = self._open(product)

        self.assertContains(response, "Alpecin")
        self.assertContains(response, "19.99 PLN", count=2)
        self.assertContains(response, "24.00 PLN", count=1)
        self.assertContains(response, "Lowest recorded price 10.00 PLN")
        self.assertContains(response, "No price", count=1)
        self.assertContains(response, "Cheapest", count=2)
        self.assertNotContains(response, "18.00 PLN")
        self.assertEqual(response.context["product"].pk, product.pk)
        self.assertEqual(response.context["figures"], card_figures(product, today))
        html = response.content.decode()
        rows = self._rows(html)
        self.assertEqual(len(rows), 4)
        self.assertIn("DOZ", rows[0])
        self.assertIn("19.99 PLN", rows[0])
        self.assertIn("Cheapest", rows[0])
        self.assertNotIn("10.00", rows[0])
        self.assertIn('href="https://www.doz.pl/p/alpecin"', rows[0])
        self.assertIn('target="_blank"', rows[0])
        self.assertIn('rel="noopener noreferrer"', rows[0])
        self.assertIn("Rossmann", rows[1])
        self.assertIn("19.99 PLN", rows[1])
        self.assertIn("Cheapest", rows[1])
        self.assertIn('href="https://www.rossmann.pl/p/alpecin"', rows[1])
        self.assertIn("Gemini", rows[2])
        self.assertIn("24.00 PLN", rows[2])
        self.assertNotIn("Cheapest", rows[2])
        self.assertNotIn("18.00", rows[2])
        self.assertIn('href="https://gemini.pl/p/alpecin"', rows[2])
        self.assertIn("Super-Pharm", rows[3])
        self.assertIn("No price", rows[3])
        self.assertNotIn("Cheapest", rows[3])
        self.assertNotIn("PLN", rows[3])
        self.assertIn('href="https://www.superpharm.pl/p/alpecin"', rows[3])
        older_points = [point for point in self._points(html) if point[3] == "18.00"]
        self.assertEqual(len(older_points), 1)
        self.assertEqual(older_points[0][2], older.isoformat())
        self.assertNotEqual(older_points[0][2], today.isoformat())
        self.assertNotIn('data-amount="10.00"', html)
        self.assertNotIn(low_day.isoformat(), html)
        low = html.split("Lowest recorded price", 1)[1].split("</p>", 1)[0]
        self.assertIn("10.00 PLN", low)
        self.assertNotIn("today", low.casefold())
        self.assertEqual(html.count("<svg"), 1)
        self.assertNotIn("<script", html.casefold())
        self.assertNotIn("<link", html.casefold())
        self.assertNotIn("<style", html.casefold())
        self.assertNotIn("availability", html.casefold())
        self.assertNotIn("shipping", html.casefold())
        self.assertNotIn("buy now", html.casefold())
        self.assertNotIn("horizon", html.casefold())
        self.assertNotIn("description", html.casefold())
        strokes = set(re.findall(r'<circle\b[^>]*stroke="(#[0-9a-fA-F]{6})"', html))
        self.assertEqual(len(strokes), 3)
        self.assertNotIn("stroke-dasharray", html)
        radii = set(re.findall(r"<circle\b[^>]*\sr=\"([^\"]+)\"", html))
        self.assertEqual(radii, {"4"})

    def test_line_includes_dates_around_a_gap_and_omits_the_gap_point(self) -> None:
        today = timezone.localdate()
        before = today - timedelta(days=2)
        gap = today - timedelta(days=1)
        first = today - timedelta(days=29)
        product = self._product("Gap shampoo")
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/gap")
        self._observation(page, "18.00", before)
        self._observation(page, "19.99", today)
        self._login()

        response = self._open(product)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        lines = self._lines(html)
        self.assertEqual(len(lines), 1)
        self.assertIn(before.isoformat(), lines[0])
        self.assertIn(today.isoformat(), lines[0])
        self.assertIn("18.00", lines[0])
        self.assertIn("19.99", lines[0])
        self.assertNotIn(gap.isoformat(), lines[0])
        pairs = re.search(r'points="([^"]+)"', lines[0])
        self.assertIsNotNone(pairs)
        assert pairs is not None
        self.assertEqual(len(pairs.group(1).split()), 2)
        points = self._points(html)
        slots = self._slots(html)
        self.assertEqual(len(slots), 30)
        self.assertEqual(
            [(point[0], point[2], point[3]) for point in points],
            [
                (slots[-3], before.isoformat(), "18.00"),
                (slots[-1], today.isoformat(), "19.99"),
            ],
        )
        self.assertNotIn(f'data-date="{gap.isoformat()}"', html)
        self.assertNotIn(gap.isoformat(), html)
        gap_x = Decimal(slots[-2])
        self.assertLess(Decimal(points[0][0]), gap_x)
        self.assertLess(gap_x, Decimal(points[1][0]))
        self.assertIn(f">{first.isoformat()}<", html)
        self.assertIn(f">{today.isoformat()}<", html)
        self.assertIn('data-price="0.00"', html)
        self.assertIn('data-price="10.00"', html)
        self.assertIn('data-price="20.00"', html)
        self.assertIn('data-legend="Rossmann"', html)

    def test_equal_amounts_draw_a_horizontal_line(self) -> None:
        today = timezone.localdate()
        earlier = today - timedelta(days=1)
        product = self._product("Flat shampoo")
        page = self._page(product, Shop.DOZ, "https://www.doz.pl/p/flat")
        self._observation(page, "19.99", earlier)
        self._observation(page, "19.99", today)
        self._login()

        response = self._open(product)

        html = response.content.decode()
        points = self._points(html)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0][1], points[1][1])
        self.assertNotEqual(points[0][0], points[1][0])
        lines = self._lines(html)
        self.assertEqual(len(lines), 1)
        pairs = re.search(r'points="([^"]+)"', lines[0])
        self.assertIsNotNone(pairs)
        assert pairs is not None
        first_pair, second_pair = pairs.group(1).split()
        self.assertEqual(first_pair.split(",")[1], second_pair.split(",")[1])
        self.assertNotEqual(first_pair.split(",")[0], second_pair.split(",")[0])

    def test_one_priced_day_has_a_point_and_no_line(self) -> None:
        today = timezone.localdate()
        product = self._product("Single shampoo")
        page = self._page(product, Shop.GEMINI, "https://gemini.pl/p/single")
        self._observation(page, "19.99", today)
        self._login()

        response = self._open(product)

        html = response.content.decode()
        self.assertEqual(self._lines(html), [])
        points = self._points(html)
        slots = self._slots(html)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0][0], slots[-1])
        self.assertEqual(points[0][2], today.isoformat())
        self.assertEqual(points[0][3], "19.99")
        self.assertEqual(len(slots), 30)

    def test_no_prices_omit_the_low_and_keep_thirty_slots(self) -> None:
        today = timezone.localdate()
        first = today - timedelta(days=29)
        product = self._product("Empty shampoo")
        self._page(product, Shop.DOZ, "https://www.doz.pl/p/empty")
        self._login()

        response = self._open(product)

        self.assertContains(response, "Empty shampoo")
        self.assertContains(response, "No price")
        self.assertContains(response, 'href="https://www.doz.pl/p/empty"')
        self.assertNotContains(response, "Lowest recorded price")
        self.assertNotContains(response, "Cheapest")
        html = response.content.decode()
        self.assertEqual(self._lines(html), [])
        self.assertEqual(self._points(html), [])
        self.assertEqual(len(self._slots(html)), 30)
        self.assertIn(f">{first.isoformat()}<", html)
        self.assertIn(f">{today.isoformat()}<", html)
        self.assertEqual(html.count("<svg"), 1)

    def test_y_axis_starts_fifty_below_the_lowest_price_and_not_below_zero(
        self,
    ) -> None:
        today = timezone.localdate()
        product = self._product("Axis shampoo")
        page = self._page(product, Shop.ROSSMANN, "https://www.rossmann.pl/p/axis")
        self._observation(page, "80.00", today - timedelta(days=1))
        self._observation(page, "90.00", today)
        self._login()

        response = self._open(product)

        html = response.content.decode()
        self.assertIn('data-price="30.00"', html)
        self.assertIn('data-price="90.00"', html)
        self.assertNotIn('data-price="0.00"', html)
        self.assertNotIn('data-price="20.00"', html)
        self.assertIn('data-legend="Rossmann"', html)
