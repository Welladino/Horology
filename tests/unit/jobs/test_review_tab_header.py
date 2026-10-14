"""The review tabs leave a tab alone when its header isn't the one they write."""
import sys

from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import review_tab  # noqa: E402


def test_a_tab_with_a_different_header_is_left_alone():
    assert review_tab._rows([["Something else"], ["1", "x"]], review_tab.ENTITY_HEADER) == []
