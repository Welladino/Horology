# Matches local dev Python (3.14) for consistency across this project's
# tooling — no technical requirement to use this specific version, the
# mcp SDK and psycopg 3 both work fine on 3.12+ too.
FROM python:3.14-slim

WORKDIR /app

COPY shared-runtime /opt/shared-runtime
COPY mcp-servers/document-graph/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==26.2.1 \
    && pip install --no-cache-dir -r requirements.txt /opt/shared-runtime \
    && pip uninstall -y pip setuptools wheel \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin horology

COPY mcp-servers/document-graph/server.py .

COPY mcp-servers/document-graph/document_graph ./document_graph

USER 10001

# Compose controls port publication; local host access is loopback only.
CMD ["python", "server.py"]
