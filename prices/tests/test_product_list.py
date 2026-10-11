from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase

from prices.models import Product, Shop, ShopPage

LIST_URL: str = "/products/"
PASSWORD: str = "correct-horse"


class ProductListTests(TestCase):
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

    def test_anonymous_get_redirects_to_sign_in(self) -> None:
        response = self.client.get(LIST_URL)
        self.assertRedirects(response, "/accounts/login/?next=/products/")

    def test_non_staff_get_is_forbidden(self) -> None:
        self._login()
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)

    def test_staff_get_lists_every_product_by_stripped_casefold_then_pk(self) -> None:
        earlier = Product.objects.create(name=" zebra ")
        Product.objects.create(name="Apple")
        Product.objects.create(name=" banana ")
        later = Product.objects.create(name="Zebra")
        Product.objects.create(name="Plain")
        self.assertLess(earlier.pk, later.pk)
        self._login(is_staff=True)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No tracked products.")
        expected = ("Apple", " banana ", "Plain", " zebra ", "Zebra")
        body = response.content.decode()
        positions = [body.index(name) for name in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(Product.objects.count(), len(expected))

    def test_staff_get_shows_shops_in_pk_order(self) -> None:
        product = Product.objects.create(name="Citrus")
        ShopPage.objects.create(
            product=product,
            shop=Shop.SUPERPHARM,
            url="https://www.superpharm.pl/p/citrus",
        )
        ShopPage.objects.create(
            product=product,
            shop=Shop.GEMINI,
            url="https://gemini.pl/p/citrus",
        )
        ShopPage.objects.create(
            product=product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/p/citrus",
        )
        self._login(is_staff=True)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertLess(body.index("Citrus"), body.index("Super-Pharm"))
        self.assertLess(body.index("Super-Pharm"), body.index("Gemini"))
        self.assertLess(body.index("Gemini"), body.index("DOZ"))

    def test_staff_product_name_opens_the_card_in_the_same_tab(self) -> None:
        product = Product.objects.create(name="Citrus")
        self._login(is_staff=True)
        response = self.client.get(LIST_URL)
        self.assertContains(
            response,
            f'<a href="/products/{product.pk}/">Citrus</a>',
        )
        self.assertNotContains(response, 'target="_blank"')

    def test_staff_get_empty_list_says_there_are_no_products(self) -> None:
        self._login(is_staff=True)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tracked products.")

    def test_staff_home_links_to_the_product_list(self) -> None:
        self._login(is_staff=True)
        response = self.client.get("/")
        self.assertContains(response, "Tracked products")
        self.assertContains(response, 'href="/products/"')
        self.assertContains(response, "Add a tracked product")

    def test_non_staff_home_has_no_product_list_link(self) -> None:
        self._login()
        response = self.client.get("/")
        self.assertContains(response, "ada")
        self.assertNotContains(response, "Tracked products")
        self.assertNotContains(response, 'href="/products/"')
