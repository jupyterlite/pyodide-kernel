"""Utilities used by multiple addons and tools."""

from __future__ import annotations
import datetime
import re
from typing import Any
from hashlib import md5, sha256
from pathlib import Path
import json

from .constants import ALL_WHL
from jupyterlite_core.constants import ALL_JSON, JSON_FMT, UTF8


def list_wheels(
    *wheel_dirs: Path,
    patterns: list[str] | None = None,
    recursive: bool = False,
) -> list[Path]:
    """get all wheels we know how to handle in a directory"""
    patterns = patterns or ALL_WHL
    wheels = []
    for wheel_dir in wheel_dirs:
        if not wheel_dir.is_dir():
            continue
        for pattern in patterns:
            wheels += [
                *(wheel_dir.rglob if recursive else wheel_dir.glob)(f"*{pattern}")
            ]
    return sorted(wheels)


def get_wheel_fileinfo(whl_path: Path) -> tuple[str, str, dict[str, Any]]:
    """Generate a minimal Warehouse-like JSON API entry from a wheel"""
    import pkginfo

    metadata = pkginfo.get_metadata(str(whl_path))
    if not (metadata and metadata.name and metadata.version):
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
        if normalized_name not in all_json:
            all_json[normalized_name] = {"releases": {}}
        all_json[normalized_name]["releases"][version] = [release]

    return all_json


def write_wheel_index(whl_dir, metadata=None):
    """Write out an all.json for a directory of wheels"""
    wheel_index = Path(whl_dir) / ALL_JSON
    index_data = get_wheel_index(list_wheels(whl_dir), metadata)
    wheel_index.write_text(json.dumps(index_data, **JSON_FMT), **UTF8)
    return wheel_index
