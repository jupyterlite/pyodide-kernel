"""a JupyterLite addon for building custom ``pyodide-lock.json``"""

from __future__ import annotations

import importlib.metadata

from jupyterlite_core.manager import LiteManager
from traitlets import Unicode, Bool

from ._base import _BaseAddon
from ..constants import (
    PYODIDE_LOCK_STEM,
    PYODIDE_CORE_URL,
)
from typing import TYPE_CHECKING, Any

PYODIDE_LOCK_VERSION: str | None

try:
    PYODIDE_LOCK_VERSION = importlib.metadata.version(PYODIDE_LOCK_STEM)
except ImportError:
    PYODIDE_LOCK_VERSION = None


if TYPE_CHECKING:
    from collections.abc import Iterator

    TTaskGenerator = Iterator[dict[str, Any]]


class PyodideLockAddon(_BaseAddon):
    __all__ = [
        "status",
        # "post_init",
        # "build",
        # "post_build",
        # "check",
    ]

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
    )  # type: ignore[assignment]

    @property
    def pyodide_addon(self):
        return self.addons["jupyterlite-pyodide-kernel-pyodide"]

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
                f"""enabled:      {self.enabled}""",
                f"""pyodide-lock: {PYODIDE_LOCK_VERSION}""",
            ]

            print(indent("\n".join(lines), "    "), flush=True)

        yield self.task(name="lock", actions=[_status])
