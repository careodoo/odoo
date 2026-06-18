from odoo import api, fields, models, _

class SecurityRole(models.Model):
    _name = 'security.role'
    _description = 'Security Role'
    _order = 'sequence, name'
    
    name = fields.Char(string='Role Name', required=True)
    code = fields.Char(string='Role Code', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_leadership = fields.Boolean(string='Leadership Role', default=False)
    min_experience = fields.Float(string='Minimum Experience (Years)')
    required_license = fields.Char(string='Required License')
    
    # Relationships
    required_skill_ids = fields.One2many('security.role.skill', 'role_id', string='Required Skills')
    guard_ids = fields.One2many('security.guard', 'security_employee_role_id', string='Guards with this Role')
    
    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Role code must be unique!')
    ]
