<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Calendar-day landed price

- **Plan**: context/changes/calendar-day-landed-price/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2, 3, 4
- **Date**: 2026-09-25
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 5 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | WARNING |

## Findings

### F1 — Invalid parsed amounts can corrupt data or stop the run

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: prices/readers.py:50-62,76-83; prices/collect.py:47-58; prices/recording.py:16-18,50-63; prices/models.py:99
- **Detail**: Super-Pharm JSON-LD is converted with `Decimal(str(...))` while only JSON syntax errors are caught. A valid document containing `null`, malformed numeric text, or a non-finite value can raise during parsing or persistence and abort the command before later pages run, contrary to the requirement that one failed page not block others. A negative price is currently accepted and stored because neither the recording boundary nor the database enforces a positive amount.
- **Fix**: Reject non-numeric, non-finite, non-positive, and unrepresentable amounts as a page gap; add a database check constraint for `amount > 0`.
  - Strength: Keeps malformed shop data isolated to one page and protects stored price integrity at both application and database boundaries.
  - Tradeoff: Requires a migration plus focused parser, recording, and command tests.
  - Confidence: HIGH — the exception path and lack of a positivity constraint are directly visible in the implementation.
  - Blind spot: The exact upper bound should be chosen from the product domain before adding application validation.
- **Decision**: FIXED

### F2 — Redirects bypass the saved shop-host restriction

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: prices/collect.py:30-38; prices/models.py:21-38,68-79
- **Detail**: Admin validation restricts the saved URL hostname, but `urlopen` follows redirects without validating each redirect target. A permitted shop URL can therefore cause the recorder to fetch an unrelated or internal host. Direct model saves can also bypass `clean()`.
- **Fix**: Validate HTTPS and the expected shop host at the fetch boundary, and use a redirect handler that rejects every target outside that same allowed host.
  - Strength: Enforces the trust boundary where network access actually occurs and closes the redirect SSRF path.
  - Tradeoff: The fetch helper must receive shop context and use a small custom opener/redirect handler.
  - Confidence: HIGH — Python's default opener follows redirects and the current helper receives only a URL.
  - Blind spot: Shop CDNs or intentional cross-host redirects may need an explicit allowlist after observing live behavior.
- **Decision**: FIXED

### F3 — HTTP responses are read without a size limit

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: prices/collect.py:34-35
- **Detail**: `response.read()` buffers the complete response. An unexpectedly large shop response can consume excessive memory and prevent the remaining pages from being processed.
- **Fix**: Enforce a maximum response size with a bounded read and treat oversized responses as `FetchFailed`.
- **Decision**: FIXED

### F4 — Promo-versus-crossed-out reader behavior is not proven

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: prices/tests/test_readers.py:20-39; prices/tests/fixtures/
- **Detail**: The plan requires a fixture with a higher crossed-out price and a lower current price, but no test fixture contains and asserts that numeric pair. Existing tests prove current selectors, shipping exclusion, and no-price behavior, but not the explicit promo-price rule.
- **Fix**: Add a saved/minimal fixture containing both numeric prices and assert that the reader returns the lower current price.
- **Decision**: FIXED

### F5 — Single-shop and retry command cases are under-tested

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: prices/tests/test_commands.py:42-109
- **Detail**: The all-shop command covers store, unchanged, and gap outcomes, while the single-shop command only covers storing and filtering. The plan requires one single-shop command to cover store, unchanged, and gap, and the retry test does not assert that exactly two fetch attempts occurred.
- **Fix**: Extend the single-shop tests with unchanged and failed-retry cases and assert a two-call fetch count.
- **Decision**: FIXED

### F6 — Command class attributes are not annotated

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: prices/management/commands/record_prices.py:5; prices/management/commands/record_doz_prices.py:6-7; prices/management/commands/record_gemini_prices.py:6-7; prices/management/commands/record_rossmann_prices.py:6-7; prices/management/commands/record_superpharm_prices.py:6-7
- **Detail**: New `help` and overridden `shop_code` class attributes lack annotations, contrary to the repository rule that every new or changed class attribute is typed.
- **Fix**: Annotate command attributes as `help: str` and `shop_code: str`.
- **Decision**: FIXED

### F7 — Checked manual criteria have no durable evidence

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: context/changes/calendar-day-landed-price/plan.md:222-250
- **Detail**: Manual items 1.3, 1.4, 3.2, and 4.2-4.4 are checked with commit SHAs, but the diffs and commit messages contain no observed results, command output, or verification note. Model tests partially corroborate Phase 1, but the live-page and live-command checks cannot be independently verified from the repository.
- **Fix**: Add a concise verification note recording the date, scenario, and observed result for each completed manual check.
- **Decision**: FIXED

## Verification

- `uv run python manage.py migrate` — PASS; no migrations to apply.
- `uv run python manage.py test prices.tests.test_models` — PASS; 6 tests.
- `uv run python manage.py test prices.tests.test_recording` — PASS; 7 tests.
- `uv run python manage.py test prices.tests.test_readers` — PASS; 6 tests.
- `uv run python manage.py test prices.tests.test_commands` — PASS; 3 tests.
- Total focused tests: 22 passed; Django system checks reported no issues.

## Scope Notes

- The review covered completed phases 1, 2, 3, and 4.
- No shipping calculation, prior-day fallback, extra shops, owner-facing screens, authentication UI, product cards, charts, favorites, live HTTP tests, Render cron, or `render.yaml` changes were found.
- `prices/views.py` is an unused generated stub; it does not expand product behavior and is not treated as a finding.
