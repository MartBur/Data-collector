# Repository Guidelines

Data Collector is a Django 6.1.1 web app managed with uv on Python 3.14. Product rules: @context/foundation/prd.md. Stack intent: @context/foundation/tech-stack.md.

## Hard rules

- Do not delete, overwrite, or relocate `context/`. `context/archive/` is read-only (@context/archive/README.md). Per-change docs belong under `context/changes/<change-id>/` (@context/changes/README.md).
- Django settings module is `DataCollector.settings` (@manage.py). Do not put web-app code in `src/workspace/` — that package only prints a hello message (@src/workspace/__init__.py). Add Django apps as siblings of `DataCollector/` and register them in @DataCollector/settings.py.
- Implement must-have scope only unless asked: logged-in favorites; product cards show name, today's landed shop prices, a 30-day chart, and outbound links — no description and no availability. Tracked-list add/change/remove is list-owner only. A price labeled "today" must be that calendar day's recorded price (@context/foundation/prd.md).
- Do not commit real secrets. @DataCollector/settings.py currently ships Django's `django-insecure-` SECRET_KEY placeholder and `DEBUG = True`.

## Build, test, and development commands

- `uv run python manage.py runserver` — local server
- `uv run python manage.py migrate` — apply migrations (SQLite at `BASE_DIR / db.sqlite3`)
- `uv run python manage.py test` — Django test runner; no test modules exist yet
- `uv add <package>` — add a dependency and update @uv.lock

Use uv only. Deploy on Render from @render.yaml (web Free + Postgres Free) with Git auto-deploy on merge to main; GitHub Actions remains the CI provider (@context/foundation/tech-stack.md, @context/foundation/infrastructure.md). There is no `.github/workflows/` yet.

## Project structure

- `manage.py` and `DataCollector/` — Django project package. `urlpatterns` is admin-only (@DataCollector/urls.py). `INSTALLED_APPS` is contrib-only.
- @pyproject.toml / @uv.lock — distribution name `workspace`, `django>=6.1.1`, `requires-python = ">=3.14"` (also @.python-version).
- Scaffold record: @context/changes/bootstrap-verification/verification.md. Local `db.sqlite3` is not listed in @.gitignore; leave it untracked.

## Coding style

Annotate every new or changed function, method, and class attribute (parameters and return). Do not use `typing.Any`, `Any | …`, or untyped `*args` / `**kwargs`; pick a concrete type, `TypedDict`, a `Protocol`, or a union of those. Django views return `HttpResponse` (or a subclass); `handle` on management commands returns `None`. Do not retro-type generated files in `DataCollector/` (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`). No Ruff, Black, mypy, or EditorConfig file is present — reviewers enforce types on the diff.

## Commit and pull request guidelines

Recent commits use sentence-case subjects without Conventional Commits prefixes. Open PRs against https://github.com/MartBur/Data-collector. No CI checks are configured.
