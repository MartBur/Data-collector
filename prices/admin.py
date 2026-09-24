from django.contrib import admin

from prices.models import PriceObservation, Product, ShopPage


class ShopPageInline(admin.TabularInline):
    model: type[ShopPage] = ShopPage
    extra: int = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("name",)
    inlines: tuple[type[admin.TabularInline], ...] = (ShopPageInline,)
    search_fields: tuple[str, ...] = ("name",)


@admin.register(ShopPage)
class ShopPageAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = ("product", "shop", "url")
    list_filter: tuple[str, ...] = ("shop",)
    search_fields: tuple[str, ...] = ("url", "product__name")


@admin.register(PriceObservation)
class PriceObservationAdmin(admin.ModelAdmin):
    list_display: tuple[str, ...] = (
        "shop_page",
        "amount",
        "observed_date",
        "recorded_at",
    )
    list_filter: tuple[str, ...] = ("observed_date",)
    date_hierarchy: str = "observed_date"
