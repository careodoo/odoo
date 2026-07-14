# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    team_perf_score = fields.Float(compute='_compute_team_performance', string='Team Performance (YTD)')
    team_perf_count = fields.Integer(compute='_compute_team_performance', string='Team Performance Events')

    def _team_employees(self):
        """Team = department employees (if care_pms department set) else task assignees."""
        self.ensure_one()
        if 'pms_department_id' in self._fields and self.pms_department_id:
            return self.env['hr.employee'].sudo().search(
                [('department_id', '=', self.pms_department_id.id)])
        users = self.env['project.task'].sudo().search([('project_id', '=', self.id)]).user_ids
        return users.employee_id

    def _compute_team_performance(self):
        Log = self.env['care.performance.log'].sudo()
        year_start = fields.Date.today().replace(month=1, day=1)
        for project in self:
            emps = project._team_employees()
            if not emps:
                project.team_perf_score = 0.0
                project.team_perf_count = 0
                continue
            logs = Log.search([('employee_id', 'in', emps.ids), ('date', '>=', year_start)])
            project.team_perf_score = sum(logs.mapped('points'))
            project.team_perf_count = len(logs)

    def action_view_team_performance(self):
        self.ensure_one()
        emps = self._team_employees()
        return {
            'type': 'ir.actions.act_window',
            'name': _('أداء فريق %s') % (self.name or ''),
            'res_model': 'care.performance.log',
            'view_mode': 'pivot,graph,tree,form',
            'domain': [('employee_id', 'in', emps.ids)],
            'context': {'search_default_group_employee': 1},
        }
