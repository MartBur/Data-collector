from django.urls import path

from prices.views import (
    add_product,
    change_product,
    price_updates,
    product_card,
    product_list,
    remove_product,
    remove_shop_page,
    toggle_favourite,
)

app_name = "prices"

urlpatterns = [
    path("add/", add_product, name="add_product"),
    path("price-updates/", price_updates, name="price_updates"),
    path(
        "<int:pk>/shop-pages/<int:page_pk>/remove/",
        remove_shop_page,
        name="remove_shop_page",
    ),
    path("<int:pk>/change/", change_product, name="change_product"),
    path("<int:pk>/remove/", remove_product, name="remove_product"),
    path("<int:pk>/favourite/", toggle_favourite, name="toggle_favourite"),
    path("<int:pk>/", product_card, name="product_card"),
    path("", product_list, name="product_list"),
]
