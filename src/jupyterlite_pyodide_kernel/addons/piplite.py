"""a JupyterLite addon for supporting piplite wheels"""

import json
import re
import urllib.parse
from pathlib import Path
from typing import Tuple as _Tuple, List as _List

import doit.tools
from jupyterlite_core.constants import (
    ALL_JSON,
    JSON_FMT,
    JUPYTERLITE_JSON,
    UTF8,
)
from jupyterlite_core.trait_types import TypedTuple
from traitlets import Unicode

from ._base import _BaseAddon

from ..constants import (
    PIPLITE_INDEX_SCHEMA,
    PIPLITE_URLS,
    PYPI_WHEELS,
    KERNEL_SETTINGS_SCHEMA,
)
from ..wheel_utils import list_wheels, write_wheel_index, get_wheel_fileinfo

from jupyterlite_core.manager import LiteManager


class PipliteAddon(_BaseAddon):
    __all__ = ["post_init", "build", "post_build", "check"]

    # CLI
    aliases = {
        "piplite-wheels": "PipliteAddon.piplite_urls",
    }

    # traits
    piplite_urls: _Tuple[str] = TypedTuple(
        Unicode(),
        help="Local paths or URLs of piplite-compatible wheels to copy and index",
    ).tag(config=True)

    @property
    def piplite_schema(self) -> Path:
        """the schema for Warehouse-like API indexes"""
        return self.schemas / PIPLITE_INDEX_SCHEMA

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

        wheels = list_wheels(self.output_wheels)
        pkg_jsons = self.get_output_labextension_packages()

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

        if whl_metas or pkg_jsons:
            whl_index = self.manager.output_dir / PYPI_WHEELS / ALL_JSON

            yield self.task(
                name="patch",
                doc=f"ensure {JUPYTERLITE_JSON} includes any piplite wheels",
                file_dep=[*whl_metas, jupyterlite_json],
                actions=[
                    (
                        self.patch_jupyterlite_json,
                        [
                            jupyterlite_json,
                            whl_index,
                            whl_metas,
                            pkg_jsons,
                        ],
                    )
                ],
                targets=[whl_index],
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
        whl_metas: _List[Path],
        pkg_jsons: _List[Path],
    ):
        """add the piplite wheels to jupyter-lite.json"""
        plugin_config = self.get_pyodide_settings(config_path)
        # first add user-specified wheels to warehouse
        warehouse_urls = self.update_warehouse_index(
            plugin_config, whl_index, whl_metas
        )
        needs_save = False

        # ...then add wheels from federated extensions...
        for pkg_json in pkg_jsons:
            pkg_warehouse_url = self.get_package_wheel_index_url(pkg_json, ALL_JSON)
            if pkg_warehouse_url and pkg_warehouse_url not in warehouse_urls:
                warehouse_urls += [pkg_warehouse_url]

        # ... and only update if actually changed
        if warehouse_urls and plugin_config.get(PIPLITE_URLS) != warehouse_urls:
            plugin_config[PIPLITE_URLS] = warehouse_urls
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

    def index_wheel(self, whl_path: Path, whl_meta: Path):
        """Generate an intermediate file representation to merge with other releases"""
        name, version, release = get_wheel_fileinfo(whl_path)
        whl_meta.write_text(
            json.dumps(dict(name=name, version=version, release=release), **JSON_FMT),
            **UTF8,
        )
        self.maybe_timestamp(whl_meta)
