from django.urls import path

from prices.views import add_product

app_name = "prices"

urlpatterns = [
    path("add/", add_product, name="add_product"),
]
