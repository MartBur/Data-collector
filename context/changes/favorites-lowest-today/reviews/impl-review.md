<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Favorites lowest today

- **Plan**: context/changes/favorites-lowest-today/plan.md
- **Scope**: Full plan
- **Reviewed phases**: 1, 2, 3, 4
- **Date**: 2026-10-12
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical 2 warnings 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | WARNING |

## Findings

### F1 — Tied shops are separate rows

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Adherence
- **Location**: accounts/templates/accounts/home_price_table.html:18
- **Detail**: plan.md still requires one price phrase with tied shops joined by ` and ` (`19.99 PLN at Rossmann and DOZ`). Commit e06d993 replaced that with one row per shop, and accounts/tests/test_home.py now asserts ` and ` is absent and that the product link appears twice. plan-brief.md lines 19 and 29 already describe one row per shop. Both shops still appear, in page id order, with new-tab links. The amount, yesterday label, and historical-low membership match the plan.
- **Fix A ⭐ Recommended**: Amend the phase 2 contract in plan.md to one row per tied shop.
  - Strength: Matches home_price_table.html, the home tests, and the decision already written in plan-brief.md.
  - Tradeoff: plan.md no longer matches the phrase it was originally reviewed against.
  - Confidence: HIGH — the brief, the template, and the tests already agree.
  - Blind spot: None significant. The PRD does not require the joined phrase.
- **Fix B**: Restore one phrase joined by ` and ` and point the home tests back at that phrase.
  - Strength: Makes the page match the phase 2 contract that is still in plan.md.
  - Tradeoff: Undoes the split from e06d993, and one anchor still cannot open two shop URLs.
  - Confidence: MEDIUM — the later brief treats the split as the decision.
  - Blind spot: Whether a single joined phrase is still wanted on the start page.
- **Decision**: FIXED via Fix A

### F2 — ASCII frame and underscore empty row

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: accounts/templates/accounts/home_price_table.html:39
- **Detail**: The plan's home template is the four captions, the update line, and one empty `<td>` when a table has no products. Commit e06d993 added accounts/templates/accounts/ascii_rule.html, the `+` cross in accounts/templates/accounts/home.html, and an empty row whose data cells are `_`. The frame does not change a price, a favourite, or the recording clock. The empty Favourites test now looks for `<td class="ascii-cell">_</td>`.
- **Fix**: Record the ASCII frame and the `_` empty row in the plan's home-template contract.
- **Decision**: FIXED

### F3 — Manual boxes checked inside implementation commits

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: context/changes/favorites-lowest-today/plan.md:427
- **Detail**: Phase 2 manual items 2.3–2.6 were checked in e06d993, phase 3 manual items 3.4–3.6 in 0079680, and phase 4 manual items 4.3–4.5 and 4.7 in 33a90ae, each in the same commit as the feature. Phase 4 automated items 4.1, 4.2, and 4.6 are checked without a commit SHA. The plan says to pause for a human check before the next phase. Re-running the automated commands on 2026-10-12 passed: the listed test modules (49 tests) and the full suite (178 tests). `manage.py migrate` reported no migrations to apply.
- **Fix**: Confirm the manual browser checks, or uncheck 2.3–2.6, 3.4–3.6, 4.3–4.5, and 4.7 until that confirmation exists. Leave the automated boxes checked.
- **Decision**: FIXED — user confirmed on 2026-10-12; manual boxes 2.3–2.6, 3.4–3.6, 4.3–4.5, and 4.7 are checked
