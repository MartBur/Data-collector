from django.urls import path

from prices.views import add_product, change_product, product_list

app_name = "prices"

urlpatterns = [
    path("add/", add_product, name="add_product"),
    path("<int:pk>/change/", change_product, name="change_product"),
    path("", product_list, name="product_list"),
]
