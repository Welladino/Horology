"""Register one private Cloudflare Pages project per workspace.

Only the owner/admin connection changes this mapping. The gateway can read it
but cannot enable publishing or alter a project or Access application ID.
"""
from alembic import op

revision = '20261022_009'
down_revision = '20261016_008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE access.workspace_pages (
            workspace text PRIMARY KEY REFERENCES access.workspaces (name) ON DELETE CASCADE,
            project text NOT NULL UNIQUE CHECK (project ~ '^[a-z][a-z0-9-]{0,62}$'),
            main_access_app_id text NOT NULL,
            preview_access_app_id text NOT NULL,
            enabled boolean NOT NULL DEFAULT false,
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (main_access_app_id <> preview_access_app_id)
        )
    """)
    op.execute('GRANT SELECT ON access.workspace_pages TO horology_gateway')


def downgrade():
    op.execute('REVOKE SELECT ON access.workspace_pages FROM horology_gateway')
    op.execute('DROP TABLE access.workspace_pages')
