from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from .common import ProductReturnReasonCommon


@tagged('post_install', '-at_install', 'access_rights')
class TestSecurity(ProductReturnReasonCommon):

    def test_01_base_group_user(self):
        group_user = self.env.ref('base.group_user').id
        self.user_1.write({'groups_id': [(6, 0, [group_user])]})

        self.reason_1.with_user(self.user_1).read(['id'])
        with self.assertRaises(AccessError):
            self.reason_1.with_user(self.user_1).write({'name': 'name_test'})

        with self.assertRaises(AccessError):
            self.reason_1.with_user(self.user_1).unlink()

        with self.assertRaises(AccessError):
            self.env['product.return.reason'].with_user(self.user_1).create({
                'name': 'test_new',
                'description': 'description_new'
            })

    def test_02_group_return_reason_manager(self):
        group_return_reason_manager = self.env.ref(
            'to_product_return_reason.group_return_reason_manager').id
        self.user_1.write({'groups_id': [(6, 0, [group_return_reason_manager])]})

        self.reason_1.with_user(self.user_1).read(['id'])
        self.reason_1.with_user(self.user_1).write({'name': 'name_test'})
        self.reason_1.with_user(self.user_1).unlink()
        self.env['product.return.reason'].with_user(self.env['product.return.reason']).create({
            'name': 'test_new',
            'description': 'description_new'
        })
