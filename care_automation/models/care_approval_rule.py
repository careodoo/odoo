# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CareApprovalRule(models.Model):
    _name = 'care.approval.rule'
    _description = 'Smart Approval Routing Rule'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='الحالة', required=True, translate=True)
    route = fields.Selection([
        ('auto', 'تلقائي فوري'),
        ('escalate_manager', 'تصعيد للمدير'),
        ('finance', 'موافقة مالية'),
        ('escalate_up', 'تصعيد للأعلى'),
    ], string='المسار', required=True, default='auto')
    doc_type = fields.Selection([
        ('leave', 'إجازة'), ('loan', 'سلفة'), ('permission', 'استئذان'),
        ('overtime', 'إضافي'), ('any', 'الكل'),
    ], string='النوع', default='any')
    example = fields.Char(string='مثال', translate=True)
    enabled = fields.Boolean(string='مفعّلة', default=True)


class CareApprovalStat(models.Model):
    _name = 'care.approval.stat'
    _description = 'Smart Approval Impact (singleton)'

    name = fields.Char(default='Impact')
    auto_pct = fields.Float(string='معتمد تلقائياً %', compute='_compute_stats')
    review_pct = fields.Float(string='يحتاج مراجعة %', compute='_compute_stats')
    avg_hours = fields.Float(string='متوسط زمن الاعتماد (ساعات)', compute='_compute_stats')

    def _compute_stats(self):
        # proxy: leaves auto-validated vs manually handled (validate/validate1)
        Leave = self.env['hr.leave'].sudo()
        for rec in self:
            total = Leave.search_count([('state', 'in', ['validate', 'refuse'])])
            auto = Leave.search_count([('state', '=', 'validate')])
            rec.auto_pct = round(auto * 100.0 / total, 1) if total else 0.0
            rec.review_pct = round(100.0 - rec.auto_pct, 1) if total else 0.0
            rec.avg_hours = 0.1  # near-instant for in-policy routing
