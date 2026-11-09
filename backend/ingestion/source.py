"""Bounded public-source acquisition. No SDK, credentials, mirrors or automatic retries."""
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPException, IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ingestion.service import SOURCE_URL


@dataclass(frozen=True)
class SourceConfig:
    name: str = 'nflverse-release'
    csv_url: str = SOURCE_URL
    metadata_url: str = 'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/schedules'
    timeout_seconds: int = 15
    total_seconds: int = 60
    max_bytes: int = 32 * 1024 * 1024


SOURCES = {'nflverse-release': SourceConfig()}
ALLOWED_HOSTS = {'github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class SourceFailure(ValueError):
    def __init__(self, code, *, data=None, evidence=None):
        self.code = code
        self.data = data
        self.evidence = evidence
        super().__init__(code)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def check_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname not in ALLOWED_HOSTS or parts.port not in (None, 443)
            or parts.username or parts.password or parts.fragment):
        raise SourceFailure('unapproved_redirect')


class ApprovedRedirects(HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_bytes(url, *, limit, config):
    """Return bytes and only non-secret headers. Signed redirect URLs are never recorded."""
    check_url(url)
    request = Request(url, headers={'User-Agent': 'nfl-research-development-refresh/1',
                                   'Accept': 'application/json' if url == config.metadata_url else 'text/csv, application/octet-stream',
                                   'Accept-Encoding': 'identity'})
    started = time.monotonic()
    try:
        with build_opener(ApprovedRedirects()).open(request, timeout=config.timeout_seconds) as response:
            if response.status != 200:
                raise SourceFailure('unexpected_http_status')
            check_url(response.url)
            headers = {k: response.headers.get(k) for k in ('Content-Length', 'Content-Type', 'Content-Encoding', 'ETag', 'Last-Modified')}
            if headers['Content-Encoding'] not in (None, 'identity'):
                raise SourceFailure('unexpected_content_encoding')
            length = headers['Content-Length']
            if length is not None and (not length.isdecimal() or int(length) > limit):
                raise SourceFailure('invalid_content_length')
            chunks, size = [], 0
            while True:
                if time.monotonic() - started > config.total_seconds:
                    raise SourceFailure('download_deadline')
                chunk = response.read(min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > limit:
                    raise SourceFailure('download_too_large')
            if length is not None and size != int(length):
                raise SourceFailure('truncated_download')
            return b''.join(chunks), headers
    except SourceFailure:
        raise
    except HTTPError as exc:
        raise SourceFailure(f'http_{exc.code}') from None
    except IncompleteRead:
        raise SourceFailure('truncated_download') from None
    except (URLError, OSError, EOFError, HTTPException):
        raise SourceFailure('network_failure') from None


def asset_metadata(data):
    try:
        assets = json.loads(data)['assets']
        matches = [a for a in assets if a['name'] == 'games.csv' and a.get('state') == 'uploaded']
        if len(matches) != 1:
            raise ValueError()
        a = matches[0]
        if a.get('browser_download_url') != SOURCE_URL or type(a.get('id')) is not int or type(a.get('size')) is not int or a['size'] < 1:
            raise ValueError()
        digest = a.get('digest')
        if digest is not None and not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ValueError()
        updated = a.get('updated_at')
        if updated is not None:
            parsed = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            if parsed.utcoffset() is None:
                raise ValueError()
        return dict(asset_id=a['id'], byte_size=a['size'], publisher_sha256=digest[7:] if digest else None,
                    asset_updated_at=updated)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SourceFailure('invalid_source_metadata') from None


def retrieve(config: SourceConfig, fetch=get_bytes):
    """Metadata can be unavailable; invalid/contradictory available evidence fails closed."""
    metadata, metadata_failure = None, None
    try:
        data, _ = fetch(config.metadata_url, limit=2*1024*1024, config=config)
    except SourceFailure as exc:
        metadata_failure = exc.code
    else:
        metadata = asset_metadata(data)
    data, headers = fetch(config.csv_url, limit=config.max_bytes, config=config)
    digest = hashlib.sha256(data).hexdigest()
    evidence = dict(source=config.name, source_url=config.csv_url, metadata_url=config.metadata_url,
        sha256=digest, byte_size=len(data), retrieved_at=utcnow(), origin_status='DECLARED',
        metadata=metadata, metadata_failure=metadata_failure,
        digest_matches_publisher=False, etag=headers.get('ETag'), last_modified=headers.get('Last-Modified'))
    try:
        if not data or 'html' in (headers.get('Content-Type') or '').lower() or data.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            raise SourceFailure('not_csv_download')
        if metadata:
            after, _ = fetch(config.metadata_url, limit=2*1024*1024, config=config)
            if asset_metadata(after) != metadata:
                raise SourceFailure('source_changed_during_download')
            if len(data) != metadata['byte_size']:
                raise SourceFailure('publisher_size_mismatch')
            if metadata['publisher_sha256'] and digest != metadata['publisher_sha256']:
                raise SourceFailure('publisher_digest_mismatch')
        evidence['digest_matches_publisher'] = bool(metadata and metadata['publisher_sha256'])
    except SourceFailure as exc:
        evidence['integrity_error'] = exc.code
        raise SourceFailure(exc.code,data=data,evidence=evidence) from None
    return data,evidence
