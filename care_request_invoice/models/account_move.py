from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one('project.project', string='Project')
    department_id = fields.Many2one('hr.department', string='Department')
    request_invoice = fields.Many2one('request.invoice', string='Request Invoice')