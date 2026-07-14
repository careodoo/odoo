# -*- coding: utf-8 -*-
from odoo import fields, models, tools, _


class LetterDelegateStat(models.Model):
    _name = 'letter.delegate.stat'
    _description = 'Delegate Performance'
    _auto = False
    _order = 'overdue_count desc, current_count desc, total desc'

    delegate_id = fields.Many2one('hr.employee', string='Delegate', readonly=True)
    total = fields.Integer(string='Total', readonly=True)
    current_count = fields.Integer(string='With Delegate', readonly=True)
    overdue_count = fields.Integer(string='Overdue', readonly=True)
    delivered_count = fields.Integer(string='Delivered', readonly=True)
    avg_days = fields.Float(string='Avg Days', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (
                SELECT emp.id AS id,
                       emp.id AS delegate_id,
                       COUNT(lf.id) AS total,
                       COUNT(lf.id) FILTER (WHERE lf.letter_state = 'with_delegate') AS current_count,
                       COUNT(lf.id) FILTER (WHERE lf.is_overdue) AS overdue_count,
                       COUNT(lf.id) FILTER (WHERE lf.letter_state IN ('delivered','acknowledged','archived')) AS delivered_count,
                       COALESCE(ROUND(AVG(lf.days_with_delegate)
                                FILTER (WHERE lf.delegate_handover_date IS NOT NULL)::numeric, 1), 0) AS avg_days
                FROM hr_employee emp
                JOIN letter_file lf ON lf.delegate_id = emp.id
                GROUP BY emp.id
            )
        """ % self._table)

    def _open(self, extra_domain, name):
        self.ensure_one()
        domain = [('delegate_id', '=', self.delegate_id.id)] + extra_domain
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'letter.file',
            'view_mode': 'tree,kanban,form',
            'domain': domain,
            'target': 'current',
        }

    def action_open_all(self):
        return self._open([], _('كتب %s') % (self.delegate_id.name or ''))

    def action_open_current(self):
        return self._open([('letter_state', '=', 'with_delegate')], _('مع المندوب — %s') % (self.delegate_id.name or ''))

    def action_open_overdue(self):
        return self._open([('is_overdue', '=', True)], _('متأخرات %s') % (self.delegate_id.name or ''))

    def action_open_delivered(self):
        return self._open([('letter_state', 'in', ['delivered', 'acknowledged', 'archived'])],
                          _('مُسلَّم — %s') % (self.delegate_id.name or ''))
