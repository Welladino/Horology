# Matches local dev Python (3.14) for consistency across this project's
# tooling — no technical requirement to use this specific version, the
# mcp SDK and psycopg2-binary both work fine on 3.12+ too.
FROM python:3.14-slim

WORKDIR /app

COPY shared-runtime /opt/shared-runtime
COPY mcp-servers/document-graph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt /opt/shared-runtime

COPY mcp-servers/document-graph/server.py .

COPY mcp-servers/document-graph/document_graph ./document_graph

# Internal Compose network only; no published host port.
CMD ["python", "server.py"]
