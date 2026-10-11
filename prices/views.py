from typing import TypedDict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from prices.forms import AddProductForm, ChangeProductForm
from prices.models import PriceObservation, Product, ShopPage

_MAX_ADDED_PK: int = 2**63 - 1


class AddProductPage(TypedDict):
    form: AddProductForm
    added: Product | None
    added_pages: list[ShopPage]


class ProductListPage(TypedDict):
    products: list[Product]
    kept_notice: bool
    canceled_notice: bool


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


def _list_shows_kept_notice(raw_pk: str | None) -> bool:
    """Return True when kept identifies a product that is still stored."""
    return _product_for_added(raw_pk) is not None


def _list_shows_canceled_notice(raw_flag: str | None) -> bool:
    """Return True when the list was opened by canceling a confirm step."""
    return isinstance(raw_flag, str) and raw_flag.strip() != ""


@login_required
def product_list(request: HttpRequest) -> HttpResponse:
    """Show every tracked product to staff.

    A kept id that matches a stored product adds the last-page notice.
    Canceling a confirm step adds the canceled notice.
    """
    if not request.user.is_staff:
        raise PermissionDenied
    context: ProductListPage = {
        "products": _products_for_list(),
        "kept_notice": _list_shows_kept_notice(request.GET.get("kept")),
        "canceled_notice": _list_shows_canceled_notice(request.GET.get("canceled")),
    }
    return render(request, "prices/product_list.html", context)


_MAX_CHANGE_SHOPS: int = 3


class ChangeProductPage(TypedDict):
    product: Product
    form: ChangeProductForm | None
    confirm_pages: list[ShopPage]
    too_many_shops: bool


def _product_has_too_many_shop_pages(product: Product) -> bool:
    """Return True when the product has more shop pages than the change form can save."""
    return product.shop_pages.count() > _MAX_CHANGE_SHOPS


def _change_confirmed(request: HttpRequest) -> bool:
    """Return True when the post includes a non-empty confirm flag."""
    confirm = request.POST.get("confirm")
    if not isinstance(confirm, str):
        return False
    return confirm.strip() != ""


def _change_page(
    product: Product,
    form: ChangeProductForm | None,
    confirm_pages: list[ShopPage],
    too_many_shops: bool,
) -> ChangeProductPage:
    """Build the change-product template context."""
    return {
        "product": product,
        "form": form,
        "confirm_pages": confirm_pages,
        "too_many_shops": too_many_shops,
    }


@login_required
def change_product(request: HttpRequest, pk: int) -> HttpResponse:
    """Show the change form, or save a correction and return to the list.

    A save that would delete a recorded price renders a confirm step and
    writes nothing until the confirm flag is posted.
    """
    if not request.user.is_staff:
        raise PermissionDenied
    product = get_object_or_404(Product, pk=pk)
    if _product_has_too_many_shop_pages(product):
        return render(
            request,
            "prices/change_product.html",
            _change_page(product, None, [], True),
        )
    confirm_pages: list[ShopPage] = []
    if request.method == "POST":
        form = ChangeProductForm(product, request.POST)
        if form.is_valid():
            losing = form.pages_whose_prices_would_be_deleted()
            if losing and not _change_confirmed(request):
                confirm_pages = losing
            else:
                try:
                    form.save()
                except ValidationError:
                    pass
                else:
                    return redirect("prices:product_list")
    else:
        form = ChangeProductForm(product)
    return render(
        request,
        "prices/change_product.html",
        _change_page(product, form, confirm_pages, False),
    )


class RemoveConfirmPage(TypedDict):
    product: Product
    pages: list[ShopPage]
    action: str


def _pages_whose_prices_would_be_deleted(pages: list[ShopPage]) -> list[ShopPage]:
    """Return pages that have a recorded price, keeping the given order."""
    if not pages:
        return []
    priced_ids: set[int] = set(
        PriceObservation.objects.filter(
            shop_page_id__in=[page.pk for page in pages],
        ).values_list("shop_page_id", flat=True)
    )
    return [page for page in pages if page.pk in priced_ids]


def _render_remove_confirm(
    request: HttpRequest,
    product: Product,
    pages: list[ShopPage],
    action: str,
) -> HttpResponse:
    """Render the confirm step for a remove that would delete prices."""
    context: RemoveConfirmPage = {
        "product": product,
        "pages": pages,
        "action": action,
    }
    return render(request, "prices/remove_confirm.html", context)


def _kept_list_redirect(product: Product) -> HttpResponse:
    """Redirect to the list with the last-page notice for this product."""
    location = reverse("prices:product_list")
    return redirect(f"{location}?kept={product.pk}")


@login_required
@require_POST
def remove_shop_page(request: HttpRequest, pk: int, page_pk: int) -> HttpResponse:
    """Delete one shop page, or refuse when it is the product's last page.

    A page with recorded prices renders confirm and writes nothing until
    the confirm flag is posted. GET does not delete.
    """
    if not request.user.is_staff:
        raise PermissionDenied
    product = get_object_or_404(Product, pk=pk)
    page = get_object_or_404(ShopPage, pk=page_pk, product_id=product.pk)
    if product.shop_pages.count() <= 1:
        return _kept_list_redirect(product)
    priced = _pages_whose_prices_would_be_deleted([page])
    if priced and not _change_confirmed(request):
        action = reverse(
            "prices:remove_shop_page",
            kwargs={"pk": product.pk, "page_pk": page.pk},
        )
        return _render_remove_confirm(request, product, [page], action)
    page.delete()
    return redirect("prices:product_list")


@login_required
@require_POST
def remove_product(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a tracked product, after confirm when any page has a price.

    GET does not delete. Pages and their prices go with the product.
    """
    if not request.user.is_staff:
        raise PermissionDenied
    product = get_object_or_404(Product, pk=pk)
    pages = list(product.shop_pages.order_by("pk"))
    if _pages_whose_prices_would_be_deleted(pages) and not _change_confirmed(request):
        action = reverse("prices:remove_product", kwargs={"pk": product.pk})
        return _render_remove_confirm(request, product, pages, action)
    product.delete()
    return redirect("prices:product_list")
