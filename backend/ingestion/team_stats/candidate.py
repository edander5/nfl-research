"""Revalidate a successful offline audit from original bytes, not trusted derived totals."""
import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ingestion.team_stats.source import LICENSE_URL, SEASONS, capture, read_input, source_url
from ingestion.team_stats.validation import audit, aware_time, canonical_map, reference_list
from ingestion.validation import validate_bytes, record_hash

DEFINITION = 'net_pass_negative_sacks_v1'


class StatsRejected(ValueError):
    """A bounded machine-readable failure code, never an untrusted input/connection string."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode())


def require(condition, code):
    if not condition:
        raise StatsRejected(code)


@dataclass(frozen=True)
class Candidate:
    sha256: str
    evidence: dict
    pairs: tuple[dict, ...]
    blobs: dict[str, bytes]


def validate_receipt(receipt, data, year):
    require(isinstance(receipt, dict), 'missing_receipt')
    require(receipt.get('sha256') == digest(data) and type(receipt.get('byte_size')) is int
            and receipt['byte_size'] == len(data) and receipt.get('season') == year, 'receipt_bytes_mismatch')
    require(receipt.get('source_url') == source_url(year) and receipt.get('origin') == 'DECLARED'
            and receipt.get('independently_authenticated') is False and receipt.get('license_url') == LICENSE_URL
            and isinstance(receipt.get('attribution'), str) and receipt['attribution'].strip(), 'invalid_source_provenance')
    require(not receipt.get('acquisition_errors') and receipt.get('integrity') in
            ('unverified', 'publisher_digest_matched', 'size_checked_digest_unavailable'), 'failed_acquisition')
    try:
        aware_time(receipt['captured_at'])
        if receipt.get('retrieved_at') is not None:
            aware_time(receipt['retrieved_at'])
    except (ValueError, KeyError, TypeError):
        raise StatsRejected('invalid_receipt_timestamp') from None
    method = receipt.get('method')
    require((method == 'operator_local_file' and receipt.get('retrieved_at') is None
             and receipt.get('source_url_basis') == 'documented_expected_url_not_verified_origin')
            or (method == 'official_download' and receipt.get('retrieved_at') is not None
                and receipt.get('source_url_basis') == 'actual_requested_url'), 'invalid_retrieval_claim')
    meta = receipt.get('publisher_metadata')
    if meta is not None:
        require(isinstance(meta, dict) and meta.get('browser_download_url') == source_url(year)
                and type(meta.get('size')) is int and meta['size'] == len(data)
                and type(meta.get('id')) is int and meta['id'] > 0, 'invalid_publisher_metadata')
        try:
            aware_time(meta['updated_at'])
        except (ValueError, KeyError, TypeError):
            raise StatsRejected('invalid_publisher_timestamp') from None
        require(meta.get('digest') in (None, 'sha256:' + digest(data)), 'publisher_digest_mismatch')
    require(receipt.get('integrity') != 'publisher_digest_matched' or
            (meta is not None and meta.get('digest') == 'sha256:' + digest(data)), 'unsupported_integrity_claim')


def load_candidate(audit_path, artifact_dir, schedule_path, identity_path, references_path):
    try:
        audit_data = read_input(audit_path)
        report = json.loads(audit_data)
        require(type(report.get('version')) is int and report['version'] == 1
                and type(report.get('audit_exit_code')) is int and report['audit_exit_code'] == 0 and report.get('errors') == []
                and report.get('identity_scope') == 'canonical_export_and_schedule'
                and report.get('database_access') is False and report.get('rankings_published') is False
                and report.get('completion_eligibility') == 'unverified'
                and set(report.get('seasons', {})) == {'2024', '2025', '2026'}, 'unsuccessful_audit')
        schedule_data, identity_data, refs_data = (read_input(p) for p in (schedule_path, identity_path, references_path))
        require(digest(schedule_data) == report['schedule']['sha256']
                and digest(identity_data) == report['identity_map']['sha256']
                and digest(refs_data) == report['references']['sha256'], 'audit_input_hash_mismatch')
        schedule = [r.raw for r in validate_bytes(schedule_data).rows]
        identities = canonical_map(json.loads(identity_data), schedule)
        refs = reference_list(json.loads(refs_data))
        blobs = {'audit.json': audit_data, 'schedule.csv': schedule_data,
                 'identities.json': identity_data, 'references.json': refs_data}
        pairs, receipts = [], {}
        for year in SEASONS:
            recorded = report['seasons'][str(year)]
            sha = recorded['sha256']
            require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'invalid_artifact_hash')
            # Never follow an arbitrary receipt path; bind the supplied artifact directory to the measured hash.
            path = Path(artifact_dir) / (sha + '.csv')
            require(not path.is_symlink(), 'symlink_artifact')
            data = read_input(path)
            validate_receipt(recorded['receipt'], data, year)
            require(digest(data) == sha and recorded.get('state') == 'audited', 'artifact_hash_mismatch')
            checked = audit(data, year, schedule, identities, refs)
            require(not checked['errors'] and checked['sack_convention'] == 'negative_validated_against_reviewed_reference'
                    and not any(v['missing_reported_score_games'] for v in checked['coverage'].values()), 'statistics_contract_failed')
            for field in ('matched_games', 'sha256', 'rows_read', 'coverage', 'sack_convention', 'references'):
                require(checked[field] == recorded[field], 'audit_revalidation_mismatch')
            reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
            raw_rows = {}
            for raw in reader:
                raw_rows[reader.line_num] = raw
            receipts[str(year)] = recorded['receipt']
            blobs[str(year) + '.csv'] = data
            for game in checked['matched_games']:
                teams = []
                for t in game['teams']:
                    raw = raw_rows[t['source_line']]
                    require(raw['team'] == t['source_team'] and raw['season'] == str(year), 'raw_record_mismatch')
                    values = {k: t[k] for k in ('gross_passing_yards', 'original_sack_yards', 'net_passing_yards', 'rushing_yards')}
                    require(all(type(v) is int and -(2**31) <= v < 2**31 for v in values.values())
                            and values['original_sack_yards'] <= 0
                            and values['net_passing_yards'] == values['gross_passing_yards'] + values['original_sack_yards'], 'invalid_net_values')
                    teams.append(dict(team_id=t['canonical_team_id'], code=t['team'], values=values,
                                      raw=raw, row_sha256=record_hash(raw), line=t['source_line']))
                pair = dict(game_id=game['canonical_game_id'], source_game_id=game['source_game_id'],
                            season=year, teams=sorted(teams, key=lambda t: t['team_id']), definition=DEFINITION)
                pair['content_sha256'] = pair_hash(pair)
                pairs.append(pair)
        require(len({p['game_id'] for p in pairs}) == len(pairs), 'duplicate_canonical_game')
        evidence = dict(audit_sha256=digest(audit_data), schedule_sha256=digest(schedule_data),
                        identities_sha256=digest(identity_data), references_sha256=digest(refs_data),
                        receipts=receipts, definition=DEFINITION, completion_eligibility='unverified')
        return Candidate(candidate_fingerprint(evidence, pairs, blobs), evidence, tuple(pairs), blobs)
    except StatsRejected:
        raise
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        raise StatsRejected('candidate_input_invalid') from None


def pair_hash(pair):
    return fingerprint(dict(game_id=pair['game_id'], definition=pair['definition'], teams=[
        dict(team_id=t['team_id'], values=t['values'], raw=t['raw']) for t in pair['teams']]))


def archive_candidate(candidate, directory):
    # The same no-replace capture handles bytes regardless of the historical .csv filename extension.
    return {name: str(Path(capture(directory, blob)).resolve()) for name, blob in candidate.blobs.items()}


def candidate_fingerprint(evidence, pairs, blobs):
    return fingerprint(dict(version=2, evidence=evidence, pairs=pairs,
                            blobs={name: digest(data) for name, data in blobs.items()}))
