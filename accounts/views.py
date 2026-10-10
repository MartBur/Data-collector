from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache


class SignInView(LoginView):
    template_name: str = "registration/login.html"
    redirect_authenticated_user: bool = True

    def get_redirect_url(self, request: HttpRequest | None = None) -> str:
        redirect_to = super().get_redirect_url(request)
        current = self.request if request is None else request
        if redirect_to == current.path:
            return ""
        return redirect_to


@never_cache
@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/home.html")
