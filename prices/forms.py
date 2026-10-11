from typing import Literal, NoReturn

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import QueryDict

from prices.models import Product, Shop, ShopPage, shop_url_host_is_valid

RowKind = Literal["empty", "half", "filled"]

_AT_LEAST_ONE_PAGE: str = "Enter at least one shop page."
_THIRD_ROW_PARTIAL: str = (
    "Enter both a shop and a URL for the third page, or leave both empty."
)
_THIRD_ROW_WITHOUT_SECOND: str = "Enter the second shop page before the third."
_ROW_PARTIAL: tuple[str, str, str] = (
    "Enter both a shop and a URL for the first page, or leave both empty.",
    "Enter both a shop and a URL for the second page, or leave both empty.",
    _THIRD_ROW_PARTIAL,
)
_PRIOR_ROW_REQUIRED: tuple[str, str] = (
    "Enter the first shop page before the second.",
    _THIRD_ROW_WITHOUT_SECOND,
)
_DISTINCT_SHOPS: str = "Each shop page must use a different shop."
_WRONG_HOST: str = "Enter a URL on the chosen shop's website."
_PAGE_ROWS: tuple[tuple[str, str], ...] = (
    ("shop_1", "url_1"),
    ("shop_2", "url_2"),
    ("shop_3", "url_3"),
)


def shop_field_choices() -> list[tuple[str, str]]:
    """Return a blank option followed by ``Shop.choices``.

    The blank option is not a shop. It lets the browser submit an empty
    row. Only ``Shop.choices`` values pass validation.
    """
    choices: list[tuple[str, str]] = [("", "---------")]
    for value, label in Shop.choices:
        choices.append((str(value), str(label)))
    return choices


class AddProductForm(forms.Form):
    """Collect a product name and one, two, or three shop pages."""

    name: forms.CharField = forms.CharField(
        label="Name",
        max_length=255,
        required=True,
        strip=False,
    )
    shop_1: forms.ChoiceField = forms.ChoiceField(
        label="Shop 1",
        choices=shop_field_choices(),
        required=False,
    )
    url_1: forms.URLField = forms.URLField(
        label="URL 1",
        max_length=2048,
        required=False,
    )
    shop_2: forms.ChoiceField = forms.ChoiceField(
        label="Shop 2",
        choices=shop_field_choices(),
        required=False,
    )
    url_2: forms.URLField = forms.URLField(
        label="URL 2",
        max_length=2048,
        required=False,
    )
    shop_3: forms.ChoiceField = forms.ChoiceField(
        label="Shop 3",
        choices=shop_field_choices(),
        required=False,
    )
    url_3: forms.URLField = forms.URLField(
        label="URL 3",
        max_length=2048,
        required=False,
    )

    def clean(self) -> dict[str, str]:
        """Reject an empty, half-filled, or gapped set, a repeated shop, or a bad host."""
        self._reject_row_shape()
        self._reject_duplicate_shops_and_bad_hosts()
        return self._string_cleaned_data()

    def save(self) -> Product:
        """Store the product and its shop pages in one transaction.

        On a model ``ValidationError``, attach the messages to ``name`` or that
        row's URL and re-raise so the transaction rolls back.
        """
        rows = self._filled_row_values()
        with transaction.atomic():
            product = Product(name=self._required_cleaned("name"))
            self._store_product(product)
            for shop, url, _shop_field, url_field in rows:
                page = ShopPage(product=product, shop=shop, url=url)
                self._store_page(page, url_field)
        return product

    def _posted(self, field_name: str) -> str:
        """Return the stripped posted value, or an empty string when missing."""
        value = self.data.get(field_name)
        if not isinstance(value, str):
            return ""
        return value.strip()

    def _row_kind(self, shop_field: str, url_field: str) -> RowKind:
        """Classify a shop row as empty, half-filled, or filled."""
        shop_empty = self._posted(shop_field) == ""
        url_empty = self._posted(url_field) == ""
        if shop_empty and url_empty:
            return "empty"
        if shop_empty or url_empty:
            return "half"
        return "filled"

    def _cleaned(self, field_name: str) -> str | None:
        """Return a cleaned string, or None when the field did not clean."""
        value = self.cleaned_data.get(field_name)
        if isinstance(value, str):
            return value
        return None

    def _required_cleaned(self, field_name: str) -> str:
        """Return a cleaned string, or attach a required error and raise."""
        value = self._cleaned(field_name)
        if isinstance(value, str):
            return value
        self._reraise_on_field(
            ValidationError("This field is required."),
            field_name,
        )

    def _filled_row_values(self) -> list[tuple[str, str, str, str]]:
        """Return filled rows as (shop, url, shop field, url field)."""
        rows: list[tuple[str, str, str, str]] = []
        for shop_field, url_field in _PAGE_ROWS:
            if self._row_kind(shop_field, url_field) != "filled":
                continue
            shop = self._cleaned(shop_field)
            url = self._cleaned(url_field)
            if shop is None or url is None or shop == "" or url == "":
                continue
            rows.append((shop, url, shop_field, url_field))
        return rows

    def _reject_row_shape(self) -> None:
        """Reject zero pages, a half-filled row, or a filled row after an empty one."""
        kinds: list[RowKind] = [
            self._row_kind(shop_field, url_field)
            for shop_field, url_field in _PAGE_ROWS
        ]
        filled_count: int = 0
        for index, (shop_field, url_field) in enumerate(_PAGE_ROWS):
            kind: RowKind = kinds[index]
            if kind == "filled":
                filled_count += 1
                if index > 0 and kinds[index - 1] != "filled":
                    self.add_error(url_field, _PRIOR_ROW_REQUIRED[index - 1])
            elif kind == "half":
                self._reject_half_row(shop_field, url_field, _ROW_PARTIAL[index])
        if filled_count == 0:
            self.add_error("shop_1", _AT_LEAST_ONE_PAGE)

    def _reject_half_row(self, shop_field: str, url_field: str, message: str) -> None:
        """Attach a half-filled-row message to the empty shop or URL."""
        if self._posted(shop_field) == "":
            self.add_error(shop_field, message)
        else:
            self.add_error(url_field, message)

    def _reject_duplicate_shops_and_bad_hosts(self) -> None:
        """Reject repeated shops and URLs whose host is not that shop."""
        seen: set[str] = set()
        for shop, url, shop_field, url_field in self._filled_row_values():
            if shop in seen:
                self.add_error(shop_field, _DISTINCT_SHOPS)
            else:
                seen.add(shop)
            if not shop_url_host_is_valid(shop, url):
                self.add_error(url_field, _WRONG_HOST)

    def _string_cleaned_data(self) -> dict[str, str]:
        """Return the cleaned values that are strings."""
        cleaned: dict[str, str] = {}
        for key, value in self.cleaned_data.items():
            if isinstance(value, str):
                cleaned[key] = value
        return cleaned

    def _reraise_on_field(self, exc: ValidationError, field_name: str) -> NoReturn:
        """Attach a model error to one form field, then re-raise it."""
        messages: list[str] = [str(message) for message in exc.messages]
        self.add_error(field_name, ValidationError(messages))
        raise exc

    def _store_product(self, product: Product) -> None:
        """Validate and insert the product, or re-raise on ``name``."""
        try:
            product.full_clean()
        except ValidationError as exc:
            self._reraise_on_field(exc, "name")
        product.save()

    def _store_page(self, page: ShopPage, url_field: str) -> None:
        """Validate and insert one shop page, or re-raise on its URL."""
        try:
            page.full_clean()
        except ValidationError as exc:
            self._reraise_on_field(exc, url_field)
        page.save()


class ChangeProductForm(AddProductForm):
    """Edit one product's name and its one to three shop pages."""

    def __init__(self, product: Product, data: QueryDict | None = None) -> None:
        """Prefill rows from this product's shop pages in primary-key order."""
        self.product: Product = product
        super().__init__(data, initial=self._prefill())

    def pages_whose_prices_would_be_deleted(self) -> list[ShopPage]:
        """Return pages this save would delete that already have a price.

        Does not write. Call it only after the form has validated.
        """
        filled: set[str] = {
            shop for shop, _url, _shop_field, _url_field in self._filled_row_values()
        }
        losing: list[ShopPage] = []
        for page in self.product.shop_pages.order_by("pk"):
            if str(page.shop) in filled:
                continue
            if page.observations.exists():
                losing.append(page)
        return losing

    def save(self) -> Product:
        """Update the product and its shop pages in one transaction.

        A kept shop's URL is saved on the existing page before any delete.
        A model error attaches to ``name`` or that row's URL and rolls the
        transaction back.
        """
        self._refuse_if_unsavable()
        rows: list[tuple[str, str, str, str]] = self._filled_row_values()
        filled_shops: set[str] = {shop for shop, _url, _shop_field, _url_field in rows}
        try:
            with transaction.atomic():
                self.product.name = self._required_cleaned("name")
                self._store_product(self.product)
                existing: dict[str, ShopPage] = {}
                for page in self.product.shop_pages.order_by("pk"):
                    existing[str(page.shop)] = page
                for shop, url, _shop_field, url_field in rows:
                    page = existing.get(shop)
                    if page is None:
                        continue
                    page.url = url
                    self._store_page(page, url_field)
                self.product.shop_pages.exclude(shop__in=filled_shops).delete()
                for shop, url, _shop_field, url_field in rows:
                    if shop in existing:
                        continue
                    created = ShopPage(product=self.product, shop=shop, url=url)
                    self._store_page(created, url_field)
        except ValidationError:
            self.product.refresh_from_db()
            raise
        return self.product

    def _prefill(self) -> dict[str, str]:
        """Return the name and up to three shop rows in primary-key order."""
        initial: dict[str, str] = {"name": str(self.product.name)}
        for shop_field, url_field in _PAGE_ROWS:
            initial[shop_field] = ""
            initial[url_field] = ""
        pages = self.product.shop_pages.order_by("pk")
        for (shop_field, url_field), page in zip(_PAGE_ROWS, pages):
            initial[shop_field] = str(page.shop)
            initial[url_field] = str(page.url)
        return initial

    def _refuse_if_unsavable(self) -> None:
        """Raise before any write when the save would drop every page or a hidden one."""
        if self.product.shop_pages.count() > len(_PAGE_ROWS):
            self._raise_refused(
                "This product has more shops than this form can save.",
                None,
            )
        if not self._filled_row_values():
            self._raise_refused(_AT_LEAST_ONE_PAGE, "shop_1")

    def _raise_refused(self, message: str, field_name: str | None) -> NoReturn:
        """Attach ``message`` and raise so nothing is written."""
        error = ValidationError(message)
        self.add_error(field_name, error)
        raise error
