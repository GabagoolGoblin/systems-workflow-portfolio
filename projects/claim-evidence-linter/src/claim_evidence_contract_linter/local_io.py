"""Bounded, local file I/O with duplicate-key-aware JSON parsing."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from .errors import InputError, LocalIOError

MAX_INPUT_BYTES = 1_048_576
MAX_JSON_DEPTH = 100
MAX_JSON_NODES = 100_000


def _reject_constant(token: str) -> None:
    raise InputError(f"non-finite JSON number is not allowed: {token}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def decode_json_bytes(data: bytes, *, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"{label}: input is not valid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except InputError:
        raise
    except json.JSONDecodeError as exc:
        raise InputError(
            f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    except RecursionError as exc:
        # Older CPython JSON scanners hit the interpreter recursion limit before
        # the explicit depth walk below can run; report the same depth boundary.
        raise InputError(f"{label}: JSON exceeds maximum depth {MAX_JSON_DEPTH}") from exc
    except ValueError as exc:
        raise InputError(
            f"{label}: JSON structure or number is outside safe parser limits"
        ) from exc
    stack: list[tuple[Any, int]] = [(value, 1)]
    node_count = 0
    while stack:
        current, depth = stack.pop()
        node_count += 1
        if depth > MAX_JSON_DEPTH:
            raise InputError(f"{label}: JSON exceeds maximum depth {MAX_JSON_DEPTH}")
        if node_count > MAX_JSON_NODES:
            raise InputError(f"{label}: JSON exceeds maximum node count {MAX_JSON_NODES}")
        if type(current) is dict:
            stack.extend((child, depth + 1) for child in current.values())
        elif type(current) is list:
            stack.extend((child, depth + 1) for child in current)
    return value


def read_regular_file(path_value: str | os.PathLike[str]) -> bytes:
    path = Path(path_value)
    if not hasattr(os, "O_NOFOLLOW"):
        raise LocalIOError("this platform cannot enforce no-symlink input reads")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise LocalIOError(f"cannot safely open input file {path}: {exc.strerror}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LocalIOError(f"input is not a regular file: {path}")
        if metadata.st_size > MAX_INPUT_BYTES:
            raise InputError(
                f"input exceeds {MAX_INPUT_BYTES} byte limit: {path}"
            )
        chunks: list[bytes] = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_INPUT_BYTES:
            raise InputError(
                f"input exceeds {MAX_INPUT_BYTES} byte limit: {path}"
            )
        return data
    except OSError as exc:
        raise LocalIOError(f"cannot read input file {path}: {exc.strerror}") from exc
    finally:
        os.close(descriptor)


def load_json_file(path_value: str | os.PathLike[str], *, label: str) -> tuple[Any, bytes]:
    data = read_regular_file(path_value)
    return decode_json_bytes(data, label=label), data


def write_new_private_file(path_value: str | os.PathLike[str], data: bytes) -> None:
    """Create one mode-0600 file; never follow a symlink or overwrite a path."""

    path = Path(path_value)
    if not hasattr(os, "O_NOFOLLOW"):
        raise LocalIOError("this platform cannot enforce no-symlink output creation")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise LocalIOError(
            f"refusing or unable to create new output file {path}: {exc.strerror}"
        ) from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written == 0:
                raise LocalIOError(f"zero-byte write while creating output file {path}")
            view = view[written:]
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
    except OSError as exc:
        raise LocalIOError(f"cannot write output file {path}: {exc.strerror}") from exc
    finally:
        os.close(descriptor)
