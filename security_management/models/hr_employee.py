from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    # Only define the minimal fields needed for security management
    security_rank = fields.Selection([
        ('guard', 'Security Guard'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Security Manager'),
        ('director', 'Security Director')
    ], string='Security Rank', default='guard', tracking=True)
    
    employee_code = fields.Char(string='Employee Code', tracking=True)
    security_employee_id = fields.Many2one('security.employee', string='Security Employee')
    