"""Repository paths, so tests don't compute them from their own location."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATEWAY = REPO / "mcp-servers" / "mcp-gateway"
DOCUMENT_GRAPH = REPO / "mcp-servers" / "document-graph"
SYNC_JOB = REPO / "jobs" / "document-graph-sync"
WORKFLOW = REPO / "plugins" / "horology-workflows" / "skills" / "horology-capture-triage" / "references" / "workflow.yaml"
PLUGINS = REPO / "plugins"
CLICKUP_SYNC = REPO / "google_appscript" / "clickup-sync"
PIPELINE_DECISIONS = REPO / "google_appscript" / "pipeline-decisions"
