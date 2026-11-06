"""Initial schedule foundation; no seed data or CSV ingestion.

Revision ID: 0001_schedule
Revises: None
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_schedule"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("code", name=op.f("uq_teams_code")),
    )
    op.create_table(
        "team_aliases",
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("source_team_code", sa.Text(), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("provider", "source_team_code", name=op.f("pk_team_aliases")),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name=op.f("fk_team_aliases_team_id_teams"), ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_team_aliases_team_id"), "team_aliases", ["team_id"])
    op.create_table(
        "source_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("documented_source_url", sa.Text(), nullable=True),
        sa.Column("declared_source_url", sa.Text(), nullable=True),
        sa.Column("source_revision", sa.Text(), nullable=True),
        sa.Column("publisher_sha256", sa.String(64), nullable=True),
        sa.Column("provider_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("origin_status", sa.Text(), server_default="DECLARED", nullable=False),
        sa.Column("origin_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_method", sa.Text(), nullable=True),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("provenance_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_artifacts")),
        sa.UniqueConstraint("id", "provider", name="uq_source_artifacts_id_provider"),
    )
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("source_game_id", sa.Text(), nullable=False),
        sa.Column("old_game_id", sa.Text(), nullable=True),
        sa.Column("external_ids", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("season_type", sa.Text(), nullable=False),
        sa.Column("game_type", sa.Text(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("home_team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("away_team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_home_team", sa.Text(), nullable=False),
        sa.Column("source_away_team", sa.Text(), nullable=False),
        sa.Column("source_gameday", sa.Date(), nullable=True),
        sa.Column("source_gametime", sa.Time(), nullable=True),
        sa.Column("source_timezone", sa.Text(), server_default="America/New_York", nullable=False),
        sa.Column("scheduled_kickoff_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("neutral_site", sa.Boolean(), nullable=True),
        sa.Column("overtime", sa.Boolean(), nullable=True),
        sa.Column("reported_home_score", sa.Integer(), nullable=True),
        sa.Column("reported_away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), server_default="UNKNOWN", nullable=False),
        sa.Column("final_evidence_url", sa.Text(), nullable=True),
        sa.Column("final_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_sha256", sa.String(64), nullable=False),
        sa.Column("source_line", sa.Integer(), nullable=True),
        sa.Column("raw_source_record", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
        sa.UniqueConstraint("provider", "source_game_id", name="uq_games_provider_source_game_id"),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"], name=op.f("fk_games_home_team_id_teams"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"], name=op.f("fk_games_away_team_id_teams"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_artifact_id", "provider"], ["source_artifacts.id", "source_artifacts.provider"], name="fk_games_artifact_provider", ondelete="RESTRICT"),
    )
    op.create_index("ix_games_schedule", "games", ["season", "season_type", "week"])
    op.create_index(op.f("ix_games_home_team_id"), "games", ["home_team_id"])
    op.create_index(op.f("ix_games_away_team_id"), "games", ["away_team_id"])
    op.create_index(op.f("ix_games_source_artifact_id"), "games", ["source_artifact_id"])

    op.create_check_constraint(op.f("ck_teams_code_format"), "teams", "code ~ '^[A-Z]{2,3}$'")
    op.create_check_constraint(op.f("ck_teams_name_nonblank"), "teams", 'length(btrim(name)) > 0')
    op.create_check_constraint(op.f("ck_team_aliases_provider_nonblank"), "team_aliases", 'length(btrim(provider)) > 0')
    op.create_check_constraint(op.f("ck_team_aliases_code_nonblank"), "team_aliases", 'length(btrim(source_team_code)) > 0')
    op.create_check_constraint(op.f("ck_source_artifacts_provider_nonblank"), "source_artifacts", 'length(btrim(provider)) > 0')
    op.create_check_constraint(op.f("ck_source_artifacts_path_nonblank"), "source_artifacts", 'length(btrim(artifact_path)) > 0')
    op.create_check_constraint(op.f("ck_source_artifacts_sha256_format"), "source_artifacts", "sha256 ~ '^[0-9a-f]{64}$'")
    op.create_check_constraint(op.f("ck_source_artifacts_publisher_hash_format"), "source_artifacts", "publisher_sha256 IS NULL OR publisher_sha256 ~ '^[0-9a-f]{64}$'")
    op.create_check_constraint(op.f("ck_source_artifacts_byte_size_nonnegative"), "source_artifacts", 'byte_size >= 0')
    op.create_check_constraint(op.f("ck_source_artifacts_origin_status"), "source_artifacts", "origin_status IN ('DECLARED', 'VERIFIED')")
    op.create_check_constraint(op.f("ck_source_artifacts_verified_origin_evidence"), "source_artifacts", "origin_status != 'VERIFIED' OR (publisher_sha256 IS NOT NULL AND publisher_sha256 = sha256 AND origin_verified_at IS NOT NULL AND declared_source_url IS NOT NULL AND length(btrim(declared_source_url)) > 0 AND verification_method IS NOT NULL AND length(btrim(verification_method)) > 0)")
    op.create_check_constraint(op.f("ck_games_provider_nonblank"), "games", 'length(btrim(provider)) > 0')
    op.create_check_constraint(op.f("ck_games_source_game_id_nonblank"), "games", 'length(btrim(source_game_id)) > 0')
    op.create_check_constraint(op.f("ck_games_season_scope"), "games", 'season BETWEEN 2024 AND 2026')
    op.create_check_constraint(op.f("ck_games_distinct_teams"), "games", 'home_team_id != away_team_id')
    op.create_check_constraint(op.f("ck_games_source_teams_nonblank"), "games", 'length(btrim(source_home_team)) > 0 AND length(btrim(source_away_team)) > 0')
    op.create_check_constraint(op.f("ck_games_stage_round_week"), "games", "(season_type = 'REG' AND game_type = 'REG' AND week BETWEEN 1 AND 18) OR (season_type = 'POST' AND ((game_type = 'WC' AND week = 19) OR (game_type = 'DIV' AND week = 20) OR (game_type = 'CON' AND week = 21) OR (game_type = 'SB' AND week = 22)))")
    op.create_check_constraint(op.f("ck_games_source_timezone"), "games", "source_timezone = 'America/New_York'")
    op.create_check_constraint(op.f("ck_games_kickoff_inputs"), "games", 'scheduled_kickoff_utc IS NULL OR (source_gameday IS NOT NULL AND source_gametime IS NOT NULL)')
    op.create_check_constraint(op.f("ck_games_score_pair"), "games", '(reported_home_score IS NULL AND reported_away_score IS NULL) OR (reported_home_score IS NOT NULL AND reported_away_score IS NOT NULL AND reported_home_score >= 0 AND reported_away_score >= 0)')
    op.create_check_constraint(op.f("ck_games_status"), "games", "status IN ('UNKNOWN', 'FINAL')")
    op.create_check_constraint(op.f("ck_games_final_evidence"), "games", "status != 'FINAL' OR (final_evidence_url IS NOT NULL AND length(btrim(final_evidence_url)) > 0 AND final_verified_at IS NOT NULL AND reported_home_score IS NOT NULL AND reported_away_score IS NOT NULL)")
    op.create_check_constraint(op.f("ck_games_record_hash_format"), "games", "source_record_sha256 ~ '^[0-9a-f]{64}$'")
    op.create_check_constraint(op.f("ck_games_source_line"), "games", 'source_line IS NULL OR source_line >= 2')


def downgrade():
    raise RuntimeError("Initial migration downgrade is disabled: destructive schema changes require explicit owner approval.")
