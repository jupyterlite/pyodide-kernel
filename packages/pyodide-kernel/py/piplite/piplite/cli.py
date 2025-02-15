"""A CLI for the subset of ``pip`` commands supported by ``micropip.install``.

As of the upstream:

    https://github.com/pyodide/micropip/blob/v0.2.0/micropip/_micropip.py#L468

.. code:

    async def install(
        self,
        requirements: str | list[str],                  # -r and [packages]
        keep_going: bool = False,                       # --verbose
        deps: bool = True,                              # --no-deps
        credentials: str | None = None,                 # no CLI alias
        pre: bool = False,                              # --pre
        index_urls: list[str] | str | None = None,      # -i and --index-url
        *,
        verbose: bool | int | None = None,
    ):
```

As this is _not_ really a CLI, it doesn't bother with accurate return codes, and
failures should not block execution.
"""

import re
import sys
import typing
from typing import Optional, List, Tuple
from dataclasses import dataclass

from argparse import ArgumentParser
from pathlib import Path


@dataclass
class RequirementsContext:
    """Track state while parsing requirements files."""

    index_url: Optional[str] = None
    requirements: List[str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []

    def add_requirement(self, req: str):
        """Add a requirement with the currently active index URL."""
        self.requirements.append((req, self.index_url))


REQ_FILE_PREFIX = r"^(-r|--requirements)\s*=?\s*(.*)\s*"

# Matches a pip-style index URL, with support for quote enclosures
INDEX_URL_PREFIX = (
    r'^(--index-url|-i)\s*=?\s*(?:"([^"]*)"|\047([^\047]*)\047|([^\s]*))\s*$'
)


__all__ = ["get_transformed_code"]


def warn(msg):
    print(msg, file=sys.stderr, flush=True)


def _get_parser() -> ArgumentParser:
    """Build a pip-like CLI parser."""
    parser = ArgumentParser(
        "piplite",
        exit_on_error=False,
        allow_abbrev=False,
        description="a pip-like wrapper for `piplite` and `micropip`",
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
        help="paths to requirements files",
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
        help="the index URL to use for package lookup",
    )
    parser.add_argument(
        "packages",
        nargs="*",
        type=str,
        default=[],
        help="package names (or wheel URLs) to install",
    )

    return parser


async def get_transformed_code(argv: list[str]) -> typing.Optional[str]:
    """Return a string of code for use in in-kernel execution."""
    action, kwargs = await get_action_kwargs(argv)

    if action == "help":
        pass
    if action == "install":
        if kwargs["requirements"]:
            return f"""await __import__("piplite").install(**{kwargs})\n"""
        else:
            warn("piplite needs at least one package to install")


async def get_action_kwargs(argv: list[str]) -> tuple[typing.Optional[str], dict]:
    """Get the arguments to `piplite` subcommands from CLI-like tokens."""
    parser = _get_parser()

    try:
        args = parser.parse_intermixed_args(argv)
    except (Exception, SystemExit):
        return None, {}

    kwargs = {}
    action = args.action

    if action == "install":
        # CLI index URL, if provided, is the only one we'll use
        cli_index_url = args.index_url
        all_requirements = []
        last_seen_file_index = None

        if args.packages:
            all_requirements.extend((pkg, cli_index_url) for pkg in args.packages)

        # Process requirements files
        for req_file in args.requirements or []:
            context = RequirementsContext()

            if not Path(req_file).exists():
                warn(f"piplite could not find requirements file {req_file}")
                continue

            # Process the file and capture any index URL it contains
            for line_no, line in enumerate(
                Path(req_file).read_text(encoding="utf-8").splitlines()
            ):
                await _packages_from_requirements_line(
                    Path(req_file), line_no + 1, line, context
                )

            # Keep track of the last index URL we saw in any requirements file
            if context.index_url is not None:
                last_seen_file_index = context.index_url

            # Add requirements - if CLI provided an index URL, use that instead
            if cli_index_url:
                all_requirements.extend(
                    (req, cli_index_url) for req, _ in context.requirements
                )
            else:
                all_requirements.extend(context.requirements)

        if all_requirements:
            kwargs["requirements"] = []

            # Add all requirements
            kwargs["requirements"].extend(req for req, _ in all_requirements)

            # Use index URL with proper precedence:
            # 1. CLI index URL if provided
            # 2. Otherwise, last seen index URL from any requirements file
            effective_index = cli_index_url or last_seen_file_index
            if effective_index:
                kwargs["index_urls"] = effective_index

        # Other CLI flags remain unchanged
        if args.pre:
            kwargs["pre"] = True
        if args.no_deps:
            kwargs["deps"] = False
        if args.verbose:
            kwargs["keep_going"] = True

    return action, kwargs


async def _packages_from_requirements_file(
    req_path: Path,
) -> Tuple[List[Tuple[str, Optional[List[str]]]], List[str]]:
    """Extract package requirements and index URLs from a requirements file.

    This function processes a requirements file to collect both package requirements
    and any index URLs specified in it (with support for nested requirements).

    Returns:
        A tuple of:
        - List of (requirement, index_urls) pairs, where index_urls is a list of URLs
          that should be used for this requirement
        - List of index URLs found in the file
    """

    if not req_path.exists():
        warn(f"piplite could not find requirements file {req_path}")
        return [], []

    context = RequirementsContext()

    for line_no, line in enumerate(req_path.read_text(encoding="utf-8").splitlines()):
        await _packages_from_requirements_line(req_path, line_no + 1, line, context)

    return context.requirements, context.index_urls


async def _packages_from_requirements_line(
    req_path: Path, line_no: int, line: str, context: RequirementsContext
) -> None:
    """Extract (potentially nested) package requirements from line of a
    requirements file.

    `micropip` has a sufficient pep508 implementation to handle most cases
    """
    req = line.strip().split("#")[0].strip()
    if not req:
        return

    # Handle nested requirements file
    req_file_match = re.match(REQ_FILE_PREFIX, req)
    if req_file_match:
        sub_path = req_file_match[2]
        if sub_path.startswith("/"):
            sub_req = Path(sub_path)
        else:
            sub_req = req_path.parent / sub_path
        nested_context = RequirementsContext()
        await _packages_from_requirements_file(sub_req, nested_context)
        # Use the last index URL from nested file, if one was found
        if nested_context.index_url:
            context.index_url = nested_context.index_url
        context.requirements.extend(nested_context.requirements)
        return

    # Check for index URL - this becomes the new active index URL.
    index_match = re.match(INDEX_URL_PREFIX, req)
    if index_match:
        url = next(group for group in index_match.groups()[1:] if group is not None)
        context.index_url = url.strip()
        return

    if req.startswith("-"):
        warn(f"{req_path}:{line_no}: unrecognized requirement: {req}")
        return

    context.add_requirement(req)
