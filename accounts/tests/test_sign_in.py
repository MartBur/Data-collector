from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase

INVALID_LOGIN = (
    "Please enter a correct username and password. Note that both "
    "fields may be case-sensitive."
)
PASSWORD = "correct-horse"


class SignInTests(TestCase):
    def _user(self, username: str, *, is_active: bool = True) -> AbstractUser:
        user = get_user_model().objects.create_user(
            username=username,
            password=PASSWORD,
        )
        if not is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
        return user

    def test_anonymous_root_redirects_to_sign_in(self) -> None:
        response = self.client.get("/")
        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_sign_in_form_renders(self) -> None:
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

    def test_active_non_staff_user_signs_in_and_sees_username(self) -> None:
        user = self._user("ada")
        self.assertFalse(user.is_staff)
        response = self.client.post(
            "/accounts/login/",
            {"username": "ada", "password": PASSWORD},
        )
        self.assertRedirects(response, "/")
        home = self.client.get("/")
        self.assertContains(home, "ada")

    def test_wrong_password_stays_anonymous(self) -> None:
        self._user("ada")
        response = self.client.post(
            "/accounts/login/",
            {"username": "ada", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, INVALID_LOGIN)

    def test_unknown_username_stays_anonymous(self) -> None:
        response = self.client.post(
            "/accounts/login/",
            {"username": "missing", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, INVALID_LOGIN)

    def test_inactive_user_stays_anonymous_with_the_same_error(self) -> None:
        self._user("ada", is_active=False)
        response = self.client.post(
            "/accounts/login/",
            {"username": "ada", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, INVALID_LOGIN)
        self.assertNotContains(response, "This account is inactive.")

    def test_username_case_must_match(self) -> None:
        self._user("ada")
        response = self.client.post(
            "/accounts/login/",
            {"username": "Ada", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_safe_next_is_followed(self) -> None:
        self._user("ada")
        response = self.client.post(
            "/accounts/login/",
            {"username": "ada", "password": PASSWORD, "next": "/admin/login/"},
        )
        self.assertRedirects(
            response,
            "/admin/login/",
            fetch_redirect_response=False,
        )

    def test_off_host_next_is_ignored(self) -> None:
        self._user("ada")
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "ada",
                "password": PASSWORD,
                "next": "https://example.com/",
            },
        )
        self.assertRedirects(response, "/")

    def test_admin_login_still_renders(self) -> None:
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
