from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SecurityKeyLostWizard(models.TransientModel):
    _name = 'security.key.lost.wizard'
    _description = 'Key Lost Wizard'
    
    key_id = fields.Many2one('security.key', string='Key', required=True, readonly=True)
    key_name = fields.Char(related='key_id.name', string='Key Name', readonly=True)
    key_hub_id = fields.Many2one(related='key_id.key_hub_id', string='Key Hub', readonly=True)
    current_holder_id = fields.Many2one(related='key_id.current_holder_id', string='Current Holder', readonly=True)
    
    lost_date = fields.Date(string='Date Lost', required=True, default=fields.Date.context_today)
    reported_by_id = fields.Many2one('security.employee', string='Reported By', required=True, 
                                    default=lambda self: self.env['security.employee'].search([('employee_id', '=', self.env.user.employee_id.id)], limit=1).id or self.env['security.employee'].search([], limit=1).id)
    description = fields.Text(string='Description of Loss', required=True)
    location = fields.Char(string='Last Known Location')
    reason = fields.Text(string='Reason', required=True)
    
    def action_report_lost(self):
        """Mark the key as lost"""
        self.ensure_one()
        
        if not self.key_id:
            raise UserError(_("No key selected"))
            
        if self.key_id.state != 'checked_out':
            raise UserError(_("Only checked out keys can be reported as lost"))
            
        # Update key status
        self.key_id.write({
            'state': 'lost',
        })
        
        # Create key log
        self.env['security.key.log'].create({
            'key_id': self.key_id.id,
            'security_employee_id': self.reported_by_id.id,
            'operation': 'lost',
            'timestamp': fields.Datetime.now(),
            'reason': self.description,
        })
        
        # Create notification for security team
        user_ids = self.env.ref('security_management.group_security_manager').users.ids
        if user_ids:
            self.key_id.message_post(
                body=_("Key %s reported lost by %s. %s") % (
                    self.key_name, 
                    self.reported_by_id.name, 
                    self.description
                ),
                partner_ids=[(4, user.partner_id.id) for user in self.env['res.users'].browse(user_ids) if user.partner_id],
                message_type='notification',
                subtype='mail.mt_note',
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Key Reported Lost'),
                'message': _("The key %s has been reported as lost.") % self.key_name,
                'sticky': False,
                'type': 'warning',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    def action_mark_lost(self):
        self.key_id.write({'state': 'lost'})
        
        # Create key log
        self.env['security.key.log'].create({
            'key_id': self.key_id.id,
            'security_employee_id': self.reported_by_id.id,
            'operation': 'lost',
            'timestamp': fields.Datetime.now(),
            'reason': self.reason,
        })
                
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Key Marked as Lost'),
                'message': _("The key %s has been marked as lost.") % self.key_name,
                'sticky': False,
                'type': 'warning',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }