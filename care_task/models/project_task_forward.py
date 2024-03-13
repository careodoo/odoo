from odoo import fields, models, api


class TaskForward(models.Model):
    _name = 'project.task.forward'
    _description = 'Task Forward'

    task_id = fields.Many2one('project.task', required=True)
    user_id = fields.Many2one('res.users', required=True)
    confirm_date = fields.Datetime()
    project_id = fields.Many2one('project.project', related='task_id.project_id', store=True)
    name = fields.Char(related='task_id.name', store=True)
    date_deadline = fields.Date(related='task_id.date_deadline', store=True)
    stage_id = fields.Many2one('project.task.type', related='task_id.stage_id', store=True, string='Task Stage')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')
    ], default='draft', string='Forward Status')

    def button_confirm_forward(self):
        self.state = 'confirmed'
        self.confirm_date = fields.Datetime.now()
        self.task_id.sudo().write({
            'user_ids': [(4, self.user_id.id)]
        })

    def button_reject_forward(self):
        self.state = 'rejected'
