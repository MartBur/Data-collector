from typing import TypedDict

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from prices.list_prices import ListPrice, list_prices
from prices.models import Product
from prices.recording_clock import latest_recording_finished_at


class SignInView(LoginView):
    template_name: str = "registration/login.html"
    redirect_authenticated_user: bool = True

    def get_redirect_url(self, request: HttpRequest | None = None) -> str:
        redirect_to = super().get_redirect_url(request)
        current = self.request if request is None else request
        if redirect_to == current.path:
            return ""
        return redirect_to


class HomePriceRow(TypedDict):
    product: Product
    price: ListPrice


class HomePage(TypedDict):
    all_products: list[HomePriceRow]
    favourites: list[HomePriceRow]
    historical_lowest_today: list[HomePriceRow]
    lowest_price_today: list[HomePriceRow]
    last_price_update: str


def _home_product_key(product: Product) -> tuple[str, int]:
    """Sort a tracked product by casefolded name, then pk."""
    return (product.name.casefold(), int(product.pk))


def _products_for_home() -> list[Product]:
    """Return every tracked product for the signed-in home list."""
    products = list(Product.objects.all())
    products.sort(key=_home_product_key)
    return products


def _home_rows(
    products: list[Product],
    prices: dict[int, ListPrice],
) -> list[HomePriceRow]:
    """Return casefold-then-pk rows paired with each product's list price."""
    ordered = list(products)
    ordered.sort(key=_home_product_key)
    return [
        {"product": product, "price": prices[product.pk]}
        for product in ordered
    ]


def _last_price_update_line() -> str:
    """Return the active-timezone finish line, or none when no run is stored."""
    finished_at = latest_recording_finished_at()
    if finished_at is None:
        return "Last price update: none - Warsaw time"
    finished_local = timezone.localtime(finished_at)
    recorded = finished_local.strftime("%d.%m.%Y %H:%M")
    return f"Last price update: {recorded} - Warsaw time"


@never_cache
@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Show four price tables and the last recording time."""
    products = _products_for_home()
    prices = list_prices(products, timezone.localdate())
    historical_products = [
        product
        for product in products
        if prices[product.pk]["matches_lowest_stored"]
    ]
    favourites: list[HomePriceRow] = []
    context: HomePage = {
        "all_products": _home_rows(products, prices),
        "favourites": favourites,
        "historical_lowest_today": _home_rows(historical_products, prices),
        "lowest_price_today": _home_rows(products, prices),
        "last_price_update": _last_price_update_line(),
    }
    return render(request, "accounts/home.html", context)
