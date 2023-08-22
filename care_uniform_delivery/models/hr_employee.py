from odoo import fields, models, api, _


class Employee(models.Model):
    _inherit = 'hr.employee'

    uniform_delivery_count = fields.Integer(compute='compute_uniform_delivery_count')
    bulk_uniform_delivery_count = fields.Integer(compute='compute_bulk_uniform_delivery_count')

    def compute_uniform_delivery_count(self):
        for rec in self:
            rec.uniform_delivery_count = self.env['uniform.delivery'].search_count([('employee_id', '=', rec.id)])

    def compute_bulk_uniform_delivery_count(self):
        for rec in self:
            rec.bulk_uniform_delivery_count = len(self.env['uniform.delivery'].search([
                ('employee_id', '=', False)
            ]).filtered(lambda u: rec.id in u.employee_ids.ids))

    def button_show_uniform_delivery(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Uniform Delivery'),
            'res_model': 'uniform.delivery',
            'view_mode': 'tree',
            'context': {'show_employee': True},
            'domain': [('employee_id', '=', self.id)],
        }

    def button_show_bulk_uniform_delivery(self):
        bulk = self.env['uniform.delivery'].search([
            ('employee_id', '=', False)
        ]).filtered(lambda u: self.id in u.employee_ids.ids)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bulk Uniform Delivery'),
            'res_model': 'uniform.delivery',
            'view_mode': 'tree',
            'context': {'show_employees': True},
            'domain': [('id', 'in', bulk.ids)],
        }
