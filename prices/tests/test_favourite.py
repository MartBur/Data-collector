import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from prices.models import Favourite, PriceObservation, Product, Shop, ShopPage

PASSWORD: str = "correct-horse"
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


class FavouriteTests(TestCase):
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

    def _toggle_url(self, pk: int) -> str:
        return reverse("prices:toggle_favourite", kwargs={"pk": pk})

    def _card_url(self, pk: int) -> str:
        return reverse("prices:product_card", kwargs={"pk": pk})

    def _home_body(self) -> str:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_non_staff_post_toggles_the_card_and_the_favourites_table(self) -> None:
        product = self._product()
        page = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/p/alpecin",
        )
        PriceObservation.objects.create(
            shop_page=page,
            amount=Decimal("19.99"),
            observed_date=timezone.localdate(),
        )
        user = self._login()
        self.assertFalse(user.is_staff)
        toggle_url = self._toggle_url(product.pk)
        card_url = self._card_url(product.pk)
        self.assertEqual(toggle_url, f"/products/{product.pk}/favourite/")
        link = f'href="/products/{product.pk}/">Alpecin</a>'

        before = self.client.get(card_url)
        self.assertEqual(before.status_code, 200)
        before_html = before.content.decode()
        form = before_html.split("<form", 1)[1].split("</form>", 1)[0]
        self.assertLess(before_html.index("<p>Alpecin</p>"), before_html.index("<form"))
        self.assertIn(f'action="{toggle_url}"', form)
        self.assertIn("csrfmiddlewaretoken", form)
        self.assertIn("Add to favourites", form)
        self.assertNotIn("Remove from favourites", form)
        self.assertIn("19.99 PLN", before_html)
        self.assertIn("Rossmann", before_html)
        self.assertIn("<svg", before_html)

        added = self.client.post(toggle_url)
        self.assertRedirects(added, card_url)
        self.assertTrue(Favourite.objects.filter(user=user, product=product).exists())
        after_add = self.client.get(card_url)
        self.assertContains(after_add, "Remove from favourites")
        self.assertNotContains(after_add, "Add to favourites")
        after_add_html = after_add.content.decode()
        self.assertIn("19.99 PLN", after_add_html)
        self.assertIn("Rossmann", after_add_html)
        self.assertIn("<svg", after_add_html)

        body = self._home_body()
        favourites = _slice_table(body, "Favourites")
        all_products = _slice_table(body, "All products")
        self.assertIn(link, favourites)
        self.assertIn(link, all_products)
        self.assertNotIn('target="_blank"', favourites)
        self.assertIn("19.99 PLN", favourites)
        self.assertIn("19.99 PLN", all_products)
        self.assertNotIn("Rossmann", favourites)
        self.assertIn("19.99 PLN", _visible_text(favourites))

        removed = self.client.post(toggle_url)
        self.assertRedirects(removed, card_url)
        self.assertFalse(Favourite.objects.filter(user=user, product=product).exists())
        after_remove = self.client.get(card_url)
        self.assertContains(after_remove, "Add to favourites")
        self.assertNotContains(after_remove, "Remove from favourites")

        cleared = self._home_body()
        cleared_favourites = _slice_table(cleared, "Favourites")
        self.assertIn("<caption>Favourites</caption>", cleared_favourites)
        self.assertIn("<td class=\"ascii-cell\">_</td>", cleared_favourites)
        self.assertNotIn("Alpecin", cleared_favourites)
        self.assertIn(link, _slice_table(cleared, "All products"))

    def test_second_user_does_not_see_the_first_users_favourite(self) -> None:
        product = self._product()
        owner = self._login()
        toggle_url = self._toggle_url(product.pk)
        self.assertRedirects(self.client.post(toggle_url), self._card_url(product.pk))
        self.assertTrue(Favourite.objects.filter(user=owner, product=product).exists())
        other = self._user("bea")
        self.client.force_login(other)

        body = self._home_body()
        favourites = _slice_table(body, "Favourites")
        all_products = _slice_table(body, "All products")

        self.assertIn("<caption>Favourites</caption>", favourites)
        self.assertIn("<td class=\"ascii-cell\">_</td>", favourites)
        self.assertNotIn("Alpecin", favourites)
        self.assertIn(
            f'href="/products/{product.pk}/">Alpecin</a>',
            all_products,
        )
        self.assertFalse(Favourite.objects.filter(user=other, product=product).exists())

    def test_staff_can_toggle(self) -> None:
        product = self._product()
        user = self._login(is_staff=True)
        self.assertTrue(user.is_staff)
        toggle_url = self._toggle_url(product.pk)
        card_url = self._card_url(product.pk)

        added = self.client.post(toggle_url)
        self.assertRedirects(added, card_url)
        self.assertTrue(Favourite.objects.filter(user=user, product=product).exists())
        self.assertContains(self.client.get(card_url), "Remove from favourites")

        removed = self.client.post(toggle_url)
        self.assertRedirects(removed, card_url)
        self.assertFalse(Favourite.objects.filter(user=user, product=product).exists())
        self.assertContains(self.client.get(card_url), "Add to favourites")

    def test_anonymous_post_redirects_to_sign_in(self) -> None:
        product = self._product()
        toggle_url = self._toggle_url(product.pk)
        self.assertRedirects(
            self.client.post(toggle_url),
            f"/accounts/login/?next={toggle_url}",
        )
        self.assertEqual(Favourite.objects.count(), 0)

    def test_missing_product_is_not_found(self) -> None:
        self._login()
        response = self.client.post(self._toggle_url(999999))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Favourite.objects.count(), 0)

    def test_get_does_not_toggle(self) -> None:
        product = self._product()
        self._login()
        response = self.client.get(self._toggle_url(product.pk))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Favourite.objects.count(), 0)

    def test_post_ignores_a_user_id_in_the_body(self) -> None:
        product = self._product()
        actor = self._user("ada")
        other = self._user("bea")
        self.client.force_login(actor)
        response = self.client.post(
            self._toggle_url(product.pk),
            {"user": str(other.pk)},
        )
        self.assertRedirects(response, self._card_url(product.pk))
        self.assertTrue(Favourite.objects.filter(user=actor, product=product).exists())
        self.assertFalse(Favourite.objects.filter(user=other, product=product).exists())

    def test_deleting_the_product_removes_the_favourite(self) -> None:
        user = self._user("ada")
        product = self._product()
        favourite = Favourite.objects.create(user=user, product=product)
        product.delete()
        self.assertFalse(Favourite.objects.filter(pk=favourite.pk).exists())
        self.assertEqual(Favourite.objects.count(), 0)
