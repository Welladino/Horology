"""add_readonly_role_for_cron_sweep

Revision ID: 20260807_001
Revises: 20260806_001
Create Date: 2026-08-07 15:24:41.346933

Adds a dedicated Postgres role, SELECT-only on documents and
document_embeddings (exactly what list_unembedded_documents' query
touches - nothing else, not document_links, not run_log, and no
default-privilege grant on future tables either - a later migration
that wants this role to read a new table should grant it explicitly,
here or in its own migration, rather than inheriting it silently).
This is the credential the daily cron backfill-sweep script uses, kept
separate from document-graph-mcp's own read-write DATABASE_URL_POOLED,
per the "every credential-holder gets its own narrowly-scoped
credential" pattern already used for both MCP servers. See
docs/planning/notes/2026-08-07_document-graph-completeness-punch-list_note.md
and the accompanying research brief on the cron script/security
pattern.

The password is read from the CRON_SWEEP_RO_PASSWORD env var at
migration time, never hardcoded - required, not optional, so a bad
`alembic upgrade head` run can't silently create the role with no
password or a placeholder value.
"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260807_001'
down_revision: Union[str, Sequence[str], None] = '20260806_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_NAME = "horology_cron_sweep_ro"


def upgrade() -> None:
    """Upgrade schema."""
    password = os.environ.get("CRON_SWEEP_RO_PASSWORD")
    if not password:
        raise RuntimeError(
            "CRON_SWEEP_RO_PASSWORD must be set in the environment to run this "
            "migration - it's the password for the new read-only role, not "
            "something this migration should invent or hardcode."
        )

    # CREATE ROLE / GRANT don't support bind params - the password comes from
    # a trusted env var (validated above), not user input, so direct string
    # interpolation into DDL is the standard psycopg2/Alembic pattern here.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROLE_NAME}') THEN
                CREATE ROLE {ROLE_NAME} LOGIN PASSWORD '{password}';
            END IF;
        END
        $$;
        """
    )
    bind = op.get_bind()
    db_name = bind.engine.url.database
    op.execute(f'GRANT CONNECT ON DATABASE "{db_name}" TO {ROLE_NAME};')
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE_NAME};")
    op.execute(f"GRANT SELECT ON documents, document_embeddings TO {ROLE_NAME};")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {ROLE_NAME};")
    op.execute(f"DROP ROLE IF EXISTS {ROLE_NAME};")
