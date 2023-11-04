from odoo import fields, models, api


class ManpowerRequisition(models.Model):
    _name = 'manpower.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manpower Requisition'

    request_date = fields.Date(string='Date of Request')
    manager_id = fields.Many2one('hr.employee', string='Requesting Manager')
    location = fields.Char()
    required_title = fields.Char(string='Title of position required')
    requirement_number = fields.Integer(string='No of Requirements')
    type = fields.Selection(selection=[
        ('overseas', 'Overseas'), ('local', 'Local')
    ], required=True, string='Overseas / Local')
    # reasons
    leaving_employee_id = fields.Many2one('hr.employee', string='Employee Leaving')
    resignation_date = fields.Date(string='Resignation submitted on')
    transferred_employee_id = fields.Many2one('hr.employee', string='Employee being transferred')
    transfer_from = fields.Many2one('hr.department')
    transfer_to = fields.Many2one('hr.department')
    transfer_reason = fields.Char()
    project_id = fields.Many2one('project.project', string='Project Name')
    actual_headcount = fields.Integer()
    requirement_reason = fields.Text()
    specific_requirements = fields.Text()
    salary = fields.Float(string='Assigned salary for this requirements')
    working_hours = fields.Float()
