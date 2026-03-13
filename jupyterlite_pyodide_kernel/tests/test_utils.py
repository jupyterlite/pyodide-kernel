from __future__ import annotations

import pytest

#: a "weird" URL with lots of `-`, may not exist in the future, but worked once
RTD_JLPK = (
    "https://jupyterlite-pyodide-kernel--269.org.readthedocs.build/en/269/"
    "_static/jupyterlite_pyodide_kernel-0.7.1-py3-none-any.whl"
)
#: just a wheel, probably available in the future
PYPI_JLW = (
    "https://pypi.org/packages/py3/j/jupyterlab-widgets/"
    "jupyterlab_widgets-3.0.15-py3-none-any.whl"
)


@pytest.mark.parametrize(
    ("raw", "expect_spec"),
    [
        ("not-a-valid.whl", ""),
        (RTD_JLPK, f"jupyterlite-pyodide-kernel @ {RTD_JLPK}"),
        (PYPI_JLW, f"jupyterlab-widgets @ {PYPI_JLW}"),
    ],
)
def test_wheel_to_pep508(raw: str, expect_spec: str) -> None:
    """Can we extract package names from wheels?"""
    from jupyterlite_pyodide_kernel.utils import wheel_to_pep508

    observed = wheel_to_pep508(raw) or ""
    assert observed == expect_spec
