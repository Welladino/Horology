"""create_document_graph

Revision ID: 20260805_001
Revises:
Create Date: 2026-08-05 19:20:18.215072

Creates the document graph: documents (what Horology's agents produce
while running), document_links (the graph structure between them), and
run_log (audit trail of what each supervisor/subagent run did).

This is separate from Hermes's own SQLite state (sessions/messages) and
from Article_aggregator_agent's own Supabase project — see
docs/planning/notes/2026-08-05_horology-founding-decisions_note.md and
docs/planning/notes/2026-08-05_hermes-hardening_note.md
for why.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260805_001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DOC_TYPES = ("recommendation", "content", "analysis", "report")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_agent", sa.Text(), nullable=False),
        sa.Column(
            "supersedes_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"doc_type IN {DOC_TYPES}",
            name="documents_doc_type_check",
        ),
    )
    op.create_index("ix_documents_doc_type", "documents", ["doc_type"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_supersedes_id", "documents", ["supersedes_id"])

    op.create_table(
        "document_links",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "from_doc_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_doc_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "from_doc_id", "to_doc_id", "relation", name="uq_document_links_edge"
        ),
    )
    op.create_index("ix_document_links_from_doc_id", "document_links", ["from_doc_id"])
    op.create_index("ix_document_links_to_doc_id", "document_links", ["to_doc_id"])

    op.create_table(
        "run_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("agent", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_run_log_agent", "run_log", ["agent"])
    op.create_index("ix_run_log_document_id", "run_log", ["document_id"])
    op.create_index("ix_run_log_started_at", "run_log", ["started_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_run_log_started_at", table_name="run_log")
    op.drop_index("ix_run_log_document_id", table_name="run_log")
    op.drop_index("ix_run_log_agent", table_name="run_log")
    op.drop_table("run_log")

    op.drop_index("ix_document_links_to_doc_id", table_name="document_links")
    op.drop_index("ix_document_links_from_doc_id", table_name="document_links")
    op.drop_table("document_links")

    op.drop_index("ix_documents_supersedes_id", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_doc_type", table_name="documents")
    op.drop_table("documents")
