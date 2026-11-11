# NFL Betting Research

**Status:** Owner reports foundation, ingestion, read-only API and dashboard completed/merged, with 842 imported games and the prior 139-test backend suite validated. The approved [guarded manual refresh runner](docs/schedule-refresh.md) is implemented; fresh-source and new PostgreSQL runtime checks remain blocked in this agent environment. No unattended scheduler is active.

A private, self-hosted, NFL statistics and player-prop research web app. The first working vertical slice is a 2024–2026 weekly NFL schedule, backed by real imported data in PostgreSQL and served by FastAPI to React.

## Read this first

1. `docs/product-requirements.md` — what the MVP is and is not.
2. `docs/architecture.md` — chosen stack, service boundaries, security, operations.
3. `docs/data-sources.md` — *preliminary* public-source findings, remaining validation, provider distinctions.
4. `docs/data-model.md` — conceptual records, identities, cutoffs, and statistical conventions.
5. `docs/implementation-plan.md` — vertical slices, dependencies, acceptance criteria and gates.
6. `docs/decisions.md` — binding decisions and change-control policy.
7. `docs/agent-task-001.md` — first **research-only** task for a coding agent.
8. `AGENTS.md` — explicit instructions for agents; no unauthorized implementation.

The first agent task is **source feasibility**, not application development. Source references were checked on **2026-11-04**; public documentation may change. The provisional data sources and sample route names are not contractual until verified.

That first research task and subsequent CSV validation, [foundation/schema](docs/agent-task-002.md), [environment validation](docs/agent-task-003.md) and [schedule ingestion](docs/agent-task-004.md) are complete. The original CSV remains unchanged. The owner reports successful development import and normal-WSL tests; historical agent environment failures remain recorded in the task reports.

The guarded refresh scope is recorded in [Task 007](docs/agent-task-007.md). The owner reports the [current-week default](docs/agent-task-008.md) and freshness indicator complete. Current approved work is [Task 010 guarded statistics storage](docs/agent-task-010.md); development migration/import remain separately gated. The [refresh guide](docs/schedule-refresh.md) documents dry-run, snapshot-specific review/apply, hard blockers and exact WSL verification commands. Source authentication/checksum and unsupported finality limitations remain governed by the [schedule data contract](docs/schedule-data-contract.md). No unattended updates, ranking publication, unrelated statistics features or deployment are authorized.

Development startup after completing the frontend checks in the guide:

```bash
docker compose up -d --build --wait db api frontend
```

Visit http://127.0.0.1:5173. Full install/test/build commands, limitations and changed files: [dashboard guide](docs/schedule-dashboard.md).

## Key constraints

- **$0/month for sports data APIs**, no unapproved paid services.
- Private, personal-use MVP; access restricted through Tailscale.
- Historical *pregame* statistics must exclude games occurring after the selected matchup; do not pretend today's reconstructed stats are contemporary publication-time snapshots.
- No bet tracking, prediction models, public accounts, or unsupported live features in MVP.
- Agent works in scoped tasks with owner approval gates. No autonomous deployment.


## Schedule data freshness

The dashboard now includes manual refresh history via GET `/api/data-status/schedule`. See [contract, commands and verification](docs/schedule-freshness.md). No background updates are activated.


## Guarded team-statistics storage

Current approved task: [Task 010](docs/agent-task-010.md), PostgreSQL storage and guarded manual statistics ingestion after the 705-pair offline audit. [Schema, exact WSL commands, tests and review gates](docs/team-stats-ingestion.md). Implementation is written; no development migration or real statistics import has been executed. Existing schedule APIs/dashboard/refresh behavior are unchanged.

Current Task 010 security review follow-up: [hardening implementation, isolated restricted-role tests, explicit existing-volume transition and NO-GO gate](docs/team-stats-security-hardening.md). Normal runtime credentials are now separate from bootstrap administration; do not use the API to run migrations. No development role provisioning/migration/import has been executed.

## Task 011 — accepted team statistics API

Owner reports Task 010 merged, 705 accepted pairs/1,410 rows imported, migration 0002 and restricted roles validated with 343 WSL tests. [Task 011 API, approved column grants, exact owner commands and test results](docs/team-stats-api.md) supersedes the earlier pending-ingestion status above. No real ingestion or development grants are executed by the agent in this task.

## Task 012 — reconstructed season rankings

Owner reports Task 011 merged and verified with 374 passing WSL tests and live read-only endpoints. Current work is the [read-only rankings engine/API](docs/team-rankings-api.md), using existing accepted statistics and grants. No frontend, historical pregame eligibility, schema/permission changes or new ingestion is included.

## Team rankings dashboard — Task 013

Owner reports the rankings engine/API merged and verified. Open `/rankings` for the [frontend rankings dashboard and lightweight team game logs](docs/team-rankings-dashboard.md), with URL filters, authoritative ranks, responsive tables and explicit coverage. This task changes no backend/data/permissions. The guide records actual frontend tests/builds and remaining live/browser checks.
