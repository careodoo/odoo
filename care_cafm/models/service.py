# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


PALETTE = {
    'cleaning': '#0ea5e9', 'security': '#e11d48', 'agriculture': '#16a34a',
    'facade': '#8b5cf6', 'maintenance': '#f59e0b', 'pest': '#7c3aed',
    'waste': '#16a34a', 'disinfection': '#0ea5a5', 'pool': '#0891b2',
    'watertank': '#0e7a5f', 'valet': '#b45309', 'hospitality': '#8a6d3b',
    'other': '#64748b',
}


class CafmService(models.Model):
    """A service line offered to clients (cleaning, security, agriculture...).
    Each service has its own teams, SLA, mobile interface flavour and colour."""
    _name = 'care.cafm.service'
    _description = 'CAFM Service Line'
    _order = 'sequence, name'

    name = fields.Char(string='الخدمة', required=True, translate=True)
    code = fields.Char(string='الرمز')
    sequence = fields.Integer(default=10)
    service_type = fields.Selection([
        ('cleaning', 'النظافة'),
        ('security', 'الأمن'),
        ('agriculture', 'الزراعة وتنسيق الحدائق'),
        ('facade', 'الواجهات'),
        ('maintenance', 'الصيانة (تكييف/كهرباء/سباكة)'),
        ('pest', 'مكافحة الحشرات'),
        ('waste', 'إدارة النفايات'),
        ('disinfection', 'التعقيم'),
        ('pool', 'صيانة المسابح'),
        ('watertank', 'تنظيف خزانات المياه'),
        ('valet', 'صف السيارات'),
        ('hospitality', 'الضيافة'),
        ('other', 'أخرى'),
    ], string='نوع الخدمة', required=True, default='cleaning')
    default_sla_hours = fields.Float(string='SLA الافتراضي (ساعات)', default=4.0)
    color = fields.Integer(string='لون')
    icon = fields.Char(string='أيقونة', default='🧹',
                       help='إيموجي يمثّل الخدمة في تطبيق الموبايل.')
    # The same service used to render in a different colour in the app, the
    # /cafm/m portal and the client portal, because each carried its own
    # hardcoded map. The record is now the single source of truth.
    color_hex = fields.Char(string='لون الخدمة', default='#64748b',
                            help='يُستخدم في التطبيق والبوابة معًا — لون واحد لكل خدمة.')
    active = fields.Boolean(default=True)

    # Some services are really specialisations of another: pool maintenance is
    # maintenance, tank cleaning and disinfection are cleaning. Nesting them
    # keeps the client's service list readable instead of eleven flat tiles.
    parent_id = fields.Many2one('care.cafm.service', string='ضمن خدمة',
                                ondelete='set null', index=True,
                                help='اتركه فارغًا للخدمات الرئيسية.')
    child_ids = fields.One2many('care.cafm.service', 'parent_id', string='الخدمات الفرعية')
    is_sub = fields.Boolean(string='خدمة فرعية', compute='_compute_is_sub', store=True)

    team_ids = fields.One2many('care.cafm.team', 'service_id', string='الفِرَق')
    workorder_count = fields.Integer(compute='_compute_counts')
    team_count = fields.Integer(compute='_compute_counts')

    @api.depends('parent_id')
    def _compute_is_sub(self):
        for r in self:
            r.is_sub = bool(r.parent_id)

    @api.constrains('parent_id')
    def _check_parent_loop(self):
        if not self._check_recursion():
            raise ValidationError(_('لا يمكن أن تكون الخدمة ضمن نفسها.'))

    def _compute_counts(self):
        WO = self.env['care.cafm.workorder']
        for rec in self:
            rec.workorder_count = WO.search_count([('service_id', '=', rec.id)])
            rec.team_count = len(rec.team_ids)

    _sql_constraints = [('code_uniq', 'unique(code)', 'رمز الخدمة يجب أن يكون فريداً.')]

    @api.onchange('service_type')
    def _onchange_service_type_colour(self):
        for r in self:
            if r.service_type:
                r.color_hex = PALETTE.get(r.service_type, '#64748b')

    @api.model
    def palette(self):
        """type -> {colour, icon, label} for any surface that needs to style a
        service it only knows by type code."""
        out = {}
        for s in self.sudo().search([]):
            if s.service_type and s.service_type not in out:
                out[s.service_type] = {
                    'color': s.color_hex or PALETTE.get(s.service_type, '#64748b'),
                    'icon': s.icon or '🧩', 'label': s.name,
                }
        for t, c in PALETTE.items():
            out.setdefault(t, {'color': c, 'icon': '🧩', 'label': t})
        return out
