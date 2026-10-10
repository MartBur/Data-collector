from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.http import HttpResponse
from django.test import TestCase

from prices.models import PriceObservation, Product, Shop, ShopPage

ADD_URL: str = "/products/add/"
PASSWORD: str = "correct-horse"


class AddProductTests(TestCase):
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

    def _payload(self, **overrides: str) -> dict[str, str]:
        data: dict[str, str] = {
            "name": "Alpecin",
            "shop_1": Shop.ROSSMANN,
            "url_1": "https://www.rossmann.pl/Produkt/alpecin",
            "shop_2": Shop.DOZ,
            "url_2": "https://www.doz.pl/p/alpecin",
            "shop_3": "",
            "url_3": "",
        }
        data.update(overrides)
        return data

    def _assert_rejected(self, payload: dict[str, str]) -> HttpResponse:
        products_before = Product.objects.count()
        pages_before = ShopPage.objects.count()
        response = self.client.post(ADD_URL, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), products_before)
        self.assertEqual(ShopPage.objects.count(), pages_before)
        self.assertEqual(PriceObservation.objects.count(), 0)
        return response

    def test_anonymous_get_redirects_to_sign_in(self) -> None:
        response = self.client.get(ADD_URL)
        self.assertRedirects(response, "/accounts/login/?next=/products/add/")
        self.assertEqual(Product.objects.count(), 0)

    def test_non_staff_get_and_post_are_forbidden(self) -> None:
        self._login()
        self.assertEqual(self.client.get(ADD_URL).status_code, 403)
        response = self.client.post(ADD_URL, self._payload())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(ShopPage.objects.count(), 0)

    def test_staff_get_returns_the_form(self) -> None:
        self._login(is_staff=True)
        response = self.client.get(ADD_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add product")
        self.assertFalse(response.context["form"].is_bound)

    def test_staff_post_two_pages_redirects_and_confirms(self) -> None:
        older = Product.objects.create(name="Older shampoo")
        ShopPage.objects.create(
            product=older,
            shop=Shop.GEMINI,
            url="https://gemini.pl/p/older",
        )
        self._login(is_staff=True)
        response = self.client.post(ADD_URL, self._payload())
        product = Product.objects.get(name="Alpecin")
        self.assertRedirects(response, f"{ADD_URL}?added={product.pk}")
        self.assertEqual(
            list(product.shop_pages.order_by("pk").values_list("shop", "url")),
            [
                (Shop.ROSSMANN, "https://www.rossmann.pl/Produkt/alpecin"),
                (Shop.DOZ, "https://www.doz.pl/p/alpecin"),
            ],
        )
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 2)
        follow = self.client.get(f"{ADD_URL}?added={product.pk}")
        self.assertContains(follow, "Alpecin")
        self.assertContains(
            follow,
            "Rossmann https://www.rossmann.pl/Produkt/alpecin",
        )
        self.assertContains(follow, "DOZ https://www.doz.pl/p/alpecin")
        self.assertNotContains(follow, "Older shampoo")
        self.assertNotContains(follow, "https://gemini.pl/p/older")
        self.assertFalse(follow.context["form"].is_bound)
        self.assertEqual(Product.objects.count(), 2)

    def test_three_valid_pages_store_three(self) -> None:
        self._login(is_staff=True)
        response = self.client.post(
            ADD_URL,
            self._payload(
                shop_3=Shop.GEMINI,
                url_3="https://gemini.pl/p/alpecin",
            ),
        )
        product = Product.objects.get()
        self.assertRedirects(response, f"{ADD_URL}?added={product.pk}")
        self.assertEqual(product.shop_pages.count(), 3)
        self.assertEqual(
            set(product.shop_pages.values_list("shop", flat=True)),
            {Shop.ROSSMANN, Shop.DOZ, Shop.GEMINI},
        )
        self.assertEqual(PriceObservation.objects.count(), 0)

    def test_staff_post_one_page_redirects_and_confirms(self) -> None:
        self._login(is_staff=True)
        response = self.client.post(
            ADD_URL,
            self._payload(shop_2="", url_2=""),
        )
        product = Product.objects.get()
        self.assertRedirects(response, f"{ADD_URL}?added={product.pk}")
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ShopPage.objects.count(), 1)
        self.assertEqual(
            list(product.shop_pages.order_by("pk").values_list("shop", "url")),
            [(Shop.ROSSMANN, "https://www.rossmann.pl/Produkt/alpecin")],
        )
        self.assertEqual(PriceObservation.objects.count(), 0)
        follow = self.client.get(f"{ADD_URL}?added={product.pk}")
        self.assertContains(follow, "Alpecin")
        self.assertContains(
            follow,
            "Rossmann https://www.rossmann.pl/Produkt/alpecin",
        )

    def test_no_shop_rows_stores_nothing(self) -> None:
        self._login(is_staff=True)
        response = self._assert_rejected(
            self._payload(
                shop_1="",
                url_1="",
                shop_2="",
                url_2="",
            )
        )
        self.assertIn(
            "Enter at least one shop page.",
            response.context["form"].errors["shop_1"],
        )

    def test_half_filled_third_row_stores_nothing(self) -> None:
        self._login(is_staff=True)
        cases: tuple[dict[str, str], ...] = (
            {"shop_3": Shop.GEMINI, "url_3": ""},
            {"shop_3": "", "url_3": "https://gemini.pl/p/alpecin"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self._assert_rejected(self._payload(**overrides))

    def test_half_filled_first_or_second_row_stores_nothing(self) -> None:
        self._login(is_staff=True)
        cases: tuple[dict[str, str], ...] = (
            {
                "shop_1": "",
                "url_1": "https://www.rossmann.pl/Produkt/alpecin",
                "shop_2": "",
                "url_2": "",
            },
            {
                "shop_1": Shop.ROSSMANN,
                "url_1": "",
                "shop_2": "",
                "url_2": "",
            },
            {"shop_2": Shop.DOZ, "url_2": ""},
            {"shop_2": "", "url_2": "https://www.doz.pl/p/alpecin"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self._assert_rejected(self._payload(**overrides))

    def test_second_row_without_first_row_stores_nothing(self) -> None:
        self._login(is_staff=True)
        self._assert_rejected(self._payload(shop_1="", url_1=""))

    def test_third_row_without_second_row_stores_nothing(self) -> None:
        self._login(is_staff=True)
        self._assert_rejected(
            self._payload(
                shop_2="",
                url_2="",
                shop_3=Shop.GEMINI,
                url_3="https://gemini.pl/p/alpecin",
            )
        )

    def test_same_shop_on_two_rows_stores_nothing(self) -> None:
        self._login(is_staff=True)
        self._assert_rejected(
            self._payload(
                shop_2=Shop.ROSSMANN,
                url_2="https://www.rossmann.pl/Produkt/other",
            )
        )

    def test_url_on_the_wrong_host_stores_nothing(self) -> None:
        self._login(is_staff=True)
        response = self._assert_rejected(
            self._payload(url_1="https://www.doz.pl/p/not-rossmann")
        )
        self.assertIn("url_1", response.context["form"].errors)

    def test_folded_duplicate_name_keeps_the_submitted_name(self) -> None:
        Product.objects.create(name="Alpecin")
        self._login(is_staff=True)
        response = self._assert_rejected(self._payload(name=" alpecin "))
        form = response.context["form"]
        self.assertTrue(form.is_bound)
        self.assertEqual(form["name"].value(), " alpecin ")
        self.assertIn("name", form.errors)
        self.assertEqual(Product.objects.get().name, "Alpecin")

    def test_same_rossmann_page_ignoring_www_and_slash_stores_nothing(self) -> None:
        other = Product.objects.create(name="Other")
        ShopPage.objects.create(
            product=other,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon",
        )
        self._login(is_staff=True)
        response = self._assert_rejected(
            self._payload(
                name="New shampoo",
                url_1="https://rossmann.pl/Produkt/szampon/",
            )
        )
        self.assertIn("url_1", response.context["form"].errors)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ShopPage.objects.count(), 1)

    def test_unknown_added_id_shows_only_the_empty_form(self) -> None:
        Product.objects.create(name="Older shampoo")
        self._login(is_staff=True)
        for raw_pk in ("999999", "nope", "\u00b2"):
            with self.subTest(raw_pk=raw_pk):
                response = self.client.get(f"{ADD_URL}?added={raw_pk}")
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "Older shampoo")
                self.assertFalse(response.context["form"].is_bound)

    def test_staff_home_links_to_the_add_page(self) -> None:
        self._login(is_staff=True)
        response = self.client.get("/")
        self.assertContains(response, "Add a tracked product")
        self.assertContains(response, 'href="/products/add/"')

    def test_non_staff_home_has_no_add_link(self) -> None:
        self._login()
        response = self.client.get("/")
        self.assertContains(response, "ada")
        self.assertContains(response, "Sign out")
        self.assertNotContains(response, "Add a tracked product")
