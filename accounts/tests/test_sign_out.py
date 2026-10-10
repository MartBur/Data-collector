from django.contrib.auth import get_user_model
from django.test import TestCase

PASSWORD = "correct-horse"


class SignOutTests(TestCase):
    def setUp(self) -> None:
        get_user_model().objects.create_user(username="ada", password=PASSWORD)
        self.client.login(username="ada", password=PASSWORD)

    def test_post_logout_ends_the_session(self) -> None:
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, "/accounts/login/")
        home = self.client.get("/")
        self.assertRedirects(home, "/accounts/login/?next=/")

    def test_get_logout_does_not_end_the_session(self) -> None:
        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.status_code, 405)
        home = self.client.get("/")
        self.assertContains(home, "ada")

    def test_signed_in_user_opening_the_form_returns_home(self) -> None:
        response = self.client.get("/accounts/login/")
        self.assertRedirects(response, "/")

    def test_signed_in_login_next_pointing_at_login_returns_home(self) -> None:
        response = self.client.get(
            "/accounts/login/",
            {"next": "/accounts/login/"},
        )
        self.assertRedirects(response, "/")

    def test_signed_in_page_has_post_logout_form(self) -> None:
        response = self.client.get("/")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "/accounts/logout/")
