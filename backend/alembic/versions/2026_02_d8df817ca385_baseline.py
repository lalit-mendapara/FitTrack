"""baseline - stamp current DB state

Revision ID: d8df817ca385
Revises: 
Create Date: 2026-02-12 15:29:21.692573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8df817ca385'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline migration - all tables already exist in the database.
    # This revision stamps the current DB state as the starting point.
    pass


def downgrade() -> None:
    # Cannot downgrade from baseline
    pass
