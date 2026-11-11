# Task 010 — PostgreSQL team statistics storage and guarded ingestion

Owner-approved branch: `feature/team-stats-ingestion`.

The owner reports successful audit `data/raw/team-stats-audit/audit-5b23716443d34c33b89818c30f3f524c.json`: 285/285/135 games, 705 pairs and 1,410 team rows; canonical UUID reconciliation and independently referenced negative sack convention passed.

Implement additive SQLAlchemy/Alembic statistics storage with canonical UUIDs, artifact/batch provenance, immutable/versioned two-team revisions, accepted selection and correction history. NET passing is gross plus original negative sack adjustment; retain both inputs. Derive allowed yards from the accepted opponent, preserve null/zero/negative distinctions and require complete accepted pairs.

Revalidate the offline contract, bytes, receipts/references and live identities. Dry-run first; changing applies require exact review tokens bound to inputs, differences and current database baseline. One transaction publishes both sides/all changed pairs; missing/inconsistent snapshots cannot damage history. Provide reviewed logical rollback to existing prior revisions without deleting history. Add unit/integration compatibility tests and exact normal-WSL commands.

Do not execute development migrations, real imports, corrections or rollbacks without separate owner approval. No schedule schema/status/ingestion/refresh behavior changes, completed-before-kickoff eligibility, rankings, endpoints, frontend, jobs, odds, player features, dependencies or deployment. No commit/merge/push.

Schema/workflow proposal was explained before implementation. [Complete design, runbook, test evidence, file inventory and review gate](team-stats-ingestion.md). Stop for owner review.
