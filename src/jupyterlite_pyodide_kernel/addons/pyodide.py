"""a JupyterLite addon for supporting the pyodide distribution"""

import os
import re
import urllib.parse
import json
from pathlib import Path
from copy import deepcopy
from typing import Optional, List, Dict, Any

import doit.tools
from jupyterlite_core.manager import LiteManager
from jupyterlite_core.constants import (
    JUPYTERLITE_JSON,
    UTF8,
    JSON_FMT,
)
from traitlets import Unicode, default, Bool

from ._base import _BaseAddon
from ..constants import (
    ALL_WHEELISH,
    PKG_JSON_SCHEMA,
    PYODIDE,
    PYODIDE_JS,
    PYODIDE_REPODATA,
    PYODIDE_URL,
    PYPI_WHEELS,
    REPODATA_JSON,
    REPODATA_SCHEMA,
    REPODATA_URLS,
)
from ..wheel_utils import write_repo_index, list_wheels, get_wheel_repodata


class PyodideAddon(_BaseAddon):
    __all__ = ["status", "post_init", "build", "post_build", "check"]

    # CLI
    aliases = {
        "pyodide": "PyodideAddon.pyodide_url",
    }

    flags = {
        "pyodide-install-on-import": (
            {"PyodideAddon": {"install_on_import": True}},
            "Index wheels by import names to install when imported",
        )
    }

    # traits
    pyodide_url: str = Unicode(
        allow_none=True, help="Local path or URL of a pyodide distribution tarball"
    ).tag(config=True)

    install_on_import: bool = Bool(
        False, help="Index wheels by import names to install when imported"
    ).tag(config=True)

    @default("pyodide_url")
    def _default_pyodide_url(self):
        return os.environ.get("JUPYTERLITE_PYODIDE_URL")

    @property
    def pyodide_cache(self):
        """where pyodide stuff will go in the cache folder"""
        return self.manager.cache_dir / PYODIDE

    @property
    def output_pyodide(self):
        """where labextensions will go in the output folder"""
        return self.manager.output_dir / "static" / PYODIDE

    @property
    def well_known_pyodide(self):
        """a well-known path where pyodide might be stored"""
        return self.manager.lite_dir / "static" / PYODIDE

    @property
    def repodata_schema(self) -> Path:
        """the schema for pyodide repodata"""
        return self.schemas / REPODATA_SCHEMA

    @property
    def package_json_schema(self) -> Path:
        """the schema for pyodide repodata"""
        return self.schemas / PKG_JSON_SCHEMA

    @property
    def well_known_repodata(self) -> Path:
        return self.well_known_wheels / REPODATA_JSON

    @property
    def well_known_repo_packages(self) -> Dict[str, Dict[str, Any]]:
        if not self.well_known_repodata.exists():
            return {}
        return json.loads(self.well_known_repodata.read_text(**UTF8))["packages"]

    def status(self, manager: LiteManager):
        """report on the status of pyodide"""
        yield self.task(
            name="pyodide",
            actions=[
                lambda: print(
                    f"     URL: {self.pyodide_url}",
                ),
                lambda: print(f" archive: {[*self.pyodide_cache.glob('*.bz2')]}"),
                lambda: print(
                    f"   cache: {len([*self.pyodide_cache.rglob('*')])} files",
                ),
                lambda: print(
                    f"   local: {len([*self.well_known_pyodide.rglob('*')])} files"
                ),
            ],
        )

    def post_init(self, manager: LiteManager):
        """handle downloading of pyodide"""
        if self.pyodide_url is None:
            return

        yield from self.cache_pyodide(self.pyodide_url)

    def build(self, manager: LiteManager):
        """copy a local (cached or well-known) pyodide into the output_dir"""
        cached_pyodide = self.pyodide_cache / PYODIDE / PYODIDE

        the_pyodide = None

        if self.well_known_pyodide.exists():
            the_pyodide = self.well_known_pyodide
        elif self.pyodide_url is not None:
            the_pyodide = cached_pyodide

        if the_pyodide:
            file_dep = [
                p
                for p in the_pyodide.rglob("*")
                if not (p.is_dir() or self.is_ignored_sourcemap(p.name))
            ]

            yield self.task(
                name="copy:pyodide",
                file_dep=file_dep,
                targets=[
                    self.output_pyodide / p.relative_to(the_pyodide) for p in file_dep
                ],
                actions=[(self.copy_one, [the_pyodide, self.output_pyodide])],
            )

        for package_name, package_info in self.well_known_repo_packages.items():
            yield from self.cache_one_repo_package(package_name, package_info)

    def post_build(self, manager):
        """configure jupyter-lite.json for pyodide"""
        repo_index: Optional[Path] = None
        jupyterlite_json = manager.output_dir / JUPYTERLITE_JSON
        file_dep: List[Path] = []
        whl_repos: List[Path] = []
        targets: list[Path] = []

        if self.install_on_import:
            wheels = list_wheels(self.output_wheels)

            # find normal wheels
            for wheel in wheels:
                whl_repo = self.wheel_cache / f"{wheel.name}.repodata.json"
                whl_repos += [whl_repo]
                yield from self.build_one_wheel(wheel, whl_repo)

            # find stdlib/dynlib
            for package_info in self.well_known_repo_packages.values():
                file_name = str(package_info["file_name"])
                url_info = urllib.parse.urlparse(file_name)
                non_wheel = self.output_wheels / Path(url_info.path).name
                non_whl_repo = self.wheel_cache / f"{non_wheel.name}.repodata.json"
                whl_repos += [non_whl_repo]
                yield from self.build_one_non_wheel(
                    package_info, non_wheel, non_whl_repo
                )

            if whl_repos:
                repo_index = self.manager.output_dir / PYPI_WHEELS / REPODATA_JSON
                targets += [repo_index]

        file_dep += whl_repos

        output_js = None

        if self.well_known_pyodide.exists() or self.pyodide_url:
            output_js = self.output_pyodide / PYODIDE_JS
            file_dep += [output_js]

        if whl_repos or output_js:
            yield self.task(
                name=f"patch:{JUPYTERLITE_JSON}",
                doc=(
                    f"ensure {JUPYTERLITE_JSON} includes pyodide.js URL "
                    "and maybe pyodide repodata"
                ),
                file_dep=file_dep,
                actions=[
                    (
                        self.patch_jupyterlite_json,
                        [jupyterlite_json, output_js, whl_repos, repo_index],
                    )
                ],
                targets=targets,
            )

    def build_one_wheel(self, wheel: Path, whl_repo: Path):
        yield self.task(
            name=f"meta:wheel:{whl_repo.name}",
            doc=f"ensure {wheel} repodata",
            file_dep=[wheel],
            actions=[
                (doit.tools.create_folder, [whl_repo.parent]),
                (self.repodata_wheel, [wheel, whl_repo]),
            ],
            targets=[whl_repo],
        )

    def build_one_non_wheel(
        self, package_info: Dict[str, Any], non_wheel: Path, non_whl_repo: Path
    ):
        package_info = deepcopy(package_info)
        package_info["file_name"] = non_wheel.name

        yield self.task(
            name=f"meta:nonwheel:{non_whl_repo.name}",
            doc=f"ensure {non_wheel} repodata",
            file_dep=[self.well_known_repodata, non_wheel],
            actions=[
                (doit.tools.create_folder, [non_whl_repo.parent]),
                lambda: json.dump(package_info, non_whl_repo.open("w"), **JSON_FMT),
            ],
            targets=[non_whl_repo],
        )

    def patch_jupyterlite_json(
        self,
        config_path: Path,
        output_js: Optional[Path],
        whl_repos: List[Path],
        repo_index: Optional[Path],
    ):
        """update ``jupyter-lite.json`` to use the local pyodide and wheels"""
        plugin_config = self.get_pyodide_settings(config_path)
        repodata_urls = []
        needs_save = False

        # ...then maybe add repodata
        if self.install_on_import:
            repodata_urls = self.update_repo_index(plugin_config, repo_index, whl_repos)

            # ...then add wheels from federated extensions...
            for pkg_json in self.get_output_labextension_packages():
                pkg_repodata_url = self.get_package_wheel_index_url(
                    pkg_json, REPODATA_JSON
                )
                if pkg_repodata_url and pkg_repodata_url not in repodata_urls:
                    repodata_urls += [pkg_repodata_url]

        if output_js:
            url = "./{}".format(
                output_js.relative_to(self.manager.output_dir).as_posix()
            )
            if plugin_config.get(PYODIDE_URL) != url:
                needs_save = True
                plugin_config[PYODIDE_URL] = url
        elif plugin_config.get(PYODIDE_URL):
            plugin_config.pop(PYODIDE_URL)
            needs_save = True

        if self.install_on_import:
            if repodata_urls and plugin_config.get(REPODATA_URLS) != repodata_urls:
                plugin_config[REPODATA_URLS] = repodata_urls
                needs_save = True

        if needs_save:
            self.set_pyodide_settings(config_path, plugin_config)

    def check(self, manager: LiteManager):
        """ensure the pyodide configuration is sound"""
        for config_path in self.get_output_config_paths():
            yield from self.check_one_config_path(config_path)

        for pkg_json in self.get_output_labextension_packages():
            yield from self.check_one_package_json(pkg_json)

        if self.install_on_import and self.pyodide_url:
            yield from self.check_repodata_totality()

    def check_one_config_path(self, config_path: Path):
        """verify the JS and repodata for a single jupyter-lite config"""
        if not config_path.exists():
            return

        rel_path = config_path.relative_to(self.manager.output_dir)
        plugin_config = self.get_pyodide_settings(config_path)

        yield self.task(
            name=f"js:{rel_path}",
            file_dep=[config_path],
            actions=[(self.check_pyodide_js_files, [config_path])],
        )

        if self.install_on_import:
            repo_urls = plugin_config.get(REPODATA_URLS, [])
            if repo_urls:
                yield from self.check_index_urls(repo_urls, self.repodata_schema)

    def check_pyodide_js_files(self, config_path: Path):
        """Ensure any local pyodide JS assets exist"""
        config = self.get_pyodide_settings(config_path)

        pyodide_url = config.get(PYODIDE_URL)

        if not pyodide_url or not pyodide_url.startswith("./"):
            return

        pyodide_path = Path(self.manager.output_dir / pyodide_url).parent
        assert pyodide_path.exists(), f"{pyodide_path} not found"
        pyodide_js = pyodide_path / PYODIDE_JS
        assert pyodide_js.exists(), f"{pyodide_js} not found"
        pyodide_repodata = pyodide_path / PYODIDE_REPODATA
        assert pyodide_repodata.exists(), f"{pyodide_repodata} not found"

    def check_one_package_json(self, pkg_json: Path):
        """validate ``pyodideKernel`` settings in a  labextension's ``package.json``"""
        if not pkg_json.exists():  # pragma: no cover
            return

        rel_path = pkg_json.parent.relative_to(self.manager.output_dir)

        yield self.task(
            name=f"validate:package:{rel_path}",
            doc=f"validate pyodideKernel data in {rel_path}",
            actions=[
                (
                    self.validate_one_json_file,
                    [self.package_json_schema, pkg_json],
                ),
            ],
            file_dep=[self.package_json_schema, pkg_json],
        )

    def check_repodata_totality(self):
        """check whether the union of all repodata provides all dependencies."""
        config_paths = sorted(self.get_output_config_paths())
        yield dict(
            name="repo:totality",
            doc="check if the union of all repodata is complete",
            file_dep=config_paths,
            actions=[(self.check_totality, [config_paths])],
        )

    def check_totality(self, config_paths: List[Path]):
        local_repo_packages: Dict[str, Any] = {}
        for config_path in config_paths:
            plugin_config = self.get_pyodide_settings(config_path)
            for repo_url in plugin_config.get(REPODATA_URLS, []):
                url = urllib.parse.urlparse(str(repo_url))
                if url.scheme:
                    self.log.warning(
                        "non-local repodata %s in %s will not be checked",
                        url,
                        config_path.relative_to(self.manager.output_dir),
                    )
                    continue
                repo_path = (config_path.parent / url.path).resolve()
                repo_packages = json.loads(repo_path.read_text(**UTF8))["packages"]
                local_repo_packages[repo_path.parent] = repo_packages

        resolved = {}
        for repo, packages in local_repo_packages.items():
            for package_name, package_info in packages.items():
                file_name = str(package_info["file_name"])
                file_url = urllib.parse.urlparse(file_name)
                if file_url.scheme:
                    resolved[package_name] = "remote"
                else:
                    if (repo / file_url.path).exists():
                        resolved[package_name] = "local"

        missing_deps = {}
        for repo, packages in local_repo_packages.items():
            for package_name, package_info in packages.items():
                for dep in package_info.get("depends", []):
                    if dep not in resolved:
                        missing_deps.setdefault(package_name, []).append(dep)

        if missing_deps:
            print(json.dumps(missing_deps, **JSON_FMT), flush=True)
            message = (
                "Repodata is not self-contained:"
                f"""Dependencies missing for: {sorted(missing_deps)}"""
            )
            raise ValueError(message)

    def cache_pyodide(self, path_or_url):
        """copy pyodide to the cache"""
        if re.findall(r"^https?://", path_or_url):
            url = urllib.parse.urlparse(path_or_url)
            name = url.path.split("/")[-1]
            dest = self.pyodide_cache / name
            local_path = dest
            if not dest.exists():
                yield self.task(
                    name=f"fetch:{name}",
                    doc=f"fetch the pyodide distribution {name}",
                    actions=[(self.fetch_one, [path_or_url, dest])],
                    targets=[dest],
                )
                will_fetch = True
        else:
            local_path = (self.manager.lite_dir / path_or_url).resolve()
            dest = self.pyodide_cache / local_path.name
            will_fetch = False

        if local_path.is_dir():
            all_paths = sorted([p for p in local_path.rglob("*") if not p.is_dir()])
            yield self.task(
                name=f"copy:pyodide:{local_path.name}",
                file_dep=[*all_paths],
                targets=[dest / p.relative_to(local_path) for p in all_paths],
                actions=[(self.copy_one, [local_path, dest])],
            )

        elif local_path.exists() or will_fetch:
            suffix = local_path.suffix
            extracted = self.pyodide_cache / PYODIDE

            if suffix == ".bz2":
                yield from self.extract_pyodide(local_path, extracted)

        else:  # pragma: no cover
            raise FileNotFoundError(path_or_url)

    def extract_pyodide(self, local_path, dest):
        """extract a local pyodide tarball to the cache"""

        yield self.task(
            name="extract:pyodide",
            file_dep=[local_path],
            uptodate=[
                doit.tools.config_changed(
                    dict(no_sourcemaps=self.manager.no_sourcemaps)
                )
            ],
            targets=[
                # there are a lot of js/data files, but we actually talk about these...
                dest / PYODIDE / PYODIDE_JS,
                dest / PYODIDE / PYODIDE_REPODATA,
            ],
            actions=[(self.extract_one, [local_path, dest])],
        )

    def update_repo_index(self, plugin_config, repo_index: Path, whl_repos: List[Path]):
        """Ensure the repodata index is up-to-date, reporting new URLs."""
        old_urls = plugin_config.get(REPODATA_URLS, [])

        if not whl_repos:
            return old_urls

        new_urls = []
        metadata = {}
        for whl_repo in whl_repos:
            meta = json.loads(whl_repo.read_text(**UTF8))
            whl = self.output_wheels / meta["file_name"]
            metadata[whl] = meta["name"], meta["version"], meta

        extensions = None
        if self.install_on_import:
            extensions = ALL_WHEELISH
        write_repo_index(self.output_wheels, metadata, extensions)
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

    def repodata_wheel(self, whl_path: Path, whl_repo: Path) -> None:
        """Write out the repodata for a wheel."""
        pkg_entry = get_wheel_repodata(whl_path)[2]
        whl_repo.write_text(
            json.dumps(pkg_entry, **JSON_FMT),
            **UTF8,
        )
        self.maybe_timestamp(whl_repo)

    def cache_one_repo_package(self, package_name, package_info):
        """ensure a local cache of a repodata package"""
        file_name = str(package_info["file_name"])
        url_info = urllib.parse.urlparse(file_name)
        scheme = url_info.scheme
        cache_path: Optional[Path] = None

        if not scheme:
            on_disk = (self.well_known_wheels / file_name).resolve()
            if on_disk.exists():
                name = on_disk.name
                cache_path = self.wheel_cache / name
                yield self.task(
                    name=f"repo:fetch:{package_name}:{name}",
                    actions=[(self.copy_one, [on_disk, cache_path])],
                    file_dep=[on_disk],
                    targets=[cache_path],
                )

        elif scheme in ["http", "https", "file"]:
            url = file_name
            name = Path(url_info.path).name
            cache_path = self.wheel_cache / name
            yield self.task(
                name=f"repo:fetch:{package_name}:{name}",
                actions=[
                    (self.fetch_one, [url, cache_path]),
                ],
                targets=[cache_path],
            )

        if cache_path is None:
            raise ValueError(
                f"Don't know what to do with {package_name}: {package_info}"
            )

        dest = self.output_wheels / cache_path.name
        yield self.task(
            name=f"repo:copy:{dest.name}",
            actions=[(self.copy_one, [cache_path, dest])],
            file_dep=[cache_path],
            targets=[dest],
        )
