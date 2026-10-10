# Account Sign-In — Plan Brief

> Full plan: `context/changes/account-sign-in/plan.md`

## What & Why

A logged-in owner is the entry to the rest of the product: favorites are per account, and every later slice assumes that session. This slice lets an existing account sign in with a username and password, see who is signed in, and sign out. FR-001 is that sign-in; the favorites page comes later.

## Starting Point

Django auth, sessions, and admin login are installed. The only sign-in URL is `/admin/login/`, which is also the Render health check. There is no app screen, no `LOGIN_REDIRECT_URL`, and the stock user model is already how `createsuperuser` and admin create accounts.

## Desired End State

Someone with an existing active account opens the site, signs in, and sees that username. A wrong password, an unknown username, or an inactive account does not start a session. Sign out returns to the form. A non-staff account can do this. Admin login stays where it is.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Who can get an account | Existing accounts only | FR-001 is sign-in, and the planning choice was to leave creation in admin and `createsuperuser`. |
| Sign-in identifier | Username and password | That is the identifier admin and `DJANGO_SUPERUSER_USERNAME` already use. |
| Page after sign-in | A page that shows the username | The favorites page is a later slice, and admin refuses a non-staff account after login. |
| Sign out | A POST form on that page, then the sign-in form | Django 6 logout accepts POST only; GET must leave the session in place. |
| Password reset | Out of this slice | Nothing in FR-001 asks for it, and the project has no Django email backend. |
| Auth mechanism | Django session and the stock user | Auth and sessions are already installed; a custom user model is not. |
| Where the screen lives | A new `accounts` app | `prices` is the price domain, and admin stays the list-owner tool. |

## Scope

**In scope:**

- Sign-in form at `/accounts/login/` for an existing active user
- Signed-in page at `/` that shows the username
- Anonymous visits to `/` redirect to the form
- Sign out back to the form
- An already signed-in visit to the form returns to `/`
- Tests for failed sign-in, inactive users, `next`, and the admin login URL

**Out of scope:**

- Registration, password reset, password change, and email login
- Favorites, product cards, and tracked-list editing
- Changing admin login, `render.yaml`, or how accounts are created
- List-owner permission checks

## Architecture / Approach

The `accounts` app serves Django's login view and a login-required home page. `LOGIN_URL` is `/accounts/login/` and `LOGIN_REDIRECT_URL` is `/`. Phase 2 adds POST-only logout at `/accounts/logout/` and turns signed-in visitors away from the form. The stock user table and the current session middleware stay. Admin remains on `/admin/`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Sign in | Existing user signs in and sees their username; bad credentials stay signed out | Login success must land on `/`, not the missing `/accounts/profile/` default |
| 2. Sign out | Session ends and returns to the form; the form is skipped when already signed in | Logout must be a POST, or the session silently stays |

**Prerequisites:** Django auth and sessions are already installed. At least one account exists via admin or `createsuperuser`. F-01 is not a prerequisite.
**Estimated effort:** About one session across 2 phases.

## Open Risks & Assumptions

- The app and admin share one session, so signing out of the app signs out of admin too.
- An inactive account sees the same error as a wrong password.
- A second person needs an account created in admin; this slice has no registration form.
- Username match is case-sensitive, same as Django's default user lookup.
- Django's default session lifetime is enough; there is no separate remember-me control.

## Success Criteria (Summary)

- An existing active user can sign in and see their username.
- A wrong password, an unknown username, or an inactive account does not sign them in.
- They can sign out and land back on the form, and the admin sign-in page still opens.
