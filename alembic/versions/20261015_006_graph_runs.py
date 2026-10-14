"""Graph runs: one sync-job run at a time per workspace, and a cooldown on agent requests.

One row per workspace and mode (sync, entities, topics):
- requested_at: the last time an agent asked for this run (sync_graph,
  rebuild_topics); another request within the cooldown is refused.
- running_since / run_token / confirmed: the workspace's claim. It is taken
  when a request is accepted (confirmed false, with a token passed to the
  job), so a second request can't slip in before the job starts; the job
  confirms it with the token. A workspace runs one execution at a time,
  whatever the mode. An unconfirmed claim expires after 10 minutes (the job
  never started); a confirmed one after the job's time limit (it crashed).
- chain: which run this is in a chain of follow-up runs (1 = first).
"""
from alembic import op

revision = '20261015_006'
down_revision = '20261014_005'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE graph_runs (
            workspace text NOT NULL,
            mode text NOT NULL CHECK (mode IN ('sync', 'entities', 'topics')),
            requested_at timestamptz,
            running_since timestamptz,
            run_token text,
            confirmed boolean NOT NULL DEFAULT false,
            chain integer,
            PRIMARY KEY (workspace, mode)
        )
    """)
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON graph_runs TO horology_graph')
    op.execute('GRANT SELECT ON graph_runs TO horology_cron_sweep_ro')


def downgrade():
    op.execute('DROP TABLE graph_runs')
