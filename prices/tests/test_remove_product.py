from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.urls import reverse

from prices.models import PriceObservation, Product, Shop, ShopPage

LIST_URL: str = "/products/"
PASSWORD: str = "correct-horse"
KEPT_SENTENCE: str = "A tracked product must keep one shop page."
PRICE_SENTENCE: str = "recorded prices will be deleted"
ROSSMANN_URL: str = "https://www.rossmann.pl/Produkt/alpecin"
DOZ_URL: str = "https://www.doz.pl/p/alpecin"
SUPERPHARM_URL: str = "https://www.superpharm.pl/p/alpecin"
GEMINI_URL: str = "https://gemini.pl/p/alpecin"


class RemoveProductTests(TestCase):
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

    def _page_url(self, pk: int, page_pk: int) -> str:
        return reverse(
            "prices:remove_shop_page",
            kwargs={"pk": pk, "page_pk": page_pk},
        )

    def _product_url(self, pk: int) -> str:
        return reverse("prices:remove_product", kwargs={"pk": pk})

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

    def _price(self, page: ShopPage) -> PriceObservation:
        return PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal("10.00"),
            observed_date=date.today(),
        )

    def _page_ids(self, product: Product) -> list[int]:
        return list(product.shop_pages.order_by("pk").values_list("pk", flat=True))

    def test_list_offers_change_and_both_remove_actions(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        self._login(is_staff=True)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rossmann")
        self.assertContains(response, "DOZ")
        self.assertContains(
            response,
            f'href="/products/{product.pk}/change/"',
        )
        self.assertContains(response, "Change")
        self.assertContains(
            response,
            f'action="/products/{product.pk}/remove/"',
        )
        self.assertContains(response, "Remove product")
        self.assertContains(
            response,
            f'action="/products/{product.pk}/shop-pages/{pages[0].pk}/remove/"',
        )
        self.assertContains(response, ">Remove<")
        self.assertNotContains(response, KEPT_SENTENCE)

    def test_removing_one_page_from_a_three_page_product_deletes_that_page_and_its_prices(
        self,
    ) -> None:
        product, pages = self._make_product(
            "Alpecin",
            (
                (Shop.ROSSMANN, ROSSMANN_URL),
                (Shop.DOZ, DOZ_URL),
                (Shop.SUPERPHARM, SUPERPHARM_URL),
            ),
        )
        doomed = self._price(pages[0])
        kept = self._price(pages[1])
        self._login(is_staff=True)
        url = self._page_url(product.pk, pages[0].pk)
        self.assertEqual(
            url,
            f"/products/{product.pk}/shop-pages/{pages[0].pk}/remove/",
        )
        response = self.client.post(url, {"confirm": "yes"})
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertFalse(PriceObservation.objects.filter(pk=doomed.pk).exists())
        self.assertEqual(self._page_ids(product), [pages[1].pk, pages[2].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=kept.pk).exists())
        listed = self.client.get(LIST_URL)
        self.assertContains(listed, "DOZ")
        self.assertContains(listed, "Super-Pharm")
        self.assertNotContains(listed, "Rossmann")

    def test_removing_a_page_with_no_prices_skips_confirm_and_deletes_the_page(
        self,
    ) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        kept = self._price(pages[1])
        self._login(is_staff=True)
        response = self.client.post(self._page_url(product.pk, pages[0].pk), {})
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertEqual(self._page_ids(product), [pages[1].pk])
        self.assertEqual(
            list(PriceObservation.objects.values_list("pk", flat=True)),
            [kept.pk],
        )

    def test_removing_a_page_with_prices_writes_nothing_until_confirm(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        price = self._price(pages[0])
        self._login(is_staff=True)
        url = self._page_url(product.pk, pages[0].pk)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpecin")
        self.assertContains(response, "Rossmann")
        self.assertContains(response, PRICE_SENTENCE)
        self.assertContains(response, 'name="confirm"')
        self.assertContains(response, 'value="yes"')
        self.assertContains(response, f'action="{url}"')
        self.assertTrue(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
        self.assertEqual(self._page_ids(product), [pages[0].pk, pages[1].pk])
        blank = self.client.post(url, {"confirm": "   "})
        self.assertEqual(blank.status_code, 200)
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
        confirmed = self.client.post(url, {"confirm": "yes"})
        self.assertRedirects(confirmed, LIST_URL)
        self.assertFalse(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertFalse(PriceObservation.objects.filter(pk=price.pk).exists())
        self.assertEqual(self._page_ids(product), [pages[1].pk])

    def test_cancel_returns_to_the_list_and_keeps_the_page(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        price = self._price(pages[0])
        self._login(is_staff=True)
        url = self._page_url(product.pk, pages[0].pk)
        confirm = self.client.post(url, {})
        self.assertContains(confirm, ">Cancel<")
        self.assertContains(confirm, 'name="canceled" value="1"')
        listed = self.client.get(f"{LIST_URL}?canceled=1")
        self.assertContains(listed, "Action was canceled.")
        self.assertTrue(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())

    def test_removing_the_only_page_leaves_the_product_and_shows_the_notice(
        self,
    ) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL),),
        )
        price = self._price(pages[0])
        self._login(is_staff=True)
        url = self._page_url(product.pk, pages[0].pk)
        response = self.client.post(url, {})
        self.assertRedirects(response, f"{LIST_URL}?kept={product.pk}")
        product.refresh_from_db()
        self.assertEqual(product.name, "Alpecin")
        self.assertEqual(self._page_ids(product), [pages[0].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
        kept = self.client.get(f"{LIST_URL}?kept={product.pk}")
        self.assertContains(kept, KEPT_SENTENCE)
        self.assertContains(kept, "Alpecin")
        self.assertContains(kept, "Rossmann")
        self.assertNotContains(kept, PRICE_SENTENCE)
        plain = self.client.get(LIST_URL)
        self.assertNotContains(plain, KEPT_SENTENCE)
        unknown = self.client.get(f"{LIST_URL}?kept=999999")
        self.assertNotContains(unknown, KEPT_SENTENCE)
        again = self.client.post(url, {"confirm": "yes"})
        self.assertRedirects(again, f"{LIST_URL}?kept={product.pk}")
        self.assertEqual(self._page_ids(product), [pages[0].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())

    def test_removing_the_product_deletes_it_after_confirm_when_a_page_has_a_price(
        self,
    ) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        priced = self._price(pages[0])
        other, other_pages = self._make_product(
            "Other",
            ((Shop.GEMINI, GEMINI_URL),),
        )
        self._login(is_staff=True)
        url = self._product_url(product.pk)
        self.assertEqual(url, f"/products/{product.pk}/remove/")
        first = self.client.post(url, {})
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, "Alpecin")
        self.assertContains(first, "Rossmann")
        self.assertContains(first, "DOZ")
        self.assertContains(first, PRICE_SENTENCE)
        self.assertContains(first, f'action="{url}"')
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertTrue(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertTrue(ShopPage.objects.filter(pk=pages[1].pk).exists())
        self.assertTrue(PriceObservation.objects.filter(pk=priced.pk).exists())
        response = self.client.post(url, {"confirm": "yes"})
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(ShopPage.objects.filter(pk=pages[0].pk).exists())
        self.assertFalse(ShopPage.objects.filter(pk=pages[1].pk).exists())
        self.assertFalse(PriceObservation.objects.filter(pk=priced.pk).exists())
        self.assertTrue(Product.objects.filter(pk=other.pk).exists())
        self.assertTrue(ShopPage.objects.filter(pk=other_pages[0].pk).exists())
        listed = self.client.get(LIST_URL)
        self.assertNotContains(listed, "Alpecin")
        self.assertContains(listed, "Other")

    def test_removing_a_product_with_no_prices_deletes_on_the_first_post(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        self._login(is_staff=True)
        response = self.client.post(self._product_url(product.pk), {})
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(ShopPage.objects.filter(pk__in=[pages[0].pk, pages[1].pk]).exists())
        self.assertEqual(PriceObservation.objects.count(), 0)

    def test_non_staff_post_is_forbidden(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        price = self._price(pages[0])
        self._login()
        page_response = self.client.post(self._page_url(product.pk, pages[0].pk), {})
        product_response = self.client.post(self._product_url(product.pk), {})
        self.assertEqual(page_response.status_code, 403)
        self.assertEqual(product_response.status_code, 403)
        self.assertEqual(self._page_ids(product), [pages[0].pk, pages[1].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_shop_page_from_another_product_returns_404_and_deletes_nothing(
        self,
    ) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        other, other_pages = self._make_product(
            "Other",
            ((Shop.GEMINI, GEMINI_URL),),
        )
        price = self._price(pages[0])
        other_price = self._price(other_pages[0])
        self._login(is_staff=True)
        response = self.client.post(
            self._page_url(product.pk, other_pages[0].pk),
            {"confirm": "yes"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self._page_ids(product), [pages[0].pk, pages[1].pk])
        self.assertEqual(self._page_ids(other), [other_pages[0].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
        self.assertTrue(PriceObservation.objects.filter(pk=other_price.pk).exists())
        missing = self.client.post(self._page_url(product.pk, 999999), {})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.client.post(self._product_url(999999), {}).status_code, 404)
        self.assertEqual(Product.objects.count(), 2)

    def test_get_does_not_delete(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        price = self._price(pages[0])
        self._login(is_staff=True)
        page_response = self.client.get(self._page_url(product.pk, pages[0].pk))
        product_response = self.client.get(self._product_url(product.pk))
        self.assertEqual(page_response.status_code, 405)
        self.assertEqual(product_response.status_code, 405)
        self.assertEqual(self._page_ids(product), [pages[0].pk, pages[1].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())

    def test_anonymous_post_redirects_to_sign_in_and_deletes_nothing(self) -> None:
        product, pages = self._make_product(
            "Alpecin",
            ((Shop.ROSSMANN, ROSSMANN_URL), (Shop.DOZ, DOZ_URL)),
        )
        price = self._price(pages[0])
        page_url = self._page_url(product.pk, pages[0].pk)
        product_url = self._product_url(product.pk)
        self.assertRedirects(
            self.client.post(page_url, {}),
            f"/accounts/login/?next={page_url}",
        )
        self.assertRedirects(
            self.client.post(product_url, {}),
            f"/accounts/login/?next={product_url}",
        )
        self.assertEqual(self._page_ids(product), [pages[0].pk, pages[1].pk])
        self.assertTrue(PriceObservation.objects.filter(pk=price.pk).exists())
