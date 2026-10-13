"""Dedicated document-graph database login and its own OAuth records table.

The document graph is about to face the internet, so it stops using the
owner login. `horology_graph` can read and write the graph tables (the sheet
sync updates and removes rows) and its own `graph_auth.records`, nothing else.
Tokens live apart from the gateway's `gateway_auth.records`.
"""
import os
from alembic import op
from psycopg2 import sql

revision = '20261013_003'
down_revision = '20261013_002'
branch_labels = None
depends_on = None


def upgrade():
    password = os.environ.get('GRAPH_DB_PASSWORD')
    if not password:
        raise RuntimeError('GRAPH_DB_PASSWORD is required before running this migration')
    bind = op.get_bind()
    raw = bind.connection.driver_connection
    # psycopg quoting handles arbitrary password characters; no secret in source.
    bind.exec_driver_sql(sql.SQL('CREATE ROLE horology_graph LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Literal(password)).as_string(raw))
    bind.exec_driver_sql(sql.SQL('GRANT CONNECT ON DATABASE {} TO horology_graph').format(sql.Identifier(bind.engine.url.database)).as_string(raw))
    op.execute('GRANT USAGE ON SCHEMA public TO horology_graph')
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO horology_graph')
    op.execute('GRANT SELECT, INSERT ON document_links TO horology_graph')
    op.execute('GRANT SELECT, INSERT, UPDATE ON document_embeddings TO horology_graph')
    for table in ('documents', 'document_links'):
        op.execute(f"DO $$ BEGIN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO horology_graph', pg_get_serial_sequence('{table}', 'id')); END $$")
    op.execute('CREATE SCHEMA graph_auth')
    op.execute('REVOKE ALL ON SCHEMA graph_auth FROM PUBLIC')
    op.execute('CREATE TABLE graph_auth.records(kind text NOT NULL,key_hash text NOT NULL,data jsonb NOT NULL,expires timestamptz NOT NULL,PRIMARY KEY(kind,key_hash))')
    op.execute('CREATE INDEX graph_auth_records_expiry ON graph_auth.records(expires)')
    op.execute("CREATE INDEX graph_auth_records_grant ON graph_auth.records((data->>'grant_id'))")
    op.execute('GRANT USAGE ON SCHEMA graph_auth TO horology_graph')
    op.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON graph_auth.records TO horology_graph')


def downgrade():
    op.execute('DROP SCHEMA graph_auth CASCADE')
    bind = op.get_bind()
    raw = bind.connection.driver_connection
    for table in ('documents', 'document_links'):
        op.execute(f"DO $$ BEGIN EXECUTE format('REVOKE USAGE ON SEQUENCE %s FROM horology_graph', pg_get_serial_sequence('{table}', 'id')); END $$")
    op.execute('REVOKE ALL ON documents, document_links, document_embeddings FROM horology_graph')
    op.execute('REVOKE USAGE ON SCHEMA public FROM horology_graph')
    bind.exec_driver_sql(sql.SQL('REVOKE CONNECT ON DATABASE {} FROM horology_graph').format(sql.Identifier(bind.engine.url.database)).as_string(raw))
    op.execute('DROP ROLE horology_graph')
