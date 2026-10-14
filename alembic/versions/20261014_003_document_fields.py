"""Domain, business entity and Pipeline ID on documents, copied from the Document Index.

`business_entity` is the sheet's "Entity" column (a named Newsletter or
Ecommerce business), renamed so it isn't confused with the graph's entity
nodes. Domains are stored in one normal form (lowercase, hyphenated).
"""
from alembic import op

revision = '20261014_003'
down_revision = '20261014_002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE documents ADD COLUMN domain text, ADD COLUMN business_entity text, ADD COLUMN pipeline_id text')
    op.execute('CREATE INDEX documents_workspace_domain ON documents (workspace, domain)')
    op.execute('CREATE INDEX documents_workspace_pipeline ON documents (workspace, pipeline_id)')


def downgrade():
    op.execute('DROP INDEX documents_workspace_pipeline')
    op.execute('DROP INDEX documents_workspace_domain')
    op.execute('ALTER TABLE documents DROP COLUMN pipeline_id, DROP COLUMN business_entity, DROP COLUMN domain')
