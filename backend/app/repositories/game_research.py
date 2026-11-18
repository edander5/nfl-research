"""Bounded accepted history plus original schedule references in one SQL snapshot."""
from sqlalchemy import select, true
from sqlalchemy.orm import aliased

from app.models import Game, SourceArtifact
from app.repositories.team_stats import TeamStatsRepository, history_selection


def game_research_query(team_id, filters):
    selected, metadata = history_selection(team_id, filters)
    artifact = aliased(SourceArtifact)
    return select(metadata, selected,
        Game.raw_source_record.label('reference_raw_record'),
        Game.source_record_sha256.label('reference_record_sha256'),
        Game.source_game_id.label('reference_source_game_id'),
        Game.source_away_team.label('reference_away_team'), Game.source_home_team.label('reference_home_team'),
        Game.season.label('reference_season'),
        artifact.id.label('reference_artifact_id'), artifact.sha256.label('reference_artifact_sha256'),
        artifact.retrieved_at.label('reference_retrieved_at'), artifact.recorded_at.label('reference_recorded_at'),
        artifact.origin_status.label('reference_origin_status'), artifact.documented_source_url.label('reference_source_url'),
        artifact.license_url.label('reference_license_url'), artifact.attribution.label('reference_attribution')
    ).select_from(metadata.outerjoin(selected, true()).outerjoin(Game, Game.id == selected.c.game_id).outerjoin(
        artifact, artifact.id == Game.source_artifact_id)).order_by(
            selected.c.scheduled_kickoff_utc.desc(), selected.c.source_game_id.desc(), selected.c.game_id.desc())


class GameResearchRepository(TeamStatsRepository):
    def research(self, team_id, filters):
        rows = self.session.execute(game_research_query(team_id, filters)).mappings().all()
        return rows[0], [row for row in rows if row['game_id'] is not None]
