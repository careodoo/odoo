# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareRecruitmentAgency(models.Model):
    _name = 'care.recruitment.agency'
    _description = 'Recruitment Agency'
    _inherit = ['mail.thread']
    _order = 'score desc, name'

    name = fields.Char(string='الوكالة', required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='الدولة')
    partner_id = fields.Many2one('res.partner', string='جهة الاتصال')
    phone = fields.Char()
    email = fields.Char()
    active = fields.Boolean(default=True)

    supply_ids = fields.One2many('care.agency.supply', 'agency_id', string='دفعات الاستقدام')
    # aggregated KPIs
    total_supplied = fields.Integer(compute='_compute_kpis', store=True, string='إجمالي المستقدَمين')
    total_arrived = fields.Integer(compute='_compute_kpis', store=True, string='الواصلون')
    total_absconded = fields.Integer(compute='_compute_kpis', store=True, string='الهاربون')
    total_rejected = fields.Integer(compute='_compute_kpis', store=True, string='المرفوضون')
    retention_rate = fields.Float(compute='_compute_kpis', store=True, string='معدل البقاء %')
    absconding_rate = fields.Float(compute='_compute_kpis', store=True, string='معدل الهروب %')
    score = fields.Float(compute='_compute_kpis', store=True, string='التقييم (0-100)')
    rating = fields.Selection([
        ('a', 'ممتازة (A)'), ('b', 'جيدة (B)'), ('c', 'مقبولة (C)'), ('d', 'ضعيفة (D)'),
    ], compute='_compute_kpis', store=True, string='التصنيف')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('supply_ids', 'supply_ids.qty', 'supply_ids.arrived',
                 'supply_ids.absconded', 'supply_ids.rejected')
    def _compute_kpis(self):
        for a in self:
            sup = a.supply_ids
            a.total_supplied = sum(sup.mapped('qty'))
            a.total_arrived = sum(sup.mapped('arrived'))
            a.total_absconded = sum(sup.mapped('absconded'))
            a.total_rejected = sum(sup.mapped('rejected'))
            base = a.total_supplied or 0
            a.retention_rate = (100.0 * (a.total_arrived - a.total_absconded) / base) if base else 0.0
            a.absconding_rate = (100.0 * a.total_absconded / base) if base else 0.0
            reject_rate = (100.0 * a.total_rejected / base) if base else 0.0
            # score = retention weighted, penalised by absconding + rejection
            a.score = max(0.0, min(100.0, a.retention_rate - a.absconding_rate - 0.5 * reject_rate))
            a.rating = ('a' if a.score >= 85 else 'b' if a.score >= 70
                        else 'c' if a.score >= 50 else 'd')


class CareAgencySupply(models.Model):
    _name = 'care.agency.supply'
    _description = 'Agency Supply Batch'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    agency_id = fields.Many2one('care.recruitment.agency', string='الوكالة', required=True, tracking=True)
    date = fields.Date(string='تاريخ الدفعة', default=fields.Date.context_today, required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='دولة الاستقدام')
    profession = fields.Char(string='المهنة')
    qty = fields.Integer(string='العدد المطلوب', required=True, tracking=True)
    arrived = fields.Integer(string='الواصلون', tracking=True)
    absconded = fields.Integer(string='الهاربون', tracking=True)
    rejected = fields.Integer(string='المرفوضون (طبياً/غيره)', tracking=True)
    cost = fields.Monetary(string='التكلفة الإجمالية', currency_field='currency_id')
    cost_per_worker = fields.Monetary(compute='_compute_cpw', store=True, currency_field='currency_id',
                                      string='تكلفة العامل')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    success_rate = fields.Float(compute='_compute_cpw', store=True, string='نسبة النجاح %')
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('cost', 'qty', 'arrived', 'absconded')
    def _compute_cpw(self):
        for r in self:
            r.cost_per_worker = (r.cost / r.qty) if r.qty else 0.0
            good = (r.arrived or 0) - (r.absconded or 0)
            r.success_rate = (100.0 * good / r.qty) if r.qty else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.agency.supply') or '/'
        return super().create(vals_list)
