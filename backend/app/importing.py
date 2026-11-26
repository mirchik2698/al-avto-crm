from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import load_workbook
from pydantic import ValidationError
from app.schemas import ImportPreview, ImportRow, ProductIn

REQUIRED_COLUMNS = {"тип", "бренд", "модель", "цена", "остаток"}
WHEEL_HEADERS = {"модель", "ширина", "диаметр", "pcd", "et", "dia", "остаток", "цена"}

def _priced_row(index, payload):
    product = ProductIn.model_validate(payload)
    source_price = product.price
    payload = product.model_dump()
    payload["price"] = (source_price * Decimal("1.25")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ImportRow(row=index, data=ProductIn.model_validate(payload), source_price=source_price, markup_percent=Decimal("25"))

def _value(row: dict, key: str):
    value = row.get(key)
    return None if value is None or value == "" else value

def _headers(values):
    return [str(value).strip().lower() if value is not None else "" for value in values]

def _bool(value):
    return str(value or "").strip().lower() in ("1", "да", "true", "yes")

def _normal_bolt_pattern(value):
    return str(value).strip().replace("*", "×").replace("/", "×")

def _stock(value):
    text = str(value).strip()
    if text.startswith(">") and text[1:].strip().isdigit():
        return int(text[1:].strip()) + 1
    return value

def _preview_standard(rows, headers):
    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        return ImportPreview(valid_rows=[], errors=[{"row": 1, "message": f"Нет обязательных колонок: {', '.join(sorted(missing))}"}])
    valid_rows, errors = [], []
    for index, values in rows:
        if not any(value is not None and str(value).strip() for value in values):
            continue
        data = dict(zip(headers, values))
        product_type = str(_value(data, "тип") or "").strip().lower()
        product_type = {"шина": "tire", "шины": "tire", "диск": "wheel", "диски": "wheel"}.get(product_type, product_type)
        try:
            payload = {"type": product_type, "brand": _value(data, "бренд"), "model": _value(data, "модель"),
                "price": _value(data, "цена"), "stock": _stock(_value(data, "остаток")), "active": _value(data, "активен") is not False,
                "image_url": _value(data, "фото")}
            if product_type == "tire":
                payload["tire"] = {"width": _value(data, "ширина"), "profile": _value(data, "профиль"), "diameter": _value(data, "диаметр"),
                    "season": _value(data, "сезон"), "load_index": _value(data, "индекс нагрузки"), "commercial": _bool(_value(data, "коммерческая")), "studded": _bool(_value(data, "шипы"))}
            elif product_type == "wheel":
                payload["wheel"] = {"diameter": _value(data, "диаметр"), "bolt_pattern": _value(data, "разболтовка"), "width": _value(data, "ширина"),
                    "center_bore": _value(data, "цо"), "et": _value(data, "et"), "color": _value(data, "цвет")}
            valid_rows.append(_priced_row(index, payload))
        except ValidationError as exc:
            errors.append({"row": index, "message": "; ".join(item["msg"] for item in exc.errors())})
    return ImportPreview(valid_rows=valid_rows, errors=errors)

def _preview_wheel_price(rows, headers):
    valid_rows, errors = [], []
    for index, values in rows:
        data = dict(zip(headers, values))
        model = _value(data, "модель")
        if not model or not _value(data, "диаметр") or not _value(data, "pcd"):
            continue
        try:
            payload = {"type": "wheel", "brand": "Литье", "model": str(model).strip(), "price": _value(data, "цена"),
                "stock": _stock(_value(data, "остаток")), "active": True, "image_url": _value(data, "фото"),
                "wheel": {"diameter": _value(data, "диаметр"), "bolt_pattern": _normal_bolt_pattern(_value(data, "pcd")),
                    "width": Decimal(str(_value(data, "ширина")).lower().replace("j", "")), "center_bore": _value(data, "dia"),
                    "et": _value(data, "et"), "color": _value(data, "цвет") or "Не указан"}}
            valid_rows.append(_priced_row(index, payload))
        except (ValidationError, ArithmeticError, ValueError) as exc:
            message = "; ".join(item["msg"] for item in exc.errors()) if isinstance(exc, ValidationError) else str(exc)
            errors.append({"row": index, "message": message})
    return ImportPreview(valid_rows=valid_rows, errors=errors)

def preview_excel(content: bytes) -> ImportPreview:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    source = list(sheet.iter_rows(values_only=True))
    for header_index, values in enumerate(source):
        headers = _headers(values)
        if WHEEL_HEADERS.issubset(set(headers)):
            return _preview_wheel_price(list(enumerate(source[header_index + 1:], start=header_index + 2)), headers)
        if REQUIRED_COLUMNS.issubset(set(headers)):
            return _preview_standard(list(enumerate(source[header_index + 1:], start=header_index + 2)), headers)
    return ImportPreview(valid_rows=[], errors=[{"row": 1, "message": "Не найдена строка заголовков поддерживаемого формата"}])
