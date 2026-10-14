"""Gateway test set-up: the gateway's folder on sys.path, and its example policy."""
import sys

import pytest

from .paths import GATEWAY

if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))  # gateway modules (policy, shared, integrations, ...) import as top-level names
from policy import load_policy  # noqa: E402


@pytest.fixture
def policy():
    return load_policy(GATEWAY / 'config/policy.example.json')
