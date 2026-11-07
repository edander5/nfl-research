"""Run with python -m ingestion.schedule; dry-run by default."""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.config import Settings
from app.db.session import make_engine
from ingestion.service import capture, reconcile
from ingestion.validation import Problem, ValidationFailure, load_snapshot


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--snapshot-dir', type=Path, default=Path('/app/snapshots'))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    engine = None
    try:
        snapshot = load_snapshot(args.file)
        if not args.apply:
            print(json.dumps(dict(mode='dry-run', rows_read=snapshot.rows_read, selected=len(snapshot.rows),
                                  sha256=snapshot.sha256, counts=snapshot.counts(), reported_scores=snapshot.score_counts(), warnings=snapshot.warnings)))
            return 0
        settings = Settings()
        if settings.db_name != 'nfl_research_dev' or settings.db_host != 'db':
            raise ValidationFailure([Problem('database_guard', None, 'configuration', 'Use the Compose db service and nfl_research_dev database')])
        if args.snapshot_dir.resolve() == args.file.resolve().parent:
            raise ValueError('Archive directory must be separate from the raw input directory')
        archive = capture(snapshot, args.snapshot_dir)
        engine = make_engine(settings)
        with Session(engine) as session, session.begin():
            result = reconcile(session, snapshot, archive)
        print(json.dumps(dict(mode='committed', **result)))
        return 0
    except ValidationFailure as exc:
        print(json.dumps(dict(error='validation', problem_count=len(exc.problems),
                              problems=[asdict(p) for p in exc.problems[:100]],
                              hint='Check source data and isolated Compose development configuration')), file=sys.stderr)
        return 2
    except (OSError, ValueError, ValidationError):
        print(json.dumps(dict(error='input_or_configuration', hint='Check file/archive permissions and required APP_DB settings')), file=sys.stderr)
        return 3
    except SQLAlchemyError:
        # Never print SQL parameters, connection strings or credentials.
        print(json.dumps(dict(error='database', hint='Transaction rolled back; verify development database health, migration and credentials')), file=sys.stderr)
        return 4
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
