# -*- coding: utf-8 -*-
"""Service Level Agreements (اتفاقية الخدمة SLA): per-priority response and
resolution targets, optionally scoped to a facility and/or service. When a work
order is created, the most specific matching policy sets its SLA (resolution)
hours — which drives the deadline and the escalation cron."""
from odoo import fields, models, api, _


class CafmSLA(models.Model):
    _name = 'care.cafm.sla'
    _description = 'CAFM Service Level Agreement'
    _inherit = ['mail.thread']
    _order = 'facility_id, service_id, id'

    name = fields.Char(string='الاتفاقية', required=True, tracking=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', tracking=True,
                                  help='اتركه فارغاً ليسري على كل المرافق.')
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', tracking=True,
                                 help='اتركه فارغاً ليسري على كل الخدمات.')
    partner_id = fields.Many2one(related='facility_id.partner_id', store=True, string='العميل')
    active = fields.Boolean(default=True, tracking=True)
    line_ids = fields.One2many('care.cafm.sla.line', 'sla_id', string='المستويات')
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model
    def resolution_hours_for(self, facility, service, priority):
        """Return the resolution-hours target for the most specific active
        policy matching (facility, service, priority) — or None."""
        Line = self.env['care.cafm.sla.line'].sudo()
        best = None
        for line in Line.search([('priority', '=', priority), ('sla_id.active', '=', True)]):
            s = line.sla_id
            if s.facility_id and s.facility_id != facility:
                continue
            if s.service_id and s.service_id != service:
                continue
            score = (2 if s.facility_id else 0) + (1 if s.service_id else 0)
            if best is None or score > best[0]:
                best = (score, line.resolution_hours)
        return best[1] if best else None


class CafmSLALine(models.Model):
    _name = 'care.cafm.sla.line'
    _description = 'CAFM SLA Level'
    _order = 'priority desc'

    sla_id = fields.Many2one('care.cafm.sla', required=True, ondelete='cascade')
    priority = fields.Selection([
        ('0', 'عادية'), ('1', 'متوسطة'), ('2', 'عالية'), ('3', 'عاجلة'),
    ], string='الأولوية', default='1', required=True)
    response_hours = fields.Float(string='زمن الاستجابة (ساعات)', default=4.0)
    resolution_hours = fields.Float(string='زمن الإنجاز (ساعات)', default=24.0)
