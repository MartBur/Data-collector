from django.urls import path

from accounts.views import SignInView

app_name = "accounts"

urlpatterns = [
    path("login/", SignInView.as_view(), name="login"),
]
