"""POSIX advisory sidecar locks for mutating and audited workflows."""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import IntegrityError


def lock_path_for(resource: Path) -> Path:
    """Return one stable lock path for relative, absolute, or symlink aliases."""

    resolved = resource.resolve(strict=False)
    return resolved.with_name(f".{resolved.name}.price-tool.lock")


@contextmanager
def advisory_lock(resource: Path) -> Iterator[Path]:
    """Hold an exclusive POSIX lock for the named resource.

    The sidecar is intentionally persistent. Removing lock files after release
    can split waiters across different inodes and defeat serialization.
    """

    lock_path = lock_path_for(resource)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise IntegrityError(f"lock: could not open {lock_path.name}: {exc.strerror or exc}") from exc
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError as exc:
            raise IntegrityError(f"lock: could not acquire {lock_path.name}: {exc.strerror or exc}") from exc
        try:
            yield lock_path
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
