from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.urls import reverse

from prices.models import PriceObservation, Product, Shop, ShopPage

LIST_URL: str = "/products/"
PASSWORD: str = "correct-horse"
ROSSMANN_URL: str = "https://www.rossmann.pl/Produkt/alpecin"
DOZ_URL: str = "https://www.doz.pl/p/alpecin"
SUPERPHARM_URL: str = "https://www.superpharm.pl/p/alpecin"
GEMINI_URL: str = "https://gemini.pl/p/alpecin"
NEW_ROSSMANN_URL: str = "https://www.rossmann.pl/Produkt/alpecin-new"


class ChangeProductTests(TestCase):
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

    def _url(self, pk: int) -> str:
        return reverse("prices:change_product", kwargs={"pk": pk})

    def _make_product(
        self,
        name: str,
        pages: tuple[tuple[str, str], ...],
    ) -> tuple[Product, list[ShopPage]]:
        product = Product.objects.create(name=name)
        stored: list[ShopPage] = []
        for shop, url in pages:
            stored.append(
                ShopPage.objects.create(product=product, shop=shop, url=url)
            )
        return product, stored

    def _price(self, page: ShopPage, amount: str = "10.00") -> PriceObservation:
        return PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal(amount),
            observed_date=date.today(),
        )

    def _payload(
        self,
        name: str,
        pages: tuple[tuple[str, str], ...],
        **overrides: str,
    ) -> dict[str, str]:
        data: dict[str, str] = {
            "name": name,
            "shop_1": "",
            "url_1": "",
            "shop_2": "",
            "url_2": "",
            "shop_3": "",
            "url_3": "",
        }
        for index, (shop, url) in enumerate(pages, start=1):
            data[f"shop_{index}"] = shop
            data[f"url_{index}"] = url
        data.update(overrides)
        return data

    def _page_rows(self, product: Product) -> list[tuple[int, str, str]]:
        return list(product.shop_pages.order_by("pk").values_list("pk", "shop", "url"))

    def _price_rows(self) -> list[tuple[int, int]]:
        return list(
            PriceObservation.objects.order_by("pk").values_list("pk", "shop_page_id")
        )

    def test_anonymous_requests_redirect_to_sign_in(self) -> None:
        product, _pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        url = self._url(product.pk)
        self.assertRedirects(
            self.client.get(url),
            f"/accounts/login/?next=/products/{product.pk}/change/",
        )
        self.assertRedirects(
            self.client.post(url, self._payload("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))),
            f"/accounts/login/?next=/products/{product.pk}/change/",
        )
        self.assertEqual(Product.objects.get().name, "Alpecin")

    def test_non_staff_post_is_forbidden(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        self._login()
        url = self._url(product.pk)
        self.assertEqual(self.client.get(url).status_code, 403)
        response = self.client.post(
            url,
            self._payload("Renamed", ((Shop.DOZ, DOZ_URL),)),
        )
        self.assertEqual(response.status_code, 403)
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_missing_product_returns_404(self) -> None:
        self._login(is_staff=True)
        self.assertEqual(self.client.get(self._url(999999)).status_code, 404)
        self.assertEqual(
            self.client.post(
                self._url(999999),
                self._payload("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),)),
            ).status_code,
            404,
        )
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(ShopPage.objects.count(), 0)

    def test_get_prefills_shop_pages_in_pk_order(self) -> None:
        product, _pages = self._make_product(
            "Alpecin",
            (
                (Shop.DOZ, DOZ_URL),
                (Shop.ROSSMANN, ROSSMANN_URL),
            ),
        )
        self._login(is_staff=True)
        url = self._url(product.pk)
        self.assertEqual(url, f"/products/{product.pk}/change/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_bound)
        self.assertEqual(form.initial["name"], "Alpecin")
        self.assertEqual(form.initial["shop_1"], Shop.DOZ)
        self.assertEqual(form.initial["url_1"], DOZ_URL)
        self.assertEqual(form.initial["shop_2"], Shop.ROSSMANN)
        self.assertEqual(form.initial["url_2"], ROSSMANN_URL)
        self.assertEqual(form.initial["shop_3"], "")
        self.assertEqual(form.initial["url_3"], "")
        self.assertContains(response, DOZ_URL)
        self.assertContains(response, ROSSMANN_URL)

    def test_same_shop_url_change_keeps_the_page_and_its_prices(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
            ),
        )
        first = self._price(pages[0], "10.00")
        second = self._price(pages[0], "12.50")
        kept = self._price(pages[1], "8.00")
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload(
                "Alpecin",
                (
                    (Shop.ROSSMANN, NEW_ROSSMANN_URL),
                    (Shop.DOZ, DOZ_URL),
                ),
            ),
        )
        self.assertRedirects(response, LIST_URL)
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(
            self._page_rows(product),
            [
                (pages[0].pk, Shop.ROSSMANN, NEW_ROSSMANN_URL),
                (pages[1].pk, Shop.DOZ, DOZ_URL),
            ],
        )
        self.assertEqual(
            self._price_rows(),
            [
                (first.pk, pages[0].pk),
                (second.pk, pages[0].pk),
                (kept.pk, pages[1].pk),
            ],
        )

    def test_rename_keeps_prices_without_a_confirm_step(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
            ),
        )
        first = self._price(pages[0])
        second = self._price(pages[1], "12.50")
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload(
                "Caffeine shampoo",
                (
                    (Shop.ROSSMANN, ROSSMANN_URL),
                    (Shop.DOZ, DOZ_URL),
                ),
            ),
        )
        self.assertRedirects(response, LIST_URL)
        self.assertNotContains(response, "recorded prices will be deleted", status_code=302)
        product.refresh_from_db()
        self.assertEqual(product.name, "Caffeine shampoo")
        self.assertEqual(
            self._page_rows(product),
            [
                (pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL),
                (pages[1].pk, Shop.DOZ, DOZ_URL),
            ],
        )
        self.assertEqual(
            self._price_rows(),
            [(first.pk, pages[0].pk), (second.pk, pages[1].pk)],
        )
        follow = self.client.get(LIST_URL)
        self.assertContains(follow, "Caffeine shampoo")
        self.assertNotContains(follow, "Alpecin")

    def test_clearing_every_row_stores_nothing(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
            ),
        )
        price = self._price(pages[0])
        before = self._page_rows(product)
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Renamed", ()),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Enter at least one shop page.",
            response.context["form"].errors["shop_1"],
        )
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), before)
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_gapped_rows_store_nothing(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload(
                "Alpecin",
                (),
                shop_2=Shop.DOZ,
                url_2=DOZ_URL,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Enter the first shop page before the second.",
            response.context["form"].errors["url_2"],
        )
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_one_page_product_can_be_renamed(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Caffeine shampoo", ((Shop.ROSSMANN, ROSSMANN_URL),)),
        )
        self.assertRedirects(response, LIST_URL)
        product.refresh_from_db()
        self.assertEqual(product.name, "Caffeine shampoo")
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_switching_the_only_shop_without_prices_saves(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        old_pk = pages[0].pk
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Alpecin", ((Shop.DOZ, DOZ_URL),)),
        )
        self.assertRedirects(response, LIST_URL)
        self.assertEqual(ShopPage.objects.count(), 1)
        new_page = ShopPage.objects.get()
        self.assertNotEqual(new_page.pk, old_pk)
        self.assertEqual(new_page.product_id, product.pk)
        self.assertEqual(new_page.shop, Shop.DOZ)
        self.assertEqual(new_page.url, DOZ_URL)
        self.assertEqual(new_page.observations.count(), 0)
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertFalse(ShopPage.objects.filter(pk=old_pk).exists())

    def test_switching_a_shop_with_prices_saves_only_after_confirm(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        old_pk = pages[0].pk
        self._login(is_staff=True)
        url = self._url(product.pk)
        payload = self._payload("Alpecin", ((Shop.DOZ, DOZ_URL),))
        first = self.client.post(url, payload)
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, "Alpecin")
        self.assertContains(first, "Rossmann")
        self.assertContains(first, "recorded prices will be deleted")
        self.assertContains(first, 'name="confirm" value="yes"')
        self.assertContains(first, 'name="name" value="Alpecin"')
        self.assertContains(first, 'name="shop_1" value="doz"')
        self.assertContains(first, f'name="url_1" value="{DOZ_URL}"')
        self.assertContains(first, 'name="shop_2" value=""')
        self.assertContains(first, 'name="url_3" value=""')
        self.assertContains(first, f'action="/products/{product.pk}/change/"')
        self.assertContains(first, 'name="canceled" value="1"')
        self.assertContains(first, ">Cancel<")
        self.assertContains(first, ">Confirm<")
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), [(old_pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, old_pk)])
        self.client.get(LIST_URL)
        self.assertEqual(self._page_rows(product), [(old_pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, old_pk)])
        payload["confirm"] = "yes"
        second = self.client.post(url, payload)
        self.assertRedirects(second, LIST_URL)
        self.assertEqual(ShopPage.objects.count(), 1)
        new_page = ShopPage.objects.get()
        self.assertNotEqual(new_page.pk, old_pk)
        self.assertEqual(new_page.shop, Shop.DOZ)
        self.assertEqual(new_page.url, DOZ_URL)
        self.assertEqual(new_page.observations.count(), 0)
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertFalse(ShopPage.objects.filter(pk=old_pk).exists())

    def test_dropping_an_unpriced_shop_saves_and_keeps_the_priced_page(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
            ),
        )
        price = self._price(pages[0])
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),)),
        )
        self.assertRedirects(response, LIST_URL)
        product.refresh_from_db()
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])
        self.assertFalse(ShopPage.objects.filter(pk=pages[1].pk).exists())

    def test_dropping_a_priced_shop_keeps_the_other_page_after_confirm(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
            ),
        )
        kept = self._price(pages[0], "10.00")
        dropped = self._price(pages[1], "12.50")
        self._login(is_staff=True)
        url = self._url(product.pk)
        payload = self._payload("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        first = self.client.post(url, payload)
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, "DOZ")
        self.assertContains(first, "recorded prices will be deleted")
        self.assertNotContains(first, "Rossmann")
        product.refresh_from_db()
        self.assertEqual(
            self._page_rows(product),
            [
                (pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL),
                (pages[1].pk, Shop.DOZ, DOZ_URL),
            ],
        )
        self.assertEqual(
            self._price_rows(),
            [(kept.pk, pages[0].pk), (dropped.pk, pages[1].pk)],
        )
        payload["confirm"] = "yes"
        second = self.client.post(url, payload)
        self.assertRedirects(second, LIST_URL)
        product.refresh_from_db()
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(kept.pk, pages[0].pk)])
        self.assertFalse(ShopPage.objects.filter(pk=pages[1].pk).exists())

    def test_four_shop_pages_writes_nothing(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
                (Shop.SUPERPHARM, SUPERPHARM_URL),
                (Shop.GEMINI, GEMINI_URL),
            ),
        )
        price = self._price(pages[0])
        before = self._page_rows(product)
        self._login(is_staff=True)
        url = self._url(product.pk)
        opened = self.client.get(url)
        self.assertEqual(opened.status_code, 200)
        self.assertContains(opened, "This product has more shops than this form can save.")
        self.assertNotContains(opened, "<form")
        posted = self.client.post(
            url,
            self._payload(
                "Renamed",
                ((Shop.ROSSMANN, NEW_ROSSMANN_URL),),
                confirm="yes",
            ),
        )
        self.assertEqual(posted.status_code, 200)
        self.assertContains(posted, "This product has more shops than this form can save.")
        self.assertNotContains(posted, "<form")
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(product.shop_pages.count(), 4)
        self.assertEqual(self._page_rows(product), before)
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_duplicate_name_writes_nothing(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        Product.objects.create(name="Other shampoo")
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Other shampoo", ((Shop.ROSSMANN, ROSSMANN_URL),)),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])

    def test_duplicate_url_on_a_shop_switch_rolls_back(self) -> None:
        product, pages = self._make_product("Alpecin", ((Shop.ROSSMANN, ROSSMANN_URL),))
        price = self._price(pages[0])
        other = Product.objects.create(name="Other shampoo")
        ShopPage.objects.create(product=other, shop=Shop.DOZ, url=DOZ_URL)
        self._login(is_staff=True)
        response = self.client.post(
            self._url(product.pk),
            self._payload("Renamed", ((Shop.DOZ, DOZ_URL),), confirm="yes"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("url_1", response.context["form"].errors)
        self.assertNotContains(response, "recorded prices will be deleted")
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_rows(product), [(pages[0].pk, Shop.ROSSMANN, ROSSMANN_URL)])
        self.assertEqual(self._price_rows(), [(price.pk, pages[0].pk)])
        self.assertEqual(other.shop_pages.get().url, DOZ_URL)
