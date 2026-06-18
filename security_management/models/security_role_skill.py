from odoo import api, fields, models, _

class SecurityRoleSkill(models.Model):
    _name = 'security.role.skill'
    _description = 'Security Role Required Skill'
    
    name = fields.Char(string='Skill Name', required=True)
    role_id = fields.Many2one('security.role', string='Role', ondelete='cascade')
    skill_id = fields.Many2one('security.skill', string='Skill', ondelete='cascade')
    min_proficiency = fields.Selection([
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert')
    ], string='Minimum Proficiency', default='basic')
    certification_required = fields.Boolean(string='Certification Required', default=False)
    description = fields.Text(string='Description')
    is_required = fields.Boolean(string='Required Skill', default=False)
    
    _sql_constraints = [
        ('role_skill_uniq', 'UNIQUE(role_id, name)', 'Skill must be unique per role!')
    ]
