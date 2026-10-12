#!/usr/bin/env bash
set -euo pipefail
: "${GATEWAY_TEST_DATABASE_URL:?disposable CI database required}"
: "${GATEWAY_TEST_RUNTIME_URL:?restricted CI database role required}"
python -m pip install --upgrade pip==26.2.1
python -m pip install -r requirements-dev.txt -r mcp-servers/mcp-gateway/requirements.txt -r mcp-servers/document-graph/requirements.txt ./shared-runtime
python - <<'CHECK'
import os, time
import psycopg2
from urllib.parse import urlparse
url = os.environ['GATEWAY_TEST_DATABASE_URL']
if urlparse(url).hostname not in ('horology-ci-postgres', '127.0.0.1', 'localhost'):
    raise SystemExit('CI must never migrate or truncate a production database')
for attempt in range(30):
    try:
        psycopg2.connect(url).close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    raise SystemExit('Disposable PostgreSQL did not become ready')
CHECK
export DATABASE_URL="${GATEWAY_TEST_DATABASE_URL/postgresql:\/\//postgresql+psycopg2:\/\/}"
export GATEWAY_DB_PASSWORD=ci-runtime-only
# Older graph migrations require graph extensions, not used by mocked graph tests.
# Exercise both actual gateway migrations against an isolated fresh database.
python -m alembic stamp 20260807_001
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
python -m pip_audit
