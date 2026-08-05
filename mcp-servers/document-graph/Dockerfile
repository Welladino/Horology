FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# stdio transport: this container is meant to be `docker exec`'d into with
# the process attached to stdin/stdout, not left running as a standalone
# service. See docs/runbook/mcp/document_graph_server.md.
CMD ["python", "server.py"]
