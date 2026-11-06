# Agent Task 001 — Read-Only NFL Data-Source Feasibility Audit

**Type:** Research and documentation only. **No application code.** **Owner approval required before Task 002.**

## Prompt to give your coding agent

You are the technical research engineer for a private NFL sports betting research application. Read `AGENTS.md`, `docs/product-requirements.md`, `docs/data-model.md`, `docs/architecture.md`, and `docs/data-sources.md` first. You must work **only** on the preliminary data-source feasibility audit and report findings; do not initialize a React/FastAPI project, write application code, install packages, run migrations, create API accounts, spend money, access secrets, scrape restricted sites, or deploy anything.

The MVP requires real 2024–2026 schedules (REG + POST), passing/rushing offense and defense yardage statistics, ten player-stat markets, team-wide injuries/practice statuses and full depth charts where possible, and optional current NFL player-prop odds with a strict $0/month data API budget. Manual prop-line entry is an acceptable fallback for odds. Historical pregame rankings must exclude future games; missing values and DNP are not zero results.

**Research tasks**

1. Review official nflverse release documentation and actual publicly accessible asset schemas for 2024, 2025, and current partial 2026 season. Check schedules' home/away, season/week/stage, UTC kickoff, game status, score and stable identifiers.
2. Identify the concrete release files and columns needed for team passing/rushing yards gained and allowed per game, and for all ten requested player stats. Check weekly granularity, availability per season, completeness, and team/player IDs.
3. Investigate player appearance/DNP evidence and transfers; determine whether data supports accurate hit-rate denominators including actual played-zero games.
4. Inspect injury and depth-chart sources, including practice status, game designation, timestamps, offense/defense/special-teams coverage, source update cadence, and whether data is actually current.
5. Distinguish **The Odds API** (`the-odds-api.com`, hyphenated) from **TheOddsAPI** (`theoddsapi.com`, unhyphenated). Verify free NFL props availability, supported markets and sportsbooks, usage-credit costs, legal caching/retention and any new terms. Do not make authenticated requests unless the owner separately approves a free-key test. Never enroll in a paid plan.
6. Document licensing, redistribution/attribution, limitations of future public release, sample provenance and any unresolved rights questions.
7. Identify alternatives for missing data, but do not silently change chosen providers or introduce costs.

**Evidence required for every dataset:** Official URL, retrieval date, actual sample/release asset when examined, fields/season coverage, IDs/join keys, format, cadence, known gaps, license or terms, risk level and confidence. Clearly distinguish a documentation claim from a successful sample-data verification. Never guess data counts or field names.

**Deliverables**

- Update `docs/data-sources.md` with a source matrix labeled **Verified / Partial / Blocked / Not yet tested**.
- Create a concise **feasibility-results.md** (under `docs/`) listing concrete field mappings and unresolved high-risk assumptions (only if research is actually performed).
- Recommend **go/no-go for Milestone 1** and any specific user decision needed before database schema implementation.
- Report URLs and findings, limitations, all files changed, verification actually performed, and next proposed task. Stop for review.

**Acceptance criteria**

- The 2024/2025/2026 schedule feasibility question is answered with evidence or explicitly marked unresolved.
- All ten player markets have a field-level support status, not a blanket assumption.
- Team defensive yardage definitions and participation eligibility are explicitly addressed.
- Injury/depth chart completeness, temporal freshness, and data-use rights are considered.
- Free NFL odds provider distinction and budget risks are correctly described.
- No code, installs, service setup, accounts, paid actions, secret changes or production changes were performed.
