from decimal import Decimal
from io import BytesIO
import unittest
from openpyxl import Workbook
from app.importing import preview_excel
from app.schemas import ImportConfirm


class ImportPriceTests(unittest.TestCase):
    def test_price_list_markup_and_confirmation_roundtrip(self):
        book = Workbook()
        sheet = book.active
        sheet.append(['Прайс'])
        sheet.append(['Модель', 'Цвет', 'Ширина', 'Диаметр', 'PCD', 'ET', 'DIA', 'Остаток', 'Цена'])
        sheet.append(['DWS-106', 'SM', '5.5', 13, '4/98', 38, '58.6', 3, 3000])
        sheet.append(['DWS-109', 'SM', '5.5', 13, '4/98', 38, '58.6', 3, 6250])
        sheet.append(['DWS-132', 'SM', '5.5', 13, '4/98', 38, '58.6', 3, 10.01])
        sheet.append(['Invalid', 'SM', '5.5', 13, '4/98', 38, '58.6', 3, -1])
        buffer = BytesIO()
        book.save(buffer)
        preview = preview_excel(buffer.getvalue())
        self.assertEqual(len(preview.errors), 1)
        self.assertEqual([r.data.price for r in preview.valid_rows], [Decimal('3750.00'), Decimal('7812.50'), Decimal('12.51')])
        self.assertEqual(preview.valid_rows[0].source_price, Decimal('3000'))
        self.assertEqual(preview.valid_rows[0].markup_percent, Decimal('25'))
        confirmation = ImportConfirm.model_validate({'rows': [r.model_dump(mode='json') for r in preview.valid_rows]})
        self.assertEqual(confirmation.rows[0].data.price, Decimal('3750.00'))
        self.assertEqual(preview_excel(buffer.getvalue()), preview)

    def test_standard_template_markup(self):
        book = Workbook()
        sheet = book.active
        sheet.append(['тип', 'бренд', 'модель', 'цена', 'остаток', 'ширина', 'профиль', 'диаметр', 'сезон', 'индекс нагрузки'])
        sheet.append(['tire', 'Example', 'T1', 100, 4, 205, 55, 16, 'Лето', '91V'])
        buffer = BytesIO()
        book.save(buffer)
        preview = preview_excel(buffer.getvalue())
        self.assertFalse(preview.errors)
        self.assertEqual(preview.valid_rows[0].data.price, Decimal('125.00'))


if __name__ == '__main__':
    unittest.main()
