"""Остатки поставщиков: разбор Excel (.xls/.xlsx/.xlsm), нормализация и применение.

Каждый поставщик присылает прайс в своём формате, поэтому колонки ищутся по
псевдонимам заголовков, а размер и сезон дополнительно вытаскиваются из
наименования. Применение атомарно: товары поставщика деактивируются, затем
создаются/обновляются по строкам прайса.
"""
import hashlib
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import select

from app.models import Product, ProductType, StockList, TireSpec

FIELD_ALIASES = {
    "brand": ("бренд", "производитель", "brand", "марка", "бренд/производитель"),
    "model": ("наименование", "название", "модель", "товар", "model", "description", "наименование товара"),
    "price": ("цена", "price", "стоимость", "цена розница", "цена розн", "опт"),
    "stock": ("остаток", "наличие", "количество", "кол-во", "кол", "шт", "stock"),
    "season": ("сезон", "сезонность", "season"),
}
SIZE_RE = re.compile(r"(\d{3})\s*/\s*(\d{2,3})(?:\s*[RР]\s*(\d{2}(?:\.\d)?))?")
SEASON_HINTS = (("зим", "Зима"), ("лет", "Лето"), ("всесезон", "Всесезон"), ("all season", "Всесезон"))
SEASON_ALIASES = {"зим": "Зима", "лето": "Лето", "лет": "Лето", "всесезон": "Всесезон", "всес": "Всесезон"}
TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def slugify_code(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower().translate(TRANSLIT)).strip("-")
    return slug or "supplier"


def generate_api_key() -> str:
    return "sk-" + secrets.token_urlsafe(24)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def read_table(content: bytes, filename: str) -> list[list]:
    name = (filename or "").lower()
    if name.endswith(".xls"):
        import xlrd
        book = xlrd.open_workbook(file_contents=content)
        sheet = book.sheet_by_index(0)
        return [[sheet.cell_value(row, column) for column in range(sheet.ncols)] for row in range(sheet.nrows)]
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    return [list(row) for row in sheet.iter_rows(values_only=True)]


def detect_columns(rows: list[list]) -> tuple[int, dict[str, int]] | None:
    best, best_score = None, 0
    for index, row in enumerate(rows[:10]):
        headers = [str(value).strip().lower() if value is not None else "" for value in row]
        mapping = {}
        for field, aliases in FIELD_ALIASES.items():
            for column, header in enumerate(headers):
                if header and any(header == alias or header.startswith(alias) for alias in aliases):
                    mapping[field] = column
                    break
        if len(mapping) > best_score:
            best, best_score = (index, mapping), len(mapping)
    if best is None or best_score < 2:
        return None
    return best


def clean_price(value) -> Decimal | None:
    text = re.sub(r"[^\d,.]", "", str(value or "")).replace(",", ".")
    if not text:
        return None
    try:
        price = Decimal(text)
    except InvalidOperation:
        return None
    return price if price > 0 else None


def clean_stock(value) -> int:
    text = str(value or "").strip().lower()
    if text in ("много", "мн.", "много.", ">10"):
        return 99
    match = re.search(r"\d+", text)
    if not match:
        return 0
    number = int(match.group())
    return number + 1 if text.startswith(">") else number


def parse_season(text: str) -> str | None:
    low = str(text or "").lower()
    for hint, season in SEASON_HINTS:
        if hint in low:
            return season
    for alias, season in SEASON_ALIASES.items():
        if low.strip().startswith(alias):
            return season
    return None


def parse_model(model: str) -> tuple[int | None, int | None, int | None, str | None]:
    text = str(model or "")
    size = SIZE_RE.search(text)
    width, profile, diameter = (None, None, None)
    if size:
        width, profile = int(size.group(1)), int(size.group(2))
        diameter = int(float(size.group(3))) if size.group(3) else None
    return width, profile, diameter, parse_season(text)


def preview_supplier_stock(content: bytes, filename: str) -> dict:
    rows = read_table(content, filename)
    detected = detect_columns(rows)
    if not detected:
        return {"columns": {}, "valid_rows": [], "errors": [
            {"row": 1, "message": "Не найдены заголовки (наименование/цена/остаток). Проверьте формат файла."}]}
    header_index, mapping = detected
    valid, errors = [], []
    for index, values in enumerate(rows[header_index + 1:], start=header_index + 2):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        def cell(field):
            column = mapping.get(field)
            return values[column] if column is not None and column < len(values) else None
        brand = str(cell("brand") or "").strip()
        model = str(cell("model") or "").strip()
        price = clean_price(cell("price"))
        stock = clean_stock(cell("stock"))
        width, profile, diameter, season = parse_model(model)
        season = parse_season(str(cell("season") or "")) or season
        if not model or price is None:
            errors.append({"row": index, "message": "Нет наименования или цены"})
            continue
        if width is None or profile is None or diameter is None:
            errors.append({"row": index, "message": "Не распознан размер, например 225/50 R18"})
            continue
        valid.append({"row": index, "brand": brand or model.split()[0], "model": model,
                      "price": str(price), "stock": stock, "season": season or "Всесезон",
                      "width": width, "profile": profile, "diameter": diameter})
    return {"columns": {field: column + 1 for field, column in mapping.items()},
            "valid_rows": valid, "errors": errors}


def normalize_ingest_item(item: dict, index: int) -> dict:
    model = str(item.get("model") or "").strip()
    price = clean_price(item.get("price"))
    width, profile, diameter, season = parse_model(model)
    season = item.get("season") or season
    if not model or price is None:
        raise ValueError(f"Строка {index + 1}: нет наименования или цены")
    if width is None or profile is None or diameter is None:
        raise ValueError(f"Строка {index + 1}: не распознан размер, например 225/50 R18")
    brand = str(item.get("brand") or "").strip() or model.split()[0]
    return {"row": index + 1, "brand": brand, "model": model, "price": str(price),
            "stock": clean_stock(item.get("stock")), "season": season or "Всесезон",
            "width": width, "profile": profile, "diameter": diameter}


def apply_stock(db, supplier, rows: list[dict], source: str, filename: str | None) -> dict:
    current = db.scalars(select(Product).where(Product.supplier == supplier.name)).all()
    index = {}
    for product in current:
        key = (product.type.value, (product.brand or "").strip().lower(), (product.model or "").strip().lower())
        index.setdefault(key, product)
    factor = Decimal(1) + (supplier.markup_percent or Decimal(0)) / Decimal(100)
    seen, created, updated = set(), 0, 0
    for row in rows:
        key = ("tire", str(row["brand"]).strip().lower(), str(row["model"]).strip().lower())
        seen.add(key)
        price = (Decimal(str(row["price"])) * factor).quantize(Decimal("0.01"))
        product = index.get(key)
        if product and product.type == ProductType.tire:
            product.price, product.stock, product.active = price, row["stock"], True
            if product.tire and row.get("season"):
                product.tire.season = row["season"]
            updated += 1
        else:
            product = Product(type=ProductType.tire, brand=row["brand"], model=row["model"],
                              price=price, stock=row["stock"], active=True, supplier=supplier.name,
                              tire=TireSpec(width=row["width"], profile=row["profile"], diameter=row["diameter"],
                                            season=row["season"], load_index="—"))
            db.add(product)
            created += 1
        index[key] = product
    deactivated = 0
    for key, product in index.items():
        if key not in seen and product.supplier == supplier.name and product.active:
            product.active = False
            deactivated += 1
    supplier.last_sync_at = datetime.now(timezone.utc)
    db.add(StockList(supplier_id=supplier.id, source=source, filename=filename,
                     rows_total=len(rows), rows_ok=len(rows), rows_failed=0))
    db.flush()
    return {"created": created, "updated": updated, "deactivated": deactivated}
