"""Utilities used by multiple addons and tools."""

from __future__ import annotations

import json
import re
from fnmatch import fnmatch
from functools import lru_cache
from urllib.parse import urlparse
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from jupyterlite_core.constants import JSON_FMT, UTF8

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
