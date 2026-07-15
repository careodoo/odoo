# -*- coding: utf-8 -*-
"""CARE 2 CARE service provider (technician/crew) that fulfils bookings."""
from odoo import api, fields, models


class C2CProvider(models.Model):
    _name = 'c2c.provider'
    _description = 'CARE 2 CARE Provider'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='مقدّم الخدمة', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف')
    user_id = fields.Many2one('res.users', string='مستخدم التطبيق', tracking=True,
                              help='حساب الدخول لهذا العضو في التطبيق — يحدّد شاشته وصلاحياته.')
    phone = fields.Char(string='الهاتف')
    role = fields.Selection([
        ('worker', 'عامل / عضو فريق'),
        ('team_leader', 'قائد فريق'),
        ('supervisor', 'مشرف'),
        ('driver', 'سائق'),
        ('ops_manager', 'مدير العمليات'),
    ], string='الدور الوظيفي', default='worker', required=True, tracking=True)
    leader_id = fields.Many2one('c2c.provider', string='قائد الفريق',
                                domain="[('role','in',('team_leader','supervisor'))]")
    supervisor_id = fields.Many2one('c2c.provider', string='المشرف',
                                    domain="[('role','in',('supervisor','ops_manager'))]")
    team_member_ids = fields.One2many('c2c.provider', 'leader_id', string='أعضاء الفريق')
    team_size = fields.Integer(string='عدد الفريق', compute='_compute_stats')
    category_ids = fields.Many2many('c2c.category', string='الفئات المؤهّل لها')
    image = fields.Image(string='صورة', max_width=512, max_height=512)
    booking_ids = fields.One2many('c2c.booking', 'provider_id', string='الحجوزات')
    booking_count = fields.Integer(compute='_compute_stats')
    rating_avg = fields.Float(string='متوسط التقييم', compute='_compute_stats')
    available = fields.Boolean(string='متاح', default=True, tracking=True)
    active = fields.Boolean(default=True)

    # role → capabilities (used by the app + API to gate actions/screens)
    _CAPS = {
        'worker': {'scope': 'own', 'can': ['view', 'start', 'complete', 'proof']},
        'team_leader': {'scope': 'team', 'can': ['view', 'start', 'complete', 'proof', 'assign', 'quality']},
        'supervisor': {'scope': 'area', 'can': ['view', 'assign', 'quality', 'approve', 'reassign', 'analytics']},
        'driver': {'scope': 'own', 'can': ['view', 'route', 'arrive', 'proof']},
        'ops_manager': {'scope': 'all', 'can': ['view', 'assign', 'reassign', 'approve', 'schedule', 'manage_team', 'analytics', 'catalog']},
    }

    def capabilities(self):
        self.ensure_one()
        return self._CAPS.get(self.role, self._CAPS['worker'])

    @api.depends('booking_ids', 'booking_ids.rating', 'team_member_ids')
    def _compute_stats(self):
        for p in self:
            p.booking_count = len(p.booking_ids)
            p.team_size = len(p.team_member_ids)
            rated = p.booking_ids.filtered(lambda b: b.rating)
            p.rating_avg = round(sum(int(b.rating) for b in rated) / len(rated), 1) if rated else 0.0

    @api.depends('booking_ids', 'booking_ids.rating')
    def _compute_stats(self):
        for p in self:
            p.booking_count = len(p.booking_ids)
            rated = p.booking_ids.filtered(lambda b: b.rating)
            p.rating_avg = round(sum(int(b.rating) for b in rated) / len(rated), 1) if rated else 0.0
