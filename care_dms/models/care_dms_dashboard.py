# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareDmsDashboard(models.Model):
    """Single landing screen for the document repository (mockup 90)."""
    _name = 'care.dms.dashboard'
    _description = 'DMS Dashboard'

    name = fields.Char(default='DMS')
    total_docs = fields.Integer(compute='_compute_kpis')
    classified_pct = fields.Float(string='مصنّفة/مفهرسة %', compute='_compute_kpis')
    expiring_count = fields.Integer(compute='_compute_kpis')
    due_disposal_count = fields.Integer(compute='_compute_kpis')
    legal_hold_count = fields.Integer(compute='_compute_kpis')
    category_count = fields.Integer(compute='_compute_kpis')

    def _compute_kpis(self):
        Doc = self.env['care.dms.document']
        for rec in self:
            total = Doc.search_count([('disposed', '=', False)])
            indexed = Doc.search_count([('disposed', '=', False), ('attachment_name', '!=', False)])
            rec.total_docs = total
            rec.classified_pct = round(indexed * 100.0 / total, 1) if total else 0.0
            rec.expiring_count = Doc.search_count([('state', '=', 'expiring')])
            rec.due_disposal_count = Doc.search_count([('state', '=', 'due_disposal')])
            rec.legal_hold_count = Doc.search_count([('state', '=', 'legal_hold')])
            rec.category_count = self.env['care.dms.category'].search_count([])

    def _open_docs(self, name, domain):
        return {
            'type': 'ir.actions.act_window', 'name': name,
            'res_model': 'care.dms.document', 'view_mode': 'tree,kanban,form',
            'domain': domain,
        }

    def action_open_all(self):
        return self._open_docs(_('كل الوثائق'), [('disposed', '=', False)])

    def action_open_expiring(self):
        return self._open_docs(_('تقترب من الإتلاف'), [('state', '=', 'expiring')])

    def action_open_due(self):
        return self._open_docs(_('مستحقة الإتلاف'), [('state', '=', 'due_disposal')])

    def action_open_hold(self):
        return self._open_docs(_('محجوزة قانونياً'), [('state', '=', 'legal_hold')])

    def action_open_categories(self):
        return self.env['ir.actions.act_window']._for_xml_id('care_dms.action_care_dms_category')
