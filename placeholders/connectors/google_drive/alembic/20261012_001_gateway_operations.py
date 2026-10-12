"""Persistent external-write idempotency and assignment-owned draft receipts."""
from alembic import op
revision = '20261012_001'
down_revision = '20261011_002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE SCHEMA gateway_operations')
    op.execute('REVOKE ALL ON SCHEMA gateway_operations FROM PUBLIC')
    op.execute("CREATE TABLE gateway_operations.operations(assignment text NOT NULL, operation text NOT NULL, key text NOT NULL, payload_hash text NOT NULL, status text NOT NULL CHECK(status IN ('pending','complete')), result jsonb, created timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(assignment,operation,key))")
    op.execute('GRANT USAGE ON SCHEMA gateway_operations TO horology_gateway')
    op.execute('GRANT SELECT,INSERT,UPDATE ON gateway_operations.operations TO horology_gateway')


def downgrade():
    op.execute('DROP SCHEMA gateway_operations CASCADE')
