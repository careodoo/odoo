from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class TrainingApplication(models.Model):
    _name = 'training.application'
    _description = 'Training Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    line_ids = fields.One2many('training.application.line', 'application_id')
    employee_id = fields.Many2one('hr.employee', required=True)
    application_name = fields.Char(required=True)
    training_name = fields.Char(required=True)
    responsible_id = fields.Many2one('hr.employee', required=True)
    project_id = fields.Many2one('project.project', required=True)
    task_ids = fields.One2many('project.task', 'application_id', string='Tasks')
    task_count = fields.Integer(compute='compute_task_count', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True, string='Create Date')
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    description = fields.Text()
    stage_id = fields.Many2one('application.stage', default=lambda self: self.get_default_stage())
    is_approved = fields.Boolean(related='stage_id.is_approved', store=True)
    is_completed = fields.Boolean(related='stage_id.is_completed', store=True)
    sign = fields.Binary()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    def print_certificate(self):
        return self.env.ref('training_management.training_certification_report').report_action(self)

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_start > rec.date_end:
                    raise ValidationError("Start Date must be before End Date!")

    def get_default_stage(self):
        stage = self.env['application.stage'].search([('is_default', '=', True)], limit=1)
        return stage.id if stage else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('training.application') or _('New')
        return super(TrainingApplication, self).create(vals_list)

    @api.depends('task_ids')
    def compute_task_count(self):
        for app in self:
            app.task_count = 0
            if app.task_ids:
                app.task_count = len(app.task_ids)

    def button_create_tasks(self):
        if not self.line_ids:
            raise ValidationError("please add training first!")
        for line in self.line_ids:
            for content in line.content_ids:
                self.env['project.task'].sudo().create({
                    'project_id': line.project_id.id,
                    'name': line.application_id.name + '-' + line.course_id.name,
                    'user_ids': line.responsible_id.user_id.ids,
                    'date_deadline': line.date_end,
                    'description': line.description,
                    'application_id': line.application_id.id,
                    'application_line_id': line.id,
                    'content_id': content.id,
                })

    def action_view_tasks(self):
        return {
            'name': _('Application Tasks'),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form,calendar,pivot,graph,activity',
            'res_model': 'project.task',
            'domain': [('application_id', '=', self.id)],
            'target': 'current',
        }


class TrainingApplicationLine(models.Model):
    _name = 'training.application.line'
    _description = 'Training Application Line'
    _rec_name = 'application_id'

    application_id = fields.Many2one('training.application', string='Number')
    employee_id = fields.Many2one('hr.employee', related='application_id.employee_id', store=True)
    responsible_id = fields.Many2one('hr.employee', related='application_id.responsible_id', store=True)
    project_id = fields.Many2one('project.project', related='application_id.project_id', store=True)
    date = fields.Date(related='application_id.date', store=True)
    course_id = fields.Many2one('slide.channel', required=True)
    content_ids = fields.Many2many('slide.slide', required=True, string='Subjects',
                                   domain="[('channel_id', '=', course_id)]")
    description = fields.Text()
    training_center_id = fields.Many2one('training.center')
    training_room_id = fields.Many2one('training.room', string='Class Room',
                                       domain="[('center_id', '=', training_center_id)]")
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_start > rec.date_end:
                    raise ValidationError("Start Date must be before End Date!")
