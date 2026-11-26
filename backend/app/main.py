from datetime import datetime, timezone
from decimal import Decimal
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.config import settings
from app.database import get_db
from app.importing import preview_excel
from app.models import Branch, Client, Mailing, Order, OrderItem, OrderStatus, Product, ProductType, StockList, Supplier, TireSpec, User, UserRole, WheelSpec
from app.schemas import (ClientIn, ClientOut, EmployeeIn, EmployeeOut, ImportConfirm, ImportPreview, IngestIn, MailingIn, MailingOut, OrderCreate, OrderOut,
                         OrderStatusIn, ProductIn, ProductOut, StockConfirmIn, SupplierIn, TokenOut, UserOut)
from app.security import create_access_token, current_user, hash_password, require_roles, verify_password
from app.supplier_stock import (apply_stock, generate_api_key, hash_api_key, normalize_ingest_item,
                                preview_supplier_stock, slugify_code)

app = FastAPI(title="АлАвто API", version="0.2.0", description="API шинного центра. Отправка рассылок пока не реализована.")
app.add_middleware(CORSMiddleware, allow_origins=[item.strip() for item in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

CATALOG_SOURCES = {1: ("discovery",), 2: ("asia tyres", "asia tires", "asia")}

def filter_catalog_source(query, source):
    if source is None:
        return query
    return query.where(func.lower(func.trim(Product.supplier)).in_(CATALOG_SOURCES[source]))

def product_query():
    return select(Product).options(selectinload(Product.tire), selectinload(Product.wheel))

def product_or_404(db: Session, product_id: int) -> Product:
    product = db.scalar(product_query().where(Product.id == product_id))
    if not product:
        raise HTTPException(404, "Товар не найден")
    return product

def assign_product(product: Product, payload: ProductIn) -> Product:
    product.type, product.brand, product.model = payload.type, payload.brand, payload.model
    product.price, product.stock, product.active = payload.price, payload.stock, payload.active
    product.image_url, product.supplier = payload.image_url, payload.supplier
    if payload.type == ProductType.tire:
        product.wheel = None
        product.tire = TireSpec(**payload.tire.model_dump())
    else:
        product.tire = None
        product.wheel = WheelSpec(**payload.wheel.model_dump())
    return product

def create_product(db: Session, payload: ProductIn) -> Product:
    product = assign_product(Product(), payload)
    db.add(product)
    return product

def order_or_404(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if not order:
        raise HTTPException(404, "Заказ не найден")
    return order

def branch_or_404(db: Session, branch_id: int | None) -> Branch:
    branch = db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(404, "Филиал не найден")
    return branch

def employee_branch_id(user: User) -> int | None:
    """Филиал сотрудника; у администратора None — доступ ко всем филиалам."""
    return user.branch_id if user.role == UserRole.employee else None

def require_order_edit(user: User, order: Order) -> None:
    branch = employee_branch_id(user)
    if branch is not None and order.branch_id != branch:
        raise HTTPException(403, "Этот заказ создан в другом филиале — редактировать может только его филиал или Администратор")

def require_client_edit(user: User, client: Client) -> None:
    branch = employee_branch_id(user)
    if branch is not None and client.branch_id != branch:
        raise HTTPException(403, "Клиент из другой базы — доступ только у Администратора")

def assign_order(db: Session, order: Order, payload: OrderCreate, creator: User | None = None) -> Order:
    if payload.new_client is not None:
        branch = employee_branch_id(creator) if creator else None
        client = Client(**payload.new_client.model_dump(), branch_id=branch or 1)
        db.add(client)
        db.flush()
        client_id: int | None = client.id
    else:
        client_id = payload.client_id
    if not client_id or not db.get(Client, client_id):
        raise HTTPException(422, "Клиент не найден")
    for item in payload.items:
        if item.product_id is not None:
            product_or_404(db, item.product_id)
    client = db.get(Client, client_id)
    order.branch_id = employee_branch_id(creator) if creator else client.branch_id
    order.client_id = client_id
    # Поставщик заказа — сводка по позициям: заказы делаются не из нашей номенклатуры.
    order.supplier = payload.supplier or (payload.items[0].supplier if payload.items else None)
    order.comment, order.total_amount, order.deposit = payload.comment, payload.total_amount, payload.deposit
    order.remainder = max(payload.total_amount - payload.deposit, Decimal("0"))
    order.status = payload.status.value
    order.items = [OrderItem(name=item.name, supplier=item.supplier, product_id=item.product_id,
                             quantity=item.quantity, unit_price=item.unit_price) for item in payload.items]
    return order

def supplier_or_404(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Поставщик не найден")
    return supplier

def supplier_by_code(db: Session, code: str) -> Supplier | None:
    return db.scalar(select(Supplier).where(Supplier.code == code))

def unique_supplier_code(db: Session, name: str) -> str:
    base = slugify_code(name)
    code, suffix = base, 1
    while db.scalar(select(Supplier.id).where(Supplier.code == code)):
        suffix += 1
        code = f"{base}-{suffix}"
    return code

def supplier_variant(supplier: Supplier) -> str | None:
    low = supplier.name.strip().lower().replace("-", " ")
    for number, names in CATALOG_SOURCES.items():
        if low in names:
            return f"Вариант {number}"
    return None

def supplier_payload(db: Session, supplier: Supplier) -> dict:
    lists = db.scalars(select(StockList).where(StockList.supplier_id == supplier.id).order_by(StockList.id.desc())).all()
    last = lists[0] if lists else None
    return {"id": supplier.id, "name": supplier.name, "code": supplier.code,
            "markup_percent": str(supplier.markup_percent), "active": supplier.active,
            "has_key": bool(supplier.api_key_hash), "last_sync_at": supplier.last_sync_at,
            "lists": len(lists), "last_rows_ok": last.rows_ok if last else None,
            "variant": supplier_variant(supplier)}

@app.get("/api/users", response_model=list[EmployeeOut], tags=["employees"])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return db.scalars(select(User).order_by(User.id)).all()

@app.post("/api/users", response_model=EmployeeOut, status_code=201, tags=["employees"])
def add_user(payload: EmployeeIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    if db.scalar(select(User.id).where(func.lower(User.login) == payload.login.lower())):
        raise HTTPException(409, "Такой логин уже занят")
    if not payload.password:
        raise HTTPException(422, "Пароль обязателен при создании сотрудника")
    if payload.branch_id is not None:
        branch_or_404(db, payload.branch_id)
    user = User(name=payload.name, login=payload.login, password_hash=hash_password(payload.password),
                role=payload.role, branch_id=payload.branch_id)
    db.add(user); db.commit(); db.refresh(user); return user

@app.put("/api/users/{user_id}", response_model=EmployeeOut, tags=["employees"])
def update_user(user_id: int, payload: EmployeeIn, db: Session = Depends(get_db), admin: User = Depends(require_roles(UserRole.admin))):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "Сотрудник не найден")
    if db.scalar(select(User.id).where(func.lower(User.login) == payload.login.lower(), User.id != user_id)):
        raise HTTPException(409, "Такой логин уже занят")
    if payload.branch_id is not None:
        branch_or_404(db, payload.branch_id)
    user.name, user.login = payload.name, payload.login
    user.role, user.branch_id = payload.role, payload.branch_id
    if payload.password:
        user.password_hash = hash_password(payload.password)
    db.commit(); db.refresh(user); return user

@app.delete("/api/users/{user_id}", status_code=204, tags=["employees"])
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_roles(UserRole.admin))):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "Сотрудник не найден")
    if user.id == admin.id:
        raise HTTPException(409, "Нельзя удалить свою учётную запись")
    if db.scalar(select(Mailing.id).where(Mailing.author_id == user_id)):
        raise HTTPException(409, "У сотрудника есть рассылки — удаление недоступно")
    db.delete(user); db.commit()

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.post("/api/auth/login", response_model=TokenOut, tags=["auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль", headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=create_access_token(user), user=user)

@app.get("/api/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)): return user

@app.get("/api/branches", tags=["branches"])
def list_branches(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{"id": branch.id, "name": branch.name, "code": branch.code}
            for branch in db.scalars(select(Branch).order_by(Branch.id)).all()]

@app.get("/api/catalog/tires", response_model=list[ProductOut], tags=["catalog"])
def tires(width: int | None = None, profile: int | None = None, diameter: int | None = None, season: str | None = None,
          price_from: Decimal | None = None, price_to: Decimal | None = None, min_stock: int | None = None,
          commercial: bool | None = None, studded: bool | None = None, source: int | None = Query(None, ge=1, le=2), db: Session = Depends(get_db)):
    query = product_query().join(TireSpec).where(Product.type == ProductType.tire, Product.active.is_(True))
    query = filter_catalog_source(query, source)
    for column, value in [(TireSpec.width, width), (TireSpec.profile, profile), (TireSpec.diameter, diameter), (TireSpec.season, season), (TireSpec.commercial, commercial), (TireSpec.studded, studded)]:
        if value is not None: query = query.where(column == value)
    if price_from is not None: query = query.where(Product.price >= price_from)
    if price_to is not None: query = query.where(Product.price <= price_to)
    if min_stock is not None: query = query.where(Product.stock >= min_stock)
    return db.scalars(query.order_by(Product.id.desc())).all()

@app.get("/api/catalog/wheels", response_model=list[ProductOut], tags=["catalog"])
def wheels(diameter: int | None = None, bolt_pattern: str | None = None, width: Decimal | None = None,
           center_bore: Decimal | None = None, et_from: Decimal | None = None, et_to: Decimal | None = None,
           source: int | None = Query(None, ge=1, le=2), db: Session = Depends(get_db)):
    query = product_query().join(WheelSpec).where(Product.type == ProductType.wheel, Product.active.is_(True))
    query = filter_catalog_source(query, source)
    for column, value in [(WheelSpec.diameter, diameter), (WheelSpec.bolt_pattern, bolt_pattern), (WheelSpec.width, width), (WheelSpec.center_bore, center_bore)]:
        if value is not None: query = query.where(column == value)
    if et_from is not None: query = query.where(WheelSpec.et >= et_from)
    if et_to is not None: query = query.where(WheelSpec.et <= et_to)
    return db.scalars(query.order_by(Product.id.desc())).all()

@app.get("/api/products", response_model=list[ProductOut], tags=["products"])
def list_products(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    return db.scalars(product_query().order_by(Product.id.desc())).all()

@app.get("/api/order-products", response_model=list[ProductOut], tags=["orders"])
def order_products(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin)), client_id: int | None = None):
    ids = select(OrderItem.product_id)
    if client_id is not None:
        ids = ids.join(Order, Order.id == OrderItem.order_id).where(Order.client_id == client_id)
    return db.scalars(product_query().where(Product.id.in_(ids))).all()

@app.post("/api/products", response_model=ProductOut, status_code=201, tags=["products"])
def add_product(payload: ProductIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    product = create_product(db, payload); db.commit(); return product_or_404(db, product.id)

@app.put("/api/products/{product_id}", response_model=ProductOut, tags=["products"])
def update_product(product_id: int, payload: ProductIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    product = assign_product(product_or_404(db, product_id), payload); db.commit(); return product_or_404(db, product.id)

@app.delete("/api/products/{product_id}", status_code=204, tags=["products"])
def archive_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    product_or_404(db, product_id).active = False; db.commit()

@app.get("/api/suppliers", tags=["suppliers"])
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    suppliers = db.scalars(select(Supplier).order_by(Supplier.id)).all()
    return [supplier_payload(db, supplier) for supplier in suppliers]

@app.post("/api/suppliers", status_code=201, tags=["suppliers"])
def add_supplier(payload: SupplierIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    if db.scalar(select(Supplier.id).where(func.lower(Supplier.name) == payload.name.lower())):
        raise HTTPException(409, "Такой поставщик уже есть")
    supplier = Supplier(name=payload.name, code=unique_supplier_code(db, payload.name), markup_percent=payload.markup_percent)
    db.add(supplier)
    db.commit()
    return supplier_payload(db, supplier)

@app.put("/api/suppliers/{supplier_id}", tags=["suppliers"])
def update_supplier(supplier_id: int, payload: SupplierIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    supplier = supplier_or_404(db, supplier_id)
    supplier.name, supplier.markup_percent, supplier.active = payload.name, payload.markup_percent, supplier.active
    db.commit()
    return supplier_payload(db, supplier)

@app.post("/api/suppliers/{supplier_id}/key", tags=["suppliers"])
def issue_supplier_key(supplier_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin))):
    supplier = supplier_or_404(db, supplier_id)
    api_key = generate_api_key()
    supplier.api_key_hash = hash_api_key(api_key)
    db.commit()
    return {"api_key": api_key, "ingest_url": f"/api/ingest/{supplier.code}"}

@app.get("/api/suppliers/{supplier_id}/lists", tags=["suppliers"])
def supplier_lists(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    supplier = supplier_or_404(db, supplier_id)
    lists = db.scalars(select(StockList).where(StockList.supplier_id == supplier.id).order_by(StockList.id.desc()).limit(20)).all()
    return [{"id": item.id, "source": item.source, "filename": item.filename, "rows_total": item.rows_total,
             "rows_ok": item.rows_ok, "rows_failed": item.rows_failed, "created_at": item.created_at} for item in lists]

@app.post("/api/suppliers/{supplier_id}/stock/preview", tags=["suppliers"])
async def preview_supplier_file(supplier_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    supplier_or_404(db, supplier_id)
    if not file.filename or not file.filename.lower().endswith((".xls", ".xlsx", ".xlsm")):
        raise HTTPException(422, "Поддерживаются только Excel .xls, .xlsx, .xlsm")
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Размер Excel не должен превышать 20 МБ")
    result = preview_supplier_stock(content, file.filename)
    result["filename"] = file.filename
    return result

@app.post("/api/suppliers/{supplier_id}/stock/confirm", tags=["suppliers"])
def confirm_supplier_stock(supplier_id: int, payload: StockConfirmIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    try:
        supplier = supplier_or_404(db, supplier_id)
        stats = apply_stock(db, supplier, [row.model_dump() for row in payload.rows], "excel", payload.filename)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {**stats, "supplier": supplier_payload(db, supplier)}

@app.post("/api/ingest/{code}", tags=["suppliers"])
def ingest_stock(code: str, payload: IngestIn, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None)):
    supplier = supplier_by_code(db, code)
    if not supplier or not supplier.active:
        raise HTTPException(404, "Поставщик не найден")
    if not supplier.api_key_hash:
        raise HTTPException(401, "У поставщика не выдан API-ключ")
    if not x_api_key or hash_api_key(x_api_key) != supplier.api_key_hash:
        raise HTTPException(403, "Неверный API-ключ")
    rows, errors = [], []
    for index, item in enumerate(payload.items):
        try:
            rows.append(normalize_ingest_item(item.model_dump(), index))
        except ValueError as error:
            errors.append({"row": index + 1, "message": str(error)})
    if not rows:
        raise HTTPException(422, {"message": "Ни одна строка не распознана", "errors": errors})
    try:
        stats = apply_stock(db, supplier, rows, "api", None)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {**stats, "accepted": len(rows), "errors": errors}

@app.get("/api/clients", response_model=list[ClientOut], tags=["clients"])
def list_clients(branch_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    query = select(Client).order_by(Client.id.desc())
    branch = employee_branch_id(user)
    if branch is not None:
        query = query.where(Client.branch_id == branch)
    elif branch_id is not None:
        query = query.where(Client.branch_id == branch_id)
    return db.scalars(query).all()

@app.post("/api/clients", response_model=ClientOut, status_code=201, tags=["clients"])
def add_client(payload: ClientIn, branch_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    branch = employee_branch_id(user)
    if branch is None:
        branch = branch_id or 1  # администратор указывает базу, по умолчанию «АлАвто»
    client = Client(**payload.model_dump(), branch_id=branch)
    db.add(client); db.commit(); db.refresh(client); return client

@app.put("/api/clients/{client_id}", response_model=ClientOut, tags=["clients"])
def update_client(client_id: int, payload: ClientIn, branch_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    client = db.get(Client, client_id)
    if not client: raise HTTPException(404, "Клиент не найден")
    require_client_edit(user, client)
    for key, value in payload.model_dump().items(): setattr(client, key, value)
    if branch_id is not None:
        if user.role != UserRole.admin:
            raise HTTPException(403, "Менять филиал клиента может только Администратор")
        branch_or_404(db, branch_id)
        client.branch_id = branch_id
    db.commit(); db.refresh(client); return client

@app.delete("/api/clients/{client_id}", status_code=204, tags=["clients"])
def delete_client(client_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    client = db.get(Client, client_id)
    if not client: raise HTTPException(404, "Клиент не найден")
    require_client_edit(user, client)
    if db.scalar(select(Order.id).where(Order.client_id == client_id)):
        raise HTTPException(409, "У клиента есть заказы — сначала удалите или перенесите заказы")
    db.delete(client); db.commit()

@app.get("/api/orders", response_model=list[OrderOut], tags=["orders"])
def list_orders(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin)), client_id: int | None = None,
                status: OrderStatus | None = None):
    """Заказы обоих филиалов видны всем сотрудникам; правка — по принадлежности филиала."""
    query = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
    if client_id is not None:
        query = query.where(Order.client_id == client_id)
    if status is not None:
        query = query.where(Order.status == status.value)
    return db.scalars(query).all()

@app.get("/api/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    return order_or_404(db, order_id)

@app.post("/api/orders", response_model=OrderOut, status_code=201, tags=["orders"])
def add_order(payload: OrderCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    try:
        order = assign_order(db, Order(), payload, creator=user)
        db.add(order)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return order_or_404(db, order.id)

@app.put("/api/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def update_order(order_id: int, payload: OrderCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    order = order_or_404(db, order_id)
    require_order_edit(user, order)
    try:
        assign_order(db, order, payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return order_or_404(db, order.id)

@app.patch("/api/orders/{order_id}/status", response_model=OrderOut, tags=["orders"])
def set_order_status(order_id: int, payload: OrderStatusIn, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    order = order_or_404(db, order_id)
    require_order_edit(user, order)
    order.status = payload.status.value
    db.commit()
    return order_or_404(db, order.id)

@app.delete("/api/orders/{order_id}", status_code=409, tags=["orders"])
def orders_not_deleted(order_id: int, _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    raise HTTPException(409, "Удаление заказов отключено: сохраняется история")

@app.get("/api/mailings", response_model=list[MailingOut], tags=["mailings"])
def list_mailings(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return db.scalars(select(Mailing).order_by(Mailing.id.desc())).all()

@app.post("/api/mailings", response_model=MailingOut, status_code=201, tags=["mailings"])
def add_mailing(payload: MailingIn, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin))):
    mailing = Mailing(**payload.model_dump(), author_id=user.id); db.add(mailing); db.commit(); db.refresh(mailing); return mailing

@app.put("/api/mailings/{mailing_id}", response_model=MailingOut, tags=["mailings"])
def update_mailing(mailing_id: int, payload: MailingIn, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    mailing = db.get(Mailing, mailing_id)
    if not mailing: raise HTTPException(404, "Черновик не найден")
    for key, value in payload.model_dump().items(): setattr(mailing, key, value)
    db.commit(); db.refresh(mailing); return mailing

@app.delete("/api/mailings/{mailing_id}", status_code=204, tags=["mailings"])
def delete_mailing(mailing_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    mailing = db.get(Mailing, mailing_id)
    if not mailing: raise HTTPException(404, "Черновик не найден")
    db.delete(mailing); db.commit()

@app.post("/api/import/products/preview", response_model=ImportPreview, tags=["products"])
async def import_preview(file: UploadFile = File(...), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(422, "Поддерживается только Excel .xlsx/.xlsm")
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Размер Excel не должен превышать 20 МБ")
    return preview_excel(content)

@app.post("/api/import/products/confirm", response_model=list[ProductOut], status_code=201, tags=["products"])
def import_confirm(payload: ImportConfirm, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    products = [create_product(db, row.data) for row in payload.rows]
    db.commit()
    return [product_or_404(db, product.id) for product in products]

@app.get("/api/suppliers/sync-time", tags=["suppliers"])
def sync_time(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.employee, UserRole.admin))):
    """Метки последнего обновления остатков — для проверки актуальности данных."""
    suppliers = db.scalars(select(Supplier).order_by(Supplier.id)).all()
    now = datetime.now(timezone.utc)
    return {"server_time": now, "suppliers": [{"id": supplier.id, "name": supplier.name,
             "last_sync_at": supplier.last_sync_at,
             "age_minutes": None if not supplier.last_sync_at else round((now - supplier.last_sync_at).total_seconds() / 60)} for supplier in suppliers]}
