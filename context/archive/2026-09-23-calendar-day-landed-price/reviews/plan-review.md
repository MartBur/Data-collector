<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Calendar-day landed price

- **Plan**: `context/changes/calendar-day-landed-price/plan.md`
- **Mode**: Deep
- **Date**: 2026-09-23
- **Verdict**: REVISE
- **Findings**: 2 critical, 2 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | FAIL |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

Grounding: 6/6 existing paths ✓, 5/5 symbols ✓, brief↔plan ✓. Planned `prices/` paths do not exist yet, as expected for this new app.

## Findings

### F1 — No unattended daily execution

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment
- **Location**: Overview, What We're NOT Doing, and Phase 4
- **Detail**: FR-008 and roadmap F-01 require recording “without user action,” but the plan delivers only manually invoked local commands and explicitly excludes Render cron. All listed success criteria can pass while no daily job ever runs. This makes the plan a recording foundation, not the unattended outcome it claims.
- **Fix A ⭐ Recommended**: Add the Render cron service and production verification to this change.
  - Strength: Satisfies FR-008 and the roadmap outcome end to end; `context/foundation/infrastructure.md` already specifies the intended Render cron architecture.
  - Tradeoff: Expands this change into deployment work and introduces Render's paid cron cost.
  - Confidence: HIGH — the infrastructure document already defines the command, database sharing, and post-midnight UTC scheduling approach.
  - Blind spot: The current free Render database conflicts with the infrastructure recommendation and may need a separate funding/deployment decision.
- **Fix B**: Reframe this change as the recording foundation and add an explicit scheduler change that must complete before FR-008/F-01 is marked done.
  - Strength: Preserves the deliberately local implementation scope and avoids mixing deployment work into the data-model change.
  - Tradeoff: This plan no longer completes FR-008 by itself; roadmap status and downstream prerequisites must remain explicit.
  - Confidence: HIGH — the plan and brief already describe cron as a later deployment change.
  - Blind spot: A follow-up without an owner or ordering could still leave production recording manual.
- **Decision**: PENDING

### F2 — A transaction alone does not serialize overlapping runs

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment
- **Location**: Phase 4 — Fetch and commands
- **Detail**: The plan promises that overlapping runs preserve compare-and-insert semantics, but `transaction.atomic()` alone does not prevent two PostgreSQL transactions from reading the same latest observation and both inserting. A unique `(shop_page, date)` constraint cannot solve this because changed prices intentionally create multiple rows per day.
- **Fix**: Specify an atomic section that locks the parent `ShopPage` row with `select_for_update()` before reading the latest daily observation and inserting, plus an overlapping-run test and a note that SQLite does not provide equivalent row locking.
  - Strength: Serializes each page independently on production PostgreSQL while retaining multiple changed observations per day.
  - Tradeoff: The concurrency test needs PostgreSQL or must clearly separate production locking verification from SQLite unit tests.
  - Confidence: HIGH — locking a stable parent row also covers the first observation of a day, when no observation row exists to lock.
  - Blind spot: The acceptable local SQLite behavior under manually started concurrent commands still needs to be stated.
- **Decision**: PENDING

### F3 — Live reader and fetch feasibility is unresolved

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Blind Spots
- **Location**: Phase 3 and Phase 4
- **Detail**: The plan names four HTML readers but records no verified selector, representative product URL, or evidence that each selling price is present in server-returned HTML rather than injected by JavaScript or blocked. The repo also has no HTTP or HTML parser dependency, and the plan leaves timeout, User-Agent, redirects, HTTP errors, and parser choice to the implementer. Fixture-only tests could pass while every live command produces gaps.
- **Fix**: Add a short feasibility step for all four shops: fetch one representative live product page, confirm the promo price is present in the response, capture the fixture and extraction target, select the HTTP/parser dependencies via `uv add`, and define handling for timeout, connection, TLS, redirect, and non-2xx failures. Add a live smoke criterion for each shop.
  - Strength: Resolves the highest-risk external integration before readers are built and makes dependency/file changes explicit.
  - Tradeoff: Shop blocking or client-side rendering may force a larger fetch strategy than plain HTTP.
  - Confidence: HIGH — the current repository has no dependency or existing pattern that answers these choices.
  - Blind spot: Shop anti-bot behavior may differ between local and Render IPs.
- **Decision**: PENDING

### F4 — Four single-shop commands are not all verified

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 4 — Automated Verification
- **Detail**: The plan creates four single-shop commands, but automated verification exercises only one unspecified single-shop command. A typo or wrong filter in any of the other three commands could ship while every criterion passes.
- **Fix**: Parameterize command tests across Rossmann, DOZ, Super-Pharm, and Gemini and assert each command records only its own shop.
- **Decision**: PENDING

### F5 — Shipping wording cites an obsolete contract

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Current State Analysis — Key Discoveries
- **Detail**: The plan says FR-008 requires price “after promo and shipping,” but the current PRD says shipping is not added. The implementation and brief follow the current PRD, while `roadmap.md` still contains stale “promo and shipping included” language. This terminology drift can mislead later slices even though this plan's intended amount is clear.
- **Fix**: Correct the Key Discovery to quote current FR-008 and update the roadmap's stale shipping wording before downstream plans use it.
- **Decision**: PENDING
