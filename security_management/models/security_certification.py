from odoo import api, fields, models, _
from datetime import timedelta


class SecurityCertification(models.Model):
    _name = 'security.certification'
    _description = 'Security Certification'
    _order = 'expiry_date, id desc'

    name = fields.Char(string='Certification Name', required=True)
    guard_id = fields.Many2one('security.guard', string='Guard', required=True)
    security_employee_id = fields.Many2one('security.employee', string='Security Employee', ondelete='cascade')
    employee_id = fields.Many2one(related='guard_id.security_employee_id.employee_id', string='Employee', store=True)
    certification_type = fields.Selection([
        ('firearm', 'Firearm License'),
        ('first_aid', 'First Aid'),
        ('cpr', 'CPR'),
        ('security_license', 'Security License'),
        ('driving', 'Driving License'),
        ('other', 'Other')
    ], string='Type', default='other', required=True)
    
    issuing_authority = fields.Char(string='Issuing Authority')
    certification_number = fields.Char(string='Certification Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    
    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired')
    ], string='Status', compute='_compute_state', store=True)
    
    @api.depends('expiry_date')
    def _compute_state(self):
        today = fields.Date.today()
        for cert in self:
            if not cert.expiry_date:
                cert.state = 'valid'
            elif cert.expiry_date < today:
                cert.state = 'expired'
            elif cert.expiry_date < today + timedelta(days=30):
                cert.state = 'expiring'
            else:
                cert.state = 'valid'
