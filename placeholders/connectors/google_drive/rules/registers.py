"""Fixed register operations, numeric identities and gateway-serialized writes.

Sheets has no conditional cell-update API: this lock coordinates gateway writers,
not direct human/Apps Script edits. Re-read expected values and use one workflow writer.
"""
import hashlib
import json
from datetime import datetime, date
from urllib.parse import quote
from zoneinfo import ZoneInfo

from policy import Denied
from shared.http import request
from ..auth import credentials
from . import drafts

REGISTERS = {
    'pipeline': ('1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI', 'Master', 2040100901, 'ID'),
    'documents': ('1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc', 'Document Index', 91352542, 'Document ID'),
    'decisions': ('1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE', 'Master', 961571432, 'Decision ID'),
}
PIPELINE_FIELDS = {'Summary / Why', 'Next step / Research question', 'Revisit trigger', 'Status', 'Agent status'}
PIPELINE_STATUSES = {'Researching', 'Awaiting decision'}


def allowed(config, register, pipeline_id):
    if register not in config.get('drive_registers', []) or str(pipeline_id) not in config.get('drive_pipeline_ids', []):
        raise Denied('Register or Pipeline ID is outside assignment scope')
    if type(pipeline_id) is not int or pipeline_id <= 0:
        raise Denied('A positive permanent Pipeline ID is required')


def date_value():
    """Native Sheets date serial, preserving the register's date formatting."""
    return (datetime.now(ZoneInfo('Asia/Singapore')).date() - date(1899, 12, 30)).days


def column(index):
    result = ''
    while index >= 0:
        index, remainder = divmod(index, 26)
        result = chr(65 + remainder) + result
        index -= 1
    return result


async def values(register, cell_range, *, formulas=False):
    file_id, tab, _, _ = REGISTERS[register]
    return (await request('GET', 'https://sheets.googleapis.com/v4/spreadsheets/' + file_id + '/values/' + quote("'"+tab+"'!"+cell_range, safe=''), token=await credentials.access_token(), params={'valueRenderOption': 'FORMULA' if formulas else 'UNFORMATTED_VALUE'})).get('values', [])


async def layout(register):
    file_id, tab, sheet_id, identity = REGISTERS[register]
    meta = await request('GET', 'https://sheets.googleapis.com/v4/spreadsheets/' + file_id, token=await credentials.access_token(), params={'fields': 'sheets.properties'})
    matches = [s['properties'] for s in meta.get('sheets', []) if s['properties'].get('sheetId') == sheet_id and s['properties'].get('title') == tab]
    if len(matches) != 1:
        raise Denied('Register sheet identity changed')
    rows = matches[0]['gridProperties']['rowCount']
    if not 2 <= rows <= 5000:
        raise Denied('Register exceeds verified row bound')
    columns = min(matches[0]['gridProperties']['columnCount'], 27)
    data = await values(register, 'A1:'+column(columns-1)+'1')
    headers = data[0] if data else []
    if identity not in headers or len(headers) != len(set(headers)):
        raise Denied('Register headers are missing or ambiguous')
    return headers, rows


async def identities(register, headers, rows):
    col = column(headers.index(REGISTERS[register][3]))
    entries = await values(register, f'{col}2:{col}{rows}')
    seen = {}
    for row, entry in enumerate(entries, 2):
        value = entry[0] if entry else ''
        if value in ('', None):
            continue
        if isinstance(value, bool) or not str(value).isdigit() or int(value) <= 0 or int(value) in seen:
            raise Denied('Register IDs require operator reconciliation')
        seen[int(value)] = row
    return seen


async def record(register, record_id):
    headers, rows = await layout(register)
    ids = await identities(register, headers, rows)
    if record_id not in ids:
        raise Denied('Permanent record ID was not found')
    row = ids[record_id]
    data = await values(register, f'A{row}:{column(len(headers)-1)}{row}', formulas=True)
    cells = data[0] if data else []
    return headers, row, {h: cells[i] if i < len(cells) else '' for i, h in enumerate(headers)}


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def text(value, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Denied('A bounded nonempty text value is required')
    return value


async def write_cells(register, headers, row, updates):
    if not set(updates).issubset(headers):
        raise Denied('Required register columns changed')
    file_id, _, sheet_id, _ = REGISTERS[register]
    requests = []
    for name, value in updates.items():
        col = headers.index(name)
        cell = {'numberValue': value} if type(value) in (int, float) else {'stringValue': str(value)}
        requests.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': row-1, 'endRowIndex': row, 'startColumnIndex': col, 'endColumnIndex': col+1}, 'rows': [{'values': [{'userEnteredValue': cell}]}], 'fields': 'userEnteredValue'}})
    await request('POST', 'https://sheets.googleapis.com/v4/spreadsheets/'+file_id+':batchUpdate', token=await credentials.access_token(), body={'requests': requests})
    actual = await values(register, f'A{row}:{column(len(headers)-1)}{row}')
    cells = actual[0] if actual else []
    def matches(actual, expected):
        # Native table/text columns may return numeric identifiers as strings.
        if type(expected) in (int, float):
            return actual == expected or (isinstance(actual, str) and actual == str(expected))
        return actual == expected
    if any(headers.index(k) >= len(cells) or not matches(cells[headers.index(k)], v) for k, v in updates.items()):
        raise Denied('Register write needs operator reconciliation')


async def free_row(register, headers, rows, ids):
    # Inspect bounded data, not just ID cells: never overwrite an incomplete record.
    data = await values(register, f'A2:{column(len(headers)-1)}{rows}', formulas=True)
    last = max((i for i, row in enumerate(data, 2) if any(v not in ('', None) for v in row)), default=1)
    if last >= rows:
        raise Denied('Register has no safe append row; operator must extend it')
    return last + 1, max(ids, default=0) + 1


async def update_pipeline(policy, config, assignment, store, pipeline_id, expected_fingerprint, updates, operation_key):
    allowed(config, 'pipeline', pipeline_id)
    if not updates or not set(updates).issubset(PIPELINE_FIELDS):
        raise Denied('Protected Pipeline fields cannot be edited')
    for value in updates.values():
        text(value)
    if 'Status' in updates and updates['Status'] not in PIPELINE_STATUSES:
        raise Denied('Agents cannot approve, reject or hand off work')
    if 'Agent status' in updates and updates['Agent status'] != 'No action':
        raise Denied('Agents cannot queue new work')
    payload = {'pipeline_id': pipeline_id, 'expected': expected_fingerprint, 'updates': updates}
    with store.ledger.connect() as db, db.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('horology-google-registers'))")
        previous = store.previous(assignment, 'drive_update_pipeline', operation_key, payload)
        if previous is not None:
            return previous
        headers, row, current = await record('pipeline', pipeline_id)
        if current.get('Agent type') == 'Manual' or fingerprint(current) != expected_fingerprint:
            raise Denied('Pipeline record changed or is founder-led')
        store.begin(assignment, 'drive_update_pipeline', operation_key, payload)
        await write_cells('pipeline', headers, row, {**updates, 'Updated': date_value()})
        result = {'pipeline_id': pipeline_id, 'updated_fields': list(updates)}
        store.finish(assignment, 'drive_update_pipeline', operation_key, result)
        return result


async def add_record(policy, config, assignment, store, register, pipeline_id, file_id, document_type, question, reason, operation_key):
    allowed(config, register, pipeline_id)
    if document_type not in ('research', 'plan', 'direction', 'assessment'):
        raise Denied('Unsupported document type')
    if register == 'decisions':
        text(question); text(reason)
    receipt = await drafts.own_draft(policy, config, assignment, file_id, store)
    if receipt['pipeline_id'] != str(pipeline_id):
        raise Denied('Draft belongs to a different Pipeline item')
    operation = 'drive_index_draft' if register == 'documents' else 'drive_propose_decision'
    payload = {'pipeline_id': pipeline_id, 'file_id': file_id, 'document_type': document_type, 'question': question, 'reason': reason}
    with store.ledger.connect() as db, db.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('horology-google-registers'))")
        previous = store.previous(assignment, operation, operation_key, payload)
        if previous is not None:
            return previous
        _, pipeline_row, item = await record('pipeline', pipeline_id)
        if item.get('Agent type') == 'Manual':
            raise Denied('Founder-led items are not agent work')
        headers, rows = await layout(register)
        ids = await identities(register, headers, rows)
        row, numeric_id = await free_row(register, headers, rows, ids)
        pipeline_url = 'https://docs.google.com/spreadsheets/d/'+REGISTERS['pipeline'][0]+'/edit#gid=2040100901&range=A'+str(pipeline_row)
        if register == 'documents':
            existing = await values(register, column(headers.index('Drive URL'))+'2:'+column(headers.index('Drive URL'))+str(rows))
            if any(file_id in str(entry[0]) for entry in existing if entry):
                raise Denied('Draft already indexed; reconcile existing record instead of duplicating')
            pipeline_ids = await values(register, column(headers.index('Pipeline ID'))+'2:'+column(headers.index('Pipeline ID'))+str(rows))
            sequences = await values(register, column(headers.index('Sequence'))+'2:'+column(headers.index('Sequence'))+str(rows))
            prior = [int(sequences[i][0]) for i, entry in enumerate(pipeline_ids) if entry and str(entry[0]) == str(pipeline_id) and i < len(sequences) and sequences[i] and str(sequences[i][0]).isdigit()]
            updates = {'Document ID': numeric_id, 'Pipeline item': item['Title'], 'Pipeline ID': pipeline_id, 'Sequence': max(prior, default=0)+1, 'Title': receipt['title'], 'Drive URL': receipt['url'], 'Workspace': 'welladino', 'Domain': item['Domain'], 'Entity': item.get('Entity', ''), 'Document Type': document_type, 'Document Status': 'draft', 'Last Updated': date_value(), 'Related Pipeline URL': pipeline_url}
        else:
            updates = {'Decision ID': numeric_id, 'Domain': item['Domain'], 'Pipeline title': item['Title'], 'Entity': item.get('Entity', ''), 'Pipeline ID': pipeline_id, 'Question': question, 'Reason': reason, 'Research Links': receipt['url'], 'Pipeline link': pipeline_url}
            # Decision, approval status/date, rework, graph state and review stage remain founder-owned.
        store.begin(assignment, operation, operation_key, payload)
        await write_cells(register, headers, row, updates)
        result = {'register': register, 'record_id': numeric_id, 'pipeline_id': pipeline_id, 'state': 'draft proposal' if register == 'decisions' else 'draft'}
        store.finish(assignment, operation, operation_key, result)
        return result
