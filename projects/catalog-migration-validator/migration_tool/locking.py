"""Persistent POSIX sidecar locks for coordinated local writers."""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import IntegrityError


def resource_key(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise IntegrityError(f"lock: could not resolve {path.name}: {exc}") from exc


def sidecar_path(path: Path) -> Path:
    resource = resource_key(path)
    return resource.with_name(f".{resource.name}.migration.lock")


@contextmanager
def locked_sidecar(path: Path) -> Iterator[Path]:
    """Hold an exclusive advisory lock; leave its inode in place on release."""

    lock_path = sidecar_path(path)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise IntegrityError(
            f"lock: could not open {lock_path.name}: {exc.strerror or exc}"
        ) from exc
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError as exc:
            raise IntegrityError(
                f"lock: could not acquire {lock_path.name}: {exc.strerror or exc}"
            ) from exc
        try:
            yield lock_path
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
