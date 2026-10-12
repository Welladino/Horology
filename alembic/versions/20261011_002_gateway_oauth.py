"""Persistent client registration, login state and revocable OAuth grants."""
from alembic import op
revision = '20261011_002'
down_revision = '20261011_001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE SCHEMA gateway_auth')
    op.execute('REVOKE ALL ON SCHEMA gateway_auth FROM PUBLIC')
    op.execute('CREATE TABLE gateway_auth.records(kind text NOT NULL,key_hash text NOT NULL,data jsonb NOT NULL,expires timestamptz NOT NULL,PRIMARY KEY(kind,key_hash))')
    op.execute('CREATE INDEX oauth_records_expiry ON gateway_auth.records(expires)')
    op.execute("CREATE INDEX oauth_records_grant ON gateway_auth.records((data->>'grant_id'))")
    op.execute('GRANT USAGE ON SCHEMA gateway_auth TO horology_gateway')
    op.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON gateway_auth.records TO horology_gateway')


def downgrade():
    op.execute('DROP SCHEMA gateway_auth CASCADE')
