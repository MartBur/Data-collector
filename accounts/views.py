from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from prices.models import Product


class SignInView(LoginView):
    template_name: str = "registration/login.html"
    redirect_authenticated_user: bool = True

    def get_redirect_url(self, request: HttpRequest | None = None) -> str:
        redirect_to = super().get_redirect_url(request)
        current = self.request if request is None else request
        if redirect_to == current.path:
            return ""
        return redirect_to


def _home_product_key(product: Product) -> tuple[str, int]:
    """Sort a tracked product by casefolded name, then pk."""
    return (product.name.casefold(), int(product.pk))


def _products_for_home() -> list[Product]:
    """Return every tracked product for the signed-in home list."""
    products = list(Product.objects.all())
    products.sort(key=_home_product_key)
    return products


@never_cache
@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Show every tracked product by name, with no prices."""
    context: dict[str, list[Product]] = {"products": _products_for_home()}
    return render(request, "accounts/home.html", context)
