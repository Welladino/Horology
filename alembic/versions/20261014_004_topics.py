"""Topics: groups of similar sections found by clustering the section-similarity graph.

A section belongs to at most one topic. Assignments cascade when a document's
sections are rebuilt, and are recreated by placement or the next re-cluster.
A topic's name is null until it has been named; pinned topics keep their name.
"""
from alembic import op

revision = '20261014_004'
down_revision = '20261014_003'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE topics (
            id bigserial PRIMARY KEY,
            workspace text NOT NULL,
            name text,
            summary text,
            pinned boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX topics_workspace ON topics (workspace)')
    op.execute("""
        CREATE TABLE section_topics (
            document_id bigint NOT NULL,
            chunk_index integer NOT NULL,
            topic_id bigint NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
            confidence real NOT NULL CHECK (confidence BETWEEN 0 AND 1),
            assigned_by text NOT NULL CHECK (assigned_by IN ('cluster', 'placement')),
            PRIMARY KEY (document_id, chunk_index),
            FOREIGN KEY (document_id, chunk_index) REFERENCES document_chunks(document_id, chunk_index) ON DELETE CASCADE
        )
    """)
    op.execute('CREATE INDEX section_topics_topic ON section_topics (topic_id)')
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON topics, section_topics TO horology_graph')
    op.execute("DO $$ BEGIN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO horology_graph', pg_get_serial_sequence('topics', 'id')); END $$")
    op.execute('GRANT SELECT ON topics, section_topics TO horology_cron_sweep_ro')


def downgrade():
    op.execute('DROP TABLE section_topics')
    op.execute('DROP TABLE topics')
