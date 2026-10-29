"""Register ID allocator: permanent Decision and Document IDs handed out atomically, one per call.

Agents used to take "max + 1" from the live sheet and upsert by ID, so two
parallel runs could pick the same ID and the second silently overwrote the
first's row (HOR-6). Now the reserve_id tool allocates from here.
- register_ids: the last ID handed out per workspace and register. A
  reservation takes greatest(last_id, highest ID in the synced sheet copy) + 1
  in one statement, so rows added by hand are respected and two concurrent
  calls never get the same ID.
- register_reservations: who took each ID (Pipeline item and run), and the
  Drive URL the row was bound to on its first write. get_item_history shows
  them. Kept as an audit trail: the service login can't delete them.
"""
from alembic import op

revision = '20261029_010'
down_revision = '20261022_009'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE register_ids (
            workspace text NOT NULL,
            register text NOT NULL CHECK (register IN ('decision', 'document')),
            last_id bigint NOT NULL CHECK (last_id > 0),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace, register)
        )
    """)
    op.execute("""
        CREATE TABLE register_reservations (
            workspace text NOT NULL,
            register text NOT NULL CHECK (register IN ('decision', 'document')),
            reserved_id bigint NOT NULL,
            pipeline_id text,
            run_id bigint REFERENCES run_log(id) ON DELETE SET NULL,
            reserved_by text,
            drive_url text,
            reserved_at timestamptz NOT NULL DEFAULT now(),
            bound_at timestamptz,
            PRIMARY KEY (workspace, register, reserved_id),
            CHECK (pipeline_id IS NULL OR run_id IS NOT NULL)
        )
    """)
    op.execute('CREATE INDEX register_reservations_item ON register_reservations (workspace, pipeline_id)')
    op.execute('CREATE INDEX register_reservations_run ON register_reservations (run_id)')
    op.execute('GRANT SELECT, INSERT, UPDATE ON register_ids, register_reservations TO horology_graph')
    op.execute('GRANT SELECT ON register_ids, register_reservations TO horology_cron_sweep_ro')


def downgrade():
    op.execute('DROP TABLE register_reservations, register_ids')
