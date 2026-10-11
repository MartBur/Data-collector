import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.utils import timezone

from prices.models import PriceObservation, Product, Shop, ShopPage

PASSWORD: str = "correct-horse"


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

    def _record_price(self, product: Product, amount: str) -> PriceObservation:
        page = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url=f"https://www.rossmann.pl/p/{product.pk}",
        )
        return PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal(amount),
            observed_date=timezone.localdate(),
        )

    def test_non_staff_sees_casefold_order_and_can_open_a_card(self) -> None:
        later = Product.objects.create(name="Zebra")
        earlier = Product.objects.create(name="apple")
        self.assertLess(later.pk, earlier.pk)
        self.assertLess(earlier.name.casefold(), later.name.casefold())
        user = self._login()
        self.assertFalse(user.is_staff)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        earlier_link = f'href="/products/{earlier.pk}/">apple'
        later_link = f'href="/products/{later.pk}/">Zebra'
        self.assertLess(body.index(earlier_link), body.index(later_link))
        match = re.search(r'href="(/products/\d+/)"', body)
        self.assertIsNotNone(match)
        assert match is not None
        opened = self.client.get(match.group(1))
        self.assertEqual(opened.status_code, 200)
        self.assertContains(opened, "apple")

    def test_stored_price_does_not_appear_on_home(self) -> None:
        product = Product.objects.create(name="Alpecin")
        self._record_price(product, "12.34")
        self._login()

        response = self.client.get("/")

        self.assertContains(response, "Alpecin")
        self.assertContains(response, f'href="/products/{product.pk}/"')
        self.assertNotContains(response, "12.34")
        self.assertNotContains(response, "PLN")
        self.assertNotContains(response, "Cheapest")
        self.assertNotContains(response, "No price")

    def test_empty_catalog_shows_username_and_sign_out_without_product_links(
        self,
    ) -> None:
        self._login()

        response = self.client.get("/")

        self.assertContains(response, "ada")
        self.assertContains(response, "Sign out")
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertNotRegex(response.content.decode(), r"/products/\d+/")

    def test_staff_still_sees_the_add_product_link(self) -> None:
        self._login(is_staff=True)

        response = self.client.get("/")

        self.assertContains(response, "Add a tracked product")
        self.assertContains(response, 'href="/products/add/"')
        self.assertContains(response, "Tracked products")
        self.assertContains(response, 'href="/products/"')
