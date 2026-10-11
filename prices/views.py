from decimal import ROUND_CEILING, Decimal
from typing import TypedDict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from prices.card import CardFigures, card_figures
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


_CHART_WIDTH: int = 720
_CHART_HEIGHT: int = 220
_PLOT_LEFT: Decimal = Decimal("72")
_PLOT_RIGHT: Decimal = Decimal("500")
_PLOT_TOP: Decimal = Decimal("28")
_PLOT_BOTTOM: Decimal = Decimal("160")
_Y_ORIGIN_GAP: Decimal = Decimal("50")
_MAX_Y_TICK_INTERVALS: int = 20
_MIN_Y_TICK_STEP: Decimal = Decimal("1")
_NICE_TICK_MULTIPLIERS: tuple[Decimal, ...] = (
    Decimal("1"),
    Decimal("2"),
    Decimal("5"),
    Decimal("10"),
)
_LEGEND_MARK_X1: Decimal = Decimal("516")
_LEGEND_MARK_X2: Decimal = Decimal("544")
_LEGEND_TEXT_X: Decimal = Decimal("552")
_LEGEND_STEP: Decimal = Decimal("22")
_SERIES_STROKES: tuple[str, ...] = ("#1f4e79", "#b85c38", "#2f6b4f", "#6b3fa0")
_POINT_RADIUS: str = "4"


class ChartPoint(TypedDict):
    x: str
    y: str
    observed_on: str
    amount: str


class ChartSeries(TypedDict):
    label: str
    stroke: str
    radius: str
    draw_line: bool
    line_points: str
    points: list[ChartPoint]
    legend_y: str


class ChartYTick(TypedDict):
    y: str
    label: str


class ChartPlot(TypedDict):
    width: int
    height: int
    axis_x: str
    axis_x1: str
    axis_x2: str
    axis_y: str
    y_top: str
    y_tick_x: str
    y_label_x: str
    tick_y: str
    label_y: str
    first_label: str
    first_x: str
    today_label: str
    today_x: str
    legend_mark_x1: str
    legend_mark_x2: str
    legend_text_x: str
    ticks: list[str]
    y_ticks: list[ChartYTick]
    series: list[ChartSeries]


class ProductCardPage(TypedDict):
    product: Product
    figures: CardFigures
    chart: ChartPlot


def _two_decimals(value: Decimal) -> str:
    """Format one amount or coordinate with two decimal places."""
    return f"{value:.2f}"


def _slot_x(index: int, count: int) -> Decimal:
    """Return the x position of one date slot, evenly spaced across the plot."""
    if count <= 1:
        return _PLOT_LEFT
    span = _PLOT_RIGHT - _PLOT_LEFT
    return _PLOT_LEFT + span * Decimal(index) / Decimal(count - 1)


def _window_bounds(figures: CardFigures) -> tuple[Decimal, Decimal] | None:
    """Return the lowest and highest priced amount inside the chart window."""
    priced: list[Decimal] = [
        amount
        for series in figures["series"]
        for amount in series["amounts"]
        if amount is not None
    ]
    if not priced:
        return None
    return min(priced), max(priced)


def _y_for_amount(amount: Decimal, low: Decimal, high: Decimal) -> Decimal:
    """Map a price onto the plot between the axis floor and the axis top."""
    if low == high:
        return (_PLOT_TOP + _PLOT_BOTTOM) / Decimal(2)
    span = _PLOT_BOTTOM - _PLOT_TOP
    return _PLOT_BOTTOM - (amount - low) * span / (high - low)


def _axis_floor(lowest: Decimal) -> Decimal:
    """Return the Y-axis start: 50 below the lowest price, and never below zero."""
    lowered = lowest - _Y_ORIGIN_GAP
    if lowered < 0:
        return Decimal("0")
    return lowered


def _tick_step(floor: Decimal, highest: Decimal) -> Decimal:
    """Return a nice tick step that keeps the chart to at most 20 intervals."""
    target = (highest - floor) / Decimal(_MAX_Y_TICK_INTERVALS)
    if target <= _MIN_Y_TICK_STEP:
        return _MIN_Y_TICK_STEP
    magnitude = Decimal("1").scaleb(target.adjusted())
    for multiplier in _NICE_TICK_MULTIPLIERS:
        candidate = magnitude * multiplier
        if candidate >= target:
            return candidate
    return magnitude * Decimal("10")


def _axis_ceiling(floor: Decimal, highest: Decimal, step: Decimal) -> Decimal:
    """Return the first tick at or above the highest price."""
    if highest <= floor:
        return floor + step
    steps = ((highest - floor) / step).to_integral_value(ROUND_CEILING)
    return floor + steps * step


def _price_ticks(
    floor: Decimal,
    ceiling: Decimal,
    step: Decimal,
) -> list[Decimal]:
    """Return Y-axis labels from the floor to the ceiling at the chosen step."""
    ticks: list[Decimal] = []
    value = floor
    while value <= ceiling:
        ticks.append(value)
        value += step
    return ticks


def _series_stroke(index: int) -> str:
    """Return one shop's color. Every shop uses the same line and point."""
    return _SERIES_STROKES[index % len(_SERIES_STROKES)]


def _chart_plot(figures: CardFigures) -> ChartPlot:
    """Build even date slots and a mark for each shop day that has a price."""
    dates = figures["dates"]
    count = len(dates)
    bounds = _window_bounds(figures)
    scale: tuple[Decimal, Decimal] | None = None
    y_ticks: list[ChartYTick] = []
    if bounds is not None:
        lowest, highest = bounds
        floor = _axis_floor(lowest)
        step = _tick_step(floor, highest)
        ceiling = _axis_ceiling(floor, highest, step)
        scale = (floor, ceiling)
        y_ticks = [
            {
                "y": _two_decimals(_y_for_amount(price, floor, ceiling)),
                "label": _two_decimals(price),
            }
            for price in _price_ticks(floor, ceiling, step)
        ]
    ticks = [_two_decimals(_slot_x(index, count)) for index in range(count)]
    plotted: list[ChartSeries] = []
    for index, shop_series in enumerate(figures["series"]):
        points: list[ChartPoint] = []
        for slot, (day, amount) in enumerate(
            zip(dates, shop_series["amounts"], strict=True)
        ):
            if amount is None or scale is None:
                continue
            low, high = scale
            points.append(
                {
                    "x": _two_decimals(_slot_x(slot, count)),
                    "y": _two_decimals(_y_for_amount(amount, low, high)),
                    "observed_on": day.isoformat(),
                    "amount": _two_decimals(amount),
                }
            )
        if not points:
            continue
        stroke = _series_stroke(index)
        draw_line = len(points) >= 2
        line_points = (
            " ".join(f"{point['x']},{point['y']}" for point in points)
            if draw_line
            else ""
        )
        plotted.append(
            {
                "label": shop_series["label"],
                "stroke": stroke,
                "radius": _POINT_RADIUS,
                "draw_line": draw_line,
                "line_points": line_points,
                "points": points,
                "legend_y": _two_decimals(
                    _PLOT_TOP + Decimal(len(plotted)) * _LEGEND_STEP
                ),
            }
        )
    if ticks:
        first_x = ticks[0]
        today_x = ticks[-1]
    else:
        first_x = _two_decimals(_PLOT_LEFT)
        today_x = _two_decimals(_PLOT_RIGHT)
    return {
        "width": _CHART_WIDTH,
        "height": _CHART_HEIGHT,
        "axis_x": _two_decimals(_PLOT_LEFT),
        "axis_x1": first_x,
        "axis_x2": today_x,
        "axis_y": _two_decimals(_PLOT_BOTTOM),
        "y_top": y_ticks[-1]["y"] if y_ticks else _two_decimals(_PLOT_TOP),
        "y_tick_x": _two_decimals(_PLOT_LEFT - Decimal("6")),
        "y_label_x": _two_decimals(_PLOT_LEFT - Decimal("10")),
        "tick_y": _two_decimals(_PLOT_BOTTOM + Decimal("6")),
        "y_ticks": y_ticks,
        "label_y": _two_decimals(_PLOT_BOTTOM + Decimal("22")),
        "first_label": dates[0].isoformat() if dates else "",
        "first_x": first_x,
        "today_label": dates[-1].isoformat() if dates else "",
        "today_x": today_x,
        "legend_mark_x1": _two_decimals(_LEGEND_MARK_X1),
        "legend_mark_x2": _two_decimals(_LEGEND_MARK_X2),
        "legend_text_x": _two_decimals(_LEGEND_TEXT_X),
        "ticks": ticks,
        "series": plotted,
    }


@login_required
def product_card(request: HttpRequest, pk: int) -> HttpResponse:
    """Show one tracked product's shop prices and 30-day chart."""
    product = get_object_or_404(Product, pk=pk)
    figures = card_figures(product, timezone.localdate())
    context: ProductCardPage = {
        "product": product,
        "figures": figures,
        "chart": _chart_plot(figures),
    }
    return render(request, "prices/product_card.html", context)
