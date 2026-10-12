from collections.abc import Callable, Iterator

from django.core.management.base import BaseCommand
from django.utils import timezone

from prices import collect
from prices.models import ShopPage
from prices.recording_clock import mark_recording_finished

_BAR_WIDTH: int = 10


def recording_progress_bar(finished: int, total: int) -> str:
    """Return ten characters, one hash for each finished tenth, rounded up.

    Zero finished pages stay dashes. An exact tenth stays on that mark.
    Any remainder fills the next hash.
    """
    if finished <= 0 or total <= 0:
        filled = 0
    else:
        filled = (finished * _BAR_WIDTH + total - 1) // total
        if filled > _BAR_WIDTH:
            filled = _BAR_WIDTH
    return "#" * filled + "-" * (_BAR_WIDTH - filled)


def iter_price_recording(
    shop_code: str | None,
    write: Callable[[str], None],
) -> Iterator[str]:
    """Record each page, yield its progress bar, then stamp the clock.

    ``shop_code`` None records every tracked shop page. A raise before the
    clock stamp leaves the previous finish time in place. No pages yield one
    full bar after the stamp.
    """
    pages = ShopPage.objects.all()
    if shop_code is not None:
        pages = pages.filter(shop=shop_code)
    page_list = list(pages)
    total = len(page_list)
    for index, shop_page in enumerate(page_list, start=1):
        result = collect.record_one_page(
            shop_page,
            collect.fetch_html,
            timezone.localdate(),
        )
        write(f"{result.value} {shop_page.get_shop_display()} {shop_page.url}")
        yield recording_progress_bar(index, total)
    mark_recording_finished(timezone.now())
    if total == 0:
        yield "#" * _BAR_WIDTH


def run_price_recording(shop_code: str | None, write: Callable[[str], None]) -> None:
    """Record today's prices for every page, or for one shop, then stamp the clock."""
    for _bar in iter_price_recording(shop_code, write):
        pass


class ShopRecordCommand(BaseCommand):
    shop_code: str | None = None

    def handle(self, *args: str, **options: object) -> None:
        run_price_recording(self.shop_code, self.stdout.write)
