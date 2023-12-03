from odoo import fields, models, api


class ApplicationStage(models.Model):
    _name = 'application.stage'
    _description = 'Application Stage'

    name = fields.Char(required=True)
    is_default = fields.Boolean(string='Default Stage')
    is_draft = fields.Boolean(string='Is Draft?')
    is_approved = fields.Boolean(string='Is Approved?')
    is_completed = fields.Boolean(string='Is Completed?')
    is_cancelled = fields.Boolean(string='Is Cancelled?')
