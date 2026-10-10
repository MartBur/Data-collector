from typing import Literal, NoReturn

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from prices.models import Product, Shop, ShopPage, shop_url_host_is_valid

RowKind = Literal["empty", "half", "filled"]

_THIRD_ROW_PARTIAL: str = (
    "Enter both a shop and a URL for the third page, or leave both empty."
)
_THIRD_ROW_WITHOUT_SECOND: str = "Enter the second shop page before the third."
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
    third row. Only ``Shop.choices`` values pass validation.
    """
    choices: list[tuple[str, str]] = [("", "---------")]
    for value, label in Shop.choices:
        choices.append((str(value), str(label)))
    return choices


class AddProductForm(forms.Form):
    """Collect a product name and two or three shop pages."""

    name: forms.CharField = forms.CharField(
        label="Name",
        max_length=255,
        required=True,
        strip=False,
    )
    shop_1: forms.ChoiceField = forms.ChoiceField(
        label="Shop 1",
        choices=shop_field_choices(),
        required=True,
    )
    url_1: forms.URLField = forms.URLField(
        label="URL 1",
        max_length=2048,
        required=True,
    )
    shop_2: forms.ChoiceField = forms.ChoiceField(
        label="Shop 2",
        choices=shop_field_choices(),
        required=True,
    )
    url_2: forms.URLField = forms.URLField(
        label="URL 2",
        max_length=2048,
        required=True,
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
        """Reject an incomplete set, a repeated shop, or a URL on the wrong host."""
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
        """Reject a half-filled third row, or a third row without the second."""
        third = self._row_kind("shop_3", "url_3")
        second = self._row_kind("shop_2", "url_2")
        if third == "half":
            if self._posted("shop_3") == "":
                self.add_error("shop_3", _THIRD_ROW_PARTIAL)
            else:
                self.add_error("url_3", _THIRD_ROW_PARTIAL)
        if third == "filled" and second != "filled":
            self.add_error("url_3", _THIRD_ROW_WITHOUT_SECOND)

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
