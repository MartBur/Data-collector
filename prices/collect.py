import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from email.message import Message
from enum import Enum
from http.client import HTTPResponse
from urllib.parse import urlparse

from django.db.models import QuerySet

from prices.models import ShopPage, shop_url_host_is_valid
from prices.readers import read_shop_price
from prices.recording import RecordOutcome, record_price

FETCH_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 2_000_000
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


def _shop_fetch_url_is_allowed(shop: str, url: str) -> bool:
    """Return True when the URL is HTTPS on the expected shop host."""
    return urlparse(url).scheme == "https" and shop_url_host_is_valid(shop, url)


class _SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, shop: str) -> None:
        super().__init__()
        self.shop: str = shop

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: HTTPResponse,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Reject a redirect that leaves HTTPS on the expected shop host."""
        if not _shop_fetch_url_is_allowed(self.shop, newurl):
            raise FetchFailed(f"Redirect left the shop host: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_limited(response: HTTPResponse, limit: int) -> bytes:
    """Read at most `limit` bytes. Raise FetchFailed when the page is larger."""
    body = response.read(limit + 1)
    if len(body) > limit:
        raise FetchFailed(f"Response exceeds {limit} bytes.")
    return body


def fetch_html(url: str, shop: str) -> str:
    """Download one HTTPS page on the expected shop host."""
    if not _shop_fetch_url_is_allowed(shop, url):
        raise FetchFailed(f"URL is not an HTTPS page for {shop}: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": FETCH_USER_AGENT})
    opener = urllib.request.build_opener(_SameHostRedirectHandler(shop))
    try:
        with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            body = _read_limited(response, MAX_RESPONSE_BYTES)
    except (TimeoutError, urllib.error.URLError, FetchFailed) as exc:
        raise FetchFailed(str(exc)) from exc
    if not _shop_fetch_url_is_allowed(shop, final_url):
        raise FetchFailed(f"Response left the shop host: {final_url}")
    return body.decode("utf-8", errors="replace")


def record_one_page(
    shop_page: ShopPage,
    fetch: Callable[[str, str], str],
    observed_date: date,
) -> PageResult:
    """Fetch a page, retry once, and store a price only when a read succeeds."""
    for _attempt in (1, 2):
        try:
            html = fetch(shop_page.url, shop_page.shop)
        except (FetchFailed, TimeoutError, OSError):
            continue
        try:
            amount = read_shop_price(shop_page.shop, html)
            if amount is None:
                continue
            outcome = record_price(shop_page, amount, observed_date)
        except (ValueError, ArithmeticError):
            continue
        if outcome is RecordOutcome.STORED:
            return PageResult.STORED
        return PageResult.UNCHANGED
    return PageResult.GAP


def record_shop_pages(
    pages: QuerySet[ShopPage],
    fetch: Callable[[str, str], str],
    observed_date: date,
    write: Callable[[str], None],
) -> None:
    """Record each page and print stored, unchanged, or gap."""
    for shop_page in pages:
        result = record_one_page(shop_page, fetch, observed_date)
        write(f"{result.value} {shop_page.get_shop_display()} {shop_page.url}")
