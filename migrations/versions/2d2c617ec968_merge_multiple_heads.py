"""merge multiple heads

Revision ID: 2d2c617ec968
Revises: 0c71b4bae2bb, appointment_calendar_fields
Create Date: 2025-02-07 10:06:02.614730

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d2c617ec968'
down_revision = ('0c71b4bae2bb', 'appointment_calendar_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
