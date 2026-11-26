from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from app.models import MailingStatus, OrderStatus, ProductType, UserRole

Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2, ge=0)]

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    login: str
    role: UserRole
    branch_id: int | None = None

class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    login: str = Field(min_length=2, max_length=64)
    password: str | None = Field(default=None, min_length=4, max_length=128)
    role: UserRole = UserRole.employee
    branch_id: int | None = None

class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    login: str
    role: UserRole
    branch_id: int | None = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TireSpecIn(BaseModel):
    width: int = Field(ge=100, le=400)
    profile: int = Field(ge=20, le=100)
    diameter: int = Field(ge=10, le=30)
    season: Literal["Лето", "Зима", "Всесезон"]
    load_index: str = Field(min_length=1, max_length=16)
    commercial: bool = False
    studded: bool = False

class WheelSpecIn(BaseModel):
    diameter: int = Field(ge=10, le=30)
    bolt_pattern: str = Field(min_length=3, max_length=24)
    width: Decimal = Field(gt=0, le=20)
    center_bore: Decimal = Field(gt=0, le=200)
    et: Decimal = Field(ge=-100, le=150)
    color: str = Field(min_length=1, max_length=64)

class ProductIn(BaseModel):
    type: ProductType
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    price: Money
    stock: int = Field(ge=0)
    active: bool = True
    image_url: str | None = Field(default=None, max_length=500)
    supplier: str | None = Field(default=None, max_length=120)
    tire: TireSpecIn | None = None
    wheel: WheelSpecIn | None = None

    @model_validator(mode="after")
    def matching_spec(self):
        if self.type == ProductType.tire and not self.tire:
            raise ValueError("Для шины обязательны характеристики шины")
        if self.type == ProductType.wheel and not self.wheel:
            raise ValueError("Для диска обязательны характеристики диска")
        return self

class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

def validate_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    starts_plus = bool(value) and value.strip().startswith("+")
    if len(digits) != 11 or not ((starts_plus and digits.startswith("7")) or (not starts_plus and digits.startswith("8"))):
        raise ValueError("Телефон должен содержать 11 цифр и начинаться с «+7» или «8»")
    return value.strip()

class ClientInBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    note: str | None = None

class ClientIn(ClientInBase):
    @field_validator("phone")
    @classmethod
    def phone_format(cls, value: str) -> str:
        return validate_phone(value)

class ClientOut(ClientInBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    code: str
    created_at: datetime

class SupplierIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    markup_percent: Decimal = Field(default=Decimal("25"), ge=0, le=100)

class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    markup_percent: Decimal
    active: bool
    has_key: bool
    last_sync_at: datetime | None

class StockRowIn(BaseModel):
    brand: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    price: Money
    stock: int = Field(default=0, ge=0, le=9999)
    season: Literal["Лето", "Зима", "Всесезон"] = "Всесезон"
    width: int = Field(ge=100, le=400)
    profile: int = Field(ge=20, le=100)
    diameter: int = Field(ge=10, le=30)
    row: int = 0

class StockConfirmIn(BaseModel):
    filename: str | None = Field(default=None, max_length=200)
    rows: list[StockRowIn] = Field(min_length=1)

class IngestItemIn(BaseModel):
    model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    brand: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    price: Money
    stock: int = Field(default=0, ge=0, le=9999)
    season: Literal["Лето", "Зима", "Всесезон"] | None = None

class IngestIn(BaseModel):
    items: list[IngestItemIn] = Field(min_length=1)
    replace: bool = True

class OrderItemIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    supplier: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    quantity: int = Field(gt=0, le=999)
    unit_price: Money = Decimal("0")
    product_id: int | None = None

class OrderDetails(BaseModel):
    supplier: str = Field(default="", max_length=120)
    comment: str = Field(default="", max_length=2000)
    total_amount: Money
    deposit: Money = Decimal("5000")
    status: OrderStatus = OrderStatus.in_transit
    items: list[OrderItemIn]

class NewOrderClient(ClientIn):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    phone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=32)]

class OrderCreate(OrderDetails):
    items: list[OrderItemIn] = Field(default_factory=list)
    client_id: int | None = Field(default=None, gt=0)
    new_client: NewOrderClient | None = None

    @model_validator(mode="after")
    def require_one_client(self):
        if (self.client_id is None) == (self.new_client is None):
            raise ValueError("Выберите существующего клиента или заполните данные нового клиента")
        return self

class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int | None
    name: str
    supplier: str
    quantity: int
    unit_price: Decimal

class OrderOut(BaseModel):
    supplier: str | None
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    client_id: int
    comment: str
    total_amount: Decimal
    deposit: Decimal
    remainder: Decimal
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemOut]

class OrderStatusIn(BaseModel):
    status: OrderStatus

class MailingIn(BaseModel):
    subject: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1)
    status: MailingStatus = MailingStatus.draft

class MailingOut(MailingIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    created_at: datetime

class ImportRow(BaseModel):
    row: int
    data: ProductIn
    source_price: Money | None = None
    markup_percent: Decimal = Decimal("0")

class ImportPreview(BaseModel):
    valid_rows: list[ImportRow]
    errors: list[dict]

class ImportConfirm(BaseModel):
    rows: list[ImportRow] = Field(min_length=1)
