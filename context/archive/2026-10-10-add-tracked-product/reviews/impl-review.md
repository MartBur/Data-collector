<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Add a tracked product with two or three shop pages

- **Plan**: context/changes/add-tracked-product/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2
- **Date**: 2026-10-10
- **Verdict**: APPROVED
- **Findings**: 0 critical, 1 warning, 0 observations

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

### F1 — Confirmation id with a non-ASCII digit returns 500

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: prices/views.py:23
- **Detail**: `_product_for_added` accepts any `isdigit()` string, then calls `int()`. A character such as `²` is a digit to `isdigit()` and raises `ValueError` from `int()`, which the view does not catch. A staff GET of `/products/add/?added=²` returns 500. The plan says a missing or unknown `added` id shows only the empty form and does not 404. `test_unknown_added_id` only posts `999999` and `nope`.
- **Fix**: Treat only ASCII digits as an id, and return `None` when `int()` fails, so the page renders the empty form.
- **Decision**: FIXED
