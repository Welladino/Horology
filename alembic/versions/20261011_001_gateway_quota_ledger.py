"""Persistent MCP quota accounting and a dedicated gateway database login."""
import os
from alembic import op
from psycopg import sql

revision = '20261011_001'
down_revision = '20260807_001'
branch_labels = None
depends_on = None


def upgrade():
    password = os.environ.get('GATEWAY_DB_PASSWORD')
    if not password:
        raise RuntimeError('GATEWAY_DB_PASSWORD is required before running this migration')
    op.execute("""
        CREATE SCHEMA gateway_quotas;
        REVOKE ALL ON SCHEMA gateway_quotas FROM PUBLIC;
        CREATE TABLE gateway_quotas.reservation_lock (id integer PRIMARY KEY CHECK (id=1));
        INSERT INTO gateway_quotas.reservation_lock VALUES (1);
        CREATE TABLE gateway_quotas.reservations (
            assignment text NOT NULL, tool text NOT NULL, provider text NOT NULL,
            credits integer NOT NULL CHECK (credits>=0), day date NOT NULL,
            month date NOT NULL, created timestamptz NOT NULL);
        CREATE INDEX reservations_assignment_tool ON gateway_quotas.reservations (assignment,tool);
        CREATE INDEX reservations_provider_day ON gateway_quotas.reservations (provider,day);
        CREATE INDEX reservations_provider_month ON gateway_quotas.reservations (provider,month);
        CREATE INDEX reservations_provider_assignment ON gateway_quotas.reservations (provider,assignment);
        CREATE TABLE gateway_quotas.cache (
            assignment text NOT NULL, key text NOT NULL, value jsonb NOT NULL,
            expires timestamptz NOT NULL, PRIMARY KEY (assignment,key));
    """)
    bind = op.get_bind()
    raw = bind.connection.driver_connection
    # psycopg quoting handles arbitrary password characters; no secret in source.
    ddl = sql.SQL('CREATE ROLE horology_gateway LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Literal(password)).as_string(raw)
    bind.exec_driver_sql(ddl)
    op.execute('GRANT USAGE ON SCHEMA gateway_quotas TO horology_gateway')
    op.execute('GRANT SELECT, UPDATE ON gateway_quotas.reservation_lock TO horology_gateway')
    op.execute('GRANT SELECT, INSERT ON gateway_quotas.reservations TO horology_gateway')
    op.execute('GRANT SELECT, INSERT, UPDATE ON gateway_quotas.cache TO horology_gateway')
    connect = sql.SQL('GRANT CONNECT ON DATABASE {} TO horology_gateway').format(sql.Identifier(bind.engine.url.database)).as_string(raw)
    bind.exec_driver_sql(connect)


def downgrade():
    op.execute('DROP SCHEMA gateway_quotas CASCADE')
    bind = op.get_bind()
    statement = sql.SQL('REVOKE CONNECT ON DATABASE {} FROM horology_gateway').format(sql.Identifier(bind.engine.url.database)).as_string(bind.connection.driver_connection)
    bind.exec_driver_sql(statement)
    op.execute('DROP ROLE horology_gateway')
