# Account Sign-In Implementation Plan

## Overview

An existing account can sign in with the same username and password Django admin already uses, see that username on a small signed-in page, and sign out. This is roadmap slice S-01 (FR-001). Later slices assume this session; the favorites page and the tracked list stay in their own slices.

## Current State Analysis

Django auth, sessions, and the admin login are already installed. The product has no sign-in screen of its own.

- `DataCollector/settings.py` registers `django.contrib.auth` and `prices`, and the middleware includes sessions, CSRF, and `AuthenticationMiddleware`. `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`, and `AUTH_USER_MODEL` are unset, so Django's defaults apply. The default success redirect is `/accounts/profile/`, and that path is not registered.
- `DataCollector/urls.py` exposes only `admin/`. The Render health check is `GET /admin/login/` (`render.yaml`).
- `TEMPLATES['DIRS']` is empty and `APP_DIRS` is true. No app templates exist. `prices/views.py` is an unused stub, and `prices` has no URL module.
- Accounts are created with `createsuperuser` (see `render.yaml`) or in Django admin. The stock `User` model is in use.
- Tests live under `prices/tests/` as `django.test.TestCase` methods annotated `-> None`. `uv run python manage.py check` and `uv run python manage.py makemigrations --check --dry-run` are clean today.

## Desired End State

A person with an existing active account opens the site, submits that account's username and password, and sees the username on a page at `/`. A wrong password, an unknown username, a case-different username, or an inactive account does not create a session. Signing out returns to the sign-in form. A non-staff account can complete this; list-owner powers are not checked here. `GET /admin/login/` still returns the admin sign-in page.

### Key Discoveries:

- Installed Django 6.1 `LogoutView` accepts only POST and OPTIONS (`.venv/Lib/site-packages/django/contrib/auth/views.py`). A GET to logout does not end the session.
- `ModelBackend.user_can_authenticate` rejects `is_active=False`, so `AuthenticationForm` reports the generic invalid-login error. The inactive-account sentence is not what the user sees.
- `AuthenticationForm` looks up the username with a case-sensitive natural key. The invalid-login text is `Please enter a correct username and password. Note that both fields may be case-sensitive.`
- A safe `next` value is honored. An off-host `next` is discarded (`RedirectURLMixin` in the same views module).
- App placement follows `prices`: a sibling of `DataCollector/`, registered in `INSTALLED_APPS`, with typed app config and tests (`prices/apps.py`, `prices/tests/test_models.py`).

## What We're NOT Doing

- Public registration, password reset, password change, and email as the sign-in identifier
- A custom user model or `AUTH_USER_MODEL`
- Favorites, product cards, charts, shop links, and tracked-list editing
- Replacing, restyling, or removing the admin login
- Changes to `render.yaml`, the health check, or `createsuperuser`
- Guest browsing, list-owner permission checks, sign-in rate limits, and a remember-me control beyond Django's default session
- Including `django.contrib.auth.urls` (that URL module also mounts password-reset routes)

## Implementation Approach

Add a thin `accounts` app that uses Django's `LoginView` and `LogoutView` and the stock user table. The sign-in form is `/accounts/login/`. Success and the site root land on a login-required page that shows the signed-in username. Settings point the login redirect at `/`, so the missing `/accounts/profile/` default is never used. Sign-out is a POST form on that page. Admin stays the place where accounts are created, and it keeps `/admin/`.

New functions, methods, and class attributes in `accounts/` are annotated. `DataCollector/settings.py` and `DataCollector/urls.py` stay unannotated. Views return `HttpResponse`.

## Critical Implementation Details

### User experience spec

The sign-out control is a form with `method="post"` and the CSRF token. A link that GETs `/accounts/logout/` gets HTTP 405 and the session stays in place.

### State sequencing

An inactive user with the correct password stays anonymous, and the page shows the same invalid-login sentence as a wrong password. Do not expect `This account is inactive.`

`LOGIN_REDIRECT_URL` is `/`. With `redirect_authenticated_user` enabled, pointing that setting at the login path raises `ValueError` because the redirect target would be the login page itself.

The app and admin share one session. Signing in on the app signs the same user into admin; signing out ends both.

## Phase 1: Sign in

### Overview

An existing active user can open the sign-in form, submit a username and password, and land on a page that shows that username. A failed attempt stays signed out. Opening `/` while signed out leads to the form.

### Changes Required:

#### 1. Accounts app

**File**: `accounts/` (`apps.py`, `views.py`, `urls.py`, `tests/`)

**Intent**: Give sign-in a home next to `prices`, without mixing it into the price models or into admin.

**Contract**: `AccountsConfig` matches `PricesConfig`: annotated `default_auto_field: str` and `name: str` of `"accounts"`. The app defines no models and ships no migrations. `AUTH_USER_MODEL` stays unset. `accounts/urls.py` sets `app_name = "accounts"` and names the login route `login`.

#### 2. Project wiring

**File**: `DataCollector/settings.py`, `DataCollector/urls.py`

**Intent**: Register the app and send a successful sign-in to `/` instead of the missing profile URL.

**Contract**: Add `"accounts"` to `INSTALLED_APPS`. Set `LOGIN_URL` to `"/accounts/login/"` and `LOGIN_REDIRECT_URL` to `"/"`. Mount `accounts.urls` at `accounts/` and the signed-in page at `/` with the name `home`. Leave the `admin/` route as it is. Do not annotate these two files.

#### 3. Sign-in screen

**File**: `accounts/views.py`, `accounts/templates/registration/login.html`, `accounts/templates/accounts/home.html`

**Intent**: Show a username/password form, and after success show who is signed in.

**Contract**: `SignInView` subclasses `LoginView`. Annotated attributes: `template_name: str = "registration/login.html"` and `redirect_authenticated_user: bool = False` (phase 2 flips the flag). The login template posts to the current URL, includes the CSRF token, renders the authentication form and its non-field errors, and includes a hidden `next` field. The home view is login-required, annotated to take `HttpRequest` and return `HttpResponse`, and renders `accounts/home.html`. That template includes the signed-in user's username in the body and has no sign-out control yet. Anonymous `GET /` redirects to `/accounts/login/?next=/`. A successful POST with no safe `next` redirects to `/`.

#### 4. Sign-in tests

**File**: `accounts/tests/test_sign_in.py`

**Intent**: Lock the session rules before any later slice depends on them.

**Contract**: `django.test.TestCase` methods return `None`. Build users with `get_user_model().objects.create_user` (active, non-staff). The module covers:

- Anonymous `GET /` redirects to `/accounts/login/?next=/`.
- `GET /accounts/login/` returns 200.
- POST of the right username and password for that non-staff user redirects to `/`, and the following `GET /` body contains the username.
- POST of a wrong password, and POST of an unknown username, each stay anonymous and contain `Please enter a correct username and password. Note that both fields may be case-sensitive.`
- POST of the correct password for `is_active=False` stays anonymous, contains that same sentence, and does not contain `This account is inactive.`
- POST of a username that differs only by case (stored `ada`, submitted `Ada`) stays anonymous.
- POST with `next=/admin/login/` redirects to `/admin/login/`. Assert the redirect target without requiring the admin page to render.
- POST with `next=https://example.com/` redirects to `/`.
- `GET /admin/login/` returns 200.

### Success Criteria:

#### Automated Verification:

- Sign-in tests pass: `uv run python manage.py test accounts.tests.test_sign_in`
- App adds no tables: `uv run python manage.py makemigrations --check --dry-run`
- Project check passes: `uv run python manage.py check`

#### Manual Verification:

- Browser sign-in with an existing username and password shows that username
- A wrong password stays on the form and shows the invalid-login error
- `/admin/login/` still shows the admin sign-in page

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Sign out

### Overview

The signed-in page can end the session and return to the form. Opening the form while already signed in returns to the signed-in page.

### Changes Required:

#### 1. Sign-out route

**File**: `accounts/views.py`, `accounts/urls.py`, `DataCollector/settings.py`

**Intent**: End the shared session and send the user back to the form, including when they open the form while already signed in.

**Contract**: Set `SignInView.redirect_authenticated_user` to `True`. Add a logout route named `logout` at `/accounts/logout/` using `LogoutView`. Set `LOGOUT_REDIRECT_URL` to `"/accounts/login/"`. Do not add a GET handler that logs the user out.

#### 2. Sign-out control

**File**: `accounts/templates/accounts/home.html`

**Intent**: Give the signed-in page a way to end the session from the browser.

**Contract**: The page contains a form with `method="post"`, the CSRF token, and an action of the logout URL. The username from phase 1 stays on the page.

#### 3. Sign-out tests

**File**: `accounts/tests/test_sign_out.py`

**Intent**: Prove the session actually ends, and that a signed-in user is not shown the form again.

**Contract**: `TestCase` methods return `None`. The module covers:

- An authenticated POST to `/accounts/logout/` redirects to `/accounts/login/`, and the following `GET /` redirects to the login form.
- An authenticated GET to `/accounts/logout/` returns 405, and the following `GET /` still contains the username.
- An authenticated GET to `/accounts/login/` redirects to `/`.
- `GET /` for an authenticated user contains a logout form whose method is post.

### Success Criteria:

#### Automated Verification:

- Sign-out tests pass: `uv run python manage.py test accounts.tests.test_sign_out`
- Accounts suite passes: `uv run python manage.py test accounts`

#### Manual Verification:

- Sign out from the signed-in page returns to the sign-in form
- Opening the sign-in form while signed in returns to the signed-in page

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- `accounts/tests/test_sign_in.py` covers the phase 1 cases in that phase's test contract, using the Django test client and users created in the test database.
- `accounts/tests/test_sign_out.py` covers the phase 2 cases. Phase 1 tests stay in their own module.

### Integration Tests:

- The test client walks the browser path: anonymous root to the form, successful POST, signed-in page, logout POST, and root gated again.
- `GET /admin/login/` stays in the phase 1 module so the health-check URL is not dropped while app routes are added.
- No live HTTP and no call to the shop sites. Password reset is not tested because those routes are not mounted.

### Manual Testing Steps:

1. Create an active user in admin, or use the local superuser. Open `/`, sign in with that username and password, and confirm the page shows the username.
2. Sign out, then submit a wrong password and confirm the invalid-login sentence and that the username page does not appear.
3. Sign in again, open `/accounts/login/`, and confirm the browser returns to the signed-in page.
4. Open `/admin/login/` and confirm the admin sign-in page still renders. With the app session active as a staff user, confirm `/admin/` opens as that same user.

## Performance Considerations

Sign-in is Django's normal authenticate plus one session write. This slice adds no queries beyond that, no cache, and no background work. That fits the small, low-traffic MVP.

## Migration Notes

No schema or data migration. `django.contrib.auth` tables already exist after `migrate`. An account from `createsuperuser` or admin signs in with its username and password. The accounts app must not add a table. The app session is the admin session: signing out of the app signs out of admin too.

## References

- FR-001 and access control: `context/foundation/prd.md`
- S-01: `context/foundation/roadmap.md`
- Issue: https://github.com/MartBur/Data-collector/issues/6
- App and test pattern: `prices/apps.py`, `prices/tests/test_models.py`
- Current routes and auth install: `DataCollector/urls.py`, `DataCollector/settings.py`
- Health check: `render.yaml`
- This change has no `research.md` or `frame.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Sign in

#### Automated

- [x] 1.1 Sign-in tests pass: `uv run python manage.py test accounts.tests.test_sign_in`
- [x] 1.2 App adds no tables: `uv run python manage.py makemigrations --check --dry-run`
- [x] 1.3 Project check passes: `uv run python manage.py check`

#### Manual

- [x] 1.4 Browser sign-in with an existing username and password shows that username
- [x] 1.5 A wrong password stays on the form and shows the invalid-login error
- [x] 1.6 `/admin/login/` still shows the admin sign-in page

### Phase 2: Sign out

#### Automated

- [ ] 2.1 Sign-out tests pass: `uv run python manage.py test accounts.tests.test_sign_out`
- [ ] 2.2 Accounts suite passes: `uv run python manage.py test accounts`

#### Manual

- [ ] 2.3 Sign out from the signed-in page returns to the sign-in form
- [ ] 2.4 Opening the sign-in form while signed in returns to the signed-in page
