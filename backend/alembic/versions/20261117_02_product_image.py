"""add product image URL

Revision ID: 20261117_02
Revises: 20261117_01
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20261117_02"
down_revision = "20261117_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(500), nullable=True))

def downgrade() -> None:
    op.drop_column("products", "image_url")
