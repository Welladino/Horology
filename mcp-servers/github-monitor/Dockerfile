# Matches local dev Python (3.14) for consistency across this project's
# tooling, same rationale as mcp-servers/document-graph/Dockerfile.
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

CMD ["python", "server.py"]
