"""add_source_title_to_feeds

Revision ID: 38d5c1251330
Revises: 3fa2ef5c5685
Create Date: 2025-11-19 17:44:05.919378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38d5c1251330'
down_revision = '3fa2ef5c5685'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_title column to feeds table
    op.add_column('feeds', sa.Column('source_title', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove source_title column from feeds table
    op.drop_column('feeds', 'source_title')
