# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareSuccession(models.Model):
    _name = 'care.succession'
    _description = 'Succession Plan'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='المنصب/الدور الحرج', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='القسم/المشروع', tracking=True)
    job_id = fields.Many2one('hr.job', string='الوظيفة')
    incumbent_id = fields.Many2one('hr.employee', string='الشاغل الحالي', tracking=True)
    risk = fields.Selection([
        ('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'عالٍ'),
    ], string='خطورة الشغور', default='medium', tracking=True)
    successor_ids = fields.One2many('care.succession.candidate', 'succession_id', string='المرشحون للإحلال')
    candidate_count = fields.Integer(compute='_compute_cand', store=True)
    ready_now = fields.Boolean(compute='_compute_cand', store=True, string='يوجد بديل جاهز الآن')
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('successor_ids', 'successor_ids.readiness')
    def _compute_cand(self):
        for rec in self:
            rec.candidate_count = len(rec.successor_ids)
            rec.ready_now = any(c.readiness == 'ready' for c in rec.successor_ids)


class CareSuccessionCandidate(models.Model):
    _name = 'care.succession.candidate'
    _description = 'Succession Candidate'
    _order = 'readiness, id'

    succession_id = fields.Many2one('care.succession', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='المرشح', required=True)
    readiness = fields.Selection([
        ('ready', 'جاهز الآن'),
        ('1y', 'جاهز خلال سنة'),
        ('2y', 'جاهز خلال 2-3 سنوات'),
        ('development', 'يحتاج تطوير'),
    ], string='الجاهزية', default='development', required=True)
    note = fields.Char(string='ملاحظة/خطة التطوير')
