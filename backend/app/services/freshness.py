"""Validate recorded observations and derive check age, never game/source freshness."""
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.repositories.refresh_status import RefreshStatusRepository
from app.schemas.freshness import FreshnessData, FreshnessMeta, FreshnessResponse, RefreshOutcome


class RecordedStatus(BaseModel):
    model_config = ConfigDict(extra='ignore')
    version: Literal[1]
    last_outcome: RefreshOutcome | None = None
    last_attempt_at: datetime | None = None
    last_successful_check_at: datetime | None = None
    last_successful_ingestion_at: datetime | None = None
    last_data_change_observed_at: datetime | None = None

    @field_validator('version', mode='before')
    @classmethod
    def actual_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('unsupported checkpoint version')
        return value

    @field_validator('last_attempt_at', 'last_successful_check_at', 'last_successful_ingestion_at',
                     'last_data_change_observed_at', mode='before')
    @classmethod
    def recorded_timestamp(cls, value):
        if value is None:
            return None
        if not isinstance(value, str) or len(value) > 64 or 'T' not in value or not re.search(r'(Z|[+-]\d{2}:\d{2})$', value):
            raise ValueError('expected timezone-aware recorded timestamp')
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            raise ValueError('timestamp has no timezone')
        return parsed.astimezone(timezone.utc)


def project_status(state, raw, now, stale_after_seconds):
    meta = FreshnessMeta(as_of=now, stale_after_seconds=stale_after_seconds)
    def unavailable(reason):
        return FreshnessResponse(data=FreshnessData(metadata_state=reason), meta=meta)
    if state != 'available':
        return unavailable(state)
    if 'version' not in raw:
        return unavailable('incomplete')
    try:
        recorded = RecordedStatus.model_validate(raw)
    except ValidationError:
        return unavailable('invalid')
    check = recorded.last_successful_check_at
    applied = recorded.last_successful_ingestion_at
    changed = recorded.last_data_change_observed_at
    dates = [recorded.last_attempt_at, check, applied, changed]
    # Invalid future/inconsistent evidence never becomes a reassuring recent-check badge.
    if any(date and date > now for date in dates) or (check and applied and applied > check) or (applied and changed and changed > applied):
        return unavailable('invalid')
    complete = recorded.last_outcome is not None and recorded.last_attempt_at is not None
    if recorded.last_outcome in ('dry_run', 'applied', 'unchanged') and check is None:
        complete = False
    if recorded.last_outcome in ('applied', 'unchanged') and applied is None:
        complete = False
    if recorded.last_outcome == 'applied' and changed is None:
        complete = False
    if (applied and not check) or (changed and not applied):
        complete = False
    age = int((now - check).total_seconds()) if complete and check else None
    return FreshnessResponse(data=FreshnessData(
        metadata_state='available' if complete else 'incomplete', latest_outcome=recorded.last_outcome,
        last_attempt_at=recorded.last_attempt_at, last_successful_check_at=check,
        last_successful_apply_at=applied, last_data_change_observed_at=changed,
        check_age_seconds=age, is_stale=(age > stale_after_seconds) if age is not None else None,
    ), meta=meta)


class FreshnessService:
    def __init__(self, repository: RefreshStatusRepository, stale_after_seconds: int):
        self.repository = repository
        self.stale_after_seconds = stale_after_seconds

    def read(self):
        state, raw = self.repository.read()
        # Observe time after the atomic file read, avoiding a concurrent writer's later timestamp.
        return project_status(state, raw, datetime.now(timezone.utc), self.stale_after_seconds)
