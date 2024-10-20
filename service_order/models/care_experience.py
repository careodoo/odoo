from odoo import _, api, fields, models

class CareExperience(models.Model):
  _inherit = 'care.experience'

  x_studio_contract_no = fields.Char(string='Contract No')