#!/usr/bin/env bash
set -euo pipefail
: "${GATEWAY_TEST_DATABASE_URL:?disposable CI database required}"
: "${GATEWAY_TEST_RUNTIME_URL:?restricted CI database role required}"
python -m pip install --upgrade pip==26.2.1
python -m pip install -r requirements-dev.txt -r mcp-servers/mcp-gateway/requirements.txt -r mcp-servers/document-graph/requirements.txt -r jobs/document-graph-sync/requirements.txt ./shared-runtime ./document-graph-core
python - <<'CHECK'
import os, time
import psycopg
from urllib.parse import urlparse
url = os.environ['GATEWAY_TEST_DATABASE_URL']
if urlparse(url).hostname not in ('horology-ci-postgres', '127.0.0.1', 'localhost'):
    raise SystemExit('CI must never migrate or truncate a production database')
for attempt in range(30):
    try:
        psycopg.connect(url).close()
        break
    except psycopg.OperationalError:
        time.sleep(1)
else:
    raise SystemExit('Disposable PostgreSQL did not become ready')
CHECK
export DATABASE_URL="$GATEWAY_TEST_DATABASE_URL"  # alembic/env.py selects the Psycopg 3 driver
export GATEWAY_DB_PASSWORD=ci-runtime-only GRAPH_DB_PASSWORD=ci-graph-only CRON_SWEEP_RO_PASSWORD=ci-cron-only
# The CI Postgres image has pgvector, so every migration runs from an empty database.
python -m alembic upgrade head
mkdir -p /workspace/reports
python -m pytest tests/ -q -p no:cacheprovider --junitxml=/workspace/reports/tests.xml
python - <<'CHECK_SKIPS'
import xml.etree.ElementTree as ET
for case in ET.parse('/workspace/reports/tests.xml').iter('testcase'):
    if case.find('skipped') is not None and not case.attrib.get('classname', '').startswith(('test_docker_stack.', 'tests.test_docker_stack.')):
        raise SystemExit('Unexpected skipped test: ' + case.attrib.get('classname', '') + '.' + case.attrib.get('name', ''))
CHECK_SKIPS
python -m pip_audit --disable-pip --no-deps -r mcp-servers/mcp-gateway/requirements.txt
python -m pip_audit --disable-pip --no-deps -r mcp-servers/document-graph/requirements.txt
python -m pip_audit --disable-pip --no-deps -r jobs/document-graph-sync/requirements.txt
python -m pip_audit
