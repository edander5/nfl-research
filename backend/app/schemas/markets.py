"""Source-reference markets only; no executable offers or verified pregame snapshots."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from app.schemas.schedule import GameView


class MarketSide(BaseModel):
    market: Literal['MONEYLINE', 'SPREAD', 'TOTAL']
    side: Literal['AWAY', 'HOME', 'OVER', 'UNDER']
    line: Decimal | None
    price: Decimal | None
    result: Literal['WIN', 'LOSS', 'PUSH', 'UNDETERMINED']
    reason: str


class MarketReference(BaseModel):
    snapshot_id: str
    provider: Literal['nflverse'] = 'nflverse'
    bookmaker: None = None
    classification: Literal['UNVERIFIED_SOURCE_REFERENCE'] = 'UNVERIFIED_SOURCE_REFERENCE'
    quote_updated_at: None = None
    freshness: Literal['UNKNOWN'] = 'UNKNOWN'
    artifact_id: UUID
    artifact_sha256: str
    source_record_sha256: str
    artifact_retrieved_at: datetime | None
    artifact_recorded_at: datetime
    origin_status: str
    source_url: str | None
    license_url: str | None
    attribution: str | None
    sides: list[MarketSide]
    warnings: list[str]


class MarketsData(BaseModel):
    game: GameView
    references: list[MarketReference]
    unavailable_reason: str | None = None


class MarketsMeta(BaseModel):
    current_offers_available: Literal[False] = False
    verified_pregame_snapshot_available: Literal[False] = False
    settlement_verified: Literal[False] = False
    semantics: str = ('Source-reference lines only: bookmaker and quote time are unknown; not verified opening, '
        'closing or pregame lines, and not current offers. WIN/LOSS/PUSH are hypothetical score comparisons, '
        'provisional even when the selected game has final evidence. No wager settlement is certified.')
    timestamp_semantics: str = 'Artifact retrieval/recording times are not odds update times. Quote freshness is unknown.'
    tie_policy: str = 'Moneyline ties are UNDETERMINED: two-way/three-way and bookmaker tie rules are unknown.'
    spread_definition: str = 'nflverse positive spread_line favors home: home signed spread = -spread_line; away = spread_line.'
    price_semantics: str = 'Prices are reported source values; no price-format conversion, payout or bookmaker rule is inferred.'


class MarketsResponse(BaseModel):
    data: MarketsData
    meta: MarketsMeta = Field(default_factory=MarketsMeta)
