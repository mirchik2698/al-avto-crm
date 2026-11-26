"""Add optional supplier to orders."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_03"
down_revision = "20261117_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("supplier", sa.String(length=120), nullable=True))


def downgrade():
    raise NotImplementedError("Downgrade would remove saved order suppliers")
