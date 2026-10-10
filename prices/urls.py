from django.urls import path

from prices.views import add_product, product_list

app_name = "prices"

urlpatterns = [
    path("add/", add_product, name="add_product"),
    path("", product_list, name="product_list"),
]
