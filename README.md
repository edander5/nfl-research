# NFL Betting Research

**Status:** Foundation and schedule ingestion are complete according to owner-reported normal-WSL validation: 842 games imported, idempotent reimport, 78 passing tests. The approved [read-only schedule API](docs/schedule-api.md) is now implemented; new API runtime validation remains pending where this agent cannot access Docker or synchronous HTTP transport. No frontend yet.

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

Current approved scope is [Task 005: read-only schedule API](docs/agent-task-005.md). [Endpoint contracts, actual tests and WSL checks](docs/schedule-api.md) distinguish new API verification from the owner's prior results. [Schedule contract](docs/schedule-data-contract.md) and [original dataset validation](docs/schedule-validation-report.md) retain UNKNOWN-status, nonunique secondary-ID and declared-origin safeguards. Source authentication/checksum limitations remain unresolved. No frontend or subsequent feature task is authorized.

## Key constraints

- **$0/month for sports data APIs**, no unapproved paid services.
- Private, personal-use MVP; access restricted through Tailscale.
- Historical *pregame* statistics must exclude games occurring after the selected matchup; do not pretend today's reconstructed stats are contemporary publication-time snapshots.
- No bet tracking, prediction models, public accounts, or unsupported live features in MVP.
- Agent works in scoped tasks with owner approval gates. No autonomous deployment.
