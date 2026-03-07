"""a JupyterLite addon for building custom ``pyodide-lock.json``"""

from __future__ import annotations

import shutil
import importlib.metadata
from datetime import datetime
from copy import deepcopy

from textwrap import indent
from urllib.parse import urlparse
from hashlib import sha256

import doit.tools

from jupyterlite_core.manager import LiteManager
from jupyterlite_core.constants import JUPYTERLITE_JSON
from jupyterlite_core.trait_types import TypedTuple
from traitlets import Unicode, Bool, Dict
from typing import TYPE_CHECKING, Any

from ._base import _BaseAddon
from ..utils import list_wheels, normalize_names, get_wheel_name
from ..constants import (
    PYODIDE_LOCK_STEM,
    PYODIDE_CORE_URL,
    PYODIDE_LOCK,
    PYODIDE_CDN_URL,
    PYPI_WHEELS,
    LOAD_PYODIDE_OPTIONS,
    PYODIDE_UV_WHEELS,
    OPTION_PACKAGES,
    OPTION_LOCK_FILE_URL,
)

PYODIDE_LOCK_VERSION: str | None

try:
    PYODIDE_LOCK_VERSION = importlib.metadata.version(PYODIDE_LOCK_STEM)
except ImportError:  # pragma: no cover
    PYODIDE_LOCK_VERSION = None


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pyodide_lock.uv_pip_compile import UvPipCompile
    from pyodide_lock.spec import PackageSpec, PyodideLockSpec
    from pathlib import Path
    from packaging.utils import NormalizedName

    TTaskGenerator = Iterator[dict[str, Any]]
    TWheels = dict[NormalizedName, Path]


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
    ).tag(config=True)  # type: ignore[assignment]

    specs: tuple[str, ...] = TypedTuple(
        Unicode(), help="PEP-508 specs for Python packages to include in the lock"
    ).tag(config=True)  # type: ignore[assignment]

    exclude: tuple[str, ...] = TypedTuple(
        Unicode(),
        help="Python package names to exclude from the lock",
        default_value=["widgetsnbextension", "jupyterlab-widgets"],
    )  # type: ignore[assignment]

    extra_exclude: tuple[str, ...] = TypedTuple(
        Unicode(),
        help="extra Python package names to exclude from the lock",
    )  # type: ignore[assignment]

    pyodide_lock_options: dict[str, Any] = Dict(
        help="extra options to pass to ``pyodide_lock.uv_pip_compile.UvPipCompile``",
    ).tag(config=True)  # type: ignore[assignment]

    prefetch_packages: tuple[str, ...] = TypedTuple(
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

    extra_prefetch_packages: tuple[str] = TypedTuple(
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
    def pyodide_lock_cache(self) -> Path:
        """where ``pyodide-lock`` and ``uv`` stuff will go in the cache folder"""
        return self.manager.cache_dir / PYODIDE_LOCK_STEM

    @property
    def all_prefetch_packages(self) -> list[NormalizedName]:
        """All packages to fetch while ``pyodide`` is initializing."""
        return normalize_names(*self.prefetch_packages, *self.extra_prefetch_packages)

    @property
    def all_exclude(self) -> list[NormalizedName]:
        """All packages to be excluded from the ``uv`` solve, and removed from the lock."""
        return normalize_names(*self.exclude, *self.extra_exclude)

    @property
    def status_info(self) -> str:
        """The status string, also used for task up-to-date checks."""
        lines = [
            f"""enabled:              {self.enabled}""",
            f"""pyodide-lock:         {PYODIDE_LOCK_VERSION or "not installed"}""",
            f"""pyodide base URL:     {self.input_base_url}""",
            f"""missing package URL:  {self.base_url_for_missing}""",
            f"""pyodide-lock options: {self.pyodide_lock_options}""",
            """packages:""",
            f""" - PEP-508 specs:       {self.specs}""",
            f""" - excludes:            {self.all_exclude}""",
            f""" - wheels:              {self.wheels}""",
            """runtime:""",
            f""" - prefetch packages:   {self.all_prefetch_packages}""",
        ]
        return "\n".join(lines)

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

        yield self.task(
            name="lock",
            doc=f"report {PYODIDE_LOCK} status",
            actions=[lambda: print(indent(self.status_info, "    "), flush=True)],
        )

    def post_build(self, manager: LiteManager) -> TTaskGenerator:
        """Build tasks to customize ``pyodide-lock.json``."""
        if not self.enabled:
            return
        out = manager.output_dir
        jupyterlite_json = out / JUPYTERLITE_JSON
        wheels = self.find_wheels_by_name()

        yield self.task(
            name="lock",
            doc=f"build {PYODIDE_LOCK} with kernel, extension, and user-requested wheels",
            actions=[(self.build_lock, [wheels])],
            file_dep=[
                *wheels.values(),
                self.pyodide_addon.output_pyodide / PYODIDE_LOCK,
            ],
            targets=[self.output_pyodide_lock],
            uptodate=[doit.tools.config_changed(self.status_info)],
        )

        yield self.task(
            name=f"patch:{JUPYTERLITE_JSON}",
            doc=f"configure runtime {PYODIDE_LOCK} settings in {JUPYTERLITE_JSON}",
            actions=[(self.patch_config, [jupyterlite_json, self.output_pyodide_lock])],
            file_dep=[jupyterlite_json, self.output_pyodide_lock],
            uptodate=[doit.tools.config_changed(self.status_info)],
        )

    def check(self, manager: LiteManager) -> TTaskGenerator:
        """Build a task to check ``pyodide-lock.json`` and wheels."""
        if not self.enabled:
            return
        yield self.task(
            name="lock",
            doc=f"ensure {PYODIDE_LOCK} and local wheels are consistent",
            actions=[self.check_lock],
        )

    # task actions
    def build_lock(self, wheels_by_name: TWheels) -> bool:
        """Build a ``pyodide-lock.json`` with all kernel and user-requested wheels."""

        upc = self.init_uv_pip_compile(wheels_by_name)
        if upc is None:  # pragma: no cover
            return False
        spec = upc.update()

        # start with a clean folder
        shutil.rmtree(self.output_pyodide_lock.parent, ignore_errors=True)
        self.output_pyodide_lock.parent.mkdir(parents=True)

        # ensure wheels not already included in the output
        for pkg in spec.packages.values():
            url = urlparse(pkg.file_name)
            if not url.scheme and url.path.startswith(PYODIDE_UV_WHEELS):
                self.ensure_local_spec(pkg, wheels_by_name)

        spec.to_json(path=self.output_pyodide_lock, indent=2)

        self.maybe_timestamp(self.output_pyodide_lock)

        return self.output_pyodide_lock.is_file()

    def check_lock(self) -> bool:
        """Check the lock."""
        ok: dict[str, bool] = {}
        spec: PyodideLockSpec | None = None
        try:
            from pyodide_lock.spec import PyodideLockSpec
            from packaging.utils import canonicalize_name

            spec = PyodideLockSpec.from_json(self.output_pyodide_lock)
            ok["lock"] = True
        except Exception as err:
            self.log.error(
                "Failed to parse lock with pyodide-lock v%s: %s\n%s\n",
                self.output_pyodide_lock,
                PYODIDE_LOCK_VERSION,
                err,
            )
            ok["lock"] = False
        if spec:
            c_names = {canonicalize_name(n) for n in spec.packages}
            for pkg in spec.packages.values():
                ok.update(self.check_package_spec(pkg, c_names))
        self.log.debug("Lock OK: %s", ok)
        return False not in ok.values()

    def patch_config(self, jupyterlite_json: Path, lockfile: Path) -> None:
        """Update the runtime ``jupyter-lite-config.json`` for ``pyodide-lock.json`."""
        self.log.debug("patching %s for pyodide-lock", jupyterlite_json)
        out = self.manager.output_dir

        settings = self.get_pyodide_settings(jupyterlite_json)

        # URL with cache-busting suffix of the lockfile SHA256
        lock_sha = sha256(lockfile.read_bytes()).hexdigest()
        lock_url = f"./{lockfile.relative_to(out).as_posix()}?sha256={lock_sha}"

        # add preloads
        lpo = settings.setdefault(LOAD_PYODIDE_OPTIONS, {})
        packages = normalize_names(
            *lpo.get(OPTION_PACKAGES, []), *self.all_prefetch_packages
        )
        lpo.update({OPTION_LOCK_FILE_URL: lock_url, OPTION_PACKAGES: packages})

        self.set_pyodide_settings(jupyterlite_json, settings)

    # helpers
    def find_wheels_by_name(self) -> TWheels:
        """Gather a wheel per canonical name."""

        out = self.manager.output_dir

        wheels_by_name: TWheels = {}

        # add directly-requested wheels
        for wheel_str in self.wheels:
            wheel_or_dir = self.manager.lite_dir / wheel_str
            if wheel_or_dir.is_dir():
                for wheel_in_dir in list_wheels(wheel_or_dir):
                    self.add_wheel_by_name(wheel_in_dir, wheels_by_name)
            elif wheel_or_dir.is_file():
                self.add_wheel_by_name(wheel_or_dir, wheels_by_name)
            else:  # pragma: no cover
                self.log.warning("Wheel requested, but not found: %s", wheel_or_dir)

        well_known = self.manager.lite_dir / "static" / PYODIDE_LOCK_STEM

        # add wheels already in well-known and output
        for wheel_dir in [well_known, out / PYPI_WHEELS, self.output_extensions]:
            for wheel in list_wheels(wheel_dir, recursive=True):
                self.add_wheel_by_name(wheel, wheels_by_name)

        return wheels_by_name

    def add_wheel_by_name(self, wheel: Path, wheels_by_name: TWheels) -> None:
        """Add a single wheel."""
        c_name = get_wheel_name(wheel)
        if c_name is None:  # pragma: no cover
            return
        if c_name in self.all_exclude:
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

    def init_uv_pip_compile(self, wheels_by_name: TWheels) -> UvPipCompile | None:
        """Create a ``UvPipCompile`` runner."""
        from pyodide_lock.uv_pip_compile import UvPipCompile

        cache_dir = self.pyodide_lock_cache
        work_dir = cache_dir / "_work"
        tmp_lock = cache_dir / PYODIDE_LOCK
        tmp_lock.parent.mkdir(parents=True, exist_ok=True)
        patched_lock = tmp_lock.parent / f"patched-{tmp_lock.name}"
        in_lock = self.pyodide_addon.output_pyodide / PYODIDE_LOCK
        self.copy_one(in_lock, tmp_lock)

        kwargs = deepcopy(self.pyodide_lock_options)
        if self.manager.source_date_epoch:
            iso = datetime.fromtimestamp(self.manager.source_date_epoch).isoformat()
            kwargs.setdefault("extra_uv_args", []).extend(["--exclude-newer", iso])

        upc = UvPipCompile(
            input_path=tmp_lock,
            output_path=patched_lock,
            input_base_url=self.input_base_url,
            wheels=[*wheels_by_name.values()],
            specs=[*self.specs],
            work_dir=work_dir,
            wheel_dir=cache_dir / PYODIDE_UV_WHEELS,
            base_url_for_missing=self.base_url_for_missing,
            **kwargs,
        )

        return upc

    def ensure_local_spec(self, pkg: PackageSpec, wheels_by_name: TWheels):
        """Ensure a ``PackageSpec`` points at a wheel in ``output_dir``."""
        url = urlparse(pkg.file_name)
        out = self.manager.output_dir
        just_name = url.path.removeprefix(f"{PYODIDE_UV_WHEELS}/")
        rel_url: str | None = None
        in_wheel = wheels_by_name.get(normalize_names(pkg.name)[0])
        out_wheel: Path | None = None

        if in_wheel and out in in_wheel.parents:
            out_wheel = in_wheel
            rel_url = out_wheel.relative_to(out).as_posix()
        else:
            uv_wheel = self.pyodide_lock_cache / PYODIDE_UV_WHEELS / just_name
            out_wheel = self.output_pyodide_lock.parent / just_name
            self.copy_one(uv_wheel, out_wheel)
            rel_url = f"static/{PYODIDE_LOCK_STEM}/{just_name}"

        if not (rel_url and out_wheel and out_wheel.exists()):  # pragma: no cover
            msg = f"Don't know what to do with {just_name} from {pkg}: {out_wheel}"
            raise NotImplementedError(msg)

        # build a relative path from root for `pyodide.js`
        pkg.file_name = f"../../{rel_url}?sha256={pkg.sha256}"

    def check_package_spec(
        self, pkg: PackageSpec, c_names: set[NormalizedName]
    ) -> dict[str, bool]:
        """Verify a single package."""
        from packaging.utils import canonicalize_name

        name = canonicalize_name(pkg.name)
        url = urlparse(pkg.file_name)

        is_ok: dict[str, bool] = {}
        if not url.scheme:
            path = self.output_pyodide_lock.parent / url.path
            file_ok = is_ok[name] = path.is_file()

            if not file_ok:
                self.log.error("[%s] missing wheel: %s", name, path)
            else:
                sha = sha256(path.read_bytes()).hexdigest()
                sha_ok = is_ok[f"{pkg.name}:sha"] = sha == pkg.sha256
                if not sha_ok:
                    self.log.error(
                        "[%s] SHA256 mismatch:\n\texpected: %s\n\tobserved: %s",
                        name,
                        pkg.sha256,
                        sha,
                    )

        for dep_name in pkg.depends:
            c_dep = canonicalize_name(dep_name)
            dep_ok = is_ok[f"{pkg.name}:depends:{c_dep}"] = c_dep in c_names
            if not dep_ok:
                self.log.error("[%s] missing dependency: %s", name, dep_name)

        return is_ok
