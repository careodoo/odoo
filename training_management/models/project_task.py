from odoo import fields, models, api


class Task(models.Model):
    _inherit = 'project.task'

    application_id = fields.Many2one('training.application')
    application_line_id = fields.Many2one('training.application.line')
    application_employee_id = fields.Many2one('hr.employee', related='application_id.employee_id', store=True)
    course_id = fields.Many2one('slide.channel', related='application_line_id.course_id', store=True)
    content_id = fields.Many2one('slide.slide')
    date_start = fields.Date(string='Training Start Date', related='application_line_id.date_start', store=True)
    date_end = fields.Date(string='Training End Date', related='application_line_id.date_start', store=True)
