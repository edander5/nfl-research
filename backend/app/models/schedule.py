from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    ForeignKeyConstraint, Index, Integer, String, Text, Time, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint("code ~ '^[A-Z]{2,3}$'", name="code_format"),
        CheckConstraint("length(btrim(name)) > 0", name="name_nonblank"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list["TeamAlias"]] = relationship(back_populates="team")


class TeamAlias(Base):
    """Provider-scoped aliases; canonical IDs survive display/code changes."""
    __tablename__ = "team_aliases"
    __table_args__ = (
        CheckConstraint("length(btrim(provider)) > 0", name="provider_nonblank"),
        CheckConstraint("length(btrim(source_team_code)) > 0", name="code_nonblank"),
    )

    provider: Mapped[str] = mapped_column(Text, primary_key=True)
    source_team_code: Mapped[str] = mapped_column(Text, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    team: Mapped[Team] = relationship(back_populates="aliases")


class SourceArtifact(Base):
    """One captured artifact version; recorded_at is not its download time."""
    __tablename__ = "source_artifacts"
    __table_args__ = (
        UniqueConstraint("id", "provider", name="uq_source_artifacts_id_provider"),
        CheckConstraint("length(btrim(provider)) > 0", name="provider_nonblank"),
        CheckConstraint("length(btrim(artifact_path)) > 0", name="path_nonblank"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint("publisher_sha256 IS NULL OR publisher_sha256 ~ '^[0-9a-f]{64}$'", name="publisher_hash_format"),
        CheckConstraint("byte_size >= 0", name="byte_size_nonnegative"),
        CheckConstraint("origin_status IN ('DECLARED', 'VERIFIED')", name="origin_status"),
        CheckConstraint(
            "origin_status != 'VERIFIED' OR "
            "(publisher_sha256 IS NOT NULL AND publisher_sha256 = sha256 "
            "AND origin_verified_at IS NOT NULL "
            "AND declared_source_url IS NOT NULL AND length(btrim(declared_source_url)) > 0 "
            "AND verification_method IS NOT NULL AND length(btrim(verification_method)) > 0)",
            name="verified_origin_evidence",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(Text)
    artifact_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    # Documented route and owner-declared actual route are distinct claims.
    documented_source_url: Mapped[str | None] = mapped_column(Text)
    declared_source_url: Mapped[str | None] = mapped_column(Text)
    source_revision: Mapped[str | None] = mapped_column(Text)
    publisher_sha256: Mapped[str | None] = mapped_column(String(64))
    provider_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    origin_status: Mapped[str] = mapped_column(Text, default="DECLARED", server_default="DECLARED")
    origin_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_method: Mapped[str | None] = mapped_column(Text)
    license_url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    provenance_notes: Mapped[str | None] = mapped_column(Text)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("provider", "source_game_id", name="uq_games_provider_source_game_id"),
        ForeignKeyConstraint(
            ["source_artifact_id", "provider"],
            ["source_artifacts.id", "source_artifacts.provider"],
            name="fk_games_artifact_provider", ondelete="RESTRICT",
        ),
        CheckConstraint("length(btrim(provider)) > 0", name="provider_nonblank"),
        CheckConstraint("length(btrim(source_game_id)) > 0", name="source_game_id_nonblank"),
        CheckConstraint("season BETWEEN 2024 AND 2026", name="season_scope"),
        CheckConstraint("home_team_id != away_team_id", name="distinct_teams"),
        CheckConstraint("length(btrim(source_home_team)) > 0 AND length(btrim(source_away_team)) > 0", name="source_teams_nonblank"),
        CheckConstraint(
            "(season_type = 'REG' AND game_type = 'REG' AND week BETWEEN 1 AND 18) OR "
            "(season_type = 'POST' AND ((game_type = 'WC' AND week = 19) OR "
            "(game_type = 'DIV' AND week = 20) OR (game_type = 'CON' AND week = 21) OR "
            "(game_type = 'SB' AND week = 22)))", name="stage_round_week",
        ),
        CheckConstraint("source_timezone = 'America/New_York'", name="source_timezone"),
        CheckConstraint("scheduled_kickoff_utc IS NULL OR (source_gameday IS NOT NULL AND source_gametime IS NOT NULL)", name="kickoff_inputs"),
        CheckConstraint(
            "(reported_home_score IS NULL AND reported_away_score IS NULL) OR "
            "(reported_home_score IS NOT NULL AND reported_away_score IS NOT NULL "
            "AND reported_home_score >= 0 AND reported_away_score >= 0)", name="score_pair",
        ),
        CheckConstraint("status IN ('UNKNOWN', 'FINAL')", name="status"),
        CheckConstraint(
            "status != 'FINAL' OR (final_evidence_url IS NOT NULL "
            "AND length(btrim(final_evidence_url)) > 0 AND final_verified_at IS NOT NULL "
            "AND reported_home_score IS NOT NULL AND reported_away_score IS NOT NULL)",
            name="final_evidence",
        ),
        CheckConstraint("source_record_sha256 ~ '^[0-9a-f]{64}$'", name="record_hash_format"),
        CheckConstraint("source_line IS NULL OR source_line >= 2", name="source_line"),
        Index("ix_games_schedule", "season", "season_type", "week"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(Text)
    source_game_id: Mapped[str] = mapped_column(Text)
    # Deliberately neither unique nor an identity/join key.
    old_game_id: Mapped[str | None] = mapped_column(Text)
    external_ids: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    season: Mapped[int] = mapped_column(Integer)
    season_type: Mapped[str] = mapped_column(Text)
    game_type: Mapped[str] = mapped_column(Text)
    week: Mapped[int] = mapped_column(Integer)
    home_team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    away_team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), index=True)
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    source_home_team: Mapped[str] = mapped_column(Text)
    source_away_team: Mapped[str] = mapped_column(Text)
    source_gameday: Mapped[date | None] = mapped_column(Date)
    source_gametime: Mapped[time | None] = mapped_column(Time)
    source_timezone: Mapped[str] = mapped_column(Text, default="America/New_York", server_default="America/New_York")
    scheduled_kickoff_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    neutral_site: Mapped[bool | None] = mapped_column(Boolean)
    overtime: Mapped[bool | None] = mapped_column(Boolean)
    reported_home_score: Mapped[int | None] = mapped_column(Integer)
    reported_away_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="UNKNOWN", server_default="UNKNOWN")
    final_evidence_url: Mapped[str | None] = mapped_column(Text)
    final_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_artifact_id: Mapped[UUID] = mapped_column(index=True)
    source_artifact: Mapped[SourceArtifact] = relationship()
    source_record_sha256: Mapped[str] = mapped_column(String(64))
    source_line: Mapped[int | None] = mapped_column(Integer)
    # Optional until an importer can retain the actual original record.
    raw_source_record: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
