import pytest
from pathlib import Path

from jupyterlite.tests.conftest import (
    an_empty_lite_dir,
    a_fixture_server,
    an_unused_port,
)

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
WHEELS = [*FIXTURES.glob("*.whl")]


@pytest.fixture
def index_cmd():
    """Get the command line arguments for indexing a folder."""
    return ("jupyter", "piplite", "index")
