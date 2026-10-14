"""Integration tests run against a disposable migrated Postgres; see tests/README.md."""
import os

import pytest


@pytest.fixture
def database():
    """The restricted horology_graph login on the disposable database; skips without it."""
    dsn = os.environ.get("GRAPH_TEST_RUNTIME_URL")
    if not dsn:
        pytest.skip("Disposable migrated Postgres with the horology_graph login is required")
    return dsn
