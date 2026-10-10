from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


class SignInView(LoginView):
    template_name: str = "registration/login.html"
    redirect_authenticated_user: bool = False


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/home.html")
