"""Entities: named things found in documents, grouped into buckets, with relationships.

- entity_types: the workspace's buckets (kind 'entity') and relationship types
  (kind 'relation'), edited in the Entity types tab. Entities point to a bucket
  by id, so renaming a bucket is one row.
- entities: one row per real thing, with a 768-dimension embedding of
  "name: description" for the resolution shortlist. A merged entity keeps its
  row (status 'merged', merged_into) so references can be followed.
- entity_aliases: other names for an entity, matched after normalising.
- entity_mentions: which section names which entity, with the text used.
- entity_relations / relation_evidence: entity -> type -> entity, with the
  sections that support it.
- entity_decisions: every resolution decision, for review and later tuning.
- entity_runs: per document, the hash of the sections last processed, so only
  new or changed documents are read again; 'failed' runs are retried.
Mentions and evidence cascade when a document's sections are rebuilt.
"""
from alembic import op

revision = '20261014_005'
down_revision = '20261014_004'
branch_labels = None
depends_on = None

TABLES = ('entity_types', 'entities', 'entity_aliases', 'entity_mentions', 'entity_relations',
          'relation_evidence', 'entity_decisions', 'entity_runs')


def upgrade():
    op.execute("""
        CREATE TABLE entity_types (
            id bigserial PRIMARY KEY,
            workspace text NOT NULL,
            kind text NOT NULL CHECK (kind IN ('entity', 'relation')),
            name text NOT NULL,
            description text NOT NULL DEFAULT '',
            position integer NOT NULL DEFAULT 0,
            UNIQUE (workspace, kind, name)
        )
    """)
    op.execute("""
        CREATE TABLE entities (
            id bigserial PRIMARY KEY,
            workspace text NOT NULL,
            type_id bigint NOT NULL REFERENCES entity_types(id),
            name text NOT NULL,
            description text NOT NULL DEFAULT '',
            suggested_type text,
            embedding vector(768),
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'merged')),
            merged_into bigint REFERENCES entities(id),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX entities_workspace_type ON entities (workspace, type_id) WHERE status = \'active\'')
    op.execute('CREATE INDEX entities_embedding_hnsw ON entities USING hnsw (embedding vector_cosine_ops)')
    op.execute("""
        CREATE TABLE entity_aliases (
            entity_id bigint NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            alias text NOT NULL,
            normalized text NOT NULL,
            PRIMARY KEY (entity_id, normalized)
        )
    """)
    op.execute('CREATE INDEX entity_aliases_normalized ON entity_aliases (normalized)')
    op.execute("""
        CREATE TABLE entity_mentions (
            entity_id bigint NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            document_id bigint NOT NULL,
            chunk_index integer NOT NULL,
            surface text NOT NULL,
            PRIMARY KEY (entity_id, document_id, chunk_index, surface),
            FOREIGN KEY (document_id, chunk_index) REFERENCES document_chunks(document_id, chunk_index) ON DELETE CASCADE
        )
    """)
    op.execute('CREATE INDEX entity_mentions_document ON entity_mentions (document_id)')
    op.execute("""
        CREATE TABLE entity_relations (
            id bigserial PRIMARY KEY,
            from_entity bigint NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            type_id bigint NOT NULL REFERENCES entity_types(id),
            to_entity bigint NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            UNIQUE (from_entity, type_id, to_entity)
        )
    """)
    op.execute("""
        CREATE TABLE relation_evidence (
            relation_id bigint NOT NULL REFERENCES entity_relations(id) ON DELETE CASCADE,
            document_id bigint NOT NULL,
            chunk_index integer NOT NULL,
            PRIMARY KEY (relation_id, document_id, chunk_index),
            FOREIGN KEY (document_id, chunk_index) REFERENCES document_chunks(document_id, chunk_index) ON DELETE CASCADE
        )
    """)
    op.execute("""
        CREATE TABLE entity_decisions (
            id bigserial PRIMARY KEY,
            workspace text NOT NULL,
            document_id bigint REFERENCES documents(id) ON DELETE SET NULL,
            mention text NOT NULL,
            bucket text NOT NULL,
            description text NOT NULL DEFAULT '',
            decision text NOT NULL CHECK (decision IN ('exact', 'same', 'new')),
            entity_id bigint REFERENCES entities(id) ON DELETE SET NULL,
            candidates jsonb NOT NULL DEFAULT '[]',
            confidence real,
            reason text,
            model text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX entity_decisions_workspace ON entity_decisions (workspace, created_at)')
    op.execute("""
        CREATE TABLE entity_runs (
            document_id bigint PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
            sections_hash text NOT NULL,
            status text NOT NULL CHECK (status IN ('done', 'failed')),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON ' + ', '.join(TABLES) + ' TO horology_graph')
    for table in ('entity_types', 'entities', 'entity_relations', 'entity_decisions'):
        op.execute(f"DO $$ BEGIN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO horology_graph', pg_get_serial_sequence('{table}', 'id')); END $$")
    op.execute('GRANT SELECT ON ' + ', '.join(TABLES) + ' TO horology_cron_sweep_ro')


def downgrade():
    for table in reversed(TABLES):
        op.execute(f'DROP TABLE {table}')
