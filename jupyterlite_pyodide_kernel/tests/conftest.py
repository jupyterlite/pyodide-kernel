from pathlib import Path

from jupyterlite.tests.conftest import (
    an_empty_lite_dir,
    a_fixture_server,
    an_unused_port,
)

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
WHEELS = [*FIXTURES.glob("*.whl")]
