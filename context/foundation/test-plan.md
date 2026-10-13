# Test Plan
> Phased test rollout for this project. Strategy is frozen at the top
> (§1–§5); cookbook patterns at the bottom (§6) fill in as phases ship.
> Read before writing any new test.
>
> Refresh: re-run `/10x-test-plan --refresh` when stale (see §8).
>
> Last updated: 2026-10-14

## 1. Strategy

Tests follow three non-negotiable principles for this project:

1. **Cost × signal.** The cheapest test that gives a real signal for the
   risk wins. Do not promote to e2e because e2e "feels safer." Do not put a
   vision model on top of a deterministic visual diff that already catches
   the regression.
2. **User concerns are first-class evidence.** Risks anchored in "the
   team is worried about X, and the failure would surface somewhere in
   an area" carry the same weight as PRD lines or hot-spot data.
3. **Risks are scenarios, not code locations.** This plan documents *what
   could fail* and *why we believe it's likely* — drawn from documents,
   interview, and codebase *signal* (churn, structure, test base). It does
   NOT claim to know which line owns the failure. That knowledge is
   produced by `/10x-research` during each rollout phase. If the plan and
   research disagree about where the failure lives, research is the
   ground truth.

Hot-spot scope used for likelihood weighting: `accounts/`, `prices/`,
`DataCollector/`; tests, migrations, fixtures, generated output, lockfiles,
and snapshots excluded.

## 2. Risk Map

The top failure scenarios this project must protect against, ordered by
risk = impact × likelihood. Sources are evidence, never code anchors.

| # | Risk (failure scenario) | Impact | Likelihood | Source (evidence — not anchor) |
|---|---|---|---|---|
| 1 | An unavailable intended product size causes another variant's plausible price to be stored silently | High | High | interview Q2; PRD lines 38–40 and 76–100 |
| 2 | Chart scale or points make historical dates and prices unreadable or misleading | High | High | interview Q1, Q3, Q4; hot-spot dirs `accounts/templates/` (9 commits/30d), `prices/templates/` (8 commits/30d) |
| 3 | An existing four-shop product cannot be managed safely through owner forms | Medium | High | interview Q1, Q3; PRD lines 111–136; archived edit-tracked-product plan |
| 4 | An authenticated but unauthorized user changes the tracked catalog or another user's favorites | High | Medium | PRD lines 117–126; hot-spot dirs `accounts/` (11 commits/30d), `prices/` (19 commits/30d) |
| 5 | A stale or wrong-calendar-day amount is presented as today's price | High | Medium | PRD lines 46 and 100–103; roadmap F-01; archived calendar-day-price plan |
| 6 | Editing or removing a shop page silently destroys price history or bypasses confirmation | High | Medium | interview Q3; archived edit-tracked-product plan; hot-spot dir `prices/` (19 commits/30d) |

Impact is High for lost access/data, a false buying decision, or a publicly
visible core-flow failure; Medium when a workaround exists. Likelihood is
High for a lived incident or frequently changed area, Medium for occasional
churn with existing protection, and Low for stable behavior.

### Risk Response Guidance

| Risk | What would prove protection | Must challenge | Context `/10x-research` must ground | Likely cheapest layer | Anti-pattern to avoid |
|---|---|---|---|---|---|
| #1 | The intended variant becoming unavailable produces a rejected read or gap, never another size's amount | A valid numeric price proves product identity | Variant identity, redirects/selection, fixture provenance, external boundary | contract + integration | happy-path fixtures only |
| #2 | Exact date/price remains readable for one to four shops, gaps, and extreme ranges at supported desktop sizes | Rendered SVG points imply human readability | Intended chart interaction, scale rules, browser states, independent readability oracle | browser e2e + scoped deterministic visual diff + manual smoke | broad meaningless snapshots or AI vision over deterministic checks |
| #3 | A four-shop record is either editable under an approved contract or refused clearly without writes or data loss | The current three-row form is safe because the PRD says two or three pages | Canonical page-count rule and form/model/admin parity | integration | silently reducing fixtures to three shops |
| #4 | Direct requests cannot cross role or ownership boundaries | Logged in means authorized | Actors, ownership relation, mutation entry points, response and persisted state | integration | testing only hidden controls |
| #5 | Local-day boundaries and gaps remain truthful around midnight and DST | Latest observation means today | Time source, timezone, write/read day boundaries | unit + integration | copying the production date calculation into the assertion |
| #6 | Same-shop URL edits retain history; destructive changes require confirmation; cross-product identifiers are denied | Database cascade plus a confirmation page is sufficient | Persistence identity, destructive boundary, rollback and confirmation state | integration | happy-path-only mutation tests |

## 3. Phased Rollout

Each row is a discrete rollout phase. Status is orchestrator-managed.

| # | Phase name | Goal (one line) | Risks covered | Test types | Status | Change folder |
|---|---|---|---|---|---|---|
| 1 | Price identity and calendar truth | Reject wrong variants and preserve truthful local-day prices | #1, #5 | contract + unit + integration | not started | — |
| 2 | Readable chart and safe form boundaries | Prove historical values are readable and four-shop records behave explicitly without data loss | #2, #3 | browser e2e + deterministic visual diff + integration + manual visual smoke | not started | — |
| 3 | Authorization and history retention | Prevent cross-role mutations and destructive history loss | #4, #6 | integration | not started | — |

Status vocabulary: `not started` → `change opened` → `researched` →
`planned` → `implementing` → `complete`.

## 4. Stack

The classic test base is meaningful: 17 Django test modules are spread
across `accounts/` and `prices/`.

| Layer | Tool | Version | Notes |
|---|---|---|---|
| unit + integration | Django DiscoverRunner, `TestCase`, test client | Django 6.1.1 | Existing default runner; no separate config required |
| network-edge contract | standard-library fakes and mocks plus saved HTML | Python 3.14 | Keep doubles at the shop/network boundary |
| browser/e2e | none installed yet — see §3 Phase 2 | — | Phase 2 selects and installs a small reproducible browser runner for chart/form behavior |
| visual regression | none installed yet — see §3 Phase 2 | — | Fixed-viewport baselines for selected chart/form states only |
| accessibility | none installed | — | Research may identify semantics checks, but no separate tool is committed |

**Stack grounding tools (current session):**
- Docs: no docs-specific MCP — official Django 6.1 testing docs checked through search; checked: 2026-10-14
- Search: Cursor Web Search — used to locate current official Django guidance; checked: 2026-10-14
- Runtime/browser: Cursor browser tool — available for Phase 2 verification, not a project dependency; checked: 2026-10-14
- Provider/platform: none used — infrastructure is deliberate negative space; checked: 2026-10-14

## 5. Quality Gates

| Gate | Where | Required? | Catches |
|---|---|---|---|
| targeted Django unit/integration tests | local | required now | focused logic, form, HTTP, and persistence regressions |
| full `uv run python manage.py test` suite | local | required now | cross-feature regressions |
| wrong-variant and calendar-boundary scenarios | local | required after §3 Phase 1 | silent price corruption and day drift |
| chart/form browser e2e matrix | local browser | required after §3 Phase 2 | unreadable history and unsafe four-shop behavior |
| scoped chart/form screenshot diff | local browser | required after §3 Phase 2 | unintended visual layout and scale regressions |
| authorization/destructive-mutation scenarios | local | required after §3 Phase 3 | ownership bypass and history loss |

No CI or deployment gate is planned; infrastructure is excluded by §7.

## 6. Cookbook Patterns

How to add new tests in this project. These entries fill in as phases ship.

### 6.1 Protecting product identity during price collection

TBD — see §3 Phase 1 for wrong-size/variant rejection and fixture-provenance
patterns.

### 6.2 Protecting local-day price truth

TBD — see §3 Phase 1 for midnight, DST, and intentional-gap patterns.

### 6.3 Testing chart readability and product-form boundaries

TBD — see §3 Phase 2 for exact historical-value readability, fixed-viewport
visual baselines, scale extremes, and four-shop no-write/data-retention
patterns.

### 6.4 Testing authorization and destructive mutations

TBD — see §3 Phase 3 for direct-request ownership, confirmation, rollback,
and retained-history patterns.

## 7. What We Deliberately Don't Test

- **Infrastructure, hosting, deployment, and CI behavior** — product-risk
  coverage has higher value for this rollout. Re-evaluate when production
  deployment becomes active scope or an environment-specific incident
  occurs. (Source: Phase 2 interview Q5.)

## 8. Freshness Ledger

- Strategy (§1–§5) last reviewed: 2026-10-14
- Stack versions last verified: 2026-10-14
- AI-native tool references last verified: 2026-10-14

Refresh (`/10x-test-plan --refresh`) when:

- a new top-3 risk surfaces from the roadmap or archive,
- a recommended tool's `checked:` date is older than three months,
- the project's tech stack changes,
- §7 negative-space no longer matches what the team believes.
