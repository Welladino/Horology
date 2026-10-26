"""Users, workspaces and MCP server access, in their own schema "access".

Replaces the Cloud Run JSON settings (DOCUMENT_GRAPH_WORKSPACES,
GRAPH_SYNC_WORKBOOKS). Its own schema because these are the only tables two
services share, and they decide who gets in: each service login is granted
USAGE on "access" and SELECT on its tables, nothing more.
- access.mcp_servers: one row per MCP server (seeded: gateway,
  document-graph); an inactive server is closed to everyone.
- access.workspaces: one row per workspace, with its spreadsheets. Names
  match the workspace column already stored in the scoped tables; those
  tables get no foreign key.
- access.users: a permanent id; email is a unique lowercase lookup.
- access.workspace_members: several workspaces per person, with a role.
- access.user_mcp_access: which MCP servers each person may use.
The services only read these tables; scripts/ops/mcp/access.py changes them
with the owner connection. No users are seeded: emails stay out of the repo.
"""
from alembic import op

revision = '20261016_008'
down_revision = '20261016_007'
branch_labels = None
depends_on = None

TABLES = ('access.mcp_servers', 'access.workspaces', 'access.users', 'access.workspace_members',
          'access.user_mcp_access')
LOGINS = ('horology_graph', 'horology_gateway')
SLUG = r"'^[a-z][a-z0-9-]{0,62}$'"


def upgrade():
    op.execute("CREATE SCHEMA access")
    op.execute(f"""
        CREATE TABLE access.mcp_servers (
            id text PRIMARY KEY CHECK (id ~ {SLUG}),
            display_name text NOT NULL,
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        INSERT INTO access.mcp_servers (id, display_name) VALUES
            ('gateway', 'MCP gateway'), ('document-graph', 'Document graph')
    """)
    op.execute(f"""
        CREATE TABLE access.workspaces (
            name text PRIMARY KEY CHECK (name ~ {SLUG}),
            display_name text NOT NULL,
            index_sheet_id text,
            pipeline_sheet_id text,
            decisions_sheet_id text,
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE access.users (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email text NOT NULL UNIQUE CHECK (email = lower(email) AND email ~ '^[^@\\s]+@[^@\\s]+$'),
            active boolean NOT NULL DEFAULT true,
            note text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE access.workspace_members (
            user_id bigint NOT NULL REFERENCES access.users (id) ON DELETE CASCADE,
            workspace text NOT NULL REFERENCES access.workspaces (name) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),
            added_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, workspace)
        )
    """)
    # A server with grants can't be deleted by accident: disable it instead.
    op.execute("""
        CREATE TABLE access.user_mcp_access (
            user_id bigint NOT NULL REFERENCES access.users (id) ON DELETE CASCADE,
            server_id text NOT NULL REFERENCES access.mcp_servers (id) ON DELETE RESTRICT,
            granted_at timestamptz NOT NULL DEFAULT now(),
            note text,
            PRIMARY KEY (user_id, server_id)
        )
    """)
    op.execute("CREATE INDEX user_mcp_access_server ON access.user_mcp_access (server_id)")
    op.execute("CREATE INDEX workspace_members_workspace ON access.workspace_members (workspace)")
    for login in LOGINS:
        op.execute(f"GRANT USAGE ON SCHEMA access TO {login}")
        op.execute(f"GRANT SELECT ON {', '.join(TABLES)} TO {login}")


def downgrade():
    for login in LOGINS:
        op.execute(f"REVOKE ALL ON {', '.join(TABLES)} FROM {login}")
        op.execute(f"REVOKE USAGE ON SCHEMA access FROM {login}")
    op.execute("DROP TABLE access.user_mcp_access, access.workspace_members, access.users, "
               "access.workspaces, access.mcp_servers")
    op.execute("DROP SCHEMA access")
