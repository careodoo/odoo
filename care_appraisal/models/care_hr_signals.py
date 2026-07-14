# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

DONE_STATES = ('approved', 'done')


class CarePenalty(models.Model):
    _inherit = 'care.penalty'

    performance_logged = fields.Boolean(default=False, copy=False, index=True)

    def _evaluate_performance(self):
        Log = self.env['care.performance.log']
        pts = Log._get_param('penalty_points')
        for rec in self:
            if rec.performance_logged or rec.state not in DONE_STATES or not rec.employee_id:
                continue
            label = rec.penalty_type_id.name if 'penalty_type_id' in rec._fields and rec.penalty_type_id else _('Penalty')
            Log.record_event(rec.employee_id.id, pts, 'penalty',
                             '%s: %s' % (label, rec.name or ''),
                             res_model='care.penalty', res_id=rec.id, date=rec.date)
            rec.performance_logged = True

    @api.model
    def cron_scan_penalty_performance(self):
        self.search([('performance_logged', '=', False),
                     ('state', 'in', DONE_STATES)], limit=3000)._evaluate_performance()
        return True


class CareBonus(models.Model):
    _inherit = 'care.bonus'

    performance_logged = fields.Boolean(default=False, copy=False, index=True)

    def _evaluate_performance(self):
        Log = self.env['care.performance.log']
        pts = Log._get_param('bonus_points')
        for rec in self:
            if rec.performance_logged or rec.state not in DONE_STATES or not rec.employee_id:
                continue
            label = rec.bonus_type if 'bonus_type' in rec._fields and rec.bonus_type else _('Bonus')
            Log.record_event(rec.employee_id.id, pts, 'bonus',
                             '%s: %s' % (label, rec.name or ''),
                             res_model='care.bonus', res_id=rec.id, date=rec.date)
            rec.performance_logged = True

    @api.model
    def cron_scan_bonus_performance(self):
        self.search([('performance_logged', '=', False),
                     ('state', 'in', DONE_STATES)], limit=3000)._evaluate_performance()
        return True
