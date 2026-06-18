from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SecurityKeyCheckoutWizard(models.TransientModel):
    _name = 'security.key.checkout.wizard'
    _description = 'Key Checkout Wizard'
    
    key_id = fields.Many2one('security.key', string='Key', required=True, readonly=True)
    key_name = fields.Char(related='key_id.name', string='Key Name', readonly=True)
    key_hub_id = fields.Many2one(related='key_id.key_hub_id', string='Key Hub', readonly=True)
    unit_id = fields.Many2one(related='key_id.unit_id', string='Unit', readonly=True)
    
    security_employee_id = fields.Many2one('security.employee', string='Employee', required=True,
                                domain="[('id', 'in', allowed_security_employee_ids)]")
    allowed_security_employee_ids = fields.Many2many('security.employee', compute='_compute_allowed_employees')
    expected_return_time = fields.Datetime(string='Expected Return Time', required=True)
    reason = fields.Text(string='Purpose/Reason', required=True)
    
    @api.depends_context('uid')
    def _compute_allowed_employees(self):
        """Get employees that can check out keys"""
        # In a real implementation, you might want to filter based on permissions,
        # team membership, etc.
        security_employees = self.env['security.employee'].search([])
        for wizard in self:
            wizard.allowed_security_employee_ids = security_employees.ids
    
    @api.model
    def default_get(self, fields):
        res = super(SecurityKeyCheckoutWizard, self).default_get(fields)
        if self.env.context.get('active_model') == 'security.key' and self.env.context.get('active_id'):
            key = self.env['security.key'].browse(self.env.context.get('active_id'))
            if key.exists():
                res['key_id'] = key.id
                # Set default expected return time (e.g., 8 hours from now)
                import datetime
                res['expected_return_time'] = fields.Datetime.now() + datetime.timedelta(hours=8)
        return res
    
    def action_checkout(self):
        """Process key checkout"""
        self.ensure_one()
        
        if not self.key_id:
            raise UserError(_("No key selected for checkout"))
            
        if self.key_id.state != 'available':
            raise UserError(_("This key is not available for checkout"))
            
        # Update key status
        self.key_id.write({
            'state': 'checked_out',
            'current_holder_id': self.security_employee_id.employee_id.id,
            'check_out_time': fields.Datetime.now(),
            'expected_return_time': self.expected_return_time,
        })
        
        # Create key log
        self.env['security.key.log'].create({
            'key_id': self.key_id.id,
            'security_employee_id': self.security_employee_id.id,
            'operation': 'check_out',
            'timestamp': fields.Datetime.now(),
            'expected_return': self.expected_return_time,
            'reason': self.reason,
        })
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'success': True, 'message': _("Key checked out successfully")}
        }


class SecurityKeyCheckinWizard(models.TransientModel):
    _name = 'security.key.checkin.wizard'
    _description = 'Key Check-in Wizard'
    
    key_id = fields.Many2one('security.key', string='Key', required=True, readonly=True)
    key_name = fields.Char(related='key_id.name', string='Key Name', readonly=True)
    key_hub_id = fields.Many2one(related='key_id.key_hub_id', string='Key Hub', readonly=True)
    current_holder_id = fields.Many2one(related='key_id.current_holder_id', string='Current Holder', readonly=True)
    notes = fields.Text(string='Notes')
    
    @api.model
    def default_get(self, fields):
        res = super(SecurityKeyCheckinWizard, self).default_get(fields)
        if self.env.context.get('active_model') == 'security.key' and self.env.context.get('active_id'):
            key = self.env['security.key'].browse(self.env.context.get('active_id'))
            if key.exists():
                res['key_id'] = key.id
        return res
    def action_checkin(self):
        """Process key check-in"""
        self.ensure_one()
        
        if not self.key_id:
            raise UserError(_("No key selected for check-in"))
            
        if self.key_id.state != 'checked_out':
            raise UserError(_("This key is not currently checked out"))
            
        # Get the security employee who checked out the key
        security_employee = self.env['security.employee'].search([('employee_id', '=', self.key_id.current_holder_id.id)], limit=1)
        security_employee_id = security_employee.id
        
        # Update key status
        self.key_id.write({
            'state': 'available',
            'current_holder_id': False,
            'check_out_time': False,
            'expected_return_time': False,
        })
        
        # Create key log
        self.env['security.key.log'].create({
            'key_id': self.key_id.id,
            'security_employee_id': security_employee_id,
            'operation': 'check_in',
            'timestamp': fields.Datetime.now(),
            'reason': self.notes,
        })
        
        # Close any related activities
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'security.key'),
            ('res_id', '=', self.key_id.id),
            ('activity_type_id', '=', self.env.ref('security_management.mail_activity_key_return').id)
        ])
        activities.action_feedback(feedback=_("Key returned on %s") % fields.Datetime.now())
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'success': True, 'message': _("Key checked in successfully")}
        }
