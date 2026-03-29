"""Utilities used by multiple addons and tools."""

from __future__ import annotations

import datetime
import json
import re
from fnmatch import fnmatch
from functools import lru_cache
from hashlib import md5, sha256
from urllib.parse import urlparse
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from jupyterlite_core.constants import ALL_JSON, JSON_FMT, UTF8

from .constants import ALL_WHL, RE_WHEEL_DIST_NAME


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from pkginfo import Distribution


@lru_cache(100)
def normalize_names(*names: str) -> list[NormalizedName]:
    """Return a normalized set of Python package names."""
    from packaging.utils import canonicalize_name

    return sorted({*map(canonicalize_name, names)})


@lru_cache(1000)
def get_wheel_metadata(filename: str) -> Distribution | None:
    """Try to get cached metadata for a Python distribution."""
    import pkginfo

    return pkginfo.get_metadata(filename)


def get_wheel_name(wheel: Path) -> NormalizedName | None:
    """Get the normalized package name contained in a wheel"""
    from packaging.utils import canonicalize_name

    info = get_wheel_metadata(f"{wheel}")
    if not (info and info.name):
        return None
    return canonicalize_name(info.name)


def wheel_to_pep508(path_or_url: str) -> str | None:
    """Get a PEP-508 direct URL from a path or URL."""
    from packaging.utils import canonicalize_name

    url = urlparse(path_or_url)

    dist_name_match = re.search(RE_WHEEL_DIST_NAME, path_or_url)

    if not dist_name_match:
        return None

    dist_name = canonicalize_name(dist_name_match.groupdict()["name"])
    final_url = path_or_url if url.scheme else Path(path_or_url).resolve().as_uri()

    return f"{dist_name} @ {final_url}"


def is_pyodide_wheel(filename: str, patterns: list[str] | None = None) -> bool:
    """get whether a wheel is a known-good pyodide wheel."""
    return any(fnmatch(filename, f"**/*{p}") for p in patterns or ALL_WHL)


def list_wheels(
    *wheel_dirs: Path,
    patterns: list[str] | None = None,
    recursive: bool = False,
) -> list[Path]:
    """get all wheels we know how to handle in a directory"""
    wheels = []
    for wheel_dir in wheel_dirs:
        if not wheel_dir.is_dir():
            continue
        wheels += sorted((wheel_dir.rglob if recursive else wheel_dir.glob)("*.whl"))
    return [w for w in wheels if is_pyodide_wheel(w, patterns)]


def get_wheel_fileinfo(whl_path: Path) -> tuple[str, str, dict[str, Any]]:
    """Generate a minimal Warehouse-like JSON API entry from a wheel"""
    metadata = get_wheel_metadata(str(whl_path))
    if not (metadata and metadata.name and metadata.version):  # pragma: no cover
        msg = f"Could not get metadata for {whl_path}"
        raise ValueError(msg)

    whl_stat = whl_path.stat()
    whl_isodate = (
        datetime.datetime.fromtimestamp(whl_stat.st_mtime, tz=datetime.timezone.utc)
        .isoformat()
        .split("+")[0]
        + "Z"
    )
    whl_bytes = whl_path.read_bytes()
    whl_sha256 = sha256(whl_bytes).hexdigest()
    whl_md5 = md5(whl_bytes).hexdigest()

    release = {
        "comment_text": "",
        "digests": {"sha256": whl_sha256, "md5": whl_md5},
        "downloads": -1,
        "filename": whl_path.name,
        "has_sig": False,
        "md5_digest": whl_md5,
        "packagetype": "bdist_wheel",
        "python_version": "py3",
        "requires_python": metadata.requires_python,
        "size": whl_stat.st_size,
        "upload_time": whl_isodate,
        "upload_time_iso_8601": whl_isodate,
        "url": f"./{whl_path.name}",
        "yanked": False,
        "yanked_reason": None,
    }

    return metadata.name, metadata.version, release


def get_wheel_index(wheels, metadata=None):
    """Get the raw python object representing a wheel index for a bunch of wheels

    If given, metadata should be a dictionary of the form:

        {Path: (name, version, metadata)}
    """
    metadata = metadata or {}
    all_json = {}

    for whl_path in sorted(wheels):
        name, version, release = metadata.get(whl_path, get_wheel_fileinfo(whl_path))
        # https://peps.python.org/pep-0503/#normalized-names
        normalized_name = re.sub(r"[-_.]+", "-", name).lower()
        if normalized_name not in all_json:  # pragma: no cover
            all_json[normalized_name] = {"releases": {}}
        all_json[normalized_name]["releases"][version] = [release]

    return all_json


def write_wheel_index(whl_dir, metadata=None):
    """Write out an all.json for a directory of wheels"""
    wheel_index = Path(whl_dir) / ALL_JSON
    index_data = get_wheel_index(list_wheels(whl_dir), metadata)
    wheel_index.write_text(json.dumps(index_data, **JSON_FMT) + "\n", **UTF8)
    return wheel_index


def patch_dict(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Recursively update a dict in-place with new values."""
    for key, value in new.items():
        if value is None:
            old.pop(key, None)
        elif isinstance(value, dict):
            old[key] = patch_dict(old.get(key, {}), value)
        else:
            old[key] = value
    return old


def patch_json_path(old_path: Path, patch: dict[str, Any]) -> None:
    """Update an on-disk JSON file with a patch."""
    old = patch_dict(json.loads(old_path.read_text(**UTF8)), patch)
    old_path.write_text(json.dumps(old, **JSON_FMT) + "\n", **UTF8)
