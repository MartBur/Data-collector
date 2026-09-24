import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from enum import Enum

from django.db.models import QuerySet

from prices.models import ShopPage
from prices.readers import read_shop_price
from prices.recording import RecordOutcome, record_price

FETCH_TIMEOUT_SECONDS = 20.0
FETCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class PageResult(Enum):
    STORED = "stored"
    UNCHANGED = "unchanged"
    GAP = "gap"


class FetchFailed(Exception):
    """The page could not be read."""


def fetch_html(url: str) -> str:
    """Download one product page. Raise FetchFailed on timeout or HTTP failure."""
    request = urllib.request.Request(url, headers={"User-Agent": FETCH_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            body = response.read()
    except (TimeoutError, urllib.error.URLError) as exc:
        raise FetchFailed(str(exc)) from exc
    return body.decode("utf-8", errors="replace")


def record_one_page(
    shop_page: ShopPage,
    fetch: Callable[[str], str],
    observed_date: date,
) -> PageResult:
    """Fetch a page, retry once, and store a price only when a read succeeds."""
    for _attempt in (1, 2):
        try:
            html = fetch(shop_page.url)
        except (FetchFailed, TimeoutError, OSError):
            continue
        amount = read_shop_price(shop_page.shop, html)
        if amount is None:
            continue
        outcome = record_price(shop_page, amount, observed_date)
        if outcome is RecordOutcome.STORED:
            return PageResult.STORED
        return PageResult.UNCHANGED
    return PageResult.GAP


def record_shop_pages(
    pages: QuerySet[ShopPage],
    fetch: Callable[[str], str],
    observed_date: date,
    write: Callable[[str], None],
) -> None:
    """Record each page and print stored, unchanged, or gap."""
    for shop_page in pages:
        result = record_one_page(shop_page, fetch, observed_date)
        write(f"{result.value} {shop_page.get_shop_display()} {shop_page.url}")
