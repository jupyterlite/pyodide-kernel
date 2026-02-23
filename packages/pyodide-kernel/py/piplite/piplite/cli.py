"""A CLI for the subset of ``pip`` commands supported by ``micropip.install``.

As of the upstream:

    https://github.com/pyodide/micropip/blob/0.10.0/micropip/package_manager.py#L43-L55

.. code:

    async def install(
        self,
        requirements: str | list[str],                  # -r and [PACKAGES]
        keep_going: bool = False,                       # --verbose
        deps: bool = True,                              # --no-deps
        credentials: str | None = None,                 # no CLI alias
        pre: bool = False,                              # --pre
        index_urls: list[str] | str | None = None,      # -i and --index-url
        *,
        constraints: list[str] | None = None,           # --constraints
        reinstall: bool = False,                        # no CLI alias
        verbose: bool | int | None = None,              # --verbose
    ) -> None:

As this is _not_ really a CLI, it doesn't bother with accurate return codes, and
failures should not block execution.
"""

from __future__ import annotations

import re
import sys
from typing import Any, TYPE_CHECKING
from argparse import ArgumentParser
from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

REQ_FILE_SPEC = r"^(?P<flag>-r|--requirements)\s*=?\s*(?P<path_ref>.+)$"

# Matches --index-url or -i directives (with optional = separator and optional quotes)
INDEX_URL_SPEC = (
    r'^(--index-url|-i)\s*=?\s*(?:"([^"]*)"|\047([^\047]*)\047|([^\s]*))\s*$'
)

__all__ = ["get_transformed_code"]


def warn(msg: str) -> None:
    """Print a warning to stderr."""
    print(msg, file=sys.stderr, flush=True)


def _get_parser() -> ArgumentParser:
    """Build a pip-like CLI parser."""
    parser = ArgumentParser(
        "piplite",
        exit_on_error=False,
        allow_abbrev=False,
        description="a ``pip``-like wrapper for ``piplite`` and ``micropip``",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        help="whether to print more output",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="only show the minimum output"
    )

    parser.add_argument(
        "action", help="action to perform", default="help", choices=["help", "install"]
    )

    parser.add_argument(
        "--requirements",
        "-r",
        nargs="*",
        help=(
            "path to a requirements file; each line should be a PEP 508 spec"
            " or -r to a relative path"
        ),
    )
    parser.add_argument(
        "--constraints",
        "-c",
        nargs="*",
        help=(
            "path to a constraints file; each line should be a PEP 508 spec"
            " or -r to a relative path"
        ),
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="whether dependencies should be installed",
    )
    parser.add_argument(
        "--pre",
        action="store_true",
        help="whether pre-release packages should be considered",
    )
    parser.add_argument(
        "--index-url",
        "-i",
        type=str,
        default=None,
        help="base URL of the package index to use for lookup",
    )
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="reinstall all packages even if they are already installed",
    )
    parser.add_argument(
        "packages",
        nargs="*",
        type=str,
        default=[],
        help="package names (or wheel URLs) to install",
    )

    return parser


async def get_transformed_code(argv: list[str]) -> str | None:
    """Return a string of code for use in in-kernel execution."""
    action, kwargs = await get_action_kwargs(argv)
    code_str: str = "\n"

    if action == "help":
        pass

    if action == "install":
        if kwargs["requirements"]:
            code_str = f"""await __import__("piplite").install(**{kwargs})\n"""
        else:
            warn("piplite needs at least one package to install")

    return code_str


async def get_action_kwargs(argv: list[str]) -> tuple[str | None, dict[str, Any]]:
    """Get the arguments to ``piplite`` subcommands from CLI-like tokens."""

    parser = _get_parser()

    try:
        args = parser.parse_intermixed_args(argv)
    except (Exception, SystemExit):
        return None, {}

    kwargs: dict[str, Any] = {}
    action = args.action

    if action == "install":
        kwargs["requirements"] = args.packages

        if args.pre:
            kwargs["pre"] = True

        if args.no_deps:
            kwargs["deps"] = False

        if args.verbose:
            kwargs["keep_going"] = True

        if args.index_url:
            kwargs["index_urls"] = args.index_url

        if args.force_reinstall:
            kwargs["reinstall"] = True

        index_urls: list[str] = []
        for req_file in args.requirements or []:
            async for spec in _specs_from_requirements_file(
                Path(req_file), index_urls=index_urls
            ):
                kwargs["requirements"] += [spec]

        for const_file in args.constraints or []:
            async for spec in _specs_from_requirements_file(Path(const_file)):
                kwargs.setdefault("constraints", []).append(spec)

        # Apply index URLs from requirements files only if --index-url was not
        # already given on the command line.
        if index_urls and "index_urls" not in kwargs:
            kwargs["index_urls"] = index_urls

    return action, kwargs


async def _specs_from_requirements_file(
    spec_path: Path,
    *,
    index_urls: list[str] | None = None,
) -> AsyncIterator[str]:
    """Extract package specs from a ``requirements.txt``-style file."""
    if not spec_path.exists():
        warn(f"piplite could not find requirements file {spec_path}")
        return

    for line_no, line in enumerate(spec_path.read_text(encoding="utf-8").splitlines()):
        async for spec in _specs_from_requirements_line(
            spec_path, line_no + 1, line, index_urls=index_urls
        ):
            yield spec


async def _specs_from_requirements_line(
    spec_path: Path,
    line_no: int,
    line: str,
    *,
    index_urls: list[str] | None = None,
) -> AsyncIterator[str]:
    """Get package specs from a line of a ``requirements.txt``-style file.

    ``micropip`` has a sufficient pep508 implementation to handle most cases.

    References to other, local files with ``-r`` are supported.
    """
    raw = line.strip().split("#")[0].strip()
    # is it another spec file?
    file_match = re.match(REQ_FILE_SPEC, raw)

    if file_match:
        ref = file_match.groupdict()["path_ref"]
        ref_path = Path(ref if ref.startswith("/") else spec_path.parent / ref)
        async for sub_spec in _specs_from_requirements_file(
            ref_path, index_urls=index_urls
        ):
            yield sub_spec
        return

    index_url_match = re.match(INDEX_URL_SPEC, raw)
    if index_url_match:
        # Extract the URL from whichever capture group matched (quoted or bare)
        # and collect it so the caller can forward it to piplite.install.
        url = next((g for g in index_url_match.groups()[1:] if g is not None), None)
        if url and index_urls is not None:
            index_urls.append(url)
        return
    elif raw.startswith("-"):
        warn(f"{spec_path}:{line_no}: unrecognized spec: {raw}")
        return

    if raw:
        yield raw
