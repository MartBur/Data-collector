---
bootstrapped_at: 2026-09-17T17:06:34Z
starter_id: django
starter_name: Django
project_name: DataCollector
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: verified
phase_3_status: ok
audit_command: pip-audit
---

## Hand-off

```yaml
starter_id: django
package_manager: uv
project_name: DataCollector
hints:
  language_family: python
  team_size: solo
  deployment_target: fly
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: verified
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: true
```

## Why this stack

A solo after-hours learner shipping a small logged-in web app in 3 weeks needs a batteries-included Python stack: auth, PostgreSQL, admin for the privileged tracked-list, and a daily scheduled price-recording job. Django is the recommended default for a Python web app; it includes auth, ORM, migrations, and admin from day one, and scheduled work fits a management command plus the host's cron. Scaffolding support is verified, so bootstrap should be smooth. Auth and background jobs are in scope; payments, realtime, and AI are not. Deploy on Fly with GitHub Actions and auto-deploy on merge to main.

## Pre-scaffold verification

| Signal             | Value                              | Severity | Notes                              |
| ------------------ | ---------------------------------- | -------- | ---------------------------------- |
| npm package        | not run                            | —        | non-JS starter; cmd_template is `django-admin`, not an npm `create-*` CLI |
| GitHub repo        | not run                            | —        | card `docs_url` is `https://docs.djangoproject.com`, not a `github.com/<owner>/<repo>` URL |

Recency: no recency signal available.

## Scaffold log

**Resolved invocation**: `django-admin startproject DataCollector .`
**Strategy**: native-cwd
**Exit code**: 0
**Pre-flight files-to-touch**: manage.py, DataCollector/__init__.py, DataCollector/asgi.py, DataCollector/settings.py, DataCollector/urls.py, DataCollector/wsgi.py
**Files written by CLI**: 6
**Pre-existing files preserved**: context/, .gitignore, and the rest of the existing cwd (none of the Django targets existed; no overwrites)

Notes:

- `{name}` was substituted with the hand-off `project_name` (`DataCollector`). The destination `.` is already in the starter `cmd_template`; replacing `{name}` with `.` would be an invalid Django project identifier.
- `package_manager: uv` was recorded but not used: `cmd_template` has no `{pm}` placeholder. Django 6.1.1 came from the `django-admin` already on PATH.
- Registry `pre: pip install django` was not run because `django-admin` was already available (version 6.1.1).
- `.gitignore` was already present in cwd; Django `startproject` did not emit one, so no append-merge ran.

## Post-scaffold audit

**Tool**: pip-audit --format json
**Summary**: 0 CRITICAL, 0 HIGH, 0 MODERATE, 0 LOW
**Direct vs transitive**: not distinguished by this tool
**Status**: ran successfully (exit code 0; stderr: "No known vulnerabilities found")
**Scope note**: no `pyproject.toml` or `requirements.txt` in the scaffold. `pip-audit` therefore scanned the current Python environment (including Django 6.1.1 and other installed packages such as `uv` and `pip-audit` itself), not a project lockfile.

#### CRITICAL findings

none

#### HIGH findings

none

#### MODERATE findings

none

#### LOW / INFO findings

none

## Hints recorded but not acted on

| Hint                       | Value                              |
| -------------------------- | ---------------------------------- |
| bootstrapper_confidence    | verified                           |
| quality_override           | false                              |
| path_taken                 | standard                           |
| self_check_answers         | null                               |
| team_size                  | solo                               |
| deployment_target          | fly                                |
| ci_provider                | github-actions                     |
| ci_default_flow            | auto-deploy-on-merge               |
| has_auth                   | true                               |
| has_payments               | false                              |
| has_realtime               | false                              |
| has_ai                     | false                              |
| has_background_jobs        | true                               |

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Useful manual steps in the meantime:
- `git init` (if you have not already) to start your own repo history.
- Review any `.scaffold` siblings the conflict policy created and decide which version of each file to keep.
- Address audit findings per your project's risk tolerance — the full breakdown is in this log.
- Declare Django with the chosen package manager (`uv init` then `uv add django`) so the project has a lockfile instead of relying on a global install.
