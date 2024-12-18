from odoo import fields, models, api


class TaskForward(models.Model):
    _name = 'project.task.forward'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Task Forward'

    task_id = fields.Many2one('project.task', required=True)
    user_id = fields.Many2one('res.users', required=True)
    confirm_date = fields.Datetime()
    project_id = fields.Many2one('project.project', related='task_id.project_id', store=True)
    name = fields.Char(related='task_id.name', store=True)
    date_deadline = fields.Datetime(related='task_id.date_deadline', store=True)
    stage_id = fields.Many2one('project.task.type', related='task_id.stage_id', store=True, string='Task Stage')
    active = fields.Boolean(default=True)
    original_user = fields.Boolean()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')
    ], default='draft', string='Forward Status')

    @api.model
    def create(self, vals):
        res = super(TaskForward, self).create(vals)
        res.sudo().activity_schedule(
            'care_task.mail_act_task_forward_create',
            summary='Task Forward',
            note='Ask To Confirm Task Forward',
            user_id=res.user_id.id)
        return res

    def button_confirm_forward(self):
        # if user confirm, delete the previous forwarder if not added manually
        if self.user_id.id in self.task_id.user_ids.ids:
            self.original_user = True
        # remove old users from assign after another user confirm forward
        old_users = self.task_id.sudo().forward_ids.filtered(lambda f: not f.original_user and f.state == 'confirmed').mapped('user_id')
        for u in old_users:
            self.task_id.sudo().write({
                'user_ids': [(3, u.id)]
            })
        self.state = 'confirmed'
        self.confirm_date = fields.Datetime.now()
        self.task_id.sudo().write({
            'user_ids': [(4, self.user_id.id)]
        })

    def button_reject_forward(self):
        self.state = 'rejected'
