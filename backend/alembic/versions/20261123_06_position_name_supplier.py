"""position supplier and name

Revision ID: 20261123_06
Revises: 20261123_05
Create Date: 2026-11-24

Позиция заказа перестаёт ссылаться на номенклатуру: у каждой позиции своё
наименование и свой поставщик. Ссылка на товар остаётся необязательной
(исторические заказы её сохраняют). Поставщик уровня заказа становится
необязательной сводкой по позициям.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_06"
down_revision = "20261123_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("name", sa.Text(), nullable=True))
    op.add_column("order_items", sa.Column("supplier", sa.String(120), nullable=True))
    op.execute("""
        UPDATE order_items SET name = COALESCE(
            NULLIF(btrim((SELECT p.brand || ' ' || p.model FROM products p WHERE p.id = order_items.product_id)), ' '),
            'Позиция')
    """)
    op.execute("""
        UPDATE order_items SET supplier = COALESCE(
            (SELECT o.supplier FROM orders o WHERE o.id = order_items.order_id), 'Не указан')
    """)
    op.alter_column("order_items", "name", existing_type=sa.Text(), nullable=False)
    op.alter_column("order_items", "supplier", existing_type=sa.String(120), nullable=False)
    op.alter_column("order_items", "product_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("orders", "supplier", existing_type=sa.String(120), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE orders SET supplier = 'Не указан' WHERE supplier IS NULL")
    op.alter_column("orders", "supplier", existing_type=sa.String(120), nullable=False)
    op.execute("UPDATE order_items SET product_id = (SELECT min(id) FROM products) WHERE product_id IS NULL")
    op.alter_column("order_items", "product_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("order_items", "supplier")
    op.drop_column("order_items", "name")
