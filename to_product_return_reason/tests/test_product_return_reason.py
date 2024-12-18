from psycopg2 import IntegrityError

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import ProductReturnReasonCommon


@tagged('post_install', '-at_install')
class TestProducReturnReason(ProductReturnReasonCommon):
    def test_01_sql_constraints_name(self):
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.reason_2.with_context(tracking_disable=True).name = 'Damaged During Transport'

    def test_01_sql_constraints_description(self):
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.reason_1.with_context(tracking_disable=True).description = 'Damaged During Transport'

    def test_copy_reason(self):
        self.reason_2 = self.reason_1.copy()
        reason_2_name = self.reason_1.name + ' (copy)'
        self.assertRecordValues(self.reason_2, [{
            'name': reason_2_name,
            'description': 'Product is harmed or experiences losses during the process of being transported'
        }])
