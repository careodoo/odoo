# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrEmployee(models.Model):
    """Give every employee a CAFM dashboard, pulled from the Employees app and
    linked to their user account — so a supervisor opens a worker and sees their
    live task load."""
    _inherit = 'hr.employee'

    cafm_workorder_count = fields.Integer(compute='_compute_cafm_wo', string='مهام CAFM')
    cafm_open_count = fields.Integer(compute='_compute_cafm_wo', string='مهام مفتوحة')
    cafm_overdue_count = fields.Integer(compute='_compute_cafm_wo', string='متأخرة')
    cafm_done_count = fields.Integer(compute='_compute_cafm_wo', string='منجزة')
    cafm_service_types = fields.Char(compute='_compute_cafm_wo', string='الخدمات')

    def _compute_cafm_wo(self):
        WO = self.env['care.cafm.workorder']
        type_lbl = dict(self.env['care.cafm.service']._fields['service_type'].selection)
        for e in self:
            wos = WO.search([('employee_id', '=', e.id)])
            e.cafm_workorder_count = len(wos)
            e.cafm_open_count = len(wos.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled')))
            e.cafm_overdue_count = len(wos.filtered('is_overdue'))
            e.cafm_done_count = len(wos.filtered(lambda w: w.state in ('done', 'verified')))
            types = sorted(set(w.service_type for w in wos if w.service_type))
            e.cafm_service_types = ' · '.join(type_lbl.get(t, t) for t in types) or '—'

    def action_view_cafm_workorders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مهام %s') % self.name,
            'res_model': 'care.cafm.workorder',
            'view_mode': 'kanban,tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id, 'search_default_group_state': 1},
        }
