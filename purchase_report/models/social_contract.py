from odoo import fields, models, api


class HRSocialContract(models.Model):
    _inherit = 'hr.social.contracts'

    work_department = fields.Char()
    work_department_eng = fields.Char()
