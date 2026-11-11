"""Versioned team statistics; schedule entities and finality semantics are unchanged."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFINITION = 'net_pass_negative_sacks_v1'


class TeamStatsBatch(Base):
    __tablename__ = 'team_stats_batches'
    __table_args__ = (
        CheckConstraint("kind IN ('IMPORT', 'ROLLBACK')", name='kind'),
        CheckConstraint("jsonb_typeof(evidence) = 'object'", name='evidence_object'),
        CheckConstraint("candidate_sha256 ~ '^[0-9a-f]{64}$'", name='candidate_hash'),
        CheckConstraint("review_token ~ '^[0-9a-f]{64}$'", name='review_token'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(Text)
    candidate_sha256: Mapped[str] = mapped_column(Text)
    review_token: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamStatsPair(Base):
    __tablename__ = 'team_stats_pairs'
    __table_args__ = (
        UniqueConstraint('id', 'game_id', name='uq_team_stats_pairs_id_game'),
        UniqueConstraint('batch_id', 'game_id', name='uq_team_stats_pairs_batch_game'),
        ForeignKeyConstraint(['previous_pair_id', 'game_id'], ['team_stats_pairs.id', 'team_stats_pairs.game_id'],
                             name='fk_team_stats_pairs_previous', ondelete='RESTRICT'),
        CheckConstraint('home_team_id != away_team_id', name='distinct_sides'),
        CheckConstraint("definition_version = 'net_pass_negative_sacks_v1'", name='definition'),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name='content_hash'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id: Mapped[UUID] = mapped_column(ForeignKey('games.id', ondelete='RESTRICT'), index=True)
    home_team_id: Mapped[UUID] = mapped_column(ForeignKey('teams.id', ondelete='RESTRICT'))
    away_team_id: Mapped[UUID] = mapped_column(ForeignKey('teams.id', ondelete='RESTRICT'))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey('team_stats_batches.id', ondelete='RESTRICT'), index=True)
    source_artifact_id: Mapped[UUID] = mapped_column(ForeignKey('source_artifacts.id', ondelete='RESTRICT'))
    previous_pair_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    definition_version: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamGameStatRevision(Base):
    __tablename__ = 'team_game_stat_revisions'
    __table_args__ = (
        UniqueConstraint('pair_id', 'side', name='uq_team_game_stat_revisions_pair_side'),
        ForeignKeyConstraint(['pair_id', 'game_id'], ['team_stats_pairs.id', 'team_stats_pairs.game_id'],
                             name='fk_team_game_stat_revisions_pair_game', ondelete='RESTRICT'),
        CheckConstraint("side IN ('HOME', 'AWAY')", name='side'),
        CheckConstraint('team_id != opponent_team_id', name='distinct_sides'),
        CheckConstraint('original_sack_yards IS NULL OR original_sack_yards <= 0', name='negative_sacks'),
        CheckConstraint('((gross_passing_yards IS NULL OR original_sack_yards IS NULL) AND net_passing_yards IS NULL) OR '
                        '(gross_passing_yards IS NOT NULL AND original_sack_yards IS NOT NULL AND net_passing_yards IS NOT NULL '
                        'AND net_passing_yards::bigint = gross_passing_yards::bigint + original_sack_yards::bigint)', name='net_identity'),
        CheckConstraint("source_record_sha256 ~ '^[0-9a-f]{64}$'", name='record_hash'),
        CheckConstraint('source_line >= 2', name='source_line'),
        CheckConstraint("jsonb_typeof(raw_source_record) = 'object'", name='raw_object'),
    )
    pair_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    team_id: Mapped[UUID] = mapped_column(ForeignKey('teams.id', ondelete='RESTRICT'), primary_key=True, index=True)
    game_id: Mapped[UUID] = mapped_column(ForeignKey('games.id', ondelete='RESTRICT'), index=True)
    opponent_team_id: Mapped[UUID] = mapped_column(ForeignKey('teams.id', ondelete='RESTRICT'))
    side: Mapped[str] = mapped_column(Text)
    gross_passing_yards: Mapped[int | None] = mapped_column(Integer)
    original_sack_yards: Mapped[int | None] = mapped_column(Integer)
    net_passing_yards: Mapped[int | None] = mapped_column(Integer)
    rushing_yards: Mapped[int | None] = mapped_column(Integer)
    source_record_sha256: Mapped[str] = mapped_column(Text)
    source_line: Mapped[int] = mapped_column(Integer)
    raw_source_record: Mapped[dict] = mapped_column(JSONB)


class TeamStatsSelectionEvent(Base):
    __tablename__ = 'team_stats_selection_events'
    __table_args__ = (
        UniqueConstraint('batch_id', 'game_id', name='uq_team_stats_selection_events_batch_game'),
        UniqueConstraint('game_id', 'generation', name='uq_team_stats_selection_events_game_generation'),
        CheckConstraint('generation >= 1', name='generation'),
        ForeignKeyConstraint(['before_pair_id', 'game_id'], ['team_stats_pairs.id', 'team_stats_pairs.game_id'],
                             name='fk_team_stats_selection_events_before', ondelete='RESTRICT'),
        ForeignKeyConstraint(['after_pair_id', 'game_id'], ['team_stats_pairs.id', 'team_stats_pairs.game_id'],
                             name='fk_team_stats_selection_events_after', ondelete='RESTRICT'),
        CheckConstraint('before_pair_id IS NULL OR before_pair_id != after_pair_id', name='changed_pair'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey('team_stats_batches.id', ondelete='RESTRICT'))
    game_id: Mapped[UUID] = mapped_column(ForeignKey('games.id', ondelete='RESTRICT'), index=True)
    generation: Mapped[int] = mapped_column(Integer)
    before_pair_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    after_pair_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamStatsAccepted(Base):
    __tablename__ = 'team_stats_accepted'
    __table_args__ = (
        ForeignKeyConstraint(['pair_id', 'game_id'], ['team_stats_pairs.id', 'team_stats_pairs.game_id'],
                             name='fk_team_stats_accepted_pair_game', ondelete='RESTRICT'),
        CheckConstraint('generation >= 1', name='generation'),
    )
    game_id: Mapped[UUID] = mapped_column(ForeignKey('games.id', ondelete='RESTRICT'), primary_key=True)
    pair_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey('team_stats_batches.id', ondelete='RESTRICT'))
    generation: Mapped[int] = mapped_column(Integer)
