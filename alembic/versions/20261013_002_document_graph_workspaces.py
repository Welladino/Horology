"""Workspaces, source and sheet identity for the document graph.

Every document belongs to one workspace. `source` says whether an agent wrote
it through the MCP (`agent`) or the Document Index sync imported it (`sheet`).
Sheet documents carry their Index Document ID, Drive file and the Drive
revision last imported, so re-syncing updates rather than duplicates.
Existing rows become workspace `welladino`, source `agent`.
"""
from alembic import op

revision = '20261013_002'
down_revision = '20261013_001'
branch_labels = None
depends_on = None

OLD_TYPES = ('recommendation', 'content', 'analysis', 'report')
# Document Type values from the Document Index Read Me tab, 2026-10-13.
DOC_TYPES = ('research', 'direction', 'plan', 'decision', 'report', 'brand_guide', 'guide',
             'template', 'pipeline', 'content', 'analysis', 'recommendation')


def upgrade():
    op.execute('ALTER TABLE documents DROP CONSTRAINT documents_doc_type_check')
    op.execute(f'ALTER TABLE documents ADD CONSTRAINT documents_doc_type_check CHECK (doc_type IN {DOC_TYPES})')
    op.execute("ALTER TABLE documents ADD COLUMN workspace text NOT NULL DEFAULT 'welladino'")
    op.execute("ALTER TABLE documents ADD COLUMN source text NOT NULL DEFAULT 'agent'")
    # Defaults only backfill existing rows; new rows must say both explicitly.
    op.execute('ALTER TABLE documents ALTER COLUMN workspace DROP DEFAULT')
    op.execute('ALTER TABLE documents ALTER COLUMN source DROP DEFAULT')
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_source_check CHECK (source IN ('agent', 'sheet'))")
    for column, kind in (('index_document_id', 'text'), ('drive_file_id', 'text'), ('drive_url', 'text'),
                         ('source_revision', 'text'), ('synced_at', 'timestamptz')):
        op.execute(f'ALTER TABLE documents ADD COLUMN {column} {kind}')
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_sheet_identity_check "
               "CHECK (source <> 'sheet' OR (index_document_id IS NOT NULL AND drive_file_id IS NOT NULL))")
    op.execute("CREATE UNIQUE INDEX uq_documents_sheet_identity ON documents (workspace, index_document_id) WHERE source = 'sheet'")
    op.execute('CREATE INDEX ix_documents_workspace_created_at ON documents (workspace, created_at)')


def downgrade():
    # Sheet-imported rows have no place in the old schema.
    op.execute("DELETE FROM documents WHERE source = 'sheet'")
    op.execute('DROP INDEX ix_documents_workspace_created_at')
    op.execute('DROP INDEX uq_documents_sheet_identity')
    op.execute('ALTER TABLE documents DROP CONSTRAINT documents_sheet_identity_check')
    for column in ('synced_at', 'source_revision', 'drive_url', 'drive_file_id', 'index_document_id'):
        op.execute(f'ALTER TABLE documents DROP COLUMN {column}')
    op.execute('ALTER TABLE documents DROP CONSTRAINT documents_source_check')
    op.execute('ALTER TABLE documents DROP COLUMN source')
    op.execute('ALTER TABLE documents DROP COLUMN workspace')
    op.execute('ALTER TABLE documents DROP CONSTRAINT documents_doc_type_check')
    op.execute(f'ALTER TABLE documents ADD CONSTRAINT documents_doc_type_check CHECK (doc_type IN {OLD_TYPES})')
