from odoo import models, fields, api


class OvertimeApproval(models.Model):
    _name = 'overtime.approver'
    _description = 'Overtime Approver'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    user_id = fields.Many2one('res.users')
