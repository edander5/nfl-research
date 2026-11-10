"""Explicit official source acquisition and immutable capture using only the stdlib."""
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SEASONS = (2024, 2025, 2026)
METADATA_URL = 'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_team'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
HOSTS = {'github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
MAX_BYTES = 32 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def source_url(season):
    if season not in SEASONS:
        raise ValueError('unsupported season')
    return f'https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{season}.csv'


class AcquisitionError(ValueError):
    pass


def check_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname not in HOSTS or parts.port not in (None, 443)
            or parts.username or parts.password or parts.fragment):
        raise AcquisitionError('unapproved_url')


class Redirects(HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=MAX_BYTES):
    check_url(url)
    request = Request(url, headers={'User-Agent': 'nfl-research-offline-team-stats-audit/1',
                                   'Accept-Encoding': 'identity'})
    start = time.monotonic()
    try:
        with build_opener(Redirects()).open(request, timeout=15) as response:
            check_url(response.url)
            if response.status != 200 or response.headers.get('Content-Encoding') not in (None, 'identity'):
                raise AcquisitionError('unexpected_response')
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdecimal() or int(length) > limit):
                raise AcquisitionError('invalid_content_length')
            chunks, size = [], 0
            while True:
                if time.monotonic() - start > 60:
                    raise AcquisitionError('download_deadline')
                chunk = response.read(min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > limit:
                    raise AcquisitionError('download_too_large')
            if length is not None and size != int(length):
                raise AcquisitionError('truncated_download')
            return b''.join(chunks)
    except AcquisitionError:
        raise
    except HTTPError as exc:
        raise AcquisitionError(f'http_{exc.code}') from None
    except (URLError, OSError, EOFError, HTTPException):
        raise AcquisitionError('network_failure') from None


def metadata(season, get):
    try:
        body = get(METADATA_URL, limit=2 * 1024 * 1024)
    except AcquisitionError as exc:
        return None, str(exc)
    try:
        raw = json.loads(body)
        assets = [a for a in raw['assets'] if a['name'] == f'stats_team_week_{season}.csv']
        if len(assets) != 1:
            raise ValueError()
        asset = assets[0]
        if (asset['browser_download_url'] != source_url(season) or type(asset['size']) is not int
                or not 0 < asset['size'] <= MAX_BYTES or type(asset['id']) is not int
                or asset['id'] <= 0 or not isinstance(asset['updated_at'], str)):
            raise ValueError()
        updated = datetime.fromisoformat(asset['updated_at'].replace('Z', '+00:00'))
        if updated.utcoffset() is None:
            raise ValueError()
        digest = asset.get('digest')
        if digest is not None:
            import re
            if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
                raise ValueError()
        return {k: asset.get(k) for k in ('id', 'size', 'updated_at', 'digest', 'browser_download_url')}, None
    except (ValueError, KeyError, TypeError, RecursionError):
        raise AcquisitionError('invalid_publisher_metadata') from None


def acquire(season, get=fetch):
    before, error = metadata(season, get)
    data = get(source_url(season))
    receipt = describe(data, season, 'official_download')
    receipt.update(retrieved_at=now(), publisher_metadata=before, metadata_error=error)
    failures = []
    if before:
        try:
            after, after_error = metadata(season, get)
        except AcquisitionError as exc:
            after, after_error = None, str(exc)
        receipt['metadata_recheck_error'] = after_error
        if after_error or after != before:
            failures.append('publisher_metadata_changed_or_unavailable')
        if before['size'] != len(data):
            failures.append('publisher_size_mismatch')
        if before['digest'] and before['digest'] != 'sha256:' + receipt['sha256']:
            failures.append('publisher_digest_mismatch')
        receipt['integrity'] = ('publisher_digest_matched' if before['digest'] and not failures
                                else 'size_checked_digest_unavailable' if not failures else 'failed')
    receipt['acquisition_errors'] = failures
    return data, receipt


def describe(data, season, method):
    return dict(season=season, source_url=source_url(season), method=method,
                sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data), captured_at=now(),
                source_url_basis='actual_requested_url' if method == 'official_download' else 'documented_expected_url_not_verified_origin',
                retrieved_at=None, publisher_metadata=None, integrity='unverified',
                independently_authenticated=False, origin='DECLARED', license_url=LICENSE_URL,
                attribution='nflverse/nflfastR; NFL data via nflverse-data. Audit transformations: identity mapping and net/opponent metrics.')


def read_input(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('input_too_large')
    return data


def capture(directory, data):
    """Atomic no-replace content-addressed file. Never write to the input path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    target = directory / f'{digest}.csv'
    fd, temporary = tempfile.mkstemp(prefix='.capture-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != data:
                raise ValueError('archive_collision')
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.unlink(temporary)
    return str(target)
