from sqlalchemy import select
from app.config import settings
from app.database import SessionLocal
from app.models import Branch, Client, Product, ProductType, User, UserRole
from app.security import hash_password

BRANCHES = [("АлАвто", "alavto"), ("Дискотека", "diskoteka")]

DEMO_PRODUCTS = [
    {"type": "tire", "brand": "Yokohama", "model": "BluEarth-A AE50", "price": 7850, "stock": 8,
     "tire": {"width": 205, "profile": 55, "diameter": 16, "season": "Лето", "load_index": "91V"}},
    {"type": "tire", "brand": "Yokohama", "model": "iceGUARD iG65", "price": 6300, "stock": 12,
     "tire": {"width": 195, "profile": 65, "diameter": 15, "season": "Зима", "load_index": "91T", "studded": True}},
    {"type": "wheel", "brand": "K&K", "model": "КС-101", "price": 8400, "stock": 8,
     "wheel": {"diameter": 16, "bolt_pattern": "5×114.3", "width": 6.5, "center_bore": 67.1, "et": 45, "color": "Graphite"}},
]

DEMO_CLIENTS = [
    {"branch_code": "alavto", "name": "Иван Петров", "phone": "+79001234567", "note": "Ford Focus 2 205/55/16"},
    {"branch_code": "diskoteka", "name": "Мария Смирнова", "phone": "+79007654321", "note": None},
]


def main() -> None:
    db = SessionLocal()
    try:
        branches = {}
        for name, code in BRANCHES:
            branch = db.scalar(select(Branch).where(Branch.code == code))
            if not branch:
                branch = Branch(name=name, code=code)
                db.add(branch)
                db.flush()
            branches[code] = branch

        if not db.scalar(select(User).where(User.login == settings.initial_admin_login)):
            db.add(User(name="Администратор", login=settings.initial_admin_login,
                        password_hash=hash_password(settings.initial_admin_password), role=UserRole.admin))
        if not db.scalar(select(User).where(User.login == "anna")):
            db.add(User(name="Анна", login="anna", password_hash=hash_password("anna-demo"),
                        role=UserRole.employee, branch_id=branches["alavto"].id))
        if not db.scalar(select(User).where(User.login == "gleb")):
            db.add(User(name="Глеб", login="gleb", password_hash=hash_password("gleb-demo"),
                        role=UserRole.employee, branch_id=branches["diskoteka"].id))

        if not db.scalar(select(Product.id).limit(1)):
            from app.main import create_product
            from app.schemas import ProductIn
            for row in DEMO_PRODUCTS:
                create_product(db, ProductIn.model_validate(row))

        if not db.scalar(select(Client.id).limit(1)):
            for row in DEMO_CLIENTS:
                db.add(Client(**{k: v for k, v in row.items() if k != "branch_code"},
                              branch_id=branches[row["branch_code"]].id))
        db.commit()
        print("Seed data created or already present.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
