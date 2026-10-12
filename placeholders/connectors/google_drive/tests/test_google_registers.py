"""Bounded register writes: fixed resources, founder fields and changed-record protection.

Google requests are mocked; no real register is mutated.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'mcp-servers/mcp-gateway'))
from integrations.google_drive.rules import registers
from policy import Denied

CONFIG = {'drive_registers': ['pipeline', 'documents', 'decisions'], 'drive_pipeline_ids': ['1']}

@pytest.mark.parametrize('register,pipeline_id', [('other', 1), ('pipeline', 2), ('pipeline', True)])
def test_unapproved_register_or_pipeline_is_denied(register, pipeline_id):
    with pytest.raises(Denied):
        registers.allowed(CONFIG, register, pipeline_id)

@pytest.mark.parametrize('updates', [{'Current decision ID': '1'}, {'Status': 'Approved'}, {'Stage': '3'}, {'Agent status': 'Ready'}, {'Agent type': 'Codex'}, {'URL': 'https://attacker.test'}, {'Summary / Why': 123}])
def test_founder_and_target_fields_are_rejected_before_db_or_provider(updates):
    with pytest.raises(Denied):
        asyncio.run(registers.update_pipeline({}, CONFIG, 'a', None, 1, 'hash', updates, 'key'))


def test_cell_writes_preserve_formatting_and_do_not_parse_formulas():
    with patch.object(registers.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(registers, 'request', AsyncMock(return_value={} )) as request, patch.object(registers, 'values', AsyncMock(return_value=[['1', '=HYPERLINK("x")']])):
        asyncio.run(registers.write_cells('pipeline', ['ID', 'Summary / Why'], 2, {'Summary / Why': '=HYPERLINK("x")'}))
        body = request.call_args.kwargs['body']
        assert len(body['requests']) == 1
        update = body['requests'][0]['updateCells']
        assert update['fields'] == 'userEnteredValue'
        assert update['range']['sheetId'] == 2040100901
        assert update['rows'][0]['values'][0]['userEnteredValue'] == {'stringValue': '=HYPERLINK("x")'}


def test_append_never_overwrites_nonempty_row_without_id():
    with patch.object(registers, 'values', AsyncMock(return_value=[['1', 'existing'], ['', 'unfinished']])):
        assert asyncio.run(registers.free_row('pipeline', ['ID', 'Title'], 10, {1: 2})) == (4, 2)


def test_numeric_ids_cannot_be_duplicated_or_formula_based():
    for entries in ([['1'], ['1']], [['=MAX(A:A)+1']], [[True]]):
        with patch.object(registers, 'values', AsyncMock(return_value=entries)):
            with pytest.raises(Denied):
                asyncio.run(registers.identities('pipeline', ['ID'], 10))


def test_register_readback_mismatch_is_not_reported_as_success():
    with patch.object(registers.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(registers, 'request', AsyncMock(return_value={})), patch.object(registers, 'values', AsyncMock(return_value=[['old']])):
        with pytest.raises(Denied, match='reconciliation'):
            asyncio.run(registers.write_cells('pipeline', ['Summary / Why'], 2, {'Summary / Why': 'new'}))


def test_missing_header_never_sends_partial_write():
    with patch.object(registers, 'request', AsyncMock()) as request:
        with pytest.raises(Denied):
            asyncio.run(registers.write_cells('pipeline', ['ID'], 2, {'Summary / Why': 'new'}))
        request.assert_not_called()


@pytest.mark.parametrize('register', ['documents', 'decisions'])
def test_foreign_draft_pipeline_cannot_be_indexed_or_proposed(register):
    with patch.object(registers.drafts, 'own_draft', AsyncMock(return_value={'pipeline_id': '2'})):
        with pytest.raises(Denied, match='different Pipeline'):
            asyncio.run(registers.add_record({}, CONFIG, 'a', None, register, 1, 'file', 'assessment', 'Question', 'Reason', 'key'))


def test_layout_rejects_renamed_register():
    with patch.object(registers.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(registers, 'request', AsyncMock(return_value={'sheets': [{'properties': {'sheetId': 2040100901, 'title': 'Other'}}]})):
        with pytest.raises(Denied, match='identity changed'):
            asyncio.run(registers.layout('pipeline'))


class Store:
    def __init__(self, receipt=None):
        self.receipt = receipt
        self.claimed = False
        self.finished = None
        self.ledger = self
    def connect(self):
        return self
    def cursor(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def execute(self, *args):
        pass
    def previous(self, *args):
        return self.receipt
    def begin(self, *args):
        self.claimed = True
    def finish(self, *args):
        self.finished = args[-1]


@pytest.mark.parametrize('manual,changed', [(True, False), (False, True)])
def test_manual_or_changed_pipeline_never_claims_or_writes(manual, changed):
    store = Store()
    item = {'Agent type': 'Manual' if manual else 'Codex', 'Title': 'item'}
    with patch.object(registers, 'record', AsyncMock(return_value=(list(item), 2, item))), patch.object(registers, 'write_cells', AsyncMock()) as write:
        with pytest.raises(Denied):
            asyncio.run(registers.update_pipeline({}, CONFIG, 'a', store, 1, 'changed' if changed else registers.fingerprint(item), {'Status': 'Researching'}, 'key'))
        assert not store.claimed
        write.assert_not_called()


def test_completed_register_write_replay_does_not_touch_google():
    receipt = {'pipeline_id': 1, 'updated_fields': ['Status']}
    store = Store(receipt)
    with patch.object(registers, 'record', AsyncMock()) as read, patch.object(registers, 'write_cells', AsyncMock()) as write:
        assert asyncio.run(registers.update_pipeline({}, CONFIG, 'a', store, 1, 'hash', {'Status': 'Researching'}, 'key')) == receipt
        read.assert_not_called()
        write.assert_not_called()
        assert not store.claimed


def test_pipeline_update_keeps_protected_fields_and_sets_operator_date():
    store = Store()
    item = {'Agent type': 'Codex', 'Title': 'item', 'Stage': '1'}
    with patch.object(registers, 'record', AsyncMock(return_value=(list(item)+['Status', 'Updated'], 2, item))), patch.object(registers, 'write_cells', AsyncMock()) as write:
        asyncio.run(registers.update_pipeline({}, CONFIG, 'a', store, 1, registers.fingerprint(item), {'Status': 'Awaiting decision'}, 'key'))
        updates = write.call_args.args[-1]
        assert set(updates) == {'Status', 'Updated'}
        assert store.claimed and store.finished['pipeline_id'] == 1


def test_native_table_numeric_id_strings_pass_exact_readback():
    with patch.object(registers.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(registers, 'request', AsyncMock(return_value={})), patch.object(registers, 'values', AsyncMock(return_value=[['17', '1', 46307]])):
        asyncio.run(registers.write_cells('documents', ['Document ID', 'Pipeline ID', 'Last Updated'], 2, {'Document ID': 17, 'Pipeline ID': 1, 'Last Updated': 46307}))


def test_changed_numeric_id_still_fails_readback():
    with patch.object(registers.credentials, 'access_token', AsyncMock(return_value='test')), patch.object(registers, 'request', AsyncMock(return_value={})), patch.object(registers, 'values', AsyncMock(return_value=[['18']])):
        with pytest.raises(Denied):
            asyncio.run(registers.write_cells('documents', ['Document ID'], 2, {'Document ID': 17}))


def test_date_value_uses_singapore_date_and_native_serial():
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    expected = (datetime.now(ZoneInfo('Asia/Singapore')).date() - date(1899,12,30)).days
    assert registers.date_value() == expected
