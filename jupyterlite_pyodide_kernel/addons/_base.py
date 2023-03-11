"""common addon features for ``jupyterlite-pyodide-kernel``

This should not be considered part of the public API, and much will disappear
when these features are added upstream:

    https://github.com/jupyterlite/jupyterlite/issues/996
"""
from pathlib import Path
import json
from hashlib import sha256
from typing import Dict, Any, List, Optional
from jupyterlite_core.addons.base import BaseAddon
from jupyterlite_core.constants import LAB_EXTENSIONS, UTF8

from ..constants import (
    PKG_JSON_PYODIDE_KERNEL,
    PKG_JSON_WHEELDIR,
    PYODIDE_KERNEL_PLUGIN_ID,
    PYODIDE_KERNEL_NPM_NAME,
    PYPI_WHEELS,
)

__all__ = ["_BaseAddon"]


class _BaseAddon(BaseAddon):
    @property
    def output_extensions(self) -> Path:
        """where labextensions will go in the output folder

        Candidate for hoisting to ``jupyterlite_core``
        """
        return self.manager.output_dir / LAB_EXTENSIONS

    def get_output_labextension_packages(self) -> List[Path]:
        """All ``package.json`` files for labextensions in ``output_dir``.

        Candidate for hoisting to ``jupyterlite_core``
        """
        return sorted(
            [
                *self.output_extensions.glob("*/package.json"),
                *self.output_extensions.glob("@*/*/package.json"),
            ]
        )

    def check_index_urls(self, raw_urls: List[str], schema: Path):
        """Validate URLs against a schema."""
        for raw_url in raw_urls:
            if not raw_url.startswith("./"):
                continue

            index_url = raw_url.split("?")[0].split("#")[0]

            index_path = self.manager.output_dir / index_url

            if not index_path.exists():
                continue

            yield self.task(
                name=f"validate:{index_url}",
                doc=f"validate {index_url} against {schema}",
                file_dep=[index_path],
                actions=[(self.validate_one_json_file, [schema, index_path])],
            )

    @property
    def output_kernel_extension(self) -> Path:
        """the location of the Pyodide kernel labextension static assets"""
        return self.output_extensions / PYODIDE_KERNEL_NPM_NAME

    @property
    def schemas(self) -> Path:
        """the path to the as-deployed schema in the labextension"""
        return self.output_kernel_extension / "static/schema"

    @property
    def output_wheels(self) -> Path:
        """where wheels will go in the output folder"""
        return self.manager.output_dir / PYPI_WHEELS

    @property
    def wheel_cache(self) -> Path:
        """where wheels will go in the cache folder"""
        return self.manager.cache_dir / "wheels"

    def get_pyodide_settings(self, config_path: Path):
        """Get the settings for the client-side Pyodide kernel."""
        return self.get_lite_plugin_settings(config_path, PYODIDE_KERNEL_PLUGIN_ID)

    def set_pyodide_settings(self, config_path: Path, settings: Dict[str, Any]) -> None:
        """Update the settings for the client-side Pyodide kernel."""
        return self.set_lite_plugin_settings(
            config_path, PYODIDE_KERNEL_PLUGIN_ID, settings
        )

    def get_index_urls(self, index_path: Path):
        """Get output_dir relative URLs for an index file."""
        index_sha256 = sha256(index_path.read_bytes()).hexdigest()
        index_url = f"./{index_path.relative_to(self.manager.output_dir).as_posix()}"
        index_url_with_sha = f"{index_url}?sha256={index_sha256}"
        return index_url, index_url_with_sha

    def get_package_wheel_index_url(
        self, pkg_json: Path, index_name: str
    ) -> Optional[Path]:
        pkg_data = json.loads(pkg_json.read_text(**UTF8))
        wheel_dir = pkg_data.get(PKG_JSON_PYODIDE_KERNEL, {}).get(PKG_JSON_WHEELDIR)
        if wheel_dir:
            pkg_whl_index = pkg_json.parent / wheel_dir / index_name
            if pkg_whl_index.exists():
                return self.get_index_urls(pkg_whl_index)[1]
        return None
