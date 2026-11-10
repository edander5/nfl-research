"""Offline NFL team-statistics capture and audit. Never connects to PostgreSQL."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from ingestion.team_stats.source import (
    AcquisitionError, SEASONS, acquire, capture, describe, now, read_input, source_url,
)
from ingestion.team_stats.validation import audit, canonical_map, reference_list
from ingestion.validation import ValidationFailure, validate_bytes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', type=Path, required=True, help='Read-only full schedule CSV')
    parser.add_argument('--output-dir', type=Path, required=True, help='New archives and unique audit reports')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--download', action='store_true', help='Official nflverse releases only; no retries')
    mode.add_argument('--file', action='append', metavar='SEASON=PATH', help='Repeat for each of 2024, 2025, 2026')
    parser.add_argument('--identity-map', type=Path, help='Optional read-only canonical UUID/alias export JSON')
    parser.add_argument('--references', type=Path, help='Optional reviewed reference-only gamebook manifest JSON')
    args = parser.parse_args(argv)
    report = dict(version=1, created_at=now(), mode='offline_audit', seasons={}, errors=[],
                  rankings_published=False, database_access=False,
                  independent_origin_authenticated=False, completion_eligibility='unverified')
    exit_code = 0
    try:
        schedule_bytes = read_input(args.schedule)
        snapshot = validate_bytes(schedule_bytes)
        schedule = [r.raw for r in snapshot.rows]
        report['schedule'] = dict(sha256=snapshot.sha256, selected_games=len(schedule),
                                  provenance='declared; no independent authentication or current database assertion')
        canonical, refs = None, []
        for name, path in (('identity_map', args.identity_map), ('references', args.references)):
            if path:
                data = read_input(path)
                raw = json.loads(data)
                report[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'origin': 'operator_supplied'}
                if name == 'identity_map':
                    canonical = canonical_map(raw, schedule)
                else:
                    refs = reference_list(raw)
        report['identity_scope'] = 'canonical_export_and_schedule' if canonical else 'schedule_source_identifiers_only'
        files = {}
        for entry in args.file or []:
            year, sep, path = entry.partition('=')
            if not sep or year not in ('2024', '2025', '2026') or not path or int(year) in files:
                raise ValueError('invalid_file_selection')
            files[int(year)] = Path(path)
        if not args.download and set(files) != set(SEASONS):
            raise ValueError('provide_all_three_season_files')
        stop_network = False
        for season in SEASONS:
            if stop_network:
                report['seasons'][str(season)] = {'state': 'not_attempted_after_network_failure', 'source_url': source_url(season)}
                continue
            try:
                if args.download:
                    data, receipt = acquire(season)
                else:
                    data = read_input(files[season])
                    receipt = describe(data, season, 'operator_local_file')
                receipt['archive'] = capture(args.output_dir / 'snapshots', data)
                result = audit(data, season, schedule, canonical, refs)
                result['receipt'] = receipt
                result['state'] = 'audited'
                report['seasons'][str(season)] = result
                if receipt.get('acquisition_errors'):
                    result['state'] = 'acquisition_integrity_failed'
                    # Never expose derived metrics from a download that failed integrity checks.
                    result['matched_games'] = []
                    result['net_metrics_validated_games'] = 0
                    exit_code = max(exit_code, 2)
                elif result['errors']:
                    exit_code = max(exit_code, 2)
                elif (result['sack_convention'] == 'unverified' or canonical is None
                      or any(c['missing_reported_score_games'] for c in result['coverage'].values())):
                    exit_code = max(exit_code, 2)
            except AcquisitionError as exc:
                report['seasons'][str(season)] = {'state': 'download_failed', 'error': str(exc), 'source_url': source_url(season)}
                exit_code = 3
                stop_network = str(exc) == 'network_failure'
            except (OSError, ValueError, TypeError, KeyError):
                report['seasons'][str(season)] = {'state': 'input_or_archive_failure'}
                exit_code = max(exit_code, 3)
    except ValidationFailure as exc:
        report['errors'].append({'code': 'schedule_contract_failed', 'problem_codes': sorted({p.code for p in exc.problems})})
        exit_code = 3
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        report['errors'].append({'code': 'invalid_input_or_manifest', 'hint': 'Check schedule, file selections, identity and reference manifests.'})
        exit_code = 3
    report['audit_exit_code'] = exit_code
    report['interpretation'] = ('0: requested artifact/identity/reference checks passed, NOT ranking eligibility; '
                                '2: data errors or verification gaps; 3: input/acquisition/configuration failure.')
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / ('audit-' + uuid4().hex + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    except OSError:
        print(json.dumps({'error': 'report_write_failed', 'audit_exit_code': exit_code}))
        return 3
    print(json.dumps({'report': str(path), 'audit_exit_code': exit_code,
                      'season_states': {y: r['state'] for y, r in report['seasons'].items()}}))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
