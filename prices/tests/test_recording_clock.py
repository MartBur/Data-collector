from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from prices.models import PriceRecordingRun, Product, Shop, ShopPage
from prices.recording_clock import latest_recording_finished_at, mark_recording_finished
from prices.tests.test_commands import DOZ_HTML, ROSSMANN_HTML


class RecordingClockTests(TestCase):
    def test_no_stored_run_has_no_finish_time(self) -> None:
        self.assertIsNone(latest_recording_finished_at())

    def test_later_aware_finish_time_wins(self) -> None:
        earlier = timezone.now()
        later = earlier + timedelta(hours=2)
        self.assertTrue(timezone.is_aware(earlier))
        self.assertTrue(timezone.is_aware(later))
        mark_recording_finished(later)
        mark_recording_finished(earlier)

        self.assertEqual(latest_recording_finished_at(), later)

    def test_record_prices_inserts_one_run(self) -> None:
        product = Product.objects.create(name="Shampoo")
        ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        ShopPage.objects.create(
            product=product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/product/1",
        )

        def fake_fetch(url: str, _shop: str) -> str:
            if "rossmann" in url:
                return ROSSMANN_HTML
            return DOZ_HTML

        with patch("prices.collect.fetch_html", side_effect=fake_fetch):
            call_command("record_prices", stdout=StringIO())

        self.assertEqual(PriceRecordingRun.objects.count(), 1)
        finished_at = latest_recording_finished_at()
        self.assertIsNotNone(finished_at)
        self.assertTrue(finished_at is not None and timezone.is_aware(finished_at))

    def test_record_rossmann_prices_inserts_one_run(self) -> None:
        product = Product.objects.create(name="Shampoo")
        ShopPage.objects.create(
            product=product,
            shop=Shop.ROSSMANN,
            url="https://www.rossmann.pl/product/1",
        )
        ShopPage.objects.create(
            product=product,
            shop=Shop.DOZ,
            url="https://www.doz.pl/product/1",
        )

        def rossmann_only(url: str, _shop: str) -> str:
            if "rossmann" not in url:
                raise AssertionError(url)
            return ROSSMANN_HTML

        with patch("prices.collect.fetch_html", side_effect=rossmann_only):
            call_command("record_rossmann_prices", stdout=StringIO())

        self.assertEqual(PriceRecordingRun.objects.count(), 1)
        finished_at = latest_recording_finished_at()
        self.assertIsNotNone(finished_at)
        self.assertTrue(finished_at is not None and timezone.is_aware(finished_at))
