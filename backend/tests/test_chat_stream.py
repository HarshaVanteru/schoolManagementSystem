import unittest
from decimal import Decimal
from datetime import date, datetime
import json
import uuid

from services.chat_service import _format_sse, _json_serializer
from services.sql_agent import _clean_cell


class TestSerialization(unittest.TestCase):
    def test_clean_cell_decimal_and_dates(self):
        self.assertEqual(_clean_cell(Decimal('45.0')), 45)
        self.assertEqual(_clean_cell(Decimal('45.75')), 45.75)
        self.assertEqual(_clean_cell(date(2026, 9, 30)), '2026-09-30')
        self.assertEqual(_clean_cell(datetime(2026, 9, 30, 10, 0, 0)), '2026-09-30T10:00:00')
        self.assertEqual(_clean_cell('normal string'), 'normal string')
        self.assertEqual(_clean_cell(123), 123)

    def test_format_sse_with_decimals_and_dates(self):
        sample_data = {
            'type': 'table',
            'result_table': {
                'columns': ['student_name', 'average_marks', 'exam_date'],
                'rows': [
                    {'student_name': 'Alice', 'average_marks': Decimal('87.50'), 'exam_date': date(2026, 3, 15)},
                    {'student_name': 'Bob', 'average_marks': Decimal('90.00'), 'exam_date': date(2026, 3, 15)},
                ],
                'row_count': 2,
            },
            'session_id': uuid.uuid4(),
        }
        sse_event = _format_sse('table', sample_data)
        self.assertTrue(sse_event.startswith('event: table\ndata: '))
        self.assertTrue(sse_event.endswith('\n\n'))
        json_str = sse_event.replace('event: table\ndata: ', '').strip()
        decoded = json.loads(json_str)
        self.assertEqual(decoded['result_table']['rows'][0]['average_marks'], 87.5)
        self.assertEqual(decoded['result_table']['rows'][0]['exam_date'], '2026-03-15')


if __name__ == '__main__':
    unittest.main()
