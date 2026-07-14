# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CareTaskCategory(models.Model):
    _name = 'care.task.category'
    _description = 'Task Category / Item'
    _order = 'sequence, id'

    name = fields.Char(string='Category', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
    task_count = fields.Integer(compute='_compute_task_count')

    def _compute_task_count(self):
        data = self.env['project.task'].read_group(
            [('pms_category_id', 'in', self.ids)], ['pms_category_id'], ['pms_category_id'])
        mapped = {d['pms_category_id'][0]: d['pms_category_id_count'] for d in data}
        for rec in self:
            rec.task_count = mapped.get(rec.id, 0)


class CareTaskGroup(models.Model):
    _name = 'care.task.group'
    _description = 'Department Private Task Group'
    _order = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Group', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    manager_id = fields.Many2one('res.users', string='Manager',
                                 default=lambda s: s.env.user, tracking=True)
    member_ids = fields.Many2many('res.users', string='Members')
    is_private = fields.Boolean(string='Private (members only)', default=True)
    color = fields.Integer(string='Color')
    task_ids = fields.One2many('project.task', 'task_group_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count')
    overdue_count = fields.Integer(compute='_compute_task_count')

    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)
            rec.overdue_count = len(rec.task_ids.filtered('is_overdue'))

    def action_open_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'project.task',
            'view_mode': 'kanban,tree,form',
            'domain': [('task_group_id', '=', self.id)],
            'context': {'default_task_group_id': self.id},
        }


class CareTaskForward(models.Model):
    _name = 'care.task.forward'
    _description = 'Task Forward Log'
    _order = 'forward_date desc, id desc'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    active = fields.Boolean(default=True)
    from_user_id = fields.Many2one('res.users', string='From', default=lambda s: s.env.user)
    to_user_id = fields.Many2one('res.users', string='To', required=True)
    reason = fields.Text(string='Reason')
    state = fields.Selection(
        [('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        string='Status', default='pending', index=True)
    response_reason = fields.Text(string='Response')
    forward_date = fields.Datetime(string='Forwarded On', default=fields.Datetime.now)
    response_date = fields.Datetime(string='Responded On')
