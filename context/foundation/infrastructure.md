---
project: DataCollector
researched_at: 2026-09-18
recommended_platform: Render
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python
  framework: Django
  runtime: "Python 3.14 (uv)"
---

## Recommendation

**Deploy on Render.**

Data Collector is a Django 6.1.1 / Python 3.14 / uv app with PostgreSQL, Django admin, and a once-per-calendar-day price-recording job (FR-008). Render is the only shortlisted platform that matches that runtime natively (Python 3.14.3 default since 2026-02-11, `uv sync` when `uv.lock` is present), keeps Postgres and cron co-located, and still gives agents a CLI plus an official MCP. Interview answers favored a single region and same-vendor data services; they did not favor global edge or a hyperscaler. Fly.io remains a strong CLI, but its supported co-located database is Managed Postgres at $38/month, and unmanaged `fly postgres` is deprecated. Railway is cheaper and has a hosted MCP, but its official Django path is dashboard-heavy and its cron silently skips if a job does not exit.

Paid MVP floor on Render (Hobby workspace): Starter web **$7**/month + Postgres basic-256mb **$6**/month + cron **$1** minimum ≈ **$14**/month. Do not use the free web or free Postgres plans from Render’s Django tutorial.

## Platform Comparison

Scores are Pass / Partial / Fail against the five agent-friendly criteria. Interview weights: co-location preferred; single region is fine; cost and DX had no strong preference; no existing platform familiarity. Persistent connections were “don’t know”; the PRD has no WebSockets (`has_realtime: false`) and does have a daily job, so serverless platforms were not hard-dropped for Q1 — they were dropped when they could not run this Django + PostgreSQL runtime.

| Platform | CLI-first | Managed/Serverless | Agent-readable docs | Stable deploy API | MCP / Integration | Total | Shortlist |
|---|---|---|---|---|---|---|---|
| Render | Pass | Pass | Pass | Pass | Pass | 5 Pass | Yes (recommended) |
| Railway | Pass | Pass | Partial | Pass | Pass | 4 Pass / 1 Partial | Yes (runner-up) |
| Fly.io | Pass | Pass | Partial | Pass | Partial | 3 Pass / 2 Partial | Yes |
| Vercel | Pass | Pass | Pass | Pass | Pass | 5 Pass | No — serverless Django, no co-located Postgres |
| Cloudflare | Pass | Pass | Pass | Partial | Pass | 4 Pass / 1 Partial | No — Python Workers **beta** (checked 2026-09-18); Django path is D1/DO, not PostgreSQL |
| Netlify | Pass | Pass | Pass | Pass | Pass | 5 Pass | **Dropped** — Functions are TypeScript/JavaScript/Go only; no Django runtime |

**Render.** Native Python 3.14.3 and uv, official Django + Postgres guide, first-class cron services, Blueprint `render.yaml`, Git auto-deploy, CLI (`render deploys create`, `render logs`, `render jobs create`, `render psql`) and official MCP. Docs are published as `.md`. CLI defaults to interactive menus; agents must pass `-o json --confirm` (or `CI=true` / `RENDER_OUTPUT=json`). There is `blueprints validate` but no Blueprint-apply command — first apply is Dashboard “New Blueprint Instance”, after which Git auto-deploy and the CLI cover the loop. API/CLI rollback does not disable auto-deploy; Dashboard rollback does.

**Railway.** Excellent co-located Postgres, native cron (service start command + crontab, billed only while running), PR environments that clone the whole project including the database, and a hosted MCP at `mcp.railway.com` (`railway mcp install`, changelog 2026-09-04). Hobby is $5/month including usage. Docs are weaker as an agent corpus; the official Django guide still sets variables and “Generate Domain” in the Dashboard. Cron **skips** the next run if the previous deployment is still Active. Railpack defaults to Python 3.13.2 unless `.python-version` / `RAILPACK_PYTHON_VERSION` pins 3.14.

**Fly.io.** Best raw CLI (`fly launch`, `fly deploy`, `fly logs`, `fly secrets`, `fly ssh`, `fly deploy --image` rollback) and the GitHub Action already implied by `tech-stack.md` (`superfly/fly-pr-review-apps`, auto-deploy on merge). Django is a first-class container app. `fly launch` still generates a Dockerfile from the detected local Python (examples showed 3.10) — this repo must pin `python:3.14`. Supported co-located DB is Managed Postgres from **$38**/month; MPG docs still list security patches, version upgrades, alerting, and migration tools as under development (checked 2026-09-18). Unmanaged Fly Postgres is deprecated and unsupported. Daily jobs need an always-on supercronic process group (~+$2/month) or an extra cron-manager app. `flyctl mcp server` wraps CLI commands; Sprites MCP is a different product.

**Vercel.** Python 3.12 default, 3.13 and 3.14 available; Django is detected via `manage.py` and deployed as one Function. Strong CLI, MDX docs, and OAuth MCP. No co-located PostgreSQL. Cron is an HTTP GET to the function (Hobby: 2 jobs, once per day). Cold starts and duration limits are a poor fit for Django admin plus a multi-shop scrape. Excluded after the co-location preference.

**Cloudflare.** `wrangler` / `pywrangler`, `llms.txt`, and MCP are excellent. Python Workers remain **beta** and require the `python_workers` flag (checked 2026-09-18). Django WSGI adapters shipped 2026-09-02. Documented Django backends are D1 / Durable Objects via `django-cf` (no transactions). Hyperdrive for Postgres from Python Workers shipped 2026-09-16 (two days before this research) — too new for an MVP bet. Excluded.

**Netlify.** Official MCP and `https://docs.netlify.com/llms.txt`. Functions support TypeScript, JavaScript, and Go only. Cannot host this Django app. Hard-dropped on runtime.

### Shortlisted Platforms

#### 1. Render (Recommended)

Won because the runtime match is exact (Python 3.14, uv, Django as a long-running gunicorn process), Postgres and cron sit in the same project, and agents can operate deploys/logs/jobs/MCP without learning Docker. Single-region Hobby is enough for the primary user. Cost at this scale is predictable and well below Fly Managed Postgres.

#### 2. Railway

Second because co-location, native cron, PR environments with a cloned database, and hosted MCP are a better *product* fit than Fly at Hobby prices. It lost to Render on this repo’s pinned Python 3.14 / uv defaults, markdown docs, and a cron failure mode that can skip FR-008 entirely.

#### 3. Fly.io

Third because `flyctl` and GitHub Actions match the stack note, but the supported database and daily-job story are the expensive, fiddly parts of this MVP. Choose Fly later if the team wants multi-region Machines and will pay for MPG (or accept an external database, which this interview did not prefer).

## Anti-Bias Cross-Check: Render

### Devil's Advocate — Weaknesses

1. **The official Django Blueprint uses `plan: free` for both web and Postgres.** Free Postgres expires after 30 days, has no backups, and may restart at any time; after a 14-day grace period Render deletes the data. Free web spins down after 15 minutes of inactivity. An agent that copies [Deploy a Django App on Render](https://render.com/docs/deploy-django) will lose price history and violate the “today means today” rule the first time the instance is cold or the database is gone.

2. **That same guide’s `build.sh` runs `pip install -r requirements.txt`.** This repo is uv + `uv.lock` + Django `>=6.1.1`. A custom `buildCommand` *replaces* Render’s native install (`uv sync` when `uv.lock` is present). Copying `build.sh` silently abandons the lockfile. The guide also sets `STATICFILES_STORAGE` (Django 4-era) and `WEB_CONCURRENCY=4` on a 512 MB Starter box.

3. **CLI/API rollback does not disable auto-deploy.** Dashboard rollback does. An agent that rolls back with the API, then someone pushes to `main`, will republish the bad commit. Render retains a limited number of build artifacts; older deploys may not be roll-backable.

4. **Cron is UTC, max 12 hours, and overlapping ticks are delayed (not skipped).** A hung shop scrape can push “today’s” recording into the next calendar day in `Europe/Warsaw`. Manual “Trigger Run” **cancels** the active run. Cron cannot attach a disk.

5. **Full-stack preview environments (web + a copy of Postgres) require a Pro workspace ($25/month).** Hobby only includes single-service previews. An agent that points a PR preview at production `DATABASE_URL` can migrate or delete real price rows.

### Pre-Mortem — How This Could Fail

The team applied the official Django Blueprint on Hobby, including `plan: free`. For three weeks the app looked fine. On day 31 the database expired; fourteen days later Render deleted it. The 30-day chart and every “today” price disappeared, and there were no backups. In a parallel timeline they paid for Postgres but left `buildCommand: ./build.sh` from the tutorial, so production installed an ad-hoc `requirements.txt` while local `uv.lock` stayed on Django 6.1.1 — admin and the recorder drifted. The cron expression `0 0 * * *` ran at UTC midnight, which was still “yesterday” in Warsaw, so the start page labeled a previous calendar day’s price as today. A later incident used `render deploys create --commit` to roll back without turning auto-deploy off; the next merge restored the break. PR previews shared the production database; a branch migration dropped a column. Six months in, the “always-on $14” bill was fine — the product just no longer told the truth about today.

### Unknown Unknowns

- Render CLI is **interactive by default**. Agents and CI must set `CI=true`, `-o json --confirm`, or `RENDER_OUTPUT=json`. Tokens from `render login` expire; automation should use `RENDER_API_KEY`.
- There is no `render blueprint apply`. `render blueprints validate` only checks YAML. First create is Dashboard Blueprint apply, or `render services create` + `render pg create`.
- `.python-version` in this repo is `3.14` (patch omitted). Render accepts that and uses the latest 3.14.x patch. `PYTHON_VERSION` must be fully qualified if used instead.
- Native `uv sync` requires `uv.lock` at the **service root**. A later Dockerfile would ignore `PYTHON_VERSION` / `.python-version`.
- Cursor Origin as a Render git provider is **beta** (checked 2026-09-18). Use GitHub for this project.
- MCP can replace a service’s environment variables in one update and can trigger deploys. Treat write tools as production-capable.
- `createsuperuser` in the Django guide uses the Dashboard Shell. Agents should use `render jobs create` / `render ssh --ephemeral` with `createsuperuser --noinput` and `DJANGO_SUPERUSER_*` (Django 6.1).
- Tech-stack notes said GitHub Actions auto-deploy on merge. Render’s native Git auto-deploy already does that; a second Actions workflow is optional, not required.

## Operational Story

- **Preview deploys**: Hobby can enable **single-service** pull-request previews on the web service (Dashboard → service → Previews, or Blueprint `previews.generation: automatic`). They are billed at the same Starter rate, prorated. They do **not** clone Postgres on Hobby. Full-stack preview environments (copy of web + database) need Pro. Do not reuse production `DATABASE_URL` on a preview. Fork PRs follow Render’s Git-provider rules; prefer same-repo PRs.
- **Secrets**: Service env vars and Environment Groups in Render. Blueprint `generateValue: true` for `SECRET_KEY`. `DATABASE_URL` comes from `fromDatabase` (internal URL). Values are not shown in the CLI the way Fly lists secret *names*; rotation is “set a new value and redeploy”. Keep `RENDER_API_KEY` and Django superuser passwords in GitHub Secrets / the Render env store, never in git. `DEBUG` must be false in production (`RENDER` is set in the app environment).
- **Rollback**: Dashboard → service → rollback to a retained deploy (this **disables** auto-deploy). CLI/API equivalent is rolling back via the rollback endpoint or `render deploys create SERVICE_ID --commit SHA --confirm` — **then** `render services update …` to set auto-deploy off, or a new commit will overwrite the rollback. Migrations are not reversed; forward-fix data, don’t assume the schema rolled back. Time-to-revert is minutes if the artifact is still retained.
- **Approval**: Human: create the paid Render account, first Blueprint apply, paid Postgres, custom domain, rotate `SECRET_KEY` / superuser password, delete a database. Agent (unattended, with API key): validate `render.yaml`, trigger deploys, tail logs, run one-off jobs, read-only `render psql -c`. Do not let an agent `pg delete` or dump production.
- **Logs**: `render logs -r SERVICE_ID --tail=true` (non-interactive: `-o json --confirm`). Filter with `--level`, `--status-code`, `--start`, `--end`. Cron history is on the cron service’s Runs page and the same logs CLI. MCP can list logs. Pipeline/build logs come from `render deploys list` / inspect in the Dashboard.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Agent copies official Blueprint `plan: free`; Postgres expires in 30 days and data is deleted | Devil's advocate / Pre-mortem / Research finding | H | H | Blueprint must use `plan: basic-256mb` (or omit `plan` — new DBs default to basic-256mb). Never `plan: free`. |
| `build.sh` + pip replaces native `uv sync`; lockfile ignored | Devil's advocate / Unknown unknowns | H | H | `buildCommand` must start with `uv sync --frozen`. Do not add a pip `build.sh`. Keep `uv.lock` at repo root. |
| CLI/API rollback republished by the next push to `main` | Devil's advocate / Research finding | M | H | After a rollback, disable auto-deploy until a known-good commit is on `main`. Prefer Dashboard rollback or follow up with a service update. |
| UTC cron vs local calendar “today” (FR-008 / NFR) | Pre-mortem / Unknown unknowns | H | H | Set Django `TIME_ZONE` to the owner’s zone (likely `Europe/Warsaw`). Schedule cron after local midnight (e.g. `0 5 * * *` UTC). The recorder must stamp the calendar date in that timezone, not UTC date(). |
| Hung scrape delays the next daily run past the calendar day (12h cap) | Devil's advocate | M | H | Keep FR-008 short (few shop URLs). Alert on cron duration. Do not use “Trigger Run” while a run is active unless cancelling is intended. |
| PR preview uses production `DATABASE_URL` | Pre-mortem / Unknown unknowns | M | H | Hobby: disable auto PR previews that can migrate, or use a separate preview DB. Do not enable full-stack previews without Pro and `previewPlan`. |
| Starter 512 MB OOM from `WEB_CONCURRENCY=4` | Devil's advocate | M | M | Set `WEB_CONCURRENCY=2` or `1` on Starter. |
| Django 6 `STORAGES` vs tutorial `STATICFILES_STORAGE` | Devil's advocate | M | L | Follow Django 6.1 staticfiles settings, not the Render 5.0 snippet. |
| Interactive CLI blocks an agent | Unknown unknowns | H | M | Always `CI=true` / `-o json --confirm`. Use `RENDER_API_KEY` in automation. |
| MCP overwrites all env vars or deploys production | Unknown unknowns | M | H | Restrict MCP to this workspace; prefer read tools for logs/SQL; confirm before env updates. |
| MPG-like “we thought Fly was already decided” drift | Research finding | M | L | `tech-stack.md` still says Fly. This file is the deployment contract; update the stack hint when convenient. |

## Getting Started

These steps are for **this** repo (Django 6.1.1, `requires-python = ">=3.14"`, `.python-version` = `3.14`, `uv.lock`, `manage.py` at repo root, `DataCollector.asgi:application`). Do not copy Render’s pip `build.sh`, `plan: free`, Django 5.0.1 pin, or `STATICFILES_STORAGE` snippet.

1. **Install the CLI (Windows):** `winget install render.cli` then `render login` and pick the Hobby workspace. Validate later with `render blueprints validate render.yaml`.
2. **Add production dependencies with uv** (not pip): `uv add gunicorn uvicorn "whitenoise[brotli]" "psycopg[binary]" dj-database-url`. Point Django `DATABASES` at `DATABASE_URL` via `dj_database_url.config`. Set `DEBUG` false when `RENDER` is in the environment; append `RENDER_EXTERNAL_HOSTNAME` to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. Keep using `uv run python manage.py runserver` locally — Render’s native runtime is the production counterpart; there is no Render-specific local emulator to install.
3. **Commit a `render.yaml` at the repo root** that declares: Postgres `plan: basic-256mb` (not `free`); web `runtime: python`, `plan: starter`; `buildCommand: uv sync --frozen && uv run python manage.py collectstatic --no-input`; `preDeployCommand: uv run python manage.py migrate`; `startCommand: uv run python -m gunicorn DataCollector.asgi:application -k uvicorn.workers.UvicornWorker`; env `DATABASE_URL` from the database `connectionString`, `SECRET_KEY` with `generateValue: true`, `WEB_CONCURRENCY=2`, `PYTHON_VERSION` omitted (`.python-version` already says `3.14`). Add a second service `type: cron` with the same build, UTC `schedule` after local midnight, and `startCommand` equal to the FR-008 management command once it exists (`uv run python manage.py …`). Share `DATABASE_URL` with the cron service.
4. **Apply once in the Dashboard** (Blueprints → New Blueprint Instance → this GitHub repo). After that, merge to the linked branch auto-deploys. Optional: `render deploys create SERVICE_ID --wait --output json --confirm`. Create the list-owner account with `render jobs create SERVICE_ID --start-command "uv run python manage.py createsuperuser --noinput" --confirm` after setting `DJANGO_SUPERUSER_USERNAME` / `EMAIL` / `PASSWORD` on the service.
5. **Verify FR-008 and logs:** `render logs -r WEB_SERVICE_ID --tail=true` and the same for the cron service. Confirm a price labeled “today” is that calendar day in Django’s `TIME_ZONE`, not yesterday UTC.

## Out of Scope

The following were not evaluated in this research:
- Docker image configuration
- CI/CD pipeline setup
- Production-scale architecture (multi-region, HA, DR)
