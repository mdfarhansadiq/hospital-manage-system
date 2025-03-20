"""Add calendar fields to Appointment table

Revision ID: appointment_calendar_fields
Revises: bed_status_update
Create Date: 2025-02-07 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'appointment_calendar_fields'
down_revision = 'bed_status_update'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to Appointment table
    op.add_column('appointment', sa.Column('duration', sa.Integer(), nullable=True, server_default='30'))
    op.add_column('appointment', sa.Column('calendar_event_id', sa.String(100), nullable=True))
    op.add_column('appointment', sa.Column('title', sa.String(200), nullable=True))
    op.add_column('appointment', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('appointment', sa.Column('updated_at', sa.DateTime(), nullable=True))

def downgrade():
    # Remove the columns if needed
    op.drop_column('appointment', 'duration')
    op.drop_column('appointment', 'calendar_event_id')
    op.drop_column('appointment', 'title')
    op.drop_column('appointment', 'description')
    op.drop_column('appointment', 'updated_at')
