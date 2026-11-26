import unittest
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.main import add_order, create_product
from app.models import Client, Order
from app.schemas import OrderCreate, ProductIn


class OrderClientTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        product = create_product(self.db, ProductIn(
            type="tire", brand="Test", model="X", price=7000, stock=4,
            tire={"width":205, "profile":55, "diameter":16, "season":"Лето", "load_index":"91V"}
        ))
        self.db.commit()
        self.details = {"comment":"Тест", "total_amount":"12000.50", "items":[{"product_id":product.id, "name":"Test", "supplier":"Test", "quantity":1, "unit_price":"7000"}]}
        self.client = {"name":" Анна ", "phone":" +79990000000 ", "note":"Звонить после 17:00"}

    def test_saves_order_and_new_client_together(self):
        order = add_order(OrderCreate(**self.details, new_client=self.client), self.db, None)
        self.db.expire_all()
        client = self.db.get(Client, order.client_id)
        self.assertEqual((client.name, client.phone, client.note), ("Анна", "+79990000000", self.client["note"]))
        self.assertEqual(order.remainder, Decimal("7000.50"))
        self.assertEqual(order.items[0].unit_price, Decimal("7000"))

    def test_failed_order_does_not_leave_client(self):
        details = {**self.details, "items":[{"product_id":999, "name":"Test", "supplier":"Test", "quantity":1, "unit_price":"7000"}]}
        with self.assertRaises(HTTPException) as error:
            add_order(OrderCreate(**details, new_client=self.client), self.db, None)
        self.assertEqual(error.exception.status_code, 404)
        self.assertIsNone(self.db.scalar(select(Client)))
        self.assertIsNone(self.db.scalar(select(Order)))

    def test_order_can_be_saved_without_product(self):
        details = {key: value for key, value in self.details.items() if key != "items"}
        order = add_order(OrderCreate(**details, new_client=self.client), self.db, None)
        self.assertEqual(order.items, [])
        self.assertIsNotNone(self.db.get(Client, order.client_id))
        self.assertEqual(order.remainder, Decimal("7000.50"))

    def test_existing_client_flow_remains_available(self):
        client = Client(name="Иван", phone="+79990000001", branch_id=1)
        self.db.add(client)
        self.db.commit()
        order = add_order(OrderCreate(**self.details, client_id=client.id), self.db, None)
        self.assertEqual(order.client_id, client.id)
        self.assertEqual(len(self.db.scalars(select(Client)).all()), 1)

    def test_rejects_invalid_client_choices(self):
        for args in ({}, {"client_id":1, "new_client":self.client}, {"new_client":{**self.client, "name":"   "}}):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                OrderCreate(**self.details, **args)
