from datetime import timezone
from uuid import UUID

from app.models import Game
from app.repositories.schedule import ScheduleRepository
from app.schemas.schedule import (
    FinalEvidence, GameResponse, GameView, Policy, Provenance, ROUND_WEEKS,
    ScheduleFilters, ScheduleMeta, ScheduleResponse, SeasonCoverage, SeasonsMeta,
    SeasonsResponse, StageCoverage, TeamView,
)


class GameNotFound(Exception):
    pass


def coverage(rows, season: int) -> list[StageCoverage]:
    stages = []
    for stage in ('REG', 'POST'):
        selected = [r for r in rows if r['season'] == season and r['season_type'] == stage]
        total = sum(r['game_count'] for r in selected)
        reported = sum(r['reported_score_pairs'] for r in selected)
        stages.append(StageCoverage(
            season_type=stage, game_count=total, weeks=sorted({r['week'] for r in selected}),
            rounds=[name for name in ROUND_WEEKS if any(r['game_type'] == name for r in selected)],
            reported_score_pairs=reported, missing_score_pairs=total-reported,
            **{key: sum(r[key] for r in selected) for key in (
                'unknown_status_games', 'final_status_games', 'unknown_kickoff_games', 'unverified_origin_games')},
        ))
    return stages


def game_view(game: Game) -> GameView:
    artifact = game.source_artifact
    final = game.status == 'FINAL'
    return GameView(
        id=game.id, season=game.season, season_type=game.season_type,
        week=game.week, game_type=game.game_type,
        home_team=TeamView.model_validate(game.home_team), away_team=TeamView.model_validate(game.away_team),
        scheduled_kickoff_utc=game.scheduled_kickoff_utc.astimezone(timezone.utc) if game.scheduled_kickoff_utc is not None else None,
        source_gameday=game.source_gameday, source_gametime=game.source_gametime,
        source_timezone=game.source_timezone, reported_home_score=game.reported_home_score,
        reported_away_score=game.reported_away_score, status=game.status,
        score_finality='CONFIRMED_FINAL' if final else ('NOT_REPORTED' if game.reported_home_score is None else 'UNVERIFIED'),
        final_evidence=FinalEvidence(url=game.final_evidence_url, verified_at=game.final_verified_at) if final else None,
        neutral_site=game.neutral_site, overtime=game.overtime, updated_at=game.updated_at,
        provenance=Provenance(
            artifact_id=artifact.id, provider=game.provider, source_game_id=game.source_game_id,
            artifact_sha256=artifact.sha256, source_record_sha256=game.source_record_sha256,
            source_line=game.source_line, origin_status=artifact.origin_status,
            **{key: getattr(artifact, key) for key in (
                'documented_source_url', 'declared_source_url', 'source_revision', 'publisher_sha256',
                'origin_verified_at', 'verification_method', 'provider_published_at', 'retrieved_at',
                'recorded_at', 'license_url', 'attribution')},
        ),
    )


class ScheduleService:
    def __init__(self, repository: ScheduleRepository):
        self.repository = repository

    def seasons(self) -> SeasonsResponse:
        rows = self.repository.coverage()
        years = sorted({r['season'] for r in rows})
        return SeasonsResponse(data=[SeasonCoverage(season=y, coverage=coverage(rows, y)) for y in years],
            meta=SeasonsMeta(missing_seasons=[y for y in (2024, 2025, 2026) if y not in years], returned_count=len(years)))

    def schedule(self, season: int, filters: ScheduleFilters) -> ScheduleResponse:
        week = ROUND_WEEKS[filters.round] if filters.round else filters.week
        all_games = self.repository.games(season)
        games = [g for g in all_games if g.season_type == filters.season_type and (week is None or g.week == week)]
        rows = [dict(season=g.season, season_type=g.season_type, week=g.week, game_type=g.game_type,
                     game_count=1, reported_score_pairs=int(g.reported_home_score is not None),
                     unknown_status_games=int(g.status == 'UNKNOWN'), final_status_games=int(g.status == 'FINAL'),
                     unknown_kickoff_games=int(g.scheduled_kickoff_utc is None),
                     unverified_origin_games=int(g.source_artifact.origin_status != 'VERIFIED')) for g in all_games]
        return ScheduleResponse(data=[game_view(g) for g in games], meta=ScheduleMeta(
            season=season, filters=filters, returned_count=len(games), season_coverage=coverage(rows, season)))

    def game(self, game_id: UUID) -> GameResponse:
        game = self.repository.game(game_id)
        if game is None:
            raise GameNotFound()
        return GameResponse(data=game_view(game), meta=Policy())
