---
project: Data Collector
version: 1
status: active
created: 2026-09-23
updated: 2026-09-23
tracker: github-issues
repo: MartBur/Data-collector
milestone_id: restock-from-history
source: context/foundation/roadmap.md
---

# Tasks: GitHub Issues

> Task tracker for Data Collector. The roadmap in `context/foundation/roadmap.md` stays the source of slice order and status. This file records how that roadmap is mirrored on GitHub.
> Edit-in-place; archive when superseded.

## Tracker

GitHub Issues on [MartBur/Data-collector](https://github.com/MartBur/Data-collector), managed with `gh`. There is no Jira or Linear project. Parked non-goals, baseline notes, and vision stay in the roadmap and are not issues.

Active work for the open milestone lives on one GitHub milestone with no due date: [M-1: Restock from history](https://github.com/MartBur/Data-collector/milestone/1).

## Issue format

**Title:** `<Roadmap ID>: <Suggested issue title>`

Examples: `S-01: Signed-in user can sign in`, `Decision: Which shops are in the fixed set?`

**Labels:**

- Kind: `foundation` or `slice`. A blocking open question uses the existing `question` label.
- Roadmap status: `ready`, `blocked`, or `proposed`, copied from the roadmap Status column.

**Body** (same headings on every slice and foundation):

- Roadmap ID, Change ID, status, PRD refs, ready-for-plan (`yes` only when `/10x-plan` can run)
- Outcome
- Prerequisites, Parallel with
- Unknowns (owner, and whether they block)
- Risk
- Source: `context/foundation/roadmap.md`, milestone `restock-from-history`

**Dependencies:** GitHub blocked-by links, set from Prerequisites. A decision issue is an extra blocker when an open question gates that slice.

## M-1 issues

| Roadmap ID | Change ID                 | Status   | Issue |
| ---------- | ------------------------- | -------- | ----- |
| F-01       | calendar-day-landed-price | blocked  | [#5](https://github.com/MartBur/Data-collector/issues/5) |
| S-01       | account-sign-in           | ready    | [#6](https://github.com/MartBur/Data-collector/issues/6) |
| S-02       | add-tracked-product       | blocked  | [#7](https://github.com/MartBur/Data-collector/issues/7) |
| S-03       | product-card-decision     | blocked  | [#8](https://github.com/MartBur/Data-collector/issues/8) |
| S-04       | favorites-lowest-today    | proposed | [#9](https://github.com/MartBur/Data-collector/issues/9) |
| S-05       | edit-tracked-product      | proposed | [#10](https://github.com/MartBur/Data-collector/issues/10) |
| —          | shop-set decision         | question | [#11](https://github.com/MartBur/Data-collector/issues/11) |

[#6](https://github.com/MartBur/Data-collector/issues/6) is the only issue with no blockers. [#11](https://github.com/MartBur/Data-collector/issues/11) blocks F-01, S-02, and S-03. The timezone question is non-blocking and lives in the F-01 and S-04 bodies.

Blocked-by edges:

- F-01 ← decision
- S-02 ← S-01, decision
- S-03 ← S-01, S-02, F-01, decision
- S-04 ← S-01, S-02, F-01
- S-05 ← S-02
