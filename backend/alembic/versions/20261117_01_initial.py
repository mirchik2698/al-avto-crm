"""initial AlAuto schema

Revision ID: 20261117_01
Revises:
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261117_01"
down_revision = None
branch_labels = None
depends_on = None

user_role = postgresql.ENUM("employee", "admin", name="userrole", create_type=False)
product_type = postgresql.ENUM("tire", "wheel", name="producttype", create_type=False)
order_status = postgresql.ENUM("new", "in_progress", "ready", "completed", "cancelled", name="orderstatus", create_type=False)
mailing_status = postgresql.ENUM("draft", "approved", name="mailingstatus", create_type=False)

def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True); product_type.create(bind, checkfirst=True)
    order_status.create(bind, checkfirst=True); mailing_status.create(bind, checkfirst=True)
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("login", sa.String(64), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", user_role, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("login"))
    op.create_index("ix_users_login", "users", ["login"])
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("type", product_type, nullable=False), sa.Column("brand", sa.String(120), nullable=False), sa.Column("model", sa.String(160), nullable=False), sa.Column("price", sa.Numeric(12, 2), nullable=False), sa.Column("stock", sa.Integer(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_products_type", "products", ["type"]); op.create_index("ix_products_brand", "products", ["brand"]); op.create_index("ix_products_active", "products", ["active"])
    op.create_table("tire_specs", sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True), sa.Column("width", sa.Integer(), nullable=False), sa.Column("profile", sa.Integer(), nullable=False), sa.Column("diameter", sa.Integer(), nullable=False), sa.Column("season", sa.String(32), nullable=False), sa.Column("load_index", sa.String(16), nullable=False), sa.Column("commercial", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("studded", sa.Boolean(), nullable=False, server_default=sa.false()))
    for field in ("width", "profile", "diameter", "season"): op.create_index(f"ix_tire_specs_{field}", "tire_specs", [field])
    op.create_table("wheel_specs", sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True), sa.Column("diameter", sa.Integer(), nullable=False), sa.Column("bolt_pattern", sa.String(24), nullable=False), sa.Column("width", sa.Numeric(4, 1), nullable=False), sa.Column("center_bore", sa.Numeric(5, 1), nullable=False), sa.Column("et", sa.Numeric(5, 1), nullable=False), sa.Column("color", sa.String(64), nullable=False))
    op.create_index("ix_wheel_specs_diameter", "wheel_specs", ["diameter"]); op.create_index("ix_wheel_specs_bolt_pattern", "wheel_specs", ["bolt_pattern"])
    op.create_table("clients", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("phone", sa.String(32), nullable=False), sa.Column("note", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_clients_name", "clients", ["name"]); op.create_index("ix_clients_phone", "clients", ["phone"])
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False), sa.Column("comment", sa.Text(), nullable=False), sa.Column("total_amount", sa.Numeric(12, 2), nullable=False), sa.Column("deposit", sa.Numeric(12, 2), nullable=False), sa.Column("remainder", sa.Numeric(12, 2), nullable=False), sa.Column("status", order_status, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price", sa.Numeric(12, 2), nullable=False))
    op.create_table("mailings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("subject", sa.String(180), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("status", mailing_status, nullable=False), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))

def downgrade() -> None:
    op.drop_table("mailings"); op.drop_table("order_items"); op.drop_table("orders")
    op.drop_index("ix_clients_phone", table_name="clients"); op.drop_index("ix_clients_name", table_name="clients"); op.drop_table("clients")
    op.drop_index("ix_wheel_specs_bolt_pattern", table_name="wheel_specs"); op.drop_index("ix_wheel_specs_diameter", table_name="wheel_specs"); op.drop_table("wheel_specs")
    for field in ("season", "diameter", "profile", "width"): op.drop_index(f"ix_tire_specs_{field}", table_name="tire_specs")
    op.drop_table("tire_specs")
    for field in ("active", "brand", "type"): op.drop_index(f"ix_products_{field}", table_name="products")
    op.drop_table("products"); op.drop_index("ix_users_login", table_name="users"); op.drop_table("users")
    bind = op.get_bind(); mailing_status.drop(bind, checkfirst=True); order_status.drop(bind, checkfirst=True); product_type.drop(bind, checkfirst=True); user_role.drop(bind, checkfirst=True)

