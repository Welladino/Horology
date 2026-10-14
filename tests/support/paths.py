"""Repository paths, so tests don't compute them from their own location."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATEWAY = REPO / "mcp-servers" / "mcp-gateway"
DOCUMENT_GRAPH = REPO / "mcp-servers" / "document-graph"
SYNC_JOB = REPO / "jobs" / "document-graph-sync"
