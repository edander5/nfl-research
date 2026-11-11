"""Additive versioned team statistics, guarded pair selection and append-only history.

Frozen PostgreSQL DDL; no schedule DDL or data backfill.
"""
from alembic import op

revision = "0002_team_stats"
down_revision = "0001_schedule"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""DO $$ BEGIN
        IF current_user <> 'nfl_owner' THEN
            RAISE EXCEPTION 'Run migrations as the dedicated nfl_owner role';
        END IF;
    END $$""")
    op.execute("""
CREATE TABLE team_stats_batches (
	id UUID NOT NULL,
	kind TEXT NOT NULL,
	candidate_sha256 TEXT NOT NULL,
	review_token TEXT NOT NULL,
	evidence JSONB NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_team_stats_batches PRIMARY KEY (id),
	CONSTRAINT ck_team_stats_batches_kind CHECK (kind IN ('IMPORT', 'ROLLBACK')),
	CONSTRAINT ck_team_stats_batches_evidence_object CHECK (jsonb_typeof(evidence) = 'object'),
	CONSTRAINT ck_team_stats_batches_candidate_hash CHECK (candidate_sha256 ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_team_stats_batches_review_token CHECK (review_token ~ '^[0-9a-f]{64}$')
)
""")
    op.execute("""
CREATE TABLE team_stats_pairs (
	id UUID NOT NULL,
	game_id UUID NOT NULL,
	home_team_id UUID NOT NULL,
	away_team_id UUID NOT NULL,
	batch_id UUID NOT NULL,
	source_artifact_id UUID NOT NULL,
	previous_pair_id UUID,
	definition_version TEXT NOT NULL,
	content_sha256 TEXT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_team_stats_pairs PRIMARY KEY (id),
	CONSTRAINT uq_team_stats_pairs_id_game UNIQUE (id, game_id),
	CONSTRAINT uq_team_stats_pairs_batch_game UNIQUE (batch_id, game_id),
	CONSTRAINT fk_team_stats_pairs_previous FOREIGN KEY(previous_pair_id, game_id) REFERENCES team_stats_pairs (id, game_id) ON DELETE RESTRICT,
	CONSTRAINT ck_team_stats_pairs_distinct_sides CHECK (home_team_id != away_team_id),
	CONSTRAINT ck_team_stats_pairs_definition CHECK (definition_version = 'net_pass_negative_sacks_v1'),
	CONSTRAINT ck_team_stats_pairs_content_hash CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
	CONSTRAINT fk_team_stats_pairs_game_id_games FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_pairs_home_team_id_teams FOREIGN KEY(home_team_id) REFERENCES teams (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_pairs_away_team_id_teams FOREIGN KEY(away_team_id) REFERENCES teams (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_pairs_batch_id_team_stats_batches FOREIGN KEY(batch_id) REFERENCES team_stats_batches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_pairs_source_artifact_id_source_artifacts FOREIGN KEY(source_artifact_id) REFERENCES source_artifacts (id) ON DELETE RESTRICT
)
""")
    op.execute('CREATE INDEX ix_team_stats_pairs_batch_id ON team_stats_pairs (batch_id)')
    op.execute('CREATE INDEX ix_team_stats_pairs_game_id ON team_stats_pairs (game_id)')
    op.execute("""
CREATE TABLE team_game_stat_revisions (
	pair_id UUID NOT NULL,
	team_id UUID NOT NULL,
	game_id UUID NOT NULL,
	opponent_team_id UUID NOT NULL,
	side TEXT NOT NULL,
	gross_passing_yards INTEGER,
	original_sack_yards INTEGER,
	net_passing_yards INTEGER,
	rushing_yards INTEGER,
	source_record_sha256 TEXT NOT NULL,
	source_line INTEGER NOT NULL,
	raw_source_record JSONB NOT NULL,
	CONSTRAINT pk_team_game_stat_revisions PRIMARY KEY (pair_id, team_id),
	CONSTRAINT uq_team_game_stat_revisions_pair_side UNIQUE (pair_id, side),
	CONSTRAINT fk_team_game_stat_revisions_pair_game FOREIGN KEY(pair_id, game_id) REFERENCES team_stats_pairs (id, game_id) ON DELETE RESTRICT,
	CONSTRAINT ck_team_game_stat_revisions_side CHECK (side IN ('HOME', 'AWAY')),
	CONSTRAINT ck_team_game_stat_revisions_distinct_sides CHECK (team_id != opponent_team_id),
	CONSTRAINT ck_team_game_stat_revisions_negative_sacks CHECK (original_sack_yards IS NULL OR original_sack_yards <= 0),
	CONSTRAINT ck_team_game_stat_revisions_net_identity CHECK (((gross_passing_yards IS NULL OR original_sack_yards IS NULL) AND net_passing_yards IS NULL) OR (gross_passing_yards IS NOT NULL AND original_sack_yards IS NOT NULL AND net_passing_yards IS NOT NULL AND net_passing_yards::bigint = gross_passing_yards::bigint + original_sack_yards::bigint)),
	CONSTRAINT ck_team_game_stat_revisions_record_hash CHECK (source_record_sha256 ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_team_game_stat_revisions_source_line CHECK (source_line >= 2),
	CONSTRAINT ck_team_game_stat_revisions_raw_object CHECK (jsonb_typeof(raw_source_record) = 'object'),
	CONSTRAINT fk_team_game_stat_revisions_team_id_teams FOREIGN KEY(team_id) REFERENCES teams (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_game_stat_revisions_game_id_games FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_game_stat_revisions_opponent_team_id_teams FOREIGN KEY(opponent_team_id) REFERENCES teams (id) ON DELETE RESTRICT
)
""")
    op.execute('CREATE INDEX ix_team_game_stat_revisions_game_id ON team_game_stat_revisions (game_id)')
    op.execute("""
CREATE TABLE team_stats_selection_events (
	id UUID NOT NULL,
	batch_id UUID NOT NULL,
	game_id UUID NOT NULL,
	generation INTEGER NOT NULL,
	before_pair_id UUID,
	after_pair_id UUID NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_team_stats_selection_events PRIMARY KEY (id),
	CONSTRAINT uq_team_stats_selection_events_batch_game UNIQUE (batch_id, game_id),
	CONSTRAINT uq_team_stats_selection_events_game_generation UNIQUE (game_id, generation),
	CONSTRAINT ck_team_stats_selection_events_generation CHECK (generation >= 1),
	CONSTRAINT fk_team_stats_selection_events_before FOREIGN KEY(before_pair_id, game_id) REFERENCES team_stats_pairs (id, game_id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_selection_events_after FOREIGN KEY(after_pair_id, game_id) REFERENCES team_stats_pairs (id, game_id) ON DELETE RESTRICT,
	CONSTRAINT ck_team_stats_selection_events_changed_pair CHECK (before_pair_id IS NULL OR before_pair_id != after_pair_id),
	CONSTRAINT fk_team_stats_selection_events_batch_id_team_stats_batches FOREIGN KEY(batch_id) REFERENCES team_stats_batches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_selection_events_game_id_games FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE RESTRICT
)
""")
    op.execute('CREATE INDEX ix_team_stats_selection_events_game_id ON team_stats_selection_events (game_id)')
    op.execute("""
CREATE TABLE team_stats_accepted (
	game_id UUID NOT NULL,
	pair_id UUID NOT NULL,
	batch_id UUID NOT NULL,
	generation INTEGER NOT NULL,
	CONSTRAINT pk_team_stats_accepted PRIMARY KEY (game_id),
	CONSTRAINT fk_team_stats_accepted_pair_game FOREIGN KEY(pair_id, game_id) REFERENCES team_stats_pairs (id, game_id) ON DELETE RESTRICT,
	CONSTRAINT ck_team_stats_accepted_generation CHECK (generation >= 1),
	CONSTRAINT fk_team_stats_accepted_game_id_games FOREIGN KEY(game_id) REFERENCES games (id) ON DELETE RESTRICT,
	CONSTRAINT fk_team_stats_accepted_batch_id_team_stats_batches FOREIGN KEY(batch_id) REFERENCES team_stats_batches (id) ON DELETE RESTRICT
)
""")
    op.execute('CREATE INDEX ix_team_game_stat_revisions_team_id ON team_game_stat_revisions (team_id)')
    op.execute("""
CREATE FUNCTION team_stats_append_only() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    RAISE EXCEPTION 'Team statistics history is append-only' USING ERRCODE = '23514';
END $$
""")
    for table in ('team_stats_batches', 'team_stats_pairs', 'team_game_stat_revisions', 'team_stats_selection_events'):
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION team_stats_append_only()')
    op.execute("""
CREATE FUNCTION team_stats_check_pair() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.games g WHERE g.id = NEW.game_id
                   AND g.home_team_id = NEW.home_team_id AND g.away_team_id = NEW.away_team_id)
       OR NOT EXISTS (SELECT 1 FROM public.source_artifacts a WHERE a.id = NEW.source_artifact_id AND a.provider = 'nflverse') THEN
        RAISE EXCEPTION 'Statistics pair canonical membership or source mismatch' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER team_stats_pair_membership BEFORE INSERT ON team_stats_pairs FOR EACH ROW EXECUTE FUNCTION team_stats_check_pair()')
    op.execute("""
CREATE FUNCTION team_stats_check_team() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.team_stats_pairs p WHERE p.id = NEW.pair_id AND p.game_id = NEW.game_id
                   AND ((NEW.side = 'HOME' AND NEW.team_id = p.home_team_id AND NEW.opponent_team_id = p.away_team_id)
                        OR (NEW.side = 'AWAY' AND NEW.team_id = p.away_team_id AND NEW.opponent_team_id = p.home_team_id))) THEN
        RAISE EXCEPTION 'Statistics team/opponent mismatch' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER team_stats_team_membership BEFORE INSERT ON team_game_stat_revisions FOR EACH ROW EXECUTE FUNCTION team_stats_check_team()')
    op.execute("""
CREATE FUNCTION public.team_stats_lock_selection() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(202426, 1);
    RETURN NULL;
END $$
""")
    op.execute('CREATE TRIGGER team_stats_selection_lock BEFORE INSERT OR UPDATE OR DELETE ON team_stats_accepted FOR EACH STATEMENT EXECUTE FUNCTION public.team_stats_lock_selection()')
    op.execute("""
CREATE FUNCTION public.team_stats_check_selection() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    previous uuid;
    pair_batch uuid;
    pair_previous uuid;
    batch_kind text;
BEGIN
    -- All writers, including independent SQL clients, serialize with schedule ingestion.
    PERFORM pg_catalog.pg_advisory_xact_lock(202426, 1);
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Accepted statistics cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        previous := OLD.pair_id;
        IF NEW.game_id != OLD.game_id OR NEW.generation != OLD.generation + 1 OR NEW.pair_id = OLD.pair_id
           OR NOT EXISTS (SELECT 1 FROM public.team_stats_selection_events e WHERE e.game_id = OLD.game_id
                          AND e.generation = OLD.generation AND e.after_pair_id = OLD.pair_id AND e.batch_id = OLD.batch_id)
           OR (SELECT max(e.generation) FROM public.team_stats_selection_events e WHERE e.game_id = OLD.game_id) != OLD.generation THEN
            RAISE EXCEPTION 'Invalid acceptance chain or generation' USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.generation != 1 OR EXISTS (SELECT 1 FROM public.team_stats_selection_events WHERE game_id = NEW.game_id) THEN
        RAISE EXCEPTION 'Initial selection must begin a new chain' USING ERRCODE = '23514';
    END IF;
    PERFORM 1 FROM public.games WHERE id = NEW.game_id FOR UPDATE;
    IF NOT EXISTS (SELECT 1 FROM public.team_stats_pairs p JOIN public.games g ON g.id = p.game_id
                   WHERE p.id = NEW.pair_id AND p.game_id = NEW.game_id
                   AND p.home_team_id = g.home_team_id AND p.away_team_id = g.away_team_id)
       OR (SELECT count(*) FROM public.team_game_stat_revisions r WHERE r.pair_id = NEW.pair_id) != 2
       OR EXISTS (SELECT 1 FROM public.team_game_stat_revisions r WHERE r.pair_id = NEW.pair_id
                  AND (r.gross_passing_yards IS NULL OR r.original_sack_yards IS NULL
                       OR r.net_passing_yards IS NULL OR r.rushing_yards IS NULL)) THEN
        RAISE EXCEPTION 'Accepted selection requires two complete canonical sides' USING ERRCODE = '23514';
    END IF;
    SELECT kind INTO batch_kind FROM public.team_stats_batches WHERE id = NEW.batch_id;
    SELECT batch_id, previous_pair_id INTO pair_batch, pair_previous FROM public.team_stats_pairs WHERE id = NEW.pair_id;
    IF batch_kind IS NULL
       OR (batch_kind = 'IMPORT' AND (pair_batch != NEW.batch_id OR pair_previous IS DISTINCT FROM previous))
       OR (batch_kind = 'ROLLBACK' AND (TG_OP != 'UPDATE' OR NOT EXISTS (
            SELECT 1 FROM public.team_stats_selection_events e WHERE e.game_id = NEW.game_id
              AND e.after_pair_id = NEW.pair_id AND e.generation < NEW.generation))) THEN
        RAISE EXCEPTION 'Target is not a valid import or previously accepted rollback revision' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER team_stats_selection_guard BEFORE INSERT OR UPDATE OR DELETE ON team_stats_accepted FOR EACH ROW EXECUTE FUNCTION public.team_stats_check_selection()')
    op.execute("""
CREATE FUNCTION public.team_stats_record_selection() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF TG_TABLE_SCHEMA <> 'public' OR TG_TABLE_NAME <> 'team_stats_accepted' OR TG_WHEN <> 'AFTER' THEN
        RAISE EXCEPTION 'Acceptance history is trigger managed' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.team_stats_selection_events(id, batch_id, game_id, generation, before_pair_id, after_pair_id)
    VALUES (pg_catalog.gen_random_uuid(), NEW.batch_id, NEW.game_id, NEW.generation,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.pair_id ELSE NULL END, NEW.pair_id);
    RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER team_stats_selection_record AFTER INSERT OR UPDATE ON team_stats_accepted FOR EACH ROW EXECUTE FUNCTION public.team_stats_record_selection()')
    for function in ('team_stats_append_only', 'team_stats_check_pair', 'team_stats_check_team',
                     'team_stats_check_selection', 'team_stats_record_selection', 'team_stats_lock_selection'):
        op.execute(f'REVOKE ALL ON FUNCTION public.{function}() FROM PUBLIC, nfl_api, nfl_ingest')
    op.execute('REVOKE ALL ON team_stats_batches, team_stats_pairs, team_game_stat_revisions, team_stats_accepted, team_stats_selection_events FROM PUBLIC, nfl_api, nfl_ingest')
    op.execute('GRANT SELECT, INSERT ON team_stats_batches, team_stats_pairs, team_game_stat_revisions, team_stats_accepted TO nfl_ingest')
    op.execute('GRANT UPDATE (pair_id, batch_id, generation) ON team_stats_accepted TO nfl_ingest')
    op.execute('GRANT SELECT ON team_stats_selection_events TO nfl_ingest')


def downgrade():
    # Destructive removal is available only through separately approved Alembic downgrade.
    for table in ('team_stats_accepted', 'team_stats_selection_events', 'team_game_stat_revisions', 'team_stats_pairs', 'team_stats_batches'):
        op.drop_table(table)
    for function in ('team_stats_record_selection', 'team_stats_lock_selection', 'team_stats_check_selection', 'team_stats_check_team', 'team_stats_check_pair', 'team_stats_append_only'):
        op.execute(f'DROP FUNCTION {function}()')
