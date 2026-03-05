"""a JupyterLite addon for building custom ``pyodide-lock.json``"""

from __future__ import annotations

import importlib.metadata
import shutil
import doit.tools
from hashlib import sha256

from jupyterlite_core.manager import LiteManager
from jupyterlite_core.constants import JUPYTERLITE_JSON
from jupyterlite_core.trait_types import TypedTuple
from traitlets import Unicode, Bool, Dict
from typing import TYPE_CHECKING, Any

from ._base import _BaseAddon
from ..utils import list_wheels
from ..constants import (
    PYODIDE_LOCK_STEM,
    PYODIDE_CORE_URL,
    PYODIDE_LOCK,
    PYODIDE_CDN_URL,
    PYODIDE_URL,
    PYPI_WHEELS,
    PYODIDE_JS,
    LOAD_PYODIDE_OPTIONS,
    PYODIDE_UV_WHEELS,
    OPTION_PACKAGES,
    OPTION_LOCK_FILE_URL,
)

PYODIDE_LOCK_VERSION: str | None

try:
    PYODIDE_LOCK_VERSION = importlib.metadata.version(PYODIDE_LOCK_STEM)
except ImportError:
    PYODIDE_LOCK_VERSION = None


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pyodide_lock.uv_pip_compile import UvPipCompile
    from pyodide_lock.spec import PackageSpec, PyodideLockSpec
    from pkginfo import Distribution
    from pathlib import Path

    TTaskGenerator = Iterator[dict[str, Any]]


class PyodideLockAddon(_BaseAddon):
    __all__ = ["pre_status", "status", "post_build", "check"]

    # traits
    enabled: bool = Bool(
        default_value=False,
        help="whether ``pyodide-lock`` customization is enabled",
    ).tag(config=True)  # type: ignore[assignment]

    pyodide_url: str = Unicode(
        default_value=PYODIDE_CORE_URL,
        help=(
            "a URL, folder, or path to a ``pyodide`` distribution, if not configured"
            " in ``PyodideAddon.pyodide_url``"
        ),
    ).tag(config=True)  # type: ignore[assignment]

    input_base_url: str = Unicode(
        default_value=PYODIDE_CDN_URL,
        help="the logical CDN URL for partial Pyodide distribution",
        allow_none=True,
    ).tag(config=True)  # type: ignore[assignment]

    base_url_for_missing: str = Unicode(
        default_value=PYODIDE_CDN_URL,
        help="a CDN URL for partial Pyodide distribution",
        allow_none=True,
    ).tag(config=True)  # type: ignore[assignment]

    wheels: tuple[str, ...] = TypedTuple(
        Unicode(), help="paths to local wheels or folders"
    ).tag(config=True)

    pyodide_lock_options: dict[str, Any] = Dict(
        kwargs=[],
        help="options to pass to ``pyodide_lock.uv_pip_compile.UvPipCompile``",
    ).tag(config=True)  # type: ignore[assignment]

    preload_packages: tuple[str, ...] = TypedTuple(
        Unicode(),
        default_value=[
            "ssl",
            "sqlite3",
            "ipykernel",
            "comm",
            "pyodide-kernel",
            "ipython",
        ],
        help=(
            "``pyodide-kernel`` dependencies to add to"
            " ``PyodideAddon.loadPyodideOptions.packages``."
            " These will be downloaded and installed, but _not_ imported to"
            " ``sys.modules``"
        ),
    ).tag(config=True)  # type: ignore[assignment]

    extra_preload_packages: tuple[str] = TypedTuple(
        Unicode(),
        help=(
            "extra packages to add to ``PyodideAddon.loadPyodideOptions.packages``."
            " These will be downloaded at kernel startup, and installed, but _not_"
            " imported to ``sys.modules``"
        ),
    ).tag(config=True)  # type: ignore[assignment]

    # properties
    @property
    def output_pyodide_lock(self) -> Path:
        return self.manager.output_dir / "static" / PYODIDE_LOCK_STEM / PYODIDE_LOCK

    @property
    def pyodide_lock_cache(self):
        """where ``pyodide-lock`` and ``uv`` stuff will go in the cache folder"""
        return self.manager.cache_dir / PYODIDE_LOCK_STEM

    # JupyterLite API methods
    def pre_status(self, manager: LiteManager) -> TTaskGenerator:
        """Patch configuration of ``PyodideAddon`` if needed."""
        if not (self.enabled or self.pyodide_addon.pyodide_url):
            return

        self.pyodide_addon.pyodide_url = self.pyodide_url

        yield self.task(
            name="patch:pyodide",
            actions=[lambda: print("    PyodideAddon.pyodide_url was patched")],
        )

    def status(self, manager: LiteManager) -> TTaskGenerator:
        """Report on the status of ``pyodide-lock``."""

        def _status() -> None:
            from textwrap import indent

            lines = [
                f"""enabled:        {self.enabled}""",
                f"""pyodide-lock:   {PYODIDE_LOCK_VERSION or "not installed"}""",
                f"""pyodide CDN:    {self.input_base_url}""",
            ]

            print(indent("\n".join(lines), "    "), flush=True)

        yield self.task(name="lock", actions=[_status])

    def post_build(self, manager: LiteManager) -> TTaskGenerator:
        """Build a customized ``pyodide-lock.json``."""
        if not self.enabled:
            return
        out = manager.output_dir
        wheels = self.find_wheels_by_name()
        cfg_str = f"""
            {self.base_url_for_missing}
            {self.input_base_url}
            {self.preload_packages}{self.extra_preload_packages}
            {self.pyodide_addon.pyodide_url}
            {self.pyodide_lock_options}
            {self.pyodide_url}
        """

        yield self.task(
            name="lock",
            doc=f"ensure {PYODIDE_LOCK} contains wheels from piplite and all extensions",
            actions=[(self.build_lock, [wheels])],
            file_dep=[
                *wheels.values(),
                self.pyodide_addon.output_pyodide / PYODIDE_LOCK,
            ],
            targets=[self.output_pyodide_lock],
            uptodate=[doit.tools.config_changed(cfg_str)],
        )

        jupyterlite_json = out / JUPYTERLITE_JSON

        yield self.task(
            name="patch",
            doc=f"configure runtime pyodide settings in {JUPYTERLITE_JSON}",
            actions=[(self.patch_config, [jupyterlite_json, self.output_pyodide_lock])],
            file_dep=[jupyterlite_json, self.output_pyodide_lock],
            uptodate=[doit.tools.config_changed(cfg_str)],
        )

    def check(self, manager: LiteManager) -> TTaskGenerator:
        if not self.enabled:
            return
        yield self.task(
            name="lock",
            doc=f"ensure {PYODIDE_LOCK} is consistent",
            actions=[self.check_lock],
        )

    # task implementations
    def build_lock(self, wheels_by_name: dict[str, Path]) -> bool:
        """Build a ``pyodide-lock.json`` with all local and user-requested wheels."""

        upc = self.init_uv_pip_compile(wheels_by_name)
        if upc is None:  # pragma: no cover
            return False
        spec = upc.update()

        shutil.rmtree(self.output_pyodide_lock.parent, ignore_errors=True)
        self.output_pyodide_lock.parent.mkdir(parents=True)

        for pkg in spec.packages.values():
            if pkg.file_name.startswith(PYODIDE_UV_WHEELS):
                self.ensure_local_spec(pkg, wheels_by_name)
        spec.to_json(path=self.output_pyodide_lock, indent=2)
        return True

    def check_lock(self) -> bool:
        """Check the lock."""
        ok = True
        spec: PyodideLockSpec | None = None
        try:
            from pyodide_lock.spec import PyodideLockSpec
            from packaging.utils import canonicalize_name

            spec = PyodideLockSpec.from_json(self.output_pyodide_lock)
        except Exception as err:  # pragma: no cover
            self.log.error(
                "%s\n%s\n!!! Failed to parse lock with pyodide-lock v%s",
                err,
                self.output_pyodide_lock,
                PYODIDE_LOCK_VERSION,
            )
            ok = False
        if spec:
            c_names = {canonicalize_name(n) for n in spec.packages}
            for pkg in spec.packages.values():
                ok = self.check_package_spec(pkg, c_names)
        return ok

    def check_package_spec(self, pkg: PackageSpec, c_names: list[str]):
        """Verify a single package."""
        ok = True
        if pkg.file_name.startswith("."):
            path = self.output_pyodide_lock.parent / pkg.file_name
            if not path.is_file():
                self.log.error("Missing wheel for %s: %s", pkg.name, path)
                ok = False
            if ok:
                sha = sha256(path.read_bytes()).hexdigest()
                if sha != pkg.sha256:  # pragma: no cover
                    self.log.error(
                        "SHA256 mismatch for %s:\n\texpected: %s\n\tobserved: %s",
                        pkg.name,
                        pkg.sha256,
                        sha,
                    )
                    ok = False
        return ok

    # helpers
    def find_wheels_by_name(self) -> dict[str, Path]:
        """Gather a wheel per canonical name from ``output_dir``."""
        from packaging.utils import canonicalize_name

        out = self.manager.output_dir
        wheel_dirs = [self.output_extensions, out / PYPI_WHEELS]
        exclude_names = {
            canonicalize_name(e) for e in self.pyodide_lock_options.get("excludes", [])
        }
        wheels: dict[str, Path] = {}

        for wheel_str in self.wheels:
            wheel = self.manager.lite_dir / wheel_str
            if wheel.is_dir():
                wheel_dirs += [wheel]
            elif wheel.is_file():
                c_name = self.get_wheel_meta(wheel)[0]
                if c_name:
                    wheels[c_name] = wheel
            else:  # pragma: no cover
                self.log.warning("Wheel %s was requested, but not found", wheel)

        for wheel in list_wheels(*wheel_dirs, recursive=True):
            c_name = self.get_wheel_meta(wheel)[0]
            if c_name is None:  # pragma: no cover
                continue
            if c_name in exclude_names:
                self.log.warning("Local wheel for %s excluded %s", c_name, wheel)
                continue
            if c_name in wheels:  # pragma: no cover
                self.log.warning(
                    "Local wheel for %s already collected from %s, discarding %s",
                    c_name,
                    wheels[c_name],
                    wheel,
                )
                continue
            wheels[c_name] = wheel
        return wheels

    def get_wheel_meta(self, wheel: Path) -> tuple[str | None, Distribution | None]:
        import pkginfo
        from packaging.utils import canonicalize_name

        info = pkginfo.get_metadata(f"{wheel}")
        if not (info and info.name):  # pragma: no cover
            self.log.warning("Couldn't recover package name from %s", wheel)
            return (None, None)
        return canonicalize_name(info.name), info

    def init_uv_pip_compile(
        self, wheels_by_name: dict[str, Path]
    ) -> UvPipCompile | None:
        """Create a ``UvPipCompile`` runner."""
        from pyodide_lock.uv_pip_compile import UvPipCompile

        cache_dir = self.pyodide_lock_cache
        work_dir = cache_dir / "_work"
        tmp_lock = cache_dir / PYODIDE_LOCK
        tmp_lock.parent.mkdir(parents=True, exist_ok=True)
        patched_lock = tmp_lock.parent / f"patched-{tmp_lock.name}"
        in_lock = self.pyodide_addon.output_pyodide / PYODIDE_LOCK
        self.copy_one(in_lock, tmp_lock)

        upc = UvPipCompile(
            input_path=tmp_lock,
            output_path=patched_lock,
            input_base_url=self.input_base_url,
            wheels=[*wheels_by_name.values()],
            work_dir=work_dir,
            wheel_dir=cache_dir / PYODIDE_UV_WHEELS,
            base_url_for_missing=self.base_url_for_missing,
        )

        for key, value in sorted(self.pyodide_lock_options.items()):
            if not hasattr(upc, key):
                self.log.error("Unrecognized option: UvPipCompile.%s", key)
                return None
            setattr(upc, key, value)

        return upc

    def ensure_local_spec(
        self,
        pkg: PackageSpec,
        wheels_by_name: dict[str, Path],
    ):
        """Ensure a ``PackageSpec`` points at a wheel in ``output_dir``."""
        fname = pkg.file_name
        out = self.manager.output_dir
        just_name = fname.replace(f"{PYODIDE_UV_WHEELS}/", "")
        output_wheels = [w for w in wheels_by_name.values() if w.name == just_name]
        rel_url: str | None = None
        out_wheel: Path | None = None

        if output_wheels:
            out_wheel = output_wheels[0]
            rel_url = out_wheel.relative_to(out).as_posix()
        else:
            uv_wheel = self.pyodide_lock_cache / PYODIDE_UV_WHEELS / just_name
            out_wheel = self.output_pyodide_lock.parent / just_name
            self.copy_one(uv_wheel, out_wheel)
            rel_url = f"static/{PYODIDE_LOCK_STEM}/{just_name}"

        if not (rel_url and out_wheel and out_wheel.exists()):
            msg = f"Don't know what to do with {just_name} from {pkg}: {out_wheel}"
            raise NotImplementedError(msg)

        pkg.file_name = f"../../{rel_url}"

    def patch_config(self, jupyterlite_json: Path, lockfile: Path) -> None:
        """Update the runtime ``jupyter-lite-config.json``."""
        self.log.debug("[lock] patching %s for pyodide-lock", jupyterlite_json)
        out = self.manager.output_dir

        settings = self.get_pyodide_settings(jupyterlite_json)

        output_js = self.pyodide_addon.output_pyodide / PYODIDE_JS
        url = f"./{output_js.relative_to(out).as_posix()}"

        settings[PYODIDE_URL] = url

        rel = lockfile.relative_to(out).as_posix()
        load_pyodide_options = settings.setdefault(LOAD_PYODIDE_OPTIONS, {})

        load_pyodide_options.update(
            {
                OPTION_LOCK_FILE_URL: f"./{rel}",
                OPTION_PACKAGES: sorted(
                    {
                        *load_pyodide_options.get(OPTION_PACKAGES, []),
                        *self.preload_packages,
                        *self.extra_preload_packages,
                    }
                ),
            }
        )

        self.set_pyodide_settings(jupyterlite_json, settings)
