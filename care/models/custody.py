# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class Custody(models.Model):
    _name = 'custody'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name         = fields.Char(string='Name', track_visibility='onchange', compute='compute_name')
    custody_name = fields.Char(string='Name', required=True)
    partner_id   = fields.Many2one('res.partner', string='Contact', required=True, track_visibility='onchange')
    date_time    = fields.Datetime(string='Date & Time', required=True, track_visibility='onchange')
    amount       = fields.Float(string='Amount', required=True, track_visibility='onchange')
    total_cost   = fields.Float(string='Service Cost', compute='compute_total_cost', store=True)
    purchase_cost   = fields.Float(compute='compute_purchase_cost', store=True)
    estimated    = fields.Float(string='Estimated', compute='compute_estimated', store=True)
    is_active    = fields.Boolean(string='Active', default=True, compute='compute_is_active', store=True)
    service_line = fields.One2many('fleet.vehicle.log.services', 'custody_id', string="Service Line", track_visibility='onchange', readonly=True)
    purchase_ids = fields.One2many('purchase.order', 'custody')
    purchase_count = fields.Integer(compute='compute_purchase_count')
    service_count = fields.Integer(compute='compute_service_count')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.depends('purchase_ids')
    def compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_ids)

    @api.depends('purchase_ids')
    def compute_purchase_cost(self):
        for rec in self:
            rec.purchase_cost = sum([rec.amount_total for rec in rec.purchase_ids])

    @api.depends('service_line')
    def compute_service_count(self):
        for rec in self:
            rec.service_count = len(rec.service_line)

    def purchasing_custody_action(self):
        return {
            'name': _('Purchasing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'purchase.order',
            'domain': [('from_custody', '=', True), ('custody', '=', self.id)],
            'target': 'current',
        }

    def service_custody_action(self):
        return {
            'name': _('Services'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'fleet.vehicle.log.services',
            'domain': [('custody_id', '=', self.id)],
            'target': 'current',
        }

    def compute_name(self):
        for record in self:
            record.name = record.custody_name + " / " + str(record.date_time.date()) + " / " + str(record.amount)

    def compute_total_cost(self):
        for record in self:
            record.total_cost = total_cost = 0
            for line in record.service_line:
                total_cost += line.total_cost

            record.total_cost = total_cost

    @api.depends('amount', 'total_cost', 'purchase_cost')
    def compute_estimated(self):
        for record in self:
            record.estimated = record.amount - record.total_cost - record.purchase_cost

    def action_is_active(self):
        self.is_active = not self.is_active

    @api.depends('estimated')
    def compute_is_active(self):
        for rec in self:
            rec.is_active = True if rec.estimated > 0 else False
