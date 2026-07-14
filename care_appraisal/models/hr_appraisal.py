# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    performance_log_ids = fields.One2many('care.performance.log', 'appraisal_id',
                                          string='Performance Events')
    performance_score = fields.Float(compute='_compute_performance', store=True,
                                     string='Performance Score')
    performance_positive = fields.Float(compute='_compute_performance', string='Rewards')
    performance_negative = fields.Float(compute='_compute_performance', string='Penalties')
    performance_task_score = fields.Float(compute='_compute_performance', string='Tasks Score')
    performance_attendance_score = fields.Float(compute='_compute_performance', string='Attendance Score')
    performance_event_count = fields.Integer(compute='_compute_performance', string='Events')
    performance_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('weak', 'Needs Improvement'),
    ], compute='_compute_performance', store=True, string='Auto Rating')

    @api.depends('performance_log_ids.points', 'performance_log_ids.source')
    def _compute_performance(self):
        for ap in self:
            logs = ap.performance_log_ids
            ap.performance_score = sum(logs.mapped('points'))
            ap.performance_positive = sum(p for p in logs.mapped('points') if p > 0)
            ap.performance_negative = sum(p for p in logs.mapped('points') if p < 0)
            ap.performance_task_score = sum(logs.filtered(lambda l: l.source == 'task').mapped('points'))
            ap.performance_attendance_score = sum(
                logs.filtered(lambda l: l.source == 'attendance').mapped('points'))
            ap.performance_event_count = len(logs)
            score = ap.performance_score
            if not logs:
                ap.performance_rating = False
            elif score >= 15:
                ap.performance_rating = 'excellent'
            elif score >= 5:
                ap.performance_rating = 'good'
            elif score >= -5:
                ap.performance_rating = 'fair'
            else:
                ap.performance_rating = 'weak'

    def action_confirm(self):
        res = super().action_confirm()
        self.filtered('employee_id').action_collect_performance()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'done':
            self.filtered('employee_id').action_collect_performance()
        return res

    def _performance_period(self):
        """(start_date or False, end_date) for this appraisal's employee."""
        self.ensure_one()
        prev = self.search([
            ('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
            ('create_date', '<', self.create_date),
        ], order='create_date desc', limit=1)
        start = prev.create_date.date() if prev else False
        end = self.date_close or fields.Date.context_today(self)
        return start, end

    def action_collect_performance(self):
        """Attach all unlinked performance events in this appraisal's period to it."""
        Log = self.env['care.performance.log']
        for ap in self:
            if not ap.employee_id:
                continue
            start, end = ap._performance_period()
            domain = [('employee_id', '=', ap.employee_id.id), ('appraisal_id', '=', False),
                      ('date', '<=', end)]
            if start:
                domain.append(('date', '>=', start))
            Log.sudo().search(domain).write({'appraisal_id': ap.id})
        return True

    def action_suggest_reward(self):
        """Propose a DRAFT performance bonus (for HR approval) when the score is high."""
        self.ensure_one()
        Log = self.env['care.performance.log']
        threshold = Log._get_param('reward_threshold')
        per_point = Log._get_param('reward_per_point')
        score = self.performance_score
        if score < threshold:
            raise UserError(_('نتيجة الأداء (%(s)s) أقل من حد استحقاق المكافأة التلقائية (%(t)s نقطة).')
                            % {'s': round(score, 1), 't': threshold})
        amount = round(score * per_point, 3)
        bonus = self.env['care.bonus'].create({
            'employee_id': self.employee_id.id,
            'bonus_type': 'performance',
            'amount': amount,
            'reason': _('اقتراح تلقائي بناءً على تقييم الأداء: %s نقطة') % round(score, 1),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('مكافأة أداء مقترحة'),
            'res_model': 'care.bonus',
            'res_id': bonus.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_performance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Performance Events'),
            'res_model': 'care.performance.log',
            'view_mode': 'tree,form',
            'domain': [('appraisal_id', '=', self.id)],
            'context': {'search_default_group_source': 1},
        }
