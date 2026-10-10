from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from prices.models import PriceObservation, Product, Shop, ShopPage


class ShopPageModelTests(TestCase):
    def setUp(self) -> None:
        self.product: Product = Product.objects.create(name="Shampoo")

    def test_product_can_have_one_page_for_each_shop(self) -> None:
        urls: dict[str, str] = {
            Shop.ROSSMANN: "https://www.rossmann.pl/product/1",
            Shop.DOZ: "https://www.doz.pl/product/1",
            Shop.SUPERPHARM: "https://www.superpharm.pl/product/1",
            Shop.GEMINI: "https://gemini.pl/product/1",
        }
        for shop, url in urls.items():
            page = ShopPage(product=self.product, shop=shop, url=url)
            page.full_clean()
            page.save()
        self.assertEqual(self.product.shop_pages.count(), 4)

    def test_second_page_for_the_same_shop_is_rejected(self) -> None:
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        duplicate = ShopPage(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/2",
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save()

    def test_two_products_may_share_a_shop(self) -> None:
        other = Product.objects.create(name="Soap")
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/a",
        )
        page = ShopPage(
            product=other,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/b",
        )
        page.full_clean()
        page.save()
        self.assertEqual(ShopPage.objects.filter(shop=Shop.ROSSMANN).count(), 2)

    def test_host_must_match_the_chosen_shop(self) -> None:
        page = ShopPage(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.doz.pl/product/1",
        )
        with self.assertRaises(ValidationError) as raised:
            page.full_clean()
        self.assertIn("url", raised.exception.error_dict)

    def test_www_and_apex_hosts_are_accepted(self) -> None:
        www_page = ShopPage(
            product=self.product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/product/1",
        )
        www_page.full_clean()
        www_page.save()
        other = Product.objects.create(name="Cream")
        apex_page = ShopPage(
            product=other,
            shop=Shop.DOZ,
            url="https://doz.pl/product/2",
        )
        apex_page.full_clean()
        apex_page.save()

    def test_same_shop_page_ignoring_www_and_trailing_slash_is_rejected(self) -> None:
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon",
        )
        other = Product.objects.create(name="Soap")
        duplicate = ShopPage(
            product=other,
            shop=Shop.ROSSMANN,
            url="https://rossmann.pl/Produkt/szampon/",
        )
        with self.assertRaises(ValidationError) as raised:
            duplicate.full_clean()
        self.assertIn("url", raised.exception.error_dict)

    def test_query_string_distinguishes_shop_pages(self) -> None:
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon?a=1",
        )
        other = Product.objects.create(name="Soap")
        page = ShopPage(
            product=other,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon?a=2",
        )
        page.full_clean()
        page.save()

    def test_scheme_distinguishes_shop_pages(self) -> None:
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon",
        )
        other = Product.objects.create(name="Soap")
        page = ShopPage(
            product=other,
            shop=Shop.ROSSMANN,
            url="http://www.rossmann.pl/Produkt/szampon",
        )
        page.full_clean()
        page.save()

    def test_fragment_does_not_distinguish_shop_pages(self) -> None:
        ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon",
        )
        other = Product.objects.create(name="Soap")
        duplicate = ShopPage(
            product=other,
            shop=Shop.ROSSMANN,
            url="https://rossmann.pl/Produkt/szampon/#opis",
        )
        with self.assertRaises(ValidationError) as raised:
            duplicate.full_clean()
        self.assertIn("url", raised.exception.error_dict)

    def test_existing_shop_page_does_not_clash_with_itself(self) -> None:
        page = ShopPage.objects.create(
            product=self.product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/Produkt/szampon/",
        )
        page.full_clean()


class ProductNameTests(TestCase):
    def test_folded_duplicate_name_is_rejected(self) -> None:
        Product.objects.create(name="Alpecin")
        duplicate = Product(name=" alpecin ")
        with self.assertRaises(ValidationError) as raised:
            duplicate.full_clean()
        self.assertIn("name", raised.exception.error_dict)
        self.assertEqual(duplicate.name, "alpecin")

    def test_internal_space_difference_is_a_different_name(self) -> None:
        Product.objects.create(name="Alpecin shampoo")
        other = Product(name="Alpecin  shampoo")
        other.full_clean()
        other.save()
        self.assertEqual(Product.objects.count(), 2)

    def test_blank_name_is_rejected(self) -> None:
        blank = Product(name="   ")
        with self.assertRaises(ValidationError) as raised:
            blank.full_clean()
        self.assertIn("name", raised.exception.error_dict)

    def test_clean_stores_the_trimmed_spelling(self) -> None:
        product = Product(name="  Alpecin  ")
        product.full_clean()
        product.save()
        self.assertEqual(product.name, "Alpecin")

    def test_existing_product_name_does_not_clash_with_itself(self) -> None:
        product = Product.objects.create(name="Alpecin")
        product.full_clean()


class PriceObservationModelTests(TestCase):
    def test_many_observations_may_exist_for_one_page_on_one_date(self) -> None:
        product = Product.objects.create(name="Shampoo")
        page = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        observed = date(2026, 9, 24)
        PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal("10.00"),
            observed_date=observed,
        )
        PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal("12.50"),
            observed_date=observed,
        )
        self.assertEqual(page.observations.filter(observed_date=observed).count(), 2)

    def test_database_rejects_a_non_positive_amount(self) -> None:
        product = Product.objects.create(name="Shampoo")
        page = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PriceObservation.objects.create(
                    shop_page=page,
                    amount=Decimal("-1.00"),
                    observed_date=date(2026, 9, 24),
                )
