from odoo import models, fields, _
from odoo.exceptions import ValidationError


class RequestInvoiceWizard(models.TransientModel):
    
    _name = 'request.invoice.refusal.wizard'
    
    text = fields.Text(required=True)

    def action_refuse(self):
        order = self.env['request.invoice'].browse(self.env.context['active_id'])
        msg = _('The Order could not be Approved for the following reason: %s'%self.text)
        order.message_post(body=msg)
        order._action_refuse()
        