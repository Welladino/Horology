"""Statement and lock timeouts as defaults on the service logins.

Postgres applies role defaults when each session starts, including sessions
the Neon pooler opens, so the services no longer send them per transaction.
"""
from alembic import op

revision = '20261014_001'
down_revision = '20261013_003'
branch_labels = None
depends_on = None

ROLES = ('horology_gateway', 'horology_graph')


def upgrade():
    for role in ROLES:
        op.execute(f"ALTER ROLE {role} SET statement_timeout = '10s'")
        op.execute(f"ALTER ROLE {role} SET lock_timeout = '3s'")


def downgrade():
    for role in ROLES:
        op.execute(f'ALTER ROLE {role} RESET statement_timeout')
        op.execute(f'ALTER ROLE {role} RESET lock_timeout')
