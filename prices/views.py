from typing import TypedDict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from prices.forms import AddProductForm
from prices.models import Product, ShopPage

_MAX_ADDED_PK: int = 2**63 - 1


class AddProductPage(TypedDict):
    form: AddProductForm
    added: Product | None
    added_pages: list[ShopPage]


class ProductListPage(TypedDict):
    products: list[Product]


def _product_for_added(raw_pk: str | None) -> Product | None:
    """Return the confirmed product, or None for a missing or unknown id."""
    if raw_pk is None or not raw_pk.isascii() or not raw_pk.isdigit():
        return None
    try:
        pk = int(raw_pk)
    except ValueError:
        return None
    if pk > _MAX_ADDED_PK:
        return None
    return Product.objects.filter(pk=pk).first()


def _added_pages(product: Product | None) -> list[ShopPage]:
    """Return one product's shop pages in insert order."""
    if product is None:
        return []
    return list(product.shop_pages.order_by("pk"))


@login_required
def add_product(request: HttpRequest) -> HttpResponse:
    """Show the add form, or save a product and redirect to its confirmation."""
    if not request.user.is_staff:
        raise PermissionDenied
    if request.method == "POST":
        form = AddProductForm(request.POST)
        if form.is_valid():
            try:
                product = form.save()
            except ValidationError:
                pass
            else:
                location = reverse("prices:add_product")
                return redirect(f"{location}?added={product.pk}")
        added: Product | None = None
    else:
        form = AddProductForm()
        added = _product_for_added(request.GET.get("added"))
    context: AddProductPage = {
        "form": form,
        "added": added,
        "added_pages": _added_pages(added),
    }
    return render(request, "prices/add_product.html", context)


def _product_list_key(product: Product) -> tuple[str, int]:
    """Sort a tracked product by stripped casefolded name, then pk."""
    return (product.name.strip().casefold(), int(product.pk))


def _products_for_list() -> list[Product]:
    """Return every product, shops in pk order, sorted for the staff list."""
    products = list(
        Product.objects.prefetch_related(
            Prefetch(
                "shop_pages",
                queryset=ShopPage.objects.order_by("pk"),
            )
        )
    )
    products.sort(key=_product_list_key)
    return products


@login_required
def product_list(request: HttpRequest) -> HttpResponse:
    """Show every tracked product to staff."""
    if not request.user.is_staff:
        raise PermissionDenied
    context: ProductListPage = {"products": _products_for_list()}
    return render(request, "prices/product_list.html", context)
