"""add_user_vote_and_score_adjustment

Revision ID: a78d6171b2f2
Revises: 38d5c1251330
Create Date: 2025-11-20 17:39:29.332072

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a78d6171b2f2"
down_revision = "38d5c1251330"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_vote column (0 = neutral, -1 = downvote)
    op.add_column(
        "articles",
        sa.Column("user_vote", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add vote_updated_at column
    op.add_column(
        "articles", sa.Column("vote_updated_at", sa.DateTime(), nullable=True)
    )

    # Add adjusted_relevance_score column (stores final score after downvote adjustment)
    op.add_column(
        "articles", sa.Column("adjusted_relevance_score", sa.Float(), nullable=True)
    )

    # Add score_adjustment_reason column (stores brief explanation for UI)
    op.add_column(
        "articles", sa.Column("score_adjustment_reason", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("articles", "score_adjustment_reason")
    op.drop_column("articles", "adjusted_relevance_score")
    op.drop_column("articles", "vote_updated_at")
    op.drop_column("articles", "user_vote")
