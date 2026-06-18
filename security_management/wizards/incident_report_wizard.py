from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)

class SecurityIncidentReportWizard(models.TransientModel):
    _name = 'security.incident.report.wizard'
    _description = 'Security Incident Report Wizard'
    
    name = fields.Char(string='Incident Title', required=True)
    incident_date = fields.Datetime(string='Incident Date/Time', required=True, default=fields.Datetime.now)
    location_id = fields.Many2one('security.premise', string='Location', required=True)
    floor_id = fields.Many2one('security.floor', string='Floor', domain="[('premise_id', '=', location_id)]")
    unit_id = fields.Many2one('security.unit', string='Unit', domain="[('floor_id', '=', floor_id)]")
    
    reporter_id = fields.Many2one('hr.employee', string='Reported By', 
                                default=lambda self: self.env.user.employee_id.id, required=True)
    team_id = fields.Many2one('security.team', string='Security Team')
    
    incident_type = fields.Selection([
        ('theft', 'Theft/Burglary'),
        ('vandalism', 'Vandalism'),
        ('trespassing', 'Trespassing'),
        ('fire', 'Fire'),
        ('medical', 'Medical Emergency'),
        ('violence', 'Violence/Assault'),
        ('suspicious', 'Suspicious Activity'),
        ('other', 'Other'),
    ], string='Incident Type', required=True)
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='medium')
    
    description = fields.Text(string='Description', required=True)
    action_taken = fields.Text(string='Action Taken')
    
    witnesses = fields.Text(string='Witnesses')
    authorities_notified = fields.Boolean(string='Authorities Notified')
    authority_report_number = fields.Char(string='Authority Report Number')
    
    image_ids = fields.Many2many('ir.attachment', string='Evidence Photos')
    
    notify_client = fields.Boolean(string='Notify Client', default=False)
    notify_management = fields.Boolean(string='Notify Management', default=True)
    
    def action_submit_report(self):
        """Submit the incident report"""
        self.ensure_one()
        
        # Create incident report
        vals = {
            'name': self.name,
            'incident_date': self.incident_date,
            'location_id': self.location_id.id,
            'floor_id': self.floor_id.id if self.floor_id else False,
            'unit_id': self.unit_id.id if self.unit_id else False,
            'reporter_id': self.reporter_id.id,
            'team_id': self.team_id.id if self.team_id else False,
            'incident_type': self.incident_type,
            'severity': self.severity,
            'description': self.description,
            'action_taken': self.action_taken,
            'witnesses': self.witnesses,
            'authorities_notified': self.authorities_notified,
            'authority_report_number': self.authority_report_number,
            'state': 'draft',
        }
        
        incident = self.env['security.incident.report'].create(vals)
        
        # Attach images
        if self.image_ids:
            for attachment in self.image_ids:
                attachment.write({
                    'res_model': 'security.incident.report',
                    'res_id': incident.id,
                })
        
        # Send notifications
        if self.notify_management:
            managers = self.env.ref('security_management.group_security_manager').users
            for manager in managers:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('New Incident Report: %s') % self.name,
                    'note': _('A new %s incident has been reported with %s severity. Please review.') % 
                            (dict(self._fields['incident_type'].selection).get(self.incident_type), 
                             dict(self._fields['severity'].selection).get(self.severity)),
                    'res_model_id': self.env.ref('security_management.model_security_incident_report').id,
                    'res_id': incident.id,
                    'user_id': manager.id,
                    'deadline': fields.Date.today(),
                })
        
        if self.notify_client and self.location_id.client_id:
            client_contacts = self.location_id.client_id.contact_ids.filtered(lambda c: c.is_security_contact)
            for contact in client_contacts:
                if contact.user_id:
                    self.env['mail.activity'].create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': _('Security Incident at %s') % self.location_id.name,
                        'note': _('A security incident has been reported at your property. Please review the details.'),
                        'res_model_id': self.env.ref('security_management.model_security_incident_report').id,
                        'res_id': incident.id,
                        'user_id': contact.user_id.id,
                        'deadline': fields.Date.today(),
                    })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Incident Report'),
            'res_model': 'security.incident.report',
            'res_id': incident.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
