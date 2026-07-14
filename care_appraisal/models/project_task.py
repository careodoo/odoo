# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    performance_logged = fields.Boolean(default=False, copy=False, index=True,
                                        help='Performance impact already recorded for this task.')

    def _evaluate_performance(self):
        """Log an on-time / overdue performance event for each assignee when a task is done."""
        Log = self.env['care.performance.log']
        ontime_pts = Log._get_param('task_ontime')
        overdue_pts = Log._get_param('task_overdue')
        for task in self:
            if task.performance_logged:
                continue
            if not (task.stage_id and task.stage_id.fold):
                continue
            employees = task.user_ids.employee_id
            if not employees:
                task.performance_logged = True
                continue
            if not task.date_deadline:
                # no deadline -> no delay signal, still mark handled
                task.performance_logged = True
                continue
            completion_dt = task.date_last_stage_update or fields.Datetime.now()
            deadline = task.date_deadline
            # date_deadline may be a Date or Datetime depending on customization
            if hasattr(deadline, 'hour'):
                on_time = completion_dt <= deadline
            else:
                on_time = completion_dt.date() <= deadline
            pts = ontime_pts if on_time else overdue_pts
            label = _('On-time') if on_time else _('Overdue')
            for emp in employees:
                Log.record_event(
                    emp.id, pts, 'task',
                    '%s: %s' % (label, task.name or ''),
                    res_model='project.task', res_id=task.id,
                    date=completion_dt.date())
            task.performance_logged = True

    @api.model
    def cron_scan_task_performance(self):
        tasks = self.search([('performance_logged', '=', False),
                             ('stage_id.fold', '=', True)], limit=2000)
        tasks._evaluate_performance()
        return True
