"""Read exactly the atomic checkpoint, without importing writer/lock/recovery functionality."""
import json
import os
import stat
from pathlib import Path

MAX_STATUS_BYTES = 1024 * 1024


class RefreshStatusRepository:
    def __init__(self, directory: Path):
        self.directory = directory

    def read(self):
        try:
            # Refuse symlinks/non-regular files; never follow a FIFO or create any state.
            descriptor = os.open(self.directory/'status.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATUS_BYTES:
                    return 'invalid', None
                data = os.read(descriptor, MAX_STATUS_BYTES + 1)
            finally:
                os.close(descriptor)
            if len(data) > MAX_STATUS_BYTES:
                return 'invalid', None
            raw = json.loads(data.decode('utf-8'))
            return ('available', raw) if isinstance(raw, dict) else ('invalid', None)
        except FileNotFoundError:
            return 'missing', None
        except (UnicodeError, ValueError):
            return 'invalid', None
        except OSError:
            return 'unreadable', None
