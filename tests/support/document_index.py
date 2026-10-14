"""Document Index sheet rows for sync tests: the header and row builders."""

HEADER = ["Document ID", "Pipeline item", "Sequence", "Title", "Drive URL", "Workspace", "Domain", "Entity",
          "Document Type", "Document Status", "Last Updated", "Graph Inclusion", "Graph Sync Status",
          "Graph Document ID", "Last Synced Revision", "Related ClickUp URL", "Related Repo Document",
          "Related Pipeline URL", "Supersedes document ID", "Pipeline ID"]


def row(doc_id, title, file_id, included, doc_type="plan", workspace="test-ws", supersedes=""):
    cells = [""] * len(HEADER)
    cells[0], cells[3], cells[5], cells[8], cells[11], cells[18] = doc_id, title, workspace, doc_type, included, supersedes
    cells[4] = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
    return cells


FIELD_HEADER = HEADER + ["Domain", "Entity", "Pipeline ID"]


def field_row(doc_id, file_id, domain, entity, pipeline):
    return row(doc_id, "Plan " + doc_id, file_id, True) + [domain, entity, pipeline]
