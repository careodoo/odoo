from odoo import fields, models, api
from odoo.exceptions import UserError


class FleetDamage(models.Model):
    _name = 'fleet.damage'
    _description = 'Fleet Damage'

    name = fields.Char(required=True)
    vehicle_id = fields.Many2one('fleet.vehicle')
    attachment_ids = fields.Many2many('ir.attachment', required=True)
    state = fields.Selection(selection=[
        ('fixed', 'Fixed'), ('not_fixed', 'Not Fixed'),
    ], default='not_fixed', required=True)
    state_description = fields.Text(required=True, string='Description')
    cause = fields.Char()

    @api.constrains('attachment_ids')
    def check_attachments(self):
        for rec in self:
            if not rec.attachment_ids:
                raise UserError("Please add attachments!!")