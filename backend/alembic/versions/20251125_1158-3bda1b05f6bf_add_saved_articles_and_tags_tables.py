"""Add saved articles and tags tables

Revision ID: 3bda1b05f6bf
Revises: d336a1a03551
Create Date: 2025-11-25 11:58:47.693031

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3bda1b05f6bf"
down_revision = "d336a1a03551"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_tag_name"),
    )
    op.create_index(op.f("ix_tags_id"), "tags", ["id"], unique=False)
    op.create_index(op.f("ix_tags_user_id"), "tags", ["user_id"], unique=False)
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    # Create saved_articles table
    op.create_table(
        "saved_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "article_id", name="uq_user_article"),
    )
    op.create_index(
        op.f("ix_saved_articles_id"), "saved_articles", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_saved_articles_user_id"), "saved_articles", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_saved_articles_article_id"),
        "saved_articles",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_saved_articles_saved_at"), "saved_articles", ["saved_at"], unique=False
    )

    # Create saved_article_tags junction table
    op.create_table(
        "saved_article_tags",
        sa.Column("saved_article_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["saved_article_id"], ["saved_articles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("saved_article_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("saved_article_tags")
    op.drop_index(op.f("ix_saved_articles_saved_at"), table_name="saved_articles")
    op.drop_index(op.f("ix_saved_articles_article_id"), table_name="saved_articles")
    op.drop_index(op.f("ix_saved_articles_user_id"), table_name="saved_articles")
    op.drop_index(op.f("ix_saved_articles_id"), table_name="saved_articles")
    op.drop_table("saved_articles")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_index(op.f("ix_tags_user_id"), table_name="tags")
    op.drop_index(op.f("ix_tags_id"), table_name="tags")
    op.drop_table("tags")
