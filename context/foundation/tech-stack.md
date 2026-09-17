---
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
---

## Why this stack

A solo after-hours learner shipping a small logged-in web app in 3 weeks needs a batteries-included Python stack: auth, PostgreSQL, admin for the privileged tracked-list, and a daily scheduled price-recording job. Django is the recommended default for a Python web app; it includes auth, ORM, migrations, and admin from day one, and scheduled work fits a management command plus the host's cron. Scaffolding support is verified, so bootstrap should be smooth. Auth and background jobs are in scope; payments, realtime, and AI are not. Deploy on Fly with GitHub Actions and auto-deploy on merge to main.
