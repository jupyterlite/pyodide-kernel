"""A ``micropip`` wrapper aware of jupyterlite conventions.

import piplite
await piplite.install("a-package")

`pyodide-kernel` also includes a browser shim for the IPython `%pip` magic

"""

from typing import Any
import asyncio
import json
import logging
from unittest.mock import patch

import micropip
from micropip.package_index import ProjectInfo
from micropip.package_index import query_package as _MP_QUERY_PACKAGE
from micropip.package_index import fetch_string_and_headers as _MP_FETCH_STRING

logger = logging.getLogger(__name__)


#: a list of Warehouse-like API endpoints or derived multi-package all.json
_PIPLITE_URLS = []

#: a cache of available packages
_PIPLITE_INDICES = {}

#: don't fall back to pypi.org if a package is not found in _PIPLITE_URLS
_PIPLITE_DISABLE_PYPI = False

#: a well-known file name respected by the rest of the build chain
ALL_JSON = "/all.json"


class PiplitePyPIDisabled(ValueError):
    """An error for when PyPI is disabled at the site level, but a download was
    attempted."""

    pass


async def _get_pypi_json_from_index(name, piplite_url, fetch_kwargs) -> ProjectInfo:
    """Attempt to load a specific ``pkgname``'s releases from a specific piplite
    URL's index.
    """
    index = _PIPLITE_INDICES.get(piplite_url, {})

    if not index:
        try:
            data, headers = await _MP_FETCH_STRING(piplite_url, fetch_kwargs)
        except Exception as err:
            logger.warn("Could not fetch %s: %s", piplite_url, err)

        try:
            index = json.loads(data)
            _PIPLITE_INDICES.update({piplite_url: index})
        except Exception as err:
            logger.warn("Could not parse %s: %s", piplite_url, err)

    pkg = dict((index or {}).get(name) or {})

    if not pkg:
        return None

    # rewrite local paths
    for release in pkg["releases"].values():
        for artifact in release:
            if artifact["url"].startswith("."):
                artifact["url"] = (
                    f"""{piplite_url.split(ALL_JSON)[0]}/{artifact["url"]}"""
                    f"""?sha256={artifact["digests"]["sha256"]}"""
                )

    info = ProjectInfo._compatible_only(name, pkg["releases"])
    return info


async def _query_package(
    name: str,
    fetch_kwargs: dict[str, Any] | None = None,
    index_urls: list[str] | str | None = None,
) -> ProjectInfo:
    """Fetch the warehouse API metadata for a specific ``pkgname``."""
    for piplite_url in _PIPLITE_URLS:
        if not piplite_url.split("?")[0].split("#")[0].endswith(ALL_JSON):
            logger.warn("Non-all.json piplite URL not supported %s", piplite_url)
            continue

        pypi_json_from_index = await _get_pypi_json_from_index(
            name, piplite_url, fetch_kwargs
        )
        if pypi_json_from_index:
            return pypi_json_from_index

    if _PIPLITE_DISABLE_PYPI:
        raise PiplitePyPIDisabled(
            f"{name} could not be installed: PyPI fallback is disabled"
        )

    return await _MP_QUERY_PACKAGE(
        name=name,
        fetch_kwargs=fetch_kwargs,
        index_urls=index_urls
    )


async def _install(
    requirements: str | list[str],
    keep_going: bool = False,
    deps: bool = True,
    credentials: str | None = None,
    pre: bool = False,
    index_urls: list[str] | str | None = None,
    *,
    verbose: bool | int = False,
):
    """Invoke micropip.install with a patch to get data from local indexes"""
    with patch("micropip.package_index.query_package", _query_package):
        return await micropip.install(
            requirements=requirements,
            keep_going=keep_going,
            deps=deps,
            credentials=credentials,
            pre=pre,
            index_urls=index_urls,
            verbose=verbose,
        )


def install(
    requirements: str | list[str],
    keep_going: bool = False,
    deps: bool = True,
    credentials: str | None = None,
    pre: bool = False,
    index_urls: list[str] | str | None = None,
    *,
    verbose: bool | int = False,
):
    """Install the given package and all of its dependencies.

    If a package is not found in the Pyodide repository it will be loaded from
    PyPI. Micropip can only load pure Python wheels or wasm32/emscripten wheels
    built by Pyodide.

    When used in web browsers, downloads from PyPI will be cached. When run in
    Node.js, packages are currently not cached, and will be re-downloaded each
    time ``micropip.install`` is run.

    Parameters
    ----------
    requirements :

        A requirement or list of requirements to install. Each requirement is a
        string, which should be either a package name or a wheel URI:

        - If the requirement does not end in ``.whl``, it will be interpreted as
          a package name. A package with this name must either be present
          in the Pyodide lock file or on PyPI.

        - If the requirement ends in ``.whl``, it is a wheel URI. The part of
          the requirement after the last ``/``  must be a valid wheel name in
          compliance with the `PEP 427 naming convention
          <https://www.python.org/dev/peps/pep-0427/#file-format>`_.

        - If a wheel URI starts with ``emfs:``, it will be interpreted as a path
          in the Emscripten file system (Pyodide's file system). E.g.,
          ``emfs:../relative/path/wheel.whl`` or ``emfs:/absolute/path/wheel.whl``.
          In this case, only .whl files are supported.

        - If a wheel URI requirement starts with ``http:`` or ``https:`` it will
          be interpreted as a URL.

        - In node, you can access the native file system using a URI that starts
          with ``file:``. In the browser this will not work.

    keep_going :

        This parameter decides the behavior of micropip when it encounters a
        Python package without a pure Python wheel while doing dependency
        resolution:

        - If ``False``, an error will be raised on first package with a missing
          wheel.

        - If ``True``, micropip will keep going after the first error, and
          report a list of errors at the end.

    deps :

        If ``True``, install dependencies specified in METADATA file for each
        package. Otherwise do not install dependencies.

    credentials :

        This parameter specifies the value of ``credentials`` when calling the
        `fetch() <https://developer.mozilla.org/en-US/docs/Web/API/fetch>`__
        function which is used to download the package.

        When not specified, ``fetch()`` is called without ``credentials``.

    pre :

        If ``True``, include pre-release and development versions. By default,
        micropip only finds stable versions.

    index_urls :

        A list of URLs or a single URL to use as the package index when looking
        up packages. If None, *https://pypi.org/pypi/{package_name}/json* is used.

        - The index URL should support the
          `JSON API <https://warehouse.pypa.io/api-reference/json/>`__ .

        - The index URL may contain the placeholder {package_name} which will be
          replaced with the package name when looking up a package. If it does not
          contain the placeholder, the package name will be appended to the URL.

        - If a list of URLs is provided, micropip will try each URL in order until
          it finds a package. If no package is found, an error will be raised.

    verbose :
        Print more information about the process.
        By default, micropip is silent. Setting ``verbose=True`` will print
        similar information as pip.
    """

    return asyncio.ensure_future(
        _install(
            requirements=requirements,
            keep_going=keep_going,
            deps=deps,
            credentials=credentials,
            pre=pre,
            index_urls=index_urls,
            verbose=verbose,
        )
    )


__all__ = ["install"]
