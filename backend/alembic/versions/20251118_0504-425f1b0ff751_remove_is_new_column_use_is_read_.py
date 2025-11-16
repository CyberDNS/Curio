"""remove_is_new_column_use_is_read_inverted

Revision ID: 425f1b0ff751
Revises: add_tags_and_newspapers
Create Date: 2025-11-18 05:04:44.815317

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '425f1b0ff751'
down_revision = 'add_tags_and_newspapers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the is_new column - we'll use !is_read instead
    op.drop_column('articles', 'is_new')


def downgrade() -> None:
    # Restore is_new column if needed
    op.add_column('articles', sa.Column('is_new', sa.Boolean(), server_default='true', nullable=False))
