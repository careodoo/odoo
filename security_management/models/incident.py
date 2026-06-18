from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SecurityIncidentReport(models.Model):
    _name = 'security.incident.report'
    _description = 'Security Incident Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Datetime(string='Date & Time', required=True, default=fields.Datetime.now, tracking=True)
    reporter_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    location = fields.Char(string='Specific Location', help="Specific location within the premise", tracking=True)
    
    incident_type = fields.Selection([
        ('theft', 'Theft/Burglary'),
        ('vandalism', 'Vandalism'),
        ('trespassing', 'Trespassing'),
        ('assault', 'Assault'),
        ('fire', 'Fire'),
        ('medical', 'Medical Emergency'),
        ('suspicious', 'Suspicious Activity'),
        ('other', 'Other'),
    ], string='Incident Type', required=True, tracking=True)
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='medium', tracking=True)
    
    description = fields.Text(string='Description', required=True, tracking=True)
    action_taken = fields.Text(string='Action Taken', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('reported', 'Reported'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    
    witness_ids = fields.Many2many('res.partner', string='Witnesses')
    involved_person_ids = fields.Many2many('res.partner', 'incident_involved_person_rel', 'incident_id', 'person_id', string='Involved Persons')
    
    guard_id = fields.Many2one('security.guard', string='Responding Guard', tracking=True)
    team_id = fields.Many2one('security.team', string='Security Team', tracking=True)
    patrol_id = fields.Many2one('security.patrol', string='Related Patrol', tracking=True)
    
    police_notified = fields.Boolean(string='Police Notified', default=False, tracking=True)
    police_report_number = fields.Char(string='Police Report #', tracking=True)
    
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    resolution_date = fields.Datetime(string='Resolution Date', tracking=True)
    resolution_notes = fields.Text(string='Resolution Notes', tracking=True)
    
    follow_up_required = fields.Boolean(string='Follow-up Required', default=False, tracking=True)
    follow_up_date = fields.Date(string='Follow-up Date', tracking=True)
    follow_up_notes = fields.Text(string='Follow-up Notes', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.incident.report') or _('New')
        return super(SecurityIncidentReport, self).create(vals_list)
    
    def action_report(self):
        self.ensure_one()
        self.write({'state': 'reported'})
        
    def action_investigate(self):
        self.ensure_one()
        self.write({'state': 'investigating'})
        
    def action_resolve(self):
        self.ensure_one()
        self.write({
            'state': 'resolved',
            'resolution_date': fields.Datetime.now(),
        })
        
    def action_close(self):
        self.ensure_one()
        if not self.resolution_notes:
            raise UserError(_("Please add resolution notes before closing the incident."))
        self.write({'state': 'closed'})
        
    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        
    def action_notify_police(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Police Report'),
            'res_model': 'security.police.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_incident_id': self.id},
        }
