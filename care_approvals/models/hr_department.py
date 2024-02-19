from odoo import fields, models, api


class Department(models.Model):
    _inherit = 'hr.department'

    product_ids = fields.One2many('hr.department.product', 'department_id')


class DepartmentProduct(models.Model):
    _name = 'hr.department.product'
    _description = 'Department List of Materials'

    department_id = fields.Many2one('hr.department')
    product_id = fields.Many2one('product.product', required=True)
    limit = fields.Integer()
