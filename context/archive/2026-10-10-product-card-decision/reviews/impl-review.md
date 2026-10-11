<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Product card with today's prices, a 30-day chart, and a shop link

- **Plan**: context/changes/product-card-decision/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2, 3, 4
- **Date**: 2026-10-11
- **Verdict**: APPROVED
- **Findings**: 0 critical, 2 warnings, 0 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | WARNING |

## Verification

- **PASS** — `uv run python manage.py test prices.tests.test_card`: 8 tests ran; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test prices.tests.test_product_card`: 10 tests ran after triage; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test prices`: 113 tests ran; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test accounts.tests.test_home`: 5 tests ran; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test`: 134 tests ran after triage; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test accounts.tests.test_home.HomeTests.test_home_button_is_on_every_page`: 1 test ran; `OK`; no system-check issues.
- **PASS** — `uv run python manage.py test prices.tests.test_product_card prices.tests.test_product_list`: 17 tests ran; `OK`; no system-check issues.
- **Manual criteria** — All eight genuinely manual checks in Progress are marked complete. Their reproduced browser results are recorded in `context/changes/product-card-decision/verification.md`.

## Findings

### F1 — Extreme prices can create millions of chart ticks

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: prices/views.py:401-408
- **Detail**: `_price_ticks` materializes one tick for every 10 PLN between the axis floor and ceiling. `PriceObservation.amount` permits values up to 99,999,999.99, so one malformed or extreme stored value can create roughly ten million tick dictionaries and SVG elements whenever an authenticated user opens the card, exhausting memory or producing an unusable response.
- **Fix A ⭐ Recommended**: Preserve 10 PLN ticks for ordinary ranges, but switch to a larger “nice” interval once a fixed tick budget would be exceeded.
  - Strength: Bounds response work for both existing and future data while preserving every planned example.
  - Tradeoff: Extreme ranges no longer follow the plan's literal every-10-PLN rule.
  - Confidence: HIGH — the loop and model limit make the failure mode deterministic.
  - Blind spot: The accepted business maximum for a product price is not documented.
- **Fix B**: Enforce a documented maximum amount before recording and validate or repair existing observations.
  - Strength: Keeps the chart's every-10-PLN contract unchanged.
  - Tradeoff: Changes the recording boundary and requires a policy plus handling for existing outliers.
  - Confidence: MEDIUM — the appropriate business maximum is unknown.
  - Blind spot: External shop parsers and existing production data were not inspected for realistic upper bounds.
- **Decision**: FIXED — implemented adaptive nice-number tick intervals with a 1 PLN minimum and a maximum of 20 intervals; added regression coverage for sub-100 and extreme ranges.

### F2 — Completed manual checks have no auditable evidence

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: context/changes/product-card-decision/plan.md:310-338
- **Detail**: Progress marks manual checks 2.3, 2.4, 3.3, 3.4, 3.6, and 4.2–4.4 complete, but the reviewed commits contain no browser verification note, screenshot, or recorded observations. Commit references on some boxes identify implementation commits, not evidence that the manual steps ran.
- **Fix**: Add a short verification record describing the test data, browser actions, and observed outcomes for the completed manual checks.
- **Decision**: FIXED — reproduced the manual scenarios in a browser against an isolated database and recorded the observed results in `verification.md`.

## Triage Summary

- **Fixed**: F1 — adaptive nice-number Y-axis intervals with bounded tick count.
- **Fixed**: F2 — browser verification reproduced and recorded.
