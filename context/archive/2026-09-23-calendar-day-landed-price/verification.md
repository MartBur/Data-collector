# Manual verification

| Item | Scenario | Commit | Observed result |
|------|----------|--------|-----------------|
| 1.3 | Admin accepts one page per shop and rejects a second page for the same shop | c4ed0bb | Not recorded in the commit. |
| 1.4 | Admin rejects a URL whose host does not match the chosen shop | c4ed0bb | Not recorded in the commit. |
| 3.2 | A live page that no longer matches its saved HTML is checked by hand before the fixture is updated | 74d68c8 | Not recorded in the commit. |
| 4.2 | `record_prices` stores today's amount for a product entered in admin | 8dfd089 | Not recorded in the commit. |
| 4.3 | `record_rossmann_prices` leaves other shops untouched | 8dfd089 | Not recorded in the commit. |
| 4.4 | Running that shop command again with an unchanged price adds no row | 8dfd089 | Not recorded in the commit. |
