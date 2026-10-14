# Matches local dev Python (3.14) for consistency across this project's
# tooling — no technical requirement to use this specific version, the
# mcp SDK and psycopg 3 both work fine on 3.12+ too.
FROM python:3.14-slim

WORKDIR /app

# Pinned third-party packages first: this slow layer is reused until a requirements file changes.
COPY mcp-servers/document-graph/requirements.txt .
COPY jobs/document-graph-sync/requirements.txt sync-requirements.txt
RUN pip install --no-cache-dir --upgrade pip==26.2.1 \
    && pip install --no-cache-dir -r requirements.txt -r sync-requirements.txt

# Our own packages (no dependencies of their own), so a code change rebuilds only from here.
COPY shared-runtime /opt/shared-runtime
COPY document-graph-core /opt/document-graph-core
RUN pip install --no-cache-dir --no-deps /opt/shared-runtime /opt/document-graph-core \
    && pip uninstall -y pip setuptools wheel \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin horology

COPY mcp-servers/document-graph/server.py .

COPY mcp-servers/document-graph/document_graph ./document_graph
# Same image runs as the Cloud Run job: python -m graph_sync
COPY jobs/document-graph-sync/graph_sync ./graph_sync

USER 10001

# Compose controls port publication; local host access is loopback only.
CMD ["python", "server.py"]
