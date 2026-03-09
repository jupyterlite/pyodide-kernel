"""a JupyterLite addon for supporting the Pyodide distribution."""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import urllib.parse

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from textwrap import indent
from typing import Any, TYPE_CHECKING

from traitlets import Unicode, default, Bool, Dict
import doit.tools

from jupyterlite_core.trait_types import TypedTuple
from jupyterlite_core.constants import (
    JUPYTERLITE_JSON,
)
from ..utils import list_wheels, normalize_names, get_wheel_name, patch_json_path

from ._base import _BaseAddon
from ..constants import (
    PYODIDE,
    PYODIDE_JS,
    PYODIDE_LOCK,
    PYODIDE_URL,
    PYODIDE_LOCK_STEM,
    PYODIDE_URL_ENV_VAR,
    PYODIDE_CDN_URL,
    PYODIDE_UV_WHEELS,
    LOAD_PYODIDE_OPTIONS,
    OPTION_LOCK_FILE_URL,
    OPTION_PACKAGES,
)


if TYPE_CHECKING:
    from collections.abc import Iterator
    from packaging.utils import NormalizedName
    from pyodide_lock.spec import PackageSpec, PyodideLockSpec
    from jupyterlite_core.manager import LiteManager

    TTaskGenerator = Iterator[dict[str, Any]]
    TWheels = dict[NormalizedName, Path]


PYODIDE_LOCK_VERSION: str | None

try:
    PYODIDE_LOCK_VERSION = importlib.metadata.version(PYODIDE_LOCK_STEM)
except ImportError:  # pragma: no cover
    PYODIDE_LOCK_VERSION = None


class PyodideAddon(_BaseAddon):
    __all__ = ["status", "post_init", "build", "post_build", "check"]

    # CLI
    aliases = {
        "pyodide": "PyodideAddon.pyodide_url",
        "pyodide-lock-url": "PyodideAddon.lock_url",
        "pyodide-lock-wheels": "PyodideAddon.lock_wheels",
        "pyodide-lock-constraints": "PyodideAddon.lock_constraints",
        "pyodide-lock-specs": "PyodideAddon.lock_specs",
        "pyodide-lock-excludes": "PyodideAddon.lock_extra_excludes",
        "pyodide-lock-prefetch": "PyodideAddon.lock_extra_prefetch",
    }

    flags = {
        "pyodide-lock": (
            {"PyodideAddon": {"lock_enabled": True}},
            f"Use pyodide-lock and uv to customize {PYODIDE_LOCK}",
        ),
    }

    # traits
    pyodide_url: str = Unicode(
        allow_none=True,
        help="Local path or URL of a Pyodide distribution tarball",
    ).tag(config=True)

    pyodide_ignore: str = TypedTuple(
        Unicode(),
        default_value=["python", "python.bat", "python.exe"],
        help="names of files to exclude from a Pyodide distribution",
    ).tag(config=True)

    ## lock traits
    lock_enabled: bool = Bool(
        default_value=False,
        help="whether Pyodide lockfile customization is enabled",
    ).tag(config=True)  # type: ignore[assignment]

    lock_url: str = Unicode(
        help=f"URL of a remote {PYODIDE_LOCK}",
        default_value=f"{PYODIDE_CDN_URL}/{PYODIDE_LOCK}",
    ).tag(config=True)  # type: ignore[assignment]

    lock_wheels: tuple[str, ...] = TypedTuple(
        Unicode(), help=f"paths to local wheels or folders to include in {PYODIDE_LOCK}"
    ).tag(config=True)  # type: ignore[assignment]

    lock_specs: tuple[str, ...] = TypedTuple(
        Unicode(),
        help=f"PEP-508 specs for Python packages to include in {PYODIDE_LOCK}",
    ).tag(config=True)  # type: ignore[assignment]

    lock_constraints: tuple[str, ...] = TypedTuple(
        Unicode(),
        help=f"PEP-508 specs for Python packages to use only if required in {PYODIDE_LOCK}",
    ).tag(config=True)  # type: ignore[assignment]

    lock_excludes: tuple[str, ...] = TypedTuple(
        Unicode(),
        help=f"Python package names to exclude from {PYODIDE_LOCK}",
        default_value=["widgetsnbextension", "jupyterlab-widgets"],
    ).tag(config=True)  # type: ignore[assignment]

    lock_extra_excludes: tuple[str, ...] = TypedTuple(
        Unicode(),
        help=f"extra Python package names to exclude from {PYODIDE_LOCK}",
    ).tag(config=True)  # type: ignore[assignment]

    lock_compile_options: dict[str, Any] = Dict(
        help="extra options to pass to ``pyodide_lock.uv_pip_compile.UvPipCompile``",
    ).tag(config=True)  # type: ignore[assignment]

    lock_patches: dict[str, Any] = Dict(
        help="partial Pyodide lockfile to merge after the ``uv`` solve and URL rewrites",
    ).tag(config=True)  # type: ignore[assignment]

    lock_prefetch: tuple[str, ...] = TypedTuple(
        Unicode(),
        default_value=[
            "ssl",
            "sqlite3",
            "ipykernel",
            "comm",
            "pyodide-kernel",
            "ipython",
        ],
        help=f"Python package names from {PYODIDE_LOCK} to prefetch while initializing Pyodide",
    ).tag(config=True)  # type: ignore[assignment]

    lock_extra_prefetch: tuple[str] = TypedTuple(
        Unicode(),
        help=f"extra Python package names from {PYODIDE_LOCK} to prefetch while initializing Pyodide",
    ).tag(config=True)  # type: ignore[assignment]

    # trait defaults
    @default("pyodide_url")
    def _default_pyodide_url(self):
        """Provide a default Pyodide distribution; pyodide-lock requires a local distribution."""
        return os.environ.get(PYODIDE_URL_ENV_VAR)

    # properties
    @property
    def pyodide_cache(self) -> Path:
        """where pyodide stuff will go in the cache folder"""
        return self.manager.cache_dir / PYODIDE

    @property
    def output_pyodide(self) -> Path:
        """where pyodide will go in the output folder"""
        return self.manager.output_dir / "static" / PYODIDE

    @property
    def well_known_pyodide(self) -> Path:
        """a well-known path where pyodide might be stored"""
        return self.manager.lite_dir / "static" / PYODIDE

    @property
    def well_known_lock(self) -> Path:
        """a well-known path where pyodide-lock might be stored"""
        return self.manager.lite_dir / "static" / PYODIDE_LOCK_STEM

    @property
    def status_info(self) -> str:
        lines = [
            f"URL:     {self.pyodide_url}",
            f"archive: {[*self.pyodide_cache.glob('*.bz2')]}",
            f"cache:   {len([*self.pyodide_cache.rglob('*')])} files",
            f"local:   {len([*self.well_known_pyodide.rglob('*')])} files",
        ]
        return "\n".join(lines)

    ## lock properties
    @property
    def lock_output(self) -> Path:
        return self.manager.output_dir / "static" / PYODIDE_LOCK_STEM / PYODIDE_LOCK

    @property
    def lock_cache(self) -> Path:
        """where ``pyodide-lock`` and ``uv`` stuff will go in the cache folder"""
        return self.manager.cache_dir / PYODIDE_LOCK_STEM

    @property
    def lock_remote_cache(self) -> Path:
        """where ``pyodide-lock`` and ``uv`` stuff will go in the cache folder"""
        return self.lock_cache / f"remote-{PYODIDE_LOCK}"

    @property
    def lock_all_prefetch(self) -> list[NormalizedName]:
        """All packages to fetch while ``pyodide`` is initializing."""
        return normalize_names(*self.lock_prefetch, *self.lock_extra_prefetch)

    @property
    def lock_all_excludes(self) -> list[NormalizedName]:
        """All packages to be excluded from the ``uv`` solve, and removed from the lock."""
        return normalize_names(*self.lock_excludes, *self.lock_extra_excludes)

    @property
    def lock_all_extra_uv_args(self) -> list[str]:
        """All arguments to inject for ``uv pip compile``."""
        args: list[str] = []
        if self.manager.source_date_epoch:
            iso = datetime.fromtimestamp(self.manager.source_date_epoch).isoformat()
            args += ["--exclude-newer", iso]
        return args

    @property
    def lock_status_info(self) -> str:
        """The status string, also used for task up-to-date checks."""
        lines = [
            f"pyodide-lock version:  {PYODIDE_LOCK_VERSION or 'not installed'}",
            f"pyodide-lock URL:      {self.lock_url}",
            f"pyodide-lock options:  {self.lock_compile_options}",
            "lock:",
            f" - wheels:       {self.lock_wheels}",
            f" - specs:        {self.lock_specs}",
            f" - constraints:  {self.lock_constraints}",
            f" - excludes:     {self.lock_all_excludes}",
            f" - uv args:      {self.lock_all_extra_uv_args}",
            f" - patches:      {self.lock_patches}",
            "runtime:",
            f" - prefetch packages:   {self.lock_all_prefetch}",
        ]
        return "\n".join(lines)

    # JupyterLite API task generators
    def status(self, manager: LiteManager) -> TTaskGenerator:
        """report on the status of pyodide and pyodide-lock"""
        yield self.task(
            name="pyodide",
            actions=[lambda: print(indent(self.status_info, "    "), flush=True)],
        )

        if self.lock_enabled:
            yield self.task(
                name="pyodide-lock",
                actions=[
                    lambda: print(indent(self.lock_status_info, "    "), flush=True)
                ],
            )

    def post_init(self, manager: LiteManager) -> TTaskGenerator:
        """handle downloading of pyodide"""
        if self.pyodide_url is not None:
            yield from self.cache_pyodide(self.pyodide_url)
        elif self.lock_enabled and self.lock_url:
            yield from self.cache_pyodide_lock(self.lock_url)

    def build(self, manager: LiteManager) -> TTaskGenerator:
        """copy a local (cached or well-known) pyodide into the output_dir"""

        the_pyodide: Path | None = None

        if self.well_known_pyodide.exists():
            the_pyodide = self.well_known_pyodide
        elif self.pyodide_url is not None:
            the_pyodide = self.pyodide_cache / PYODIDE / PYODIDE

        if the_pyodide:
            file_dep_targets = {
                p: self.output_pyodide / p.relative_to(the_pyodide)
                for p in the_pyodide.rglob("*")
                if not (
                    p.is_dir()
                    or self.is_ignored_sourcemap(p.name)
                    or p.name in self.pyodide_ignore
                )
            }

            yield self.task(
                name="copy:pyodide",
                file_dep=sorted(file_dep_targets),
                targets=sorted(file_dep_targets.values()),
                actions=[
                    (self.copy_one, [p, op]) for p, op in file_dep_targets.items()
                ],
            )

    def post_build(self, manager: LiteManager) -> TTaskGenerator:
        """configure jupyter-lite.json for Pyodide, potentially after updating a lockfile."""
        out = manager.output_dir
        jupyterlite_json = out / JUPYTERLITE_JSON
        output_js = self.output_pyodide / PYODIDE_JS

        patch_kwargs: dict[str, Path] = {}
        patch_uptodate = ""

        if self.well_known_pyodide.exists() or self.pyodide_url:
            patch_kwargs["output_js"] = output_js

        if self.lock_enabled:
            wheels_by_name = self.find_wheels_by_name()
            in_lock: Path | None = None

            candidates = [self.output_pyodide / PYODIDE_LOCK, self.lock_remote_cache]
            for candidate in candidates:
                if candidate.is_file():
                    in_lock = candidate

            if not (in_lock and in_lock.is_file()):
                self.log.error(
                    "A custom %s was requested, but no input lock found in: %s",
                    PYODIDE_LOCK,
                    candidates,
                )
                return

            yield self.task(
                name="lock:build",
                doc=f"build {PYODIDE_LOCK} with kernel, extension, and user-requested wheels",
                actions=[(self.post_build_lock, [in_lock, wheels_by_name])],
                file_dep=[in_lock, *wheels_by_name.values()],
                targets=[self.lock_output],
                uptodate=[doit.tools.config_changed(self.lock_status_info)],
            )

            patch_kwargs["lockfile"] = self.lock_output
            patch_uptodate += self.lock_status_info

        if patch_kwargs:
            yield self.task(
                name=f"patch:{JUPYTERLITE_JSON}",
                doc=f"ensure {JUPYTERLITE_JSON} includes Pyodide distribution customizations",
                file_dep=[jupyterlite_json, *patch_kwargs.values()],
                actions=[
                    (self.patch_jupyterlite_json, [jupyterlite_json], patch_kwargs)
                ],
                uptodate=[doit.tools.config_changed(patch_uptodate)],
            )

    def check(self, manager: LiteManager) -> TTaskGenerator:
        """ensure the Pyodide configuration is sound"""
        for app in [None, *manager.apps]:
            app_dir = manager.output_dir / app if app else manager.output_dir
            jupyterlite_json = app_dir / JUPYTERLITE_JSON

            yield self.task(
                name=f"config:{jupyterlite_json.relative_to(manager.output_dir)}",
                file_dep=[jupyterlite_json],
                actions=[(self.check_config_paths, [jupyterlite_json])],
            )

        if self.lock_enabled:
            yield self.task(
                name="lock",
                doc=f"ensure {PYODIDE_LOCK} and local wheels are consistent",
                actions=[self.check_lock],
            )

    # task actions
    def check_config_paths(self, jupyterlite_json: Path) -> None:
        out = self.manager.output_dir
        config = self.get_pyodide_settings(jupyterlite_json)
        pyodide_url = config.get(PYODIDE_URL)

        if not pyodide_url or not pyodide_url.startswith("./"):
            return

        pyodide_path = (out / pyodide_url).parent
        assert pyodide_path.exists(), f"{pyodide_path} not found"
        pyodide_js = pyodide_path / PYODIDE_JS
        assert pyodide_js.exists(), f"{pyodide_js} not found"
        pyodide_lock = pyodide_path / PYODIDE_LOCK
        assert pyodide_lock.exists(), f"{pyodide_lock} not found"

    def patch_jupyterlite_json(
        self,
        config_path: Path,
        output_js: Path | None = None,
        lockfile: Path | None = None,
    ) -> None:
        """update jupyter-lite.json to use the custom Pyodide files"""
        out = self.manager.output_dir
        settings = self.get_pyodide_settings(config_path)

        if output_js:
            settings[PYODIDE_URL] = "./{}".format(output_js.relative_to(out).as_posix())

        if lockfile:
            lpo = settings.setdefault(LOAD_PYODIDE_OPTIONS, {})
            packages = normalize_names(
                *lpo.get(OPTION_PACKAGES, []), *self.lock_all_prefetch
            )
            lpo.update(
                {
                    OPTION_LOCK_FILE_URL: f"./{lockfile.relative_to(out).as_posix()}",
                    OPTION_PACKAGES: packages,
                }
            )

        self.set_pyodide_settings(config_path, settings)

    def cache_pyodide(self, path_or_url: str) -> TTaskGenerator:
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

    def cache_pyodide_lock(self, url: str) -> TTaskGenerator:
        """Cache a remote ``pyodide-lock.json`` if requested."""
        yield self.task(
            name=f"fetch:{PYODIDE_LOCK}",
            doc="fetch the pyodide lockfile",
            actions=[(self.fetch_one, [url, self.lock_remote_cache])],
            targets=[self.lock_remote_cache],
        )

    def extract_pyodide(self, local_path, dest) -> TTaskGenerator:
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
                dest / PYODIDE / PYODIDE_LOCK,
            ],
            actions=[(self.extract_one, [local_path, dest])],
        )

    def post_build_lock(self, input_lock: Path, wheels_by_name: TWheels) -> bool:
        """Build a Pyodide lockfile with all kernel and user-requested wheels."""
        from pyodide_lock.uv_pip_compile import UvPipCompile

        tmp_lock = self.lock_cache / PYODIDE_LOCK
        self.copy_one(input_lock, tmp_lock)

        kwargs = deepcopy(self.lock_compile_options)
        url_base: str | None = None
        if self.lock_url:
            url_base = self.lock_url.rsplit("/", 1)[0]
        extra_uv_args = [*kwargs.pop("extra_uv_args", []), *self.lock_all_extra_uv_args]

        upc = UvPipCompile(
            input_path=tmp_lock,
            output_path=tmp_lock.parent / f"patched-{tmp_lock.name}",
            input_base_url=url_base,
            wheels=[*wheels_by_name.values()],
            specs=[*self.lock_specs],
            constraints=[*self.lock_constraints],
            work_dir=self.lock_cache / "_work",
            wheel_dir=self.lock_cache / PYODIDE_UV_WHEELS,
            base_url_for_missing=url_base,
            excludes=self.lock_all_excludes,
            extra_uv_args=extra_uv_args,
            **kwargs,
        )
        spec = upc.update()

        # start with a clean folder
        shutil.rmtree(self.lock_output.parent, ignore_errors=True)
        self.lock_output.parent.mkdir(parents=True)

        # ensure wheels not already included in the output
        for pkg in spec.packages.values():
            self.ensure_local_spec(pkg, wheels_by_name)

        spec.to_json(path=self.lock_output, indent=2)
        patch_json_path(self.lock_output, self.lock_patches)
        self.maybe_timestamp(self.lock_output)

    def check_lock(self) -> bool:
        """Check the lock."""
        ok: dict[str, bool] = {}
        spec: PyodideLockSpec | None = None
        try:
            from pyodide_lock.spec import PyodideLockSpec
            from packaging.utils import canonicalize_name

            spec = PyodideLockSpec.from_json(self.lock_output)
            ok["lock"] = True
        except Exception as err:
            self.log.error(
                "Failed to parse lock with pyodide-lock v%s: %s\n%s\n",
                self.lock_output,
                PYODIDE_LOCK_VERSION,
                err,
            )
            ok["lock"] = False
        if spec:
            c_names = {canonicalize_name(n) for n in spec.packages}
            for pkg in spec.packages.values():
                ok.update(self.check_package_spec(pkg, c_names))
        self.log.debug("Lock OK: %s", ok)
        return all(ok.values())

    # helpers
    def find_wheels_by_name(self) -> TWheels:
        """Gather a wheel per canonical name, first-in wins."""

        wheels_by_name: TWheels = {}

        # add directly-requested wheels
        for wheel_str in self.lock_wheels:
            wheel_or_dir = self.manager.lite_dir / wheel_str
            if wheel_or_dir.is_dir():
                for wheel_in_dir in list_wheels(wheel_or_dir):
                    self.add_wheel_by_name(wheel_in_dir, wheels_by_name)
            elif wheel_or_dir.is_file():
                self.add_wheel_by_name(wheel_or_dir, wheels_by_name)
            else:  # pragma: no cover
                self.log.warning("Wheel requested, but not found: %s", wheel_or_dir)

        # add wheels from well-known location
        for wheel in list_wheels(self.well_known_lock):
            self.add_wheel_by_name(wheel, wheels_by_name)

        # add all wheels already in output
        for wheel in list_wheels(self.output_extensions, recursive=True):
            self.add_wheel_by_name(wheel, wheels_by_name)

        return wheels_by_name

    def add_wheel_by_name(self, wheel: Path, wheels_by_name: TWheels) -> None:
        """Add a single wheel."""
        c_name = get_wheel_name(wheel)
        if c_name is None:  # pragma: no cover
            self.log.warning("[???] name cannot be found in wheel: %s", wheel)
            return
        if c_name in self.lock_all_excludes:
            self.log.warning("[%s] local wheel excluded by name: %s", c_name, wheel)
            return
        if c_name in wheels_by_name:  # pragma: no cover
            self.log.warning(
                "[%s] local wheel already collected\n\tfrom %s\n\tdiscarding %s",
                c_name,
                wheels_by_name[c_name],
                wheel,
            )
            return
        wheels_by_name[c_name] = wheel

    def ensure_local_spec(self, pkg: PackageSpec, wheels_by_name: TWheels) -> None:
        """Ensure a ``PackageSpec`` points at a wheel in ``output_dir``."""
        url = urllib.parse.urlparse(pkg.file_name)

        if url.scheme or not url.path.startswith(PYODIDE_UV_WHEELS):
            return

        out = self.manager.output_dir
        just_name = url.path.removeprefix(f"{PYODIDE_UV_WHEELS}/")
        rel_url: str | None = None
        in_wheel = wheels_by_name.get(normalize_names(pkg.name)[0])
        out_wheel: Path | None = None

        if in_wheel and out in in_wheel.parents:
            out_wheel = in_wheel
            rel_url = out_wheel.relative_to(out).as_posix()
        else:
            uv_wheel = self.lock_cache / PYODIDE_UV_WHEELS / just_name
            out_wheel = self.lock_output.parent / just_name
            self.copy_one(uv_wheel, out_wheel)
            rel_url = f"static/{PYODIDE_LOCK_STEM}/{just_name}"

        if not (rel_url and out_wheel and out_wheel.exists()):  # pragma: no cover
            msg = f"Don't know what to do with {just_name} from {pkg}: {out_wheel}"
            raise NotImplementedError(msg)

        # build a relative path from root for `pyodide.js`
        pkg.file_name = f"../../{rel_url}"

    def check_package_spec(
        self, pkg: PackageSpec, c_names: set[NormalizedName]
    ) -> dict[str, bool]:
        """Verify a single package."""
        from packaging.utils import canonicalize_name

        name = canonicalize_name(pkg.name)
        url = urllib.parse.urlparse(pkg.file_name)

        is_ok: dict[str, bool] = {}

        for dep_name in pkg.depends:
            c_dep = canonicalize_name(dep_name)
            dep_ok = is_ok[f"{pkg.name}:depends:{c_dep}"] = c_dep in c_names
            if not dep_ok:
                self.log.error("[%s] missing dependency: %s", name, dep_name)

        if not url.scheme:
            path = self.lock_output.parent / url.path
            file_ok = is_ok[name] = path.is_file()

            if not file_ok:
                self.log.error("[%s] missing wheel: %s", name, path)

        return is_ok
