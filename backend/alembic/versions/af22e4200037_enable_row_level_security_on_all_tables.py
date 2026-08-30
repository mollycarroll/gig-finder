"""enable row level security on all tables

Revision ID: af22e4200037
Revises: 1935efcb542b
Create Date: 2026-08-30 11:41:32.172767

Our FastAPI backend connects with the `postgres` role, which bypasses RLS
regardless of this setting — enforcement of who can see/save what lives in
app/auth.py and the routers, not here. This migration exists solely because
Supabase auto-exposes every public-schema table over its PostgREST REST API
to anyone holding the (public, frontend-embedded) anon key; enabling RLS
with no policies denies that API entirely, since it isn't part of this
app's design. See CLAUDE.md / SPEC.md for why the app doesn't lean on RLS
for its own authorization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af22e4200037'
down_revision: Union[str, Sequence[str], None] = '1935efcb542b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("area", "venue", "venue_contact", "saved_venue")


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    """Downgrade schema."""
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
