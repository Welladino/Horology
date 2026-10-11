FROM python:3.12-slim
WORKDIR /app
COPY shared-runtime /opt/shared-runtime
COPY mcp-servers/mcp-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt /opt/shared-runtime && useradd --uid 10001 --create-home gateway && mkdir /state && chown gateway:gateway /state
COPY mcp-servers/mcp-gateway/server.py mcp-servers/mcp-gateway/policy.py ./
COPY mcp-servers/mcp-gateway/integrations ./integrations
COPY mcp-servers/mcp-gateway/shared ./shared
COPY mcp-servers/mcp-gateway/certs/supabase-prod-ca-2021.crt /certs/supabase-ca.crt
USER 10001:10001
ENV PGSSLROOTCERT=/certs/supabase-ca.crt PYTHONDONTWRITEBYTECODE=1 GATEWAY_BIND=0.0.0.0 GATEWAY_POLICY=/config/policy.json GATEWAY_LEDGER=/state/ledger.sqlite3
EXPOSE 8767
CMD ["python", "-m", "server"]
