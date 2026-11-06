# Task 001 feasibility results

**2026-11-05 — audit delivered with explicit verification gaps; awaiting owner review.** Full evidence and URLs: [data-sources.md](data-sources.md).

**Current assessment after local validation:** **B. CONDITIONALLY READY** for a separately approved Milestone 1 task, under the owner-approved limited status contract (Decision 53). Actual counts are 285/285/272 unique games across 2024/2025/2026. Primary integrity checks pass; eight nonunique secondary IDs and unmatched release provenance require documented safeguards. See [validation report](schedule-validation-report.md) and [contract section 12](schedule-data-contract.md#12-local-artifact-validation-and-approved-status-limitation--2026-11-05). Earlier blocked recommendations below are historical. No implementation began.

**Final schedule readiness report:** see [Schedule Contract section 11](schedule-data-contract.md#11-final-readiness-assessment--2026-11-05). Integrity is **Blocked**, status/finality **Partially resolved**, release-route licensing **Resolved** based on the official organization grant. Recommendation **C. BLOCKED** pending complete artifact verification and an explicit owner decision on unsupported status/final evidence. This supersedes historical schedule licensing and follow-up recommendations below; no additional general research task is proposed.

**Subsequent approved research:** Schedule Contract Closure is documented in [schedule-data-contract.md](schedule-data-contract.md). It confirms official release download alternatives at metadata/documentation level, but does not claim successful full-file verification or approve implementation. The original audit below remains the Task 001 record.

**Recommendation: no-go for Milestone 1 implementation approval today.** Schedule feasibility is promising, but applicable schedule rights, full-file integrity and authoritative status/completion evidence remain unresolved. This does not establish that nflverse is unusable. Approve a narrow source-contract research follow-up before scaffolding or schema implementation.

| Area | Finding / implication |
|---|---|
| 2024/2025 schedule | Actual REG/postseason samples inspected; exhaustive counts and integrity unresolved |
| Partial 2026 | Opening-game scores and future REG rows inspected; returned file ends at REG week 18; no fabricated POST matchups |
| Schedule fields | `game_id`, `season`, `week`, `game_type`, home/away teams/scores, `gameday`, `gametime`; Eastern time needs UTC conversion; status/completion evidence absent |
| Team yardage | Candidate `passing_yards`, `rushing_yards`; matched opponent offense supplies allowed yards; approve gross/net passing and reconcile sacks |
| Appearance/transfers | Snap counts offer candidate evidence, but crosswalks, played-zero coverage and transfer examples remain unverified |
| Injuries/depth | Current assets and documented practice/designation/unit fields exist; row freshness, all-team coverage and upstream rights remain partial |
| Optional odds | Hyphenated provider documents free props and retention permission; authenticated coverage/costs untested; manual lines remain usable |

All ten requested fields have documentation support. Each season status below means **Partial**, not verified rows or completeness:

| Market | nflverse field | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| Passing yards | `passing_yards` | Partial | Partial | Partial |
| Passing attempts | `attempts` | Partial | Partial | Partial |
| Passing completions | `completions` | Partial | Partial | Partial |
| Passing TDs | `passing_tds` | Partial | Partial | Partial |
| Rushing yards | `rushing_yards` | Partial | Partial | Partial |
| Rushing attempts | `carries` | Partial | Partial | Partial |
| Rushing TDs | `rushing_tds` | Partial | Partial | Partial |
| Receiving yards | `receiving_yards` | Partial | Partial | Partial |
| Receptions | `receptions` | Partial | Partial | Partial |
| Receiving TDs | `receiving_tds` | Partial | Partial | Partial |

Documented joins use GSIS `player_id`, team/opponent, season/week and REG/POST. Actual unique game mapping and transfer rows still require tests. Unknown eligibility stays unknown; no missing-to-zero inference is approved.

Before schema work, review a concrete schedule contract addressing rights, source integrity, final/status evidence, unknown kickoff handling and unpublished 2026 postseason. Preserve completed-before-kickoff cutoffs: kickoff plus scores does not establish another game's finish time. Before rankings, approve gross versus net passing. Before hit rates, prove appearance denominators. Current injury/depth observations cannot substitute for historical snapshots.

The preliminary odds claim changed: the unhyphenated domain redirects to Betting Data API, whose free tier includes NFL moneylines but excludes props. No provider substitution or free-key test was performed.

## Work and verification report

- Read AGENTS.md, README.md and project Markdown documentation under docs/.
- Inspected official loaders/dictionaries, raw schedule header/representative rows, release asset metadata, provider pricing/markets/terms and license evidence.
- Full-file retrieval failed through local DNS or web release redirects. No exhaustive counts, local hash checks, statistical reconciliation or authenticated API test completed. No application tests were applicable or run.
- Files changed: replaced `docs/data-sources.md` with evidence-qualified findings; created `docs/feasibility-results.md` for review. Architecture/decision register unchanged because no new decision is approved.
- No application code, dependencies, initialization, services, migrations, accounts, credentials, paid actions or deployments. Git status failed because the workspace is not a Git repository; no Git diff check is claimed.

**Next proposed task, for approval only:** research-only schedule source-contract closure. Inspect complete 2024–2026 artifacts, document counts/integrity and rights, and propose evidence-backed status/time/unknown-value mappings. Deliver documents and stop again before Milestone 1 implementation.
