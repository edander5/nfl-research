# NFL Betting Research

**Status:** Milestone 1 foundation/schema written; Compose configuration now validates. Runtime checks are blocked by this agent process's Docker/network socket denials and missing dependencies; host Docker/DNS health outside the agent remains unconfirmed. See [current recovery results](docs/runtime-validation.md) and [development setup](docs/development.md). No schedule importer or frontend yet.

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

That first research task and subsequent local CSV validation are complete. The owner approved foundation/schema work only; current scope is recorded in [Task 002](docs/agent-task-002.md). [Schedule contract](docs/schedule-data-contract.md) and [actual validation report](docs/schedule-validation-report.md) define the UNKNOWN-status, nonunique secondary-ID and declared-origin safeguards. The original CSV is unchanged and not imported. Start/test commands and schema tradeoffs are in [docs/development.md](docs/development.md); implementation beyond this task still needs approval.

The subsequent approved [Task 003](docs/agent-task-003.md) covers environment recovery and runtime validation only. It does not authorize ingestion. No system/Docker/WSL setting was changed; normal-terminal Docker/DNS checks are pending before recommending such changes.

## Key constraints

- **$0/month for sports data APIs**, no unapproved paid services.
- Private, personal-use MVP; access restricted through Tailscale.
- Historical *pregame* statistics must exclude games occurring after the selected matchup; do not pretend today's reconstructed stats are contemporary publication-time snapshots.
- No bet tracking, prediction models, public accounts, or unsupported live features in MVP.
- Agent works in scoped tasks with owner approval gates. No autonomous deployment.
