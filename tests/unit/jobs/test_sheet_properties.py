"""Quoting rules for any tab name, file id or Drive link, checked on generated inputs (Hypothesis)."""
import sys
from urllib.parse import unquote

from hypothesis import given, settings, strategies as st

from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import google, index  # noqa: E402


@settings(max_examples=500)
@given(st.text(max_size=60))
def test_a_tab_reference_always_reads_back_as_the_tab_name(tab):
    reference = google.repr_tab(tab)
    assert reference.startswith("'") and reference.endswith("'")
    inner = reference[1:-1]
    assert "'" not in inner.replace("''", "")  # every apostrophe inside is doubled
    assert inner.replace("''", "'") == tab


@settings(max_examples=500)
@given(st.text(max_size=60))
def test_a_path_segment_never_contains_a_separator_and_decodes_back(value):
    segment = google._path(value)
    assert not any(c in segment for c in "/?#\\ ")
    assert unquote(segment) == value


DRIVE_ID = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-", min_size=10, max_size=60)


@given(DRIVE_ID, st.sampled_from(["file", "document", "spreadsheets", "presentation"]),
       st.sampled_from(["", "/view", "/edit", "/edit?usp=sharing", "/view?usp=drivesdk"]))
def test_the_file_id_is_read_from_any_drive_link_shape(file_id, kind, suffix):
    assert index.drive_file_id(f"https://docs.google.com/{kind}/d/{file_id}{suffix}") == file_id
    assert index.drive_file_id(f"https://drive.google.com/open?id={file_id}") == file_id


@given(st.text(max_size=80).filter(lambda s: "/d/" not in s and "id=" not in s))
def test_text_that_isnt_a_drive_link_has_no_file_id(text):
    assert index.drive_file_id(text) is None
