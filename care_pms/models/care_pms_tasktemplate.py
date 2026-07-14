# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _


class CarePmsTaskTemplate(models.Model):
    _name = 'care.pms.task.template'
    _description = 'Recurring Task Template'
    _order = 'next_date, id'

    name = fields.Char(string='Title', required=True)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    pms_category_id = fields.Many2one('care.task.category', string='Category')
    task_kind = fields.Selection(
        [('task', 'Task'), ('memo', 'Memo'), ('internal_letter', 'Internal Letter'),
         ('internal_request', 'Internal Request'), ('correspondence', 'Correspondence')],
        string='Kind', default='task')
    user_ids = fields.Many2many('res.users', string='Assignees')
    description = fields.Text(string='Description')
    interval_number = fields.Integer(string='Every', default=1, required=True)
    interval_type = fields.Selection(
        [('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        string='Interval', default='days', required=True)
    next_date = fields.Date(string='Next Run', default=fields.Date.today, required=True)
    deadline_offset = fields.Integer(string='Deadline (+days)', default=1)
    generated_count = fields.Integer(string='Generated', default=0, readonly=True)

    def _advance(self):
        self.ensure_one()
        kw = {self.interval_type: self.interval_number}
        self.next_date = fields.Date.to_string(self.next_date + relativedelta(**kw))

    def action_generate_now(self):
        for tpl in self:
            tpl._generate_task()
        return True

    def _generate_task(self):
        self.ensure_one()
        deadline = fields.Datetime.now() + relativedelta(days=self.deadline_offset or 0)
        vals = {
            'name': self.name,
            'project_id': self.project_id.id,
            'task_kind': self.task_kind,
            'pms_category_id': self.pms_category_id.id,
            'pms_department_id': self.project_id.pms_department_id.id,
            'description': self.description,
            'date_deadline': deadline,
        }
        if self.user_ids:
            vals['user_ids'] = [(6, 0, self.user_ids.ids)]
        task = self.env['project.task'].create(vals)
        self.generated_count += 1
        return task

    @api.model
    def cron_generate_recurring(self):
        today = fields.Date.today()
        due = self.search([('next_date', '<=', today)])
        for tpl in due:
            tpl._generate_task()
            tpl._advance()
        return True
