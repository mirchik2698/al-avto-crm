from decimal import Decimal
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import add_order, app, assign_order, create_product
from app.models import Branch, Client, Order, User, UserRole
from app.schemas import ClientIn, EmployeeIn, OrderCreate, ProductIn
from app.security import create_access_token, hash_password

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try: yield session
    finally: session.close()

def tire_payload():
    return ProductIn.model_validate({"type":"tire", "brand":"Test", "model":"T1", "price":"7000", "stock":8,
        "tire":{"width":205,"profile":55,"diameter":16,"season":"Зима","load_index":"91T"}})

def test_order_remainder_is_automatic_and_never_negative(db):
    client = Client(name="Анна", phone="+79990000000", branch_id=1); db.add(client); db.commit()
    product = create_product(db, tire_payload()); db.commit()
    item = {"product_id":product.id,"name":"Test","supplier":"Test","quantity":1}
    normal = OrderCreate(client_id=client.id, comment="Монтаж", total_amount=Decimal("12000"), items=[item])
    order = assign_order(db, Order(), normal)
    assert order.deposit == Decimal("5000")
    assert order.remainder == Decimal("7000")
    small = OrderCreate(client_id=client.id, comment="Монтаж", total_amount=Decimal("3000"), items=[item])
    assert assign_order(db, Order(), small).remainder == Decimal("0")

def test_client_name_and_phone_are_required():
    with pytest.raises(ValidationError): ClientIn(name="", phone="")

def test_employee_cannot_access_mailings(db):
    employee = User(name="Сотрудник", login="employee", password_hash=hash_password("password"), role=UserRole.employee)
    db.add(employee); db.commit()
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    try:
        from fastapi.testclient import TestClient
        response = TestClient(app).get("/api/mailings", headers={"Authorization": f"Bearer {create_access_token(employee)}"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_employee_requires_branch():
    with pytest.raises(ValidationError):
        EmployeeIn(name="Сотрудник", login="employee", password="password", role=UserRole.employee)

def test_branchless_employee_cannot_list_clients(db):
    employee = User(name="Сотрудник", login="employee", password_hash=hash_password("password"), role=UserRole.employee)
    db.add(employee); db.commit()
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    try:
        from fastapi.testclient import TestClient
        response = TestClient(app).get("/api/clients", headers={"Authorization": f"Bearer {create_access_token(employee)}"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_employee_cannot_assign_order_to_other_branch_client(db):
    first = Branch(name="Первый", code="first")
    second = Branch(name="Второй", code="second")
    db.add_all([first, second]); db.flush()
    own_client = Client(name="Иван", phone="+79990000001", branch_id=first.id)
    other_client = Client(name="Пётр", phone="+79990000002", branch_id=second.id)
    employee = User(name="Сотрудник", login="employee", password_hash=hash_password("password"), role=UserRole.employee, branch=first)
    db.add_all([own_client, other_client, employee]); db.commit()
    payload = OrderCreate(client_id=other_client.id, total_amount=Decimal("1000"), items=[])
    with pytest.raises(HTTPException) as error:
        add_order(payload, db, employee)
    assert error.value.status_code == 403
