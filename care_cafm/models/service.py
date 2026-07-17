# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


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
        ('other', 'أخرى'),
    ], string='نوع الخدمة', required=True, default='cleaning')
    default_sla_hours = fields.Float(string='SLA الافتراضي (ساعات)', default=4.0)
    color = fields.Integer(string='لون')
    icon = fields.Char(string='أيقونة', default='🧹',
                       help='إيموجي يمثّل الخدمة في تطبيق الموبايل.')
    active = fields.Boolean(default=True)

    team_ids = fields.One2many('care.cafm.team', 'service_id', string='الفِرَق')
    workorder_count = fields.Integer(compute='_compute_counts')
    team_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        WO = self.env['care.cafm.workorder']
        for rec in self:
            rec.workorder_count = WO.search_count([('service_id', '=', rec.id)])
            rec.team_count = len(rec.team_ids)

    _sql_constraints = [('code_uniq', 'unique(code)', 'رمز الخدمة يجب أن يكون فريداً.')]
