import enum
import re
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, event, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class UserRole(str, enum.Enum):
    employee = "employee"
    admin = "admin"

class ProductType(str, enum.Enum):
    tire = "tire"
    wheel = "wheel"

class OrderStatus(str, enum.Enum):
    in_transit = "in_transit"
    completed = "completed"

class MailingStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"

class Branch(Base):
    __tablename__ = "branches"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.employee)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    branch: Mapped["Branch | None"] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ProductType] = mapped_column(Enum(ProductType), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    model: Mapped[str] = mapped_column(String(160))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tire: Mapped["TireSpec | None"] = relationship(back_populates="product", cascade="all, delete-orphan", uselist=False)
    wheel: Mapped["WheelSpec | None"] = relationship(back_populates="product", cascade="all, delete-orphan", uselist=False)

class TireSpec(Base):
    __tablename__ = "tire_specs"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    width: Mapped[int] = mapped_column(Integer, index=True)
    profile: Mapped[int] = mapped_column(Integer, index=True)
    diameter: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[str] = mapped_column(String(32), index=True)
    load_index: Mapped[str] = mapped_column(String(16))
    commercial: Mapped[bool] = mapped_column(Boolean, default=False)
    studded: Mapped[bool] = mapped_column(Boolean, default=False)
    product: Mapped[Product] = relationship(back_populates="tire")

class WheelSpec(Base):
    __tablename__ = "wheel_specs"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    diameter: Mapped[int] = mapped_column(Integer, index=True)
    bolt_pattern: Mapped[str] = mapped_column(String(24), index=True)
    width: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    center_bore: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    et: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    color: Mapped[str] = mapped_column(String(64))
    product: Mapped[Product] = relationship(back_populates="wheel")

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    orders: Mapped[list["Order"]] = relationship(back_populates="client")

def _client_code(connection, name: str, phone: str, exclude_id: int | None = None) -> str:
    """ID клиента = имя + последние четыре цифры телефона."""
    digits = re.sub(r"\D", "", phone or "")
    base = f"{' '.join((name or '').split())[:36]}{digits[-4:]}"
    code, suffix = base, 1
    while True:
        query = select(Client.id).where(Client.code == code)
        if exclude_id is not None:
            query = query.where(Client.id != exclude_id)
        if not connection.execute(query).scalar():
            return code
        suffix += 1
        code = f"{base}-{suffix}"

@event.listens_for(Client, "before_insert")
def _set_client_code_on_insert(mapper, connection, target: Client) -> None:
    target.code = _client_code(connection, target.name, target.phone)

@event.listens_for(Client, "before_update")
def _set_client_code_on_update(mapper, connection, target: Client) -> None:
    target.code = _client_code(connection, target.name, target.phone, target.id)

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    markup_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("25"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lists: Mapped[list["StockList"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")

class StockList(Base):
    __tablename__ = "stock_lists"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(10))
    filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    supplier: Mapped[Supplier] = relationship(back_populates="lists")

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    supplier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str] = mapped_column(Text)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deposit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("5000"))
    remainder: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.in_transit.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    client: Mapped[Client] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    name: Mapped[str] = mapped_column(Text)
    supplier: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()

class Mailing(Base):
    __tablename__ = "mailings"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(180))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[MailingStatus] = mapped_column(Enum(MailingStatus), default=MailingStatus.draft)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    author: Mapped[User] = relationship()
