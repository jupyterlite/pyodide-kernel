"""Utilties for working with wheels and package metadata."""
import datetime
import functools
import json
import re
import warnings
import zipfile
from hashlib import md5, sha256
from pathlib import Path
from typing import List, Optional

from jupyterlite_core.constants import (
    ALL_JSON,
    JSON_FMT,
    UTF8,
)

from .constants import (
    ALL_WHL,
    NOARCH_WHL,
    PYODIDE_MARKER_ENV,
    REPODATA_EXTRA_DEPENDS,
    REPODATA_JSON,
    TOP_LEVEL_TXT,
    WHL_RECORD,
)


def list_wheels(wheel_dir: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """Get all files we know how to handle in a directory"""
    extensions = extensions or ALL_WHL
    wheelish = sum([[*wheel_dir.glob(f"*{ext}")] for ext in extensions], [])
    return sorted(wheelish)


def get_wheel_fileinfo(whl_path: Path):
    """Generate a minimal Warehouse-like JSON API entry from a wheel"""
    metadata = get_wheel_pkginfo(whl_path)
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


def get_wheel_repodata(whl_path: Path):
    """Get pyodide-compatible `repodata.json` fragment for a wheel.

    This only knows how to handle "simple" noarch wheels, without extra binary
    depnendencies.
    """
    name, version, release = get_wheel_fileinfo(whl_path)
    normalized_name = get_normalized_name(name)
    depends = get_wheel_depends(whl_path) + REPODATA_EXTRA_DEPENDS.get(
        normalized_name, []
    )
    modules = get_wheel_modules(whl_path)
    pkg_entry = {
        "name": normalized_name,
        "version": version,
        "file_name": whl_path.name,
        "install_dir": "site" if whl_path.name.endswith(NOARCH_WHL) else "dynlib",
        "sha256": release["digests"]["sha256"],
        "imports": modules,
        "depends": depends,
    }
    return normalized_name, version, pkg_entry


@functools.lru_cache(1000)
def get_wheel_pkginfo(whl_path: Path):
    """Return the as-parsed distribution information from ``pkginfo``."""
    import pkginfo

    return pkginfo.get_metadata(str(whl_path))


def get_wheel_modules(whl_path: Path) -> List[str]:
    """Get the exported top-level modules from a wheel."""
    top_levels = {}
    records = {}
    with zipfile.ZipFile(whl_path) as zf:
        for zipinfo in zf.infolist():
            if zipinfo.filename.endswith(TOP_LEVEL_TXT):
                top_levels[zipinfo.filename] = (
                    zf.read(zipinfo).decode("utf-8").strip().splitlines()
                )
            if zipinfo.filename.endswith(WHL_RECORD):
                records[zipinfo.filename] = (
                    zf.read(zipinfo).decode("utf-8").strip().splitlines()
                )

    if len(top_levels):
        sorted_top_levels = sorted(top_levels.items(), key=lambda x: len(x[0]))
        return sorted_top_levels[0][1]

    if len(records):
        sorted_records = sorted(records.items(), key=lambda x: len(x[0]))
        # discard hash, length, etc.
        record_bits = sorted(
            [line.split(",")[0].split("/") for line in sorted_records[0][1]],
            key=lambda x: len(x),
        )

        imports = set()
        inits = []
        for bits in record_bits:
            if bits[0].endswith(".data") or bits[0].endswith(".dist-info"):
                continue
            elif bits[0].endswith(".py"):
                # this is a single-file module that gets dropped in site-packages
                imports.add(bits[0].replace(".py", ""))
            elif bits[-1].endswith("__init__.py"):
                # this might be a namespace package
                inits += [bits]

        if not imports and inits:
            for init_bits in inits:
                dotted = ".".join(init_bits[:-1])
                if any(f"{imp}." in dotted for imp in imports):
                    continue
                imports.add(dotted)

        if imports:
            return sorted(imports)

    # this should probably never happen
    raise ValueError(f"{whl_path} contains neither {TOP_LEVEL_TXT} nor {WHL_RECORD}")


def get_wheel_depends(whl_path: Path):
    """Get the normalize runtime distribution dependencies from a wheel."""
    from packaging.requirements import Requirement

    metadata = get_wheel_pkginfo(str(whl_path))

    depends: List[str] = []

    for dep_str in metadata.requires_dist:
        if dep_str.endswith(";"):
            dep_str = dep_str[:-1]
        req = Requirement(dep_str)
        if req.marker is None or req.marker.evaluate(PYODIDE_MARKER_ENV):
            depends += [get_normalized_name(req.name)]

    return sorted(set(depends))


def get_normalized_name(raw_name: str) -> str:
    """Get a PEP 503 normalized name for a python package.

    https://peps.python.org/pep-0503/#normalized-names
    """
    return re.sub(r"[-_.]+", "-", raw_name).lower()


def get_wheel_index(wheels: List[Path], metadata=None):
    """Get the raw python object representing a wheel index for a bunch of wheels

    If given, metadata should be a dictionary of the form:

        {Path: (name, version, metadata)}
    """
    metadata = metadata or {}
    all_json = {}

    for whl_path in sorted(wheels):
        name, version, release = metadata.get(whl_path) or get_wheel_fileinfo(whl_path)
        normalized_name = get_normalized_name(name)
        if normalized_name not in all_json:
            all_json[normalized_name] = {"releases": {}}
        all_json[normalized_name]["releases"][version] = [release]

    return all_json


def get_repo_index(wheelish: List[Path], metadata=None):
    """Get the data for a ``repodata.json``."""
    metadata = metadata or {}
    repodata_json = {"packages": {}}

    for whl_path in sorted(wheelish):
        name, version, pkg_entry = metadata.get(whl_path) or get_wheel_repodata(
            whl_path
        )
        normalized_name = get_normalized_name(name)
        if normalized_name in repodata_json["packages"]:
            old_version = repodata_json["packages"][normalized_name]["version"]
            warnings.warn(
                f"{normalized_name} {old_version} will be clobbered by {version}"
            )
        repodata_json["packages"][normalized_name] = pkg_entry

    return repodata_json


def write_wheel_index(whl_dir: Path, metadata=None) -> Path:
    """Write out an ``all.json`` for a directory of wheels."""
    wheel_index = Path(whl_dir) / ALL_JSON
    index_data = get_wheel_index(list_wheels(whl_dir), metadata)
    wheel_index.write_text(json.dumps(index_data, **JSON_FMT), **UTF8)
    return wheel_index


def write_repo_index(whl_dir: Path, metadata=None, extensions=None) -> Path:
    """Write out a ``repodata.json`` for a directory of wheels."""
    repo_index = Path(whl_dir) / REPODATA_JSON
    wheelish = list_wheels(whl_dir, extensions)

    index_data = get_repo_index(wheelish, metadata)
    repo_index.write_text(json.dumps(index_data, **JSON_FMT), **UTF8)
    return repo_index
