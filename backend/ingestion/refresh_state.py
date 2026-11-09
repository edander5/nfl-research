"""Durable local receipts, reports and fail-closed single-run locking (Linux/WSL)."""
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID


def write_json(path: Path, value, *, replace=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(name, path)
        else:
            os.link(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_json(path):
    value = json.loads(path.read_text())
    if not isinstance(value,dict):
        raise ValueError('invalid_state_object')
    return value


class RefreshState:
    def __init__(self, root: Path):
        self.root = root

    def path(self, kind, identifier):
        return self.root / kind / f'{UUID(identifier)}.json'

    def load(self, kind, identifier):
        return read_json(self.path(kind, identifier))

    def save_run(self, run):
        write_json(self.path('runs', run['run_id']), run)

    def status(self):
        path = self.root/'status.json'
        if path.exists():
            return read_json(path)
        if any(read_json(p).get('outcome') in ('applied','unchanged') for p in (self.root/'runs').glob('*.json')):
            raise ValueError('missing_success_checkpoint_stop_for_review')
        return {}

    def finish(self, run):
        status = self.status()
        status.update(version=1,last_run_id=run['run_id'], last_outcome=run['outcome'], last_attempt_at=run['started_at'])
        if run['outcome'] in ('applied', 'unchanged'):
            status.update(last_successful_ingestion_at=run['completed_at'], accepted_sha256=run['sha256'])
            stamp = (run.get('acquisition',{}).get('metadata') or {}).get('asset_updated_at')
            if stamp:
                status['accepted_asset_updated_at'] = stamp
            status['accepted_hashes'] = sorted(set(status.get('accepted_hashes', [])) | {run['sha256']})
            if run['outcome'] == 'applied':
                status['last_data_change_observed_at'] = run['completed_at']
        if run['outcome'] in ('dry_run', 'applied', 'unchanged'):
            status['last_successful_check_at'] = run['completed_at']
        write_json(self.root/'status.json', status)
        self.save_run(run)

    def pending(self):
        runs = [read_json(p) for p in sorted((self.root/'runs').glob('*.json'))]
        return [run for run in runs if run.get('phase') == 'commit_pending']

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root/'runner.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
