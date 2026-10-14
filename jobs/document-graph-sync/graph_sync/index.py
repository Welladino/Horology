"""Read Document Index rows into plain records; no network or database access."""
import re
from dataclasses import dataclass

TAB = "Document Index"
REQUIRED = ("Document ID", "Title", "Drive URL", "Workspace", "Document Type", "Graph Inclusion",
            "Graph Sync Status", "Graph Document ID", "Last Synced Revision", "Supersedes document ID")
# Copied onto graph documents when present; a workbook without them still syncs.
FIELD_COLUMNS = ("Domain", "Entity", "Pipeline ID")
# Columns the job writes back, in the sheet's own order.
STATUS_COLUMNS = ("Graph Sync Status", "Graph Document ID", "Last Synced Revision")
DRIVE_ID = re.compile(r"/(?:file|document|spreadsheets|presentation)/d/([A-Za-z0-9_-]{10,})|[?&]id=([A-Za-z0-9_-]{10,})")


@dataclass
class IndexRow:
    row_number: int  # 1-based sheet row
    index_id: str
    title: str
    drive_url: str
    workspace: str
    doc_type: str
    included: bool
    supersedes: str
    domain: str = ""
    business_entity: str = ""  # the sheet's "Entity" column
    pipeline_id: str = ""


def drive_file_id(url):
    match = DRIVE_ID.search(url or "")
    return (match.group(1) or match.group(2)) if match else None


def is_true(value):
    # The dropdown stores booleans; typed text is accepted too.
    return value is True or str(value).strip().upper() == "TRUE"


def text(value):
    # Numbers come back as floats from unformatted reads: 3.0 -> "3".
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return "" if value is None else str(value).strip()


def column_letter(index):
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def parse(values):
    """Return (rows, {header: column index}) from a tab's raw values, header first."""
    if not values:
        raise ValueError("Document Index is empty")
    headers = {str(name).strip(): i for i, name in enumerate(values[0])}
    missing = [name for name in REQUIRED if name not in headers]
    if missing:
        raise ValueError("Document Index is missing columns: " + ", ".join(missing))
    rows = []
    for offset, raw in enumerate(values[1:], start=2):
        cell = lambda name: raw[headers[name]] if name in headers and headers[name] < len(raw) else None
        index_id = text(cell("Document ID"))
        if not index_id:
            continue
        rows.append(IndexRow(offset, index_id, text(cell("Title")), text(cell("Drive URL")), text(cell("Workspace")),
                             text(cell("Document Type")), is_true(cell("Graph Inclusion")), text(cell("Supersedes document ID")),
                             text(cell("Domain")), text(cell("Entity")), text(cell("Pipeline ID"))))
    ids = [row.index_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Document Index has duplicate Document IDs")
    return rows, headers


def status_range(headers, row_number):
    """A1 range covering the write-back columns of one row; they must be adjacent."""
    columns = [headers[name] for name in STATUS_COLUMNS]
    if columns != list(range(columns[0], columns[0] + len(columns))):
        raise ValueError("Graph Sync Status, Graph Document ID and Last Synced Revision must be adjacent columns")
    return f"'{TAB}'!{column_letter(columns[0])}{row_number}:{column_letter(columns[-1])}{row_number}"
