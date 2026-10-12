from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models


class Shop(models.TextChoices):
    ROSSMANN = "rossmann", "Rossmann"
    DOZ = "doz", "DOZ"
    SUPERPHARM = "superpharm", "Super-Pharm"
    GEMINI = "gemini", "Gemini"


SHOP_HOSTS: dict[str, str] = {
    Shop.ROSSMANN: "rossmann.pl",
    Shop.DOZ: "doz.pl",
    Shop.SUPERPHARM: "superpharm.pl",
    Shop.GEMINI: "gemini.pl",
}


def canonical_host(url: str) -> str | None:
    """Return the URL hostname without a leading www., or None if missing."""
    hostname = urlparse(url).hostname
    if hostname is None:
        return None
    hostname = hostname.casefold()
    if hostname.startswith("www."):
        return hostname.removeprefix("www.")
    return hostname


def shop_url_host_is_valid(shop: str, url: str) -> bool:
    """Return True when the URL host belongs to the given shop."""
    expected = SHOP_HOSTS.get(shop)
    if expected is None:
        return False
    return canonical_host(url) == expected


def shop_page_key(shop: str, url: str) -> tuple[str, str, str, str, str] | None:
    """Return a shop page's identity, ignoring www, one trailing slash, and the fragment."""
    parsed = urlparse(url)
    host = canonical_host(url)
    if host is None or parsed.scheme == "":
        return None
    path = "/" if parsed.path == "" else parsed.path
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return (shop, parsed.scheme.casefold(), host, path, parsed.query)


class Product(models.Model):
    name: models.CharField = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        if self.name == "":
            raise ValidationError({"name": "Name cannot be blank."})
        folded = self.name.casefold()
        others = Product.objects.all()
        if self.pk is not None:
            others = others.exclude(pk=self.pk)
        for other in others:
            if other.name.strip().casefold() == folded:
                raise ValidationError(
                    {"name": "A product with this name already exists."}
                )


class ShopPage(models.Model):
    product: models.ForeignKey = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="shop_pages",
    )
    shop: models.CharField = models.CharField(max_length=16, choices=Shop.choices)
    url: models.URLField = models.URLField(max_length=2048)

    class Meta:
        constraints: list[models.UniqueConstraint] = [
            models.UniqueConstraint(
                fields=("product", "shop"),
                name="prices_shoppage_unique_product_shop",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} @ {self.get_shop_display()}"

    def clean(self) -> None:
        super().clean()
        if self.shop and self.url and not shop_url_host_is_valid(self.shop, self.url):
            expected = SHOP_HOSTS.get(self.shop, "")
            raise ValidationError(
                {
                    "url": (
                        f"URL host must be {expected} (with or without www) "
                        "for the chosen shop."
                    )
                }
            )
        if self.product_id is not None and self.shop:
            clash = ShopPage.objects.filter(
                product_id=self.product_id,
                shop=self.shop,
            )
            if self.pk is not None:
                clash = clash.exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError(
                    {"shop": "This product already has a page for that shop."}
                )
        if self.shop and self.url:
            key = shop_page_key(self.shop, self.url)
            if key is not None:
                others = ShopPage.objects.filter(shop=self.shop)
                if self.pk is not None:
                    others = others.exclude(pk=self.pk)
                for other in others:
                    if shop_page_key(other.shop, other.url) == key:
                        raise ValidationError(
                            {
                                "url": (
                                    "Another product already has this shop page."
                                )
                            }
                        )


class PriceObservation(models.Model):
    shop_page: models.ForeignKey = models.ForeignKey(
        ShopPage,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    amount: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)
    observed_date: models.DateField = models.DateField()
    recorded_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: list[models.CheckConstraint] = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="prices_priceobservation_amount_positive",
            )
        ]

    def __str__(self) -> str:
        return f"{self.shop_page} {self.amount} on {self.observed_date}"


class PriceRecordingRun(models.Model):
    finished_at: models.DateTimeField = models.DateTimeField()

    def __str__(self) -> str:
        return f"finished at {self.finished_at}"
