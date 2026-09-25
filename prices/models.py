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


class Product(models.Model):
    name: models.CharField = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


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
