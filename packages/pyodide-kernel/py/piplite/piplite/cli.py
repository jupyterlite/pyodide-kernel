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
    """Track state while parsing requirements files.

    This class maintains state about requirements and their associated index URLs.
    Multiple index URLs can be tracked to support searching in multiple indices
    in order of specification.
    """

    index_urls: List[str] = None
    requirements: List[str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.index_urls is None:
            self.index_urls = []

    def add_index_url(self, url: str) -> None:
        """Add an index URL to the list of URLs to search from."""
        if url not in self.index_urls:
            self.index_urls.append(url)

    def add_requirement(self, req: str):
        """Add a requirement that will use the current index URLs."""
        self.requirements.append((req, self.index_urls[:] if self.index_urls else None))


REQ_FILE_PREFIX = r"^(-r|--requirements)\s*=?\s*(.*)\s*"
INDEX_URL_PREFIX = r"^(--index-url|-i)\s*=?\s*(.*)\s*"


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
        all_index_urls = []
        if args.index_url:
            all_index_urls.append(args.index_url)

        all_requirements = []

        if args.packages:
            all_requirements.extend((pkg, all_index_urls[:]) for pkg in args.packages)

        # Process requirements files
        for req_file in args.requirements or []:
            try:
                requirements, file_index_urls = await _packages_from_requirements_file(
                    Path(req_file)
                )

                # If CLI provided an index URL, it should override the file's index URL
                # We update all requirements to use the CLI index URL instead. Or, we use
                # whatever index URL was found in the file (if any).
                if args.index_url:
                    all_requirements.extend(
                        (req, all_index_urls) for req, _ in requirements
                    )
                else:
                    for url in file_index_urls:
                        if url not in all_index_urls:
                            all_index_urls.append(url)
                    all_requirements.extend(requirements)
            except Exception as e:
                warn(f"Error processing requirements file {req_file}: {e}")
                continue

        if all_requirements:
            kwargs["requirements"] = []
            kwargs["requirements"].extend(req for req, _ in all_requirements)

            # Set the final index URLs, if we found any
            if all_index_urls:
                kwargs["index_urls"] = all_index_urls

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

    # Check for nested requirements file
    req_file_match = re.match(REQ_FILE_PREFIX, req)
    if req_file_match:
        sub_path = req_file_match[2]
        if sub_path.startswith("/"):
            sub_req = Path(sub_path)
        else:
            sub_req = req_path.parent / sub_path
        # Create a new context for the nested file to maintain its own index URLs.
        nested_context = RequirementsContext()
        nested_context.index_urls = context.index_urls[
            :
        ]  # i  nherit parent's index URLs
        await _packages_from_requirements_file(sub_req, nested_context)
        # Extend our requirements with the nested ones
        context.requirements.extend(nested_context.requirements)
        return

    # Check for index URL specification
    index_match = re.match(INDEX_URL_PREFIX, req)
    if index_match:
        context.add_index_url(index_match[2].strip())
        return

    if req.startswith("-"):
        warn(f"{req_path}:{line_no}: unrecognized requirement: {req}")
        return

    context.add_requirement(req)
