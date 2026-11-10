"""Public projection of operational metadata; no paths, identifiers or provenance payloads."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RefreshOutcome = Literal['dry_run', 'applied', 'unchanged', 'rejected', 'review_required',
                         'download_failed', 'validation_failed', 'failed', 'not_applied']
MetadataState = Literal['available', 'missing', 'incomplete', 'invalid', 'unreadable']


class FreshnessData(BaseModel):
    metadata_state: MetadataState
    latest_outcome: RefreshOutcome | None = None
    last_attempt_at: datetime | None = None
    last_successful_check_at: datetime | None = None
    last_successful_apply_at: datetime | None = None
    last_data_change_observed_at: datetime | None = None
    check_age_seconds: int | None = None
    is_stale: bool | None = None


class FreshnessMeta(BaseModel):
    as_of: datetime
    manual: Literal[True] = True
    scope: Literal['guarded_manual_refresh_runner'] = 'guarded_manual_refresh_runner'
    stale_after_seconds: int
    apply_semantics: str = 'Successful apply includes no-change reconciliation; data-change time is separate.'
    timestamp_semantics: str = 'Recorded runner observations, not source publication or game completion times. No game status is inferred.'


class FreshnessResponse(BaseModel):
    data: FreshnessData
    meta: FreshnessMeta
