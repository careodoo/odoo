from odoo import models, fields, api, _

class SecurityTeamRole(models.Model):
    _name = 'security.team.role'
    _description = 'Security Team Role'
    
    name = fields.Char(string='Role Name', required=True)
    code = fields.Char(string='Role Code', required=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this role belongs to'
    )
    
    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Role code must be unique!')
    ]
