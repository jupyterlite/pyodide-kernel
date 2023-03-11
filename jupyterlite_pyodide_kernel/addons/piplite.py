"""a JupyterLite addon for supporting piplite wheels"""

import datetime
import json
import re
import urllib.parse
import functools
from hashlib import md5, sha256
from pathlib import Path
from typing import Tuple as _Tuple, List as _List
import zipfile
import warnings

import doit.tools
from jupyterlite_core.constants import (
    ALL_JSON,
    JSON_FMT,
    JUPYTERLITE_JSON,
    LAB_EXTENSIONS,
    UTF8,
)
from jupyterlite_core.trait_types import TypedTuple
from traitlets import Unicode, Bool

from ._base import _BaseAddon

from ..constants import (
    ALL_WHL,
    NOARCH_WHL,
    PIPLITE_INDEX_SCHEMA,
    PIPLITE_URLS,
    PKG_JSON_PIPLITE,
    PKG_JSON_WHEELDIR,
    PYODIDE_KERNEL_NPM_NAME,
    PYODIDE_MARKER_ENV,
    PYPI_WHEELS,
    KERNEL_SETTINGS_SCHEMA,
    REPODATA_JSON,
    REPODATA_SCHEMA,
    REPODATA_URLS,
    TOP_LEVEL_TXT,
    WHL_RECORD,
)

from jupyterlite_core.manager import LiteManager


class PipliteAddon(_BaseAddon):
    __all__ = ["post_init", "build", "post_build", "check"]

    # CLI
    aliases = {
        "piplite-wheels": "PipliteAddon.piplite_urls",
    }

    flags = {
        "piplite-install-on-import": (
            {"PipliteAddon": {"install_on_import": True}},
            "Index wheels by import names to install when imported",
        )
    }

    # traits
    piplite_urls: _Tuple[str] = TypedTuple(
        Unicode(),
        help="Local paths or URLs of piplite-compatible wheels to copy and index",
    ).tag(config=True)

    install_on_import: bool = Bool(
        False, help="Index wheels by import names to install when imported"
    ).tag(config=True)

    @property
    def output_wheels(self) -> Path:
        """where wheels will go in the output folder"""
        return self.manager.output_dir / PYPI_WHEELS

    @property
    def wheel_cache(self) -> Path:
        """where wheels will go in the cache folder"""
        return self.manager.cache_dir / "wheels"

    @property
    def output_extensions(self) -> Path:
        """where labextensions will go in the output folder"""
        return self.manager.output_dir / LAB_EXTENSIONS

    @property
    def output_kernel_extension(self) -> Path:
        """the location of the Pyodide kernel labextension static assets"""
        return self.output_extensions / PYODIDE_KERNEL_NPM_NAME

    @property
    def schemas(self) -> Path:
        """the path to the as-deployed schema in the labextension"""
        return self.output_kernel_extension / "static/schema"

    @property
    def piplite_schema(self) -> Path:
        """the schema for Warehouse-like API indexes"""
        return self.schemas / PIPLITE_INDEX_SCHEMA

    @property
    def repodata_schema(self) -> Path:
        """the schema for pyodide repodata"""
        return self.schemas / REPODATA_SCHEMA

    @property
    def settings_schema(self) -> Path:
        """the schema for the Pyodide kernel labextension"""
        return self.schemas / KERNEL_SETTINGS_SCHEMA

    def post_init(self, manager: LiteManager):
        """handle downloading of wheels"""
        for path_or_url in self.piplite_urls:
            yield from self.resolve_one_wheel(path_or_url)

    def build(self, manager: LiteManager):
        """yield a doit task to copy each local wheel into the output_dir"""
        for wheel in list_wheels(manager.lite_dir / PYPI_WHEELS):
            yield from self.resolve_one_wheel(str(wheel.resolve()))

    def post_build(self, manager: LiteManager):
        """update the root jupyter-lite.json with user-provided ``pipliteUrls``"""
        jupyterlite_json = manager.output_dir / JUPYTERLITE_JSON
        whl_metas = []
        whl_repos = []

        wheels = list_wheels(self.output_wheels)
        pkg_jsons = sorted(
            [
                *self.output_extensions.glob("*/package.json"),
                *self.output_extensions.glob("@*/*/package.json"),
            ]
        )

        for wheel in wheels:
            whl_meta = self.wheel_cache / f"{wheel.name}.meta.json"
            whl_metas += [whl_meta]
            yield self.task(
                name=f"meta:{whl_meta.name}",
                doc=f"ensure {wheel} metadata",
                file_dep=[wheel],
                actions=[
                    (doit.tools.create_folder, [whl_meta.parent]),
                    (self.index_wheel, [wheel, whl_meta]),
                ],
                targets=[whl_meta],
            )

            if self.install_on_import:
                whl_repo = self.wheel_cache / f"{wheel.name}.repodata.json"
                whl_repos += [whl_repo]

                yield self.task(
                    name=f"meta:{whl_repo.name}",
                    doc=f"ensure {wheel} repodata",
                    file_dep=[wheel],
                    actions=[
                        (doit.tools.create_folder, [whl_repo.parent]),
                        (self.repodata_wheel, [wheel, whl_repo]),
                    ],
                    targets=[whl_repo],
                )

        if whl_metas or whl_repos or pkg_jsons:
            whl_index = self.manager.output_dir / PYPI_WHEELS / ALL_JSON
            repo_index = self.manager.output_dir / PYPI_WHEELS / REPODATA_JSON

            yield self.task(
                name="patch",
                doc=f"ensure {JUPYTERLITE_JSON} includes any piplite wheels",
                file_dep=[*whl_metas, *whl_repos, jupyterlite_json],
                actions=[
                    (
                        self.patch_jupyterlite_json,
                        [
                            jupyterlite_json,
                            whl_index,
                            repo_index,
                            whl_metas,
                            whl_repos,
                            pkg_jsons,
                        ],
                    )
                ],
                targets=[whl_index, repo_index],
            )

    def check(self, manager: LiteManager):
        """verify that all JSON for settings and Warehouse API are valid"""

        for config_path in self.get_output_config_paths():
            yield from self.check_one_config_path(config_path)

    def check_one_config_path(self, config_path: Path):
        """verify the settings and Warehouse API for a single jupyter-lite config"""
        if not config_path.exists():
            return

        rel_path = config_path.relative_to(self.manager.output_dir)
        plugin_config = self.get_pyodide_settings(config_path)

        yield from self.check_index_urls(
            plugin_config.get(PIPLITE_URLS, []), self.piplite_schema
        )

        if self.install_on_import:
            yield from self.check_index_urls(
                plugin_config.get(REPODATA_URLS, []), self.repodata_schema
            )

        yield self.task(
            name=f"validate:settings:{rel_path}",
            doc=f"validate {config_path} with the pyodide kernel settings schema",
            actions=[
                (
                    self.validate_one_json_file,
                    [self.settings_schema, None, plugin_config],
                ),
            ],
            file_dep=[self.settings_schema, config_path],
        )

    def check_index_urls(self, raw_urls, schema: Path):
        """Validate URLs against a schema."""
        for raw_url in raw_urls:
            if not raw_url.startswith("./"):
                continue

            url = raw_url.split("?")[0].split("#")[0]

            path = self.manager.output_dir / url

            if not path.exists():
                continue

            yield self.task(
                name=f"validate:{raw_url}",
                doc=f"validate {url} against {schema}",
                file_dep=[path],
                actions=[(self.validate_one_json_file, [schema, path])],
            )

    def resolve_one_wheel(self, path_or_url):
        """download a single wheel, and copy to the cache"""
        local_path = None
        will_fetch = False

        if re.findall(r"^https?://", path_or_url):
            url = urllib.parse.urlparse(path_or_url)
            name = url.path.split("/")[-1]
            dest = self.wheel_cache / name
            local_path = dest
            if not dest.exists():
                yield self.task(
                    name=f"fetch:{name}",
                    doc=f"fetch the wheel {name}",
                    actions=[(self.fetch_one, [path_or_url, dest])],
                    targets=[dest],
                )
                will_fetch = True
        else:
            local_path = (self.manager.lite_dir / path_or_url).resolve()

        if local_path.is_dir():
            for wheel in list_wheels(local_path):
                yield from self.copy_wheel(wheel)
        elif local_path.exists() or will_fetch:
            suffix = local_path.suffix

            if suffix == ".whl":
                yield from self.copy_wheel(local_path)

        else:  # pragma: no cover
            raise FileNotFoundError(path_or_url)

    def copy_wheel(self, wheel: Path):
        """copy one wheel to output"""
        dest = self.output_wheels / wheel.name
        if dest == wheel:  # pragma: no cover
            return
        yield self.task(
            name=f"copy:whl:{wheel.name}",
            file_dep=[wheel],
            targets=[dest],
            actions=[(self.copy_one, [wheel, dest])],
        )

    def patch_jupyterlite_json(
        self,
        config_path: Path,
        whl_index: Path,
        repo_index: Path,
        whl_metas: _List[Path],
        whl_repos: _List[Path],
        pkg_jsons: _List[Path],
    ):
        """add the piplite wheels to jupyter-lite.json"""
        plugin_config = self.get_pyodide_settings(config_path)
        # first add user-specified wheels to warehouse
        warehouse_urls = self.update_warehouse_index(
            plugin_config, whl_index, whl_metas
        )
        repodata_urls = []

        # ...then maybe add repodata
        if self.install_on_import:
            repodata_urls = self.update_repo_index(plugin_config, repo_index, whl_repos)

        # ...then add wheels from federated extensions...
        if pkg_jsons:
            for pkg_json in pkg_jsons:
                pkg_data = json.loads(pkg_json.read_text(**UTF8))
                wheel_dir = pkg_data.get(PKG_JSON_PIPLITE, {}).get(PKG_JSON_WHEELDIR)
                if wheel_dir:
                    pkg_whl_index = pkg_json.parent / wheel_dir / ALL_JSON
                    if pkg_whl_index.exists():
                        pkg_whl_index_url_with_sha = self.get_index_urls(pkg_whl_index)[
                            1
                        ]
                        if pkg_whl_index_url_with_sha not in warehouse_urls:
                            warehouse_urls += [pkg_whl_index_url_with_sha]

                    pkg_repo_index = pkg_json.parent / wheel_dir / REPODATA_JSON
                    if self.install_on_import and pkg_repo_index.exists():
                        pkg_repo_index_url_with_sha = self.get_index_urls(
                            pkg_repo_index
                        )[1]
                        if pkg_repo_index_url_with_sha not in repodata_urls:
                            repodata_urls += [pkg_repo_index_url_with_sha]

        needs_save = False

        # ... and only update if actually changed
        if warehouse_urls and plugin_config.get(PIPLITE_URLS) != warehouse_urls:
            plugin_config[PIPLITE_URLS] = warehouse_urls
            needs_save = True

        if self.install_on_import:
            if repodata_urls and plugin_config.get(REPODATA_URLS) != repodata_urls:
                plugin_config[REPODATA_URLS] = repodata_urls
                needs_save = True

        if needs_save:
            self.set_pyodide_settings(config_path, plugin_config)

    def update_warehouse_index(self, plugin_config, whl_index: Path, whl_metas):
        """Ensure the warehouse index is up-to-date, reporting new URLs."""
        old_warehouse_urls = plugin_config.get(PIPLITE_URLS, [])
        if not whl_metas:
            return old_warehouse_urls
        new_urls = []
        metadata = {}
        for whl_meta in whl_metas:
            meta = json.loads(whl_meta.read_text(**UTF8))
            whl = self.output_wheels / whl_meta.name.replace(".json", "")
            metadata[whl] = meta["name"], meta["version"], meta["release"]

        write_wheel_index(self.output_wheels, metadata)
        whl_index_url, whl_index_url_with_sha = self.get_index_urls(whl_index)

        added_build = False

        for url in old_warehouse_urls:
            if url.split("#")[0].split("?")[0] == whl_index_url:
                new_urls += [whl_index_url_with_sha]
                added_build = True
            else:
                new_urls += [url]

        if not added_build:
            new_urls = [whl_index_url_with_sha, *new_urls]

        return new_urls

    def update_repo_index(self, plugin_config, repo_index: Path, whl_repos):
        """Ensure the repodata index is up-to-date, reporting new URLs."""
        old_urls = plugin_config.get(REPODATA_URLS, [])
        if not whl_repos:
            return old_urls
        new_urls = []
        metadata = {}
        for whl_repo in whl_repos:
            meta = json.loads(whl_repo.read_text(**UTF8))
            whl = self.output_wheels / whl_repo.name.replace(".json", "")
            metadata[whl] = meta["name"], meta["version"], meta

        write_repo_index(self.output_wheels, metadata)
        repo_index_url, repo_index_url_with_sha = self.get_index_urls(repo_index)

        added_build = False

        for url in old_urls:
            if url.split("#")[0].split("?")[0] == repo_index_url:
                new_urls += [repo_index_url_with_sha]
                added_build = True
            else:
                new_urls += [url]

        if not added_build:
            new_urls = [repo_index_url_with_sha, *new_urls]

        return new_urls

    def get_index_urls(self, index_path: Path):
        """Get output_dir relative URLs for an index file."""
        index_sha256 = sha256(index_path.read_bytes()).hexdigest()
        index_url = f"./{index_path.relative_to(self.manager.output_dir).as_posix()}"
        index_url_with_sha = f"{index_url}?sha256={index_sha256}"
        return index_url, index_url_with_sha

    def index_wheel(self, whl_path: Path, whl_meta: Path):
        """Generate an intermediate file representation to merge with other releases"""
        name, version, release = get_wheel_fileinfo(whl_path)
        whl_meta.write_text(
            json.dumps(dict(name=name, version=version, release=release), **JSON_FMT),
            **UTF8,
        )
        self.maybe_timestamp(whl_meta)

    def repodata_wheel(self, whl_path: Path, whl_repo: Path) -> None:
        """Write out the repodata for a wheel."""
        pkg_entry = get_wheel_repodata(whl_path)[2]
        whl_repo.write_text(
            json.dumps(pkg_entry, **JSON_FMT),
            **UTF8,
        )
        self.maybe_timestamp(whl_repo)


def list_wheels(wheel_dir: Path) -> _List[Path]:
    """Get all wheels we know how to handle in a directory"""
    return sorted(sum([[*wheel_dir.glob(f"*{whl}")] for whl in ALL_WHL], []))


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
    depends = get_wheel_depends(whl_path)
    modules = get_wheel_modules(whl_path)
    normalized_name = get_normalized_name(name)
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


def get_wheel_modules(whl_path: Path) -> _List[str]:
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

    depends: _List[str] = []

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


def get_wheel_index(wheels: _List[Path], metadata=None):
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


def get_repo_index(wheels: _List[Path], metadata=None):
    """Get the data for a ``repodata.json``."""
    metadata = metadata or {}
    repodata_json = {"packages": {}}

    for whl_path in sorted(wheels):
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


def write_repo_index(whl_dir: Path, metadata=None) -> Path:
    """Write out a ``repodata.json`` for a directory of wheels."""
    repo_index = Path(whl_dir) / REPODATA_JSON
    index_data = get_repo_index(list_wheels(whl_dir), metadata)
    repo_index.write_text(json.dumps(index_data, **JSON_FMT), **UTF8)
    return repo_index
