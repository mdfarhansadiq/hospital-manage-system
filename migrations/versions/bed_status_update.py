"""Add status and additional fields to Bed table

Revision ID: bed_status_update
Revises: 
Create Date: 2025-02-07 08:09:41.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bed_status_update'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to Bed table
    op.add_column('bed', sa.Column('status', sa.String(20), server_default='available'))
    op.add_column('bed', sa.Column('equipment', sa.String(200), nullable=True))
    op.add_column('bed', sa.Column('last_cleaned', sa.DateTime, nullable=True))

def downgrade():
    # Remove the columns if needed
    op.drop_column('bed', 'status')
    op.drop_column('bed', 'equipment')
    op.drop_column('bed', 'last_cleaned')
