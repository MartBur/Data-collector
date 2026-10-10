<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Account Sign-In

- **Plan**: context/changes/account-sign-in/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2
- **Date**: 2026-10-10
- **Verdict**: APPROVED
- **Findings**: 0 critical, 1 warning, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — Signed-in login URL with next set to itself returns an error

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: accounts/views.py:9
- **Detail**: `redirect_authenticated_user` is True, which phase 2 requires. A signed-in `GET /accounts/login/?next=/accounts/login/` is a same-host `next`, so Django keeps it, then `LoginView.dispatch` raises `ValueError` because the redirect target is the login path. Calling the view with that request raised `Redirection loop for authenticated user detected`. The usual open, with no `next` or with `next=/`, still returns to `/`.
- **Fix**: In `SignInView`, ignore a `next` that points at the login path and fall back to `/`. Add a test for `GET /accounts/login/?next=/accounts/login/` while signed in.
- **Decision**: FIXED

### F2 — Signed-in page can stay in the browser cache after sign-out

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: accounts/views.py:12
- **Detail**: `home` is not wrapped with `never_cache`. Login and logout views are. After sign-out, the back button can still show the username from the cached page. The session is already ended.
- **Fix**: Decorate `home` with `never_cache`.
- **Decision**: FIXED
