"""Rename historical usage/cache identity columns; preserve all accounting rows."""
from alembic import op

revision = '20261013_001'
down_revision = '20261011_002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE gateway_quotas.reservations RENAME COLUMN assignment TO client_id')
    op.execute('ALTER TABLE gateway_quotas.cache RENAME COLUMN assignment TO client_id')
    op.execute('ALTER INDEX gateway_quotas.reservations_assignment_tool RENAME TO reservations_client_tool')
    op.execute('ALTER INDEX gateway_quotas.reservations_provider_assignment RENAME TO reservations_provider_client')


def downgrade():
    op.execute('ALTER INDEX gateway_quotas.reservations_client_tool RENAME TO reservations_assignment_tool')
    op.execute('ALTER INDEX gateway_quotas.reservations_provider_client RENAME TO reservations_provider_assignment')
    op.execute('ALTER TABLE gateway_quotas.cache RENAME COLUMN client_id TO assignment')
    op.execute('ALTER TABLE gateway_quotas.reservations RENAME COLUMN client_id TO assignment')
