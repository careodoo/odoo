# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    perf_event_count = fields.Integer(compute='_compute_performance_kpi', string='Performance Events')
    perf_score_ytd = fields.Float(compute='_compute_performance_kpi', string='Performance (YTD)')

    def _compute_performance_kpi(self):
        Log = self.env['care.performance.log'].sudo()
        year_start = fields.Date.today().replace(month=1, day=1)
        for emp in self:
            logs = Log.search([('employee_id', '=', emp.id)])
            emp.perf_event_count = len(logs)
            emp.perf_score_ytd = sum(
                logs.filtered(lambda l: l.date and l.date >= year_start).mapped('points'))

    def get_performance_statement(self):
        """Data for the printable performance statement (year-to-date)."""
        self.ensure_one()
        Log = self.env['care.performance.log'].sudo()
        year_start = fields.Date.today().replace(month=1, day=1)
        logs = Log.search([('employee_id', '=', self.id), ('date', '>=', year_start)],
                          order='date, id')
        points = logs.mapped('points')
        total = sum(points)
        if not logs:
            rating = ''
        elif total >= 15:
            rating = 'ممتاز'
        elif total >= 5:
            rating = 'جيد'
        elif total >= -5:
            rating = 'مقبول'
        else:
            rating = 'يحتاج تحسين'
        return {
            'logs': logs,
            'total': total,
            'positive': sum(p for p in points if p > 0),
            'negative': sum(p for p in points if p < 0),
            'count': len(logs),
            'rating': rating,
            'year': year_start.year,
        }

    def action_view_performance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Performance Events'),
            'res_model': 'care.performance.log',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'search_default_group_source': 1, 'default_employee_id': self.id},
        }
