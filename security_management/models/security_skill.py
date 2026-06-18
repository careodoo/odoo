from odoo import api, fields, models, _


class SecuritySkill(models.Model):
    _name = 'security.skill'
    _description = 'Security Skill'
    _order = 'name'

    name = fields.Char(string='Skill Name', required=True)
    description = fields.Text(string='Description')
    category = fields.Selection([
        ('technical', 'Technical'),
        ('physical', 'Physical'),
        ('communication', 'Communication'),
        ('leadership', 'Leadership'),
        ('specialized', 'Specialized'),
        ('other', 'Other')
    ], string='Category', default='other')
    
    level_required = fields.Selection([
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert')
    ], string='Level Required', default='basic')
    
    is_required = fields.Boolean(string='Required Skill', default=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this skill belongs to'
    )
    # For reporting and analysis
    guard_count = fields.Integer(string='Guards with Skill', compute='_compute_guard_count')
    
    @api.depends()
    def _compute_guard_count(self):
        for skill in self:
            skill.guard_count = self.env['security.guard'].search_count([
                ('skill_ids', 'in', skill.id)
            ]) if 'security.guard' in self.env else 0
