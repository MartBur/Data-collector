from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.http import StreamingHttpResponse
from django.test import TestCase

from prices.collect import FetchFailed
from prices.management.recording_command import recording_progress_bar
from prices.models import PriceObservation, PriceRecordingRun, Product, Shop, ShopPage
from prices.tests.test_commands import DOZ_HTML, ROSSMANN_HTML

PASSWORD: str = "correct-horse"
PRICE_UPDATES_URL: str = "/products/price-updates/"


def _stream_body(response: StreamingHttpResponse) -> str:
    """Return the streamed HTML once the recording generator has finished."""
    return b"".join(response.streaming_content).decode()


class PriceUpdateTests(TestCase):
    def test_progress_bar_rounds_each_remainder_up_to_the_next_tenth(self) -> None:
        self.assertEqual(recording_progress_bar(0, 10), "----------")
        self.assertEqual(recording_progress_bar(1, 10), "#---------")
        self.assertEqual(recording_progress_bar(1, 7), "##--------")
        self.assertEqual(recording_progress_bar(3, 10), "###-------")
        self.assertEqual(recording_progress_bar(9, 10), "#########-")
        self.assertEqual(recording_progress_bar(10, 10), "##########")
        self.assertEqual(recording_progress_bar(1, 1), "##########")

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

    def _pages(self) -> tuple[ShopPage, ShopPage]:
        product = Product.objects.create(name="Shampoo")
        rossmann = ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        doz = ShopPage.objects.create(
            product=product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/product/1",
        )
        return rossmann, doz

    def test_staff_sees_an_all_button_and_one_button_per_shop(self) -> None:
        self._login(is_staff=True)

        response = self.client.get(PRICE_UPDATES_URL)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "all shop update")
        self.assertContains(response, "Rossmann update")
        self.assertContains(response, "DOZ update")
        self.assertContains(response, "Super-Pharm update")
        self.assertContains(response, "Gemini update")
        self.assertContains(response, "Last price update: none - Warsaw time")
        self.assertContains(response, '<a href="/">Home</a>')
        self.assertContains(response, "----------")

    def test_non_staff_cannot_open_price_updates(self) -> None:
        self._login()

        response = self.client.get(PRICE_UPDATES_URL)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_post_redirects_to_sign_in(self) -> None:
        response = self.client.post(PRICE_UPDATES_URL, {"shop": "all"})

        self.assertRedirects(response, f"/accounts/login/?next={PRICE_UPDATES_URL}")

    def test_all_shop_update_records_every_page_and_stamps_the_clock(self) -> None:
        self._login(is_staff=True)
        self._pages()

        def fake_fetch(url: str, _shop: str) -> str:
            if "rossmann" in url:
                return ROSSMANN_HTML
            return DOZ_HTML

        with patch("prices.collect.fetch_html", side_effect=fake_fetch):
            response = self.client.post(PRICE_UPDATES_URL, {"shop": "all"})
            body = _stream_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertLess(body.index("----------"), body.index("#####-----"))
        self.assertLess(body.index("#####-----"), body.index("##########"))
        self.assertEqual(PriceObservation.objects.count(), 2)
        self.assertEqual(PriceRecordingRun.objects.count(), 1)
        follow = self.client.get(PRICE_UPDATES_URL)
        self.assertContains(follow, "Last price update:")
        self.assertNotContains(follow, "Last price update: none - Warsaw time")

    def test_one_shop_update_leaves_the_other_shop_untouched(self) -> None:
        self._login(is_staff=True)
        rossmann, doz = self._pages()

        def rossmann_only(url: str, _shop: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=rossmann_only):
            response = self.client.post(PRICE_UPDATES_URL, {"shop": Shop.ROSSMANN})
            body = _stream_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertLess(body.index("----------"), body.index("##########"))
        self.assertNotIn("#####-----", body)
        self.assertEqual(PriceObservation.objects.filter(shop_page=rossmann).count(), 1)
        self.assertEqual(PriceObservation.objects.filter(shop_page=doz).count(), 0)
        self.assertEqual(PriceRecordingRun.objects.count(), 1)

    def test_unknown_shop_does_not_record(self) -> None:
        self._login(is_staff=True)
        self._pages()

        response = self.client.post(PRICE_UPDATES_URL, {"shop": "other"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertEqual(PriceRecordingRun.objects.count(), 0)

    def test_three_pages_stream_bars_rounded_up_between_tenths(self) -> None:
        self._login(is_staff=True)
        for name in ("One", "Two", "Three"):
            product = Product.objects.create(name=name)
            ShopPage.objects.create(
                product=product,
                shop=Shop.ROSSMANN,
                url=f"https://www.rossmann.pl/product/{name}",
            )

        def fake_fetch(url: str, _shop: str) -> str:
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=fake_fetch):
            response = self.client.post(PRICE_UPDATES_URL, {"shop": "all"})
            body = _stream_body(response)

        self.assertEqual(response.status_code, 200)
        empty = body.index("----------")
        one_third = body.index("####------")
        two_thirds = body.index("#######---")
        done = body.index("##########")
        self.assertLess(empty, one_third)
        self.assertLess(one_third, two_thirds)
        self.assertLess(two_thirds, done)
        self.assertEqual(PriceObservation.objects.count(), 3)
        self.assertEqual(PriceRecordingRun.objects.count(), 1)

    def test_no_pages_fills_the_bar_and_stamps_the_clock(self) -> None:
        self._login(is_staff=True)

        with patch("prices.collect.fetch_html") as fetch:
            response = self.client.post(PRICE_UPDATES_URL, {"shop": "all"})
            body = _stream_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertLess(body.index("----------"), body.index("##########"))
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertEqual(PriceRecordingRun.objects.count(), 1)
        fetch.assert_not_called()

    def test_a_failed_page_still_advances_the_bar(self) -> None:
        self._login(is_staff=True)
        self._pages()

        def fail(url: str, _shop: str) -> str:
            raise FetchFailed(url)

        with patch("prices.collect.fetch_html", side_effect=fail):
            response = self.client.post(PRICE_UPDATES_URL, {"shop": "all"})
            body = _stream_body(response)

        self.assertEqual(response.status_code, 200)
        self.assertLess(body.index("----------"), body.index("#####-----"))
        self.assertLess(body.index("#####-----"), body.index("##########"))
        self.assertEqual(PriceObservation.objects.count(), 0)
        self.assertEqual(PriceRecordingRun.objects.count(), 1)
