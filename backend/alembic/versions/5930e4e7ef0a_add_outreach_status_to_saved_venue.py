"""add outreach status to saved_venue

Revision ID: 5930e4e7ef0a
Revises: af22e4200037
Create Date: 2026-09-09 07:42:07.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5930e4e7ef0a'
down_revision: Union[str, Sequence[str], None] = 'af22e4200037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    outreach_status = sa.Enum(
        'not_contacted', 'contacted', 'replied', 'booked', 'declined',
        name='outreach_status',
    )
    outreach_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'saved_venue',
        sa.Column(
            'status',
            outreach_status,
            server_default='not_contacted',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('saved_venue', 'status')
    sa.Enum(name='outreach_status').drop(op.get_bind(), checkfirst=True)
