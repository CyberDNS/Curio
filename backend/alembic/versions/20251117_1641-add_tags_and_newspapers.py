"""add tags and newspapers

Revision ID: add_tags_and_newspapers
Revises: initial_schema
Create Date: 2025-11-17 16:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tags_and_newspapers'
down_revision: Union[str, None] = 'initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to articles table
    op.add_column('articles', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('articles', sa.Column('is_new', sa.Boolean(), nullable=True, server_default='true'))

    # Create tags table
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_user_id'), 'tags', ['user_id'], unique=False)
    op.create_index('idx_user_tag_name', 'tags', ['user_id', 'name'], unique=True)

    # Create newspapers table
    op.create_table('newspapers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('structure', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_newspapers_id'), 'newspapers', ['id'], unique=False)
    op.create_index(op.f('ix_newspapers_user_id'), 'newspapers', ['user_id'], unique=False)
    op.create_index(op.f('ix_newspapers_date'), 'newspapers', ['date'], unique=False)
    op.create_index(op.f('ix_newspapers_created_at'), 'newspapers', ['created_at'], unique=False)
    # Ensure unique newspaper per user per day
    op.create_index('idx_user_newspaper_date', 'newspapers', ['user_id', 'date'], unique=True)


def downgrade() -> None:
    # Drop newspapers table
    op.drop_index('idx_user_newspaper_date', table_name='newspapers')
    op.drop_index(op.f('ix_newspapers_created_at'), table_name='newspapers')
    op.drop_index(op.f('ix_newspapers_date'), table_name='newspapers')
    op.drop_index(op.f('ix_newspapers_user_id'), table_name='newspapers')
    op.drop_index(op.f('ix_newspapers_id'), table_name='newspapers')
    op.drop_table('newspapers')

    # Drop tags table
    op.drop_index('idx_user_tag_name', table_name='tags')
    op.drop_index(op.f('ix_tags_user_id'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')

    # Remove columns from articles table
    op.drop_column('articles', 'is_new')
    op.drop_column('articles', 'tags')
