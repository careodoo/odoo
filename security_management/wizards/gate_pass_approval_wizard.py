from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)

class SecurityGatePassApprovalWizard(models.TransientModel):
    _name = 'security.gate.pass.approval.wizard'
    _description = 'Gate Pass Approval Wizard'
    
    gate_pass_id = fields.Many2one('security.gate.pass', string='Gate Pass', required=True, readonly=True)
    # Use computed fields instead of related fields for visitor information
    visitor_name = fields.Char(string='Visitor Name', compute='_compute_visitor_info', readonly=True)
    visitor_id_number = fields.Char(string='ID Number', compute='_compute_visitor_info', readonly=True)
    visit_purpose = fields.Text(related='gate_pass_id.purpose', string='Visit Purpose', readonly=True)
    # Remove non-existent related field
    requested_by = fields.Char(string='Requested By', compute='_compute_visitor_info', readonly=True)
    
    approval_date = fields.Datetime(string='Approval Date', default=fields.Datetime.now, readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', default=lambda self: self.env.user, readonly=True)
    valid_hours = fields.Float(string='Valid For (Hours)', default=8.0, required=True)
    approval_notes = fields.Text(string='Approval Notes')
    
    special_instructions = fields.Text(string='Special Instructions', 
                                     help="Any special instructions for the security team regarding this visitor")
    require_escort = fields.Boolean(string='Require Escort', default=False)
    escort_id = fields.Many2one('security.employee', string='Escort')
    restricted_areas = fields.Text(string='Restricted Areas', 
                                 help="List any areas that this visitor should not be allowed to access")
    requested_by_id = fields.Many2one('res.users', string='Requested By', readonly=True)
    
    
    @api.depends('gate_pass_id', 'gate_pass_id.person_ids')
    def _compute_visitor_info(self):
        """Compute visitor information from the gate pass model"""
        for wizard in self:
            if not wizard.gate_pass_id:
                wizard.visitor_name = False
                wizard.visitor_id_number = False
                wizard.requested_by = False
                continue
                
            # Get the first person from the gate pass for display purposes
            if wizard.gate_pass_id.person_ids:
                first_person = wizard.gate_pass_id.person_ids[0]
                wizard.visitor_name = first_person.name
                wizard.visitor_id_number = first_person.id_number
            else:
                wizard.visitor_name = False
                wizard.visitor_id_number = False
                
            # Set requested by information
            wizard.requested_by = wizard.gate_pass_id.create_uid.name if wizard.gate_pass_id.create_uid else False

    def action_approve(self):
        """Approve the gate pass"""
        self.ensure_one()
        
        if not self.gate_pass_id:
            raise UserError(_("No gate pass selected"))
            
        if self.gate_pass_id.state != 'draft':
            raise UserError(_("This gate pass has already been processed"))
            
        # Calculate validity period
        valid_from = fields.Datetime.now()
        valid_until = valid_from + datetime.timedelta(hours=self.valid_hours)
        
        # Update gate pass
        self.gate_pass_id.write({
            'state': 'approved',
            'approved_by': self.approved_by_id.id,
            'approval_date': self.approval_date,
            'valid_from': valid_from,
            'valid_until': valid_until,
            'approval_notes': self.approval_notes,
            'require_escort': self.require_escort,
            'escort_id': self.escort_id.id if self.require_escort else False,
            'restricted_areas': self.restricted_areas,
        })
        
        # Send notification to the requester
        if self.gate_pass_id.create_uid:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Gate Pass Approved: %s') % self.gate_pass_id.name,
                'note': _('The gate pass for %s has been approved and is valid until %s.') % 
                        (self.gate_pass_id.visitor_name, valid_until),
                'res_model_id': self.env.ref('security_management.model_security_gate_pass').id,
                'res_id': self.gate_pass_id.id,
                'user_id': self.gate_pass_id.create_uid.id,
            })
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'success': True, 'message': _("Gate pass approved successfully")}
        }
    
    def action_reject(self):
        """Reject the gate pass"""
        self.ensure_one()
        
        if not self.gate_pass_id:
            raise UserError(_("No gate pass selected"))
            
        if self.gate_pass_id.state != 'draft':
            raise UserError(_("This gate pass has already been processed"))
            
        # Update gate pass
        self.gate_pass_id.write({
            'state': 'rejected',
            'approved_by': self.approved_by_id.id,
            'approval_date': self.approval_date,
            'approval_notes': self.approval_notes,
        })
        
        # Send notification to the requester
        if self.gate_pass_id.requested_by_id:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Gate Pass Rejected: %s') % self.gate_pass_id.name,
                'note': _('The gate pass for %s has been rejected. Reason: %s') % 
                        (self.gate_pass_id.visitor_name, self.approval_notes or 'No reason provided'),
                'res_model_id': self.env.ref('security_management.model_security_gate_pass').id,
                'res_id': self.gate_pass_id.id,
                'user_id': self.gate_pass_id.requested_by_id.id,
            })
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'success': True, 'message': _("Gate pass rejected")}
        }
