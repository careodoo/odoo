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
    # ---- what an incident report has to carry ---------------------------
    # A typed description is what the reporter remembers, not what happened.
    # Photos, video and a coordinate are what an insurer, a police report or
    # a client dispute will actually ask for — and none of them can be
    # reconstructed an hour later.
    latitude = fields.Float(string='Latitude', digits=(10, 7), tracking=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), tracking=True)
    located = fields.Boolean(string='Location captured', compute='_compute_located',
                             store=True)
    map_url = fields.Char(string='Map link', compute='_compute_located')
    media_ids = fields.One2many('security.incident.media', 'incident_id',
                                string='Photos & video')
    media_count = fields.Integer(string='Attachments', compute='_compute_media')
    update_ids = fields.One2many('security.incident.update', 'incident_id',
                                 string='Updates')
    update_count = fields.Integer(string='Updates', compute='_compute_media')
    live_url = fields.Char(string='Live stream link', tracking=True,
                           help='A link to a live feed from the phone while the '
                                'incident is still unfolding.')
    live_active = fields.Boolean(string='Streaming now', tracking=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='Work order',
                                   readonly=True, copy=False,
                                   help='Raised from this incident.')

    @api.depends('latitude', 'longitude')
    def _compute_located(self):
        for r in self:
            r.located = bool(r.latitude and r.longitude)
            r.map_url = ('https://maps.google.com/?q=%s,%s'
                         % (r.latitude, r.longitude)) if r.located else False

    def _compute_media(self):
        for r in self:
            r.media_count = len(r.media_ids)
            r.update_count = len(r.update_ids)

    def action_add_update(self, text, user_id=None):
        """An incident is not a snapshot. What happened next belongs on the
        same record, timestamped, not in a chat nobody can find later."""
        self.ensure_one()
        return self.env['security.incident.update'].create({
            'incident_id': self.id, 'body': text,
            'user_id': user_id or self.env.uid,
        })

    def action_to_workorder(self, team_id=None, service_id=None):
        """Escalate to work. An incident that needs a repair should not be
        retyped by someone else into a second system."""
        self.ensure_one()
        if self.workorder_id:
            raise UserError(_('A work order was already raised from this incident.'))
        WO = self.env['care.cafm.workorder'].sudo()
        fac = getattr(self.premise_id, 'cafm_facility_id', False)
        vals = {
            'title': _('From incident %s: %s') % (self.name, self.incident_type or ''),
            'description': self.description or '',
            'priority': {'critical': '3', 'high': '2'}.get(self.severity, '1'),
        }
        if fac:
            vals['facility_id'] = fac.id
        if team_id:
            vals['team_id'] = int(team_id)
        if service_id:
            vals['service_id'] = int(service_id)
        else:
            # A work order needs a service. Default to the Security service so
            # the escalation never fails for want of a dropdown value.
            svc = self.env['care.cafm.service'].sudo().search(
                [('service_type', '=', 'security')], limit=1) or \
                self.env['care.cafm.service'].sudo().search([], limit=1)
            if svc:
                vals['service_id'] = svc.id
        wo = WO.create(vals)
        self.workorder_id = wo.id
        self.message_post(body=_('🧾 Work order %s raised from this incident.') % wo.display_name)
        return wo

    
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


class SecurityIncidentMedia(models.Model):
    """A photo or a clip, taken at the scene."""
    _name = 'security.incident.media'
    _description = 'Incident Media'
    _order = 'create_date desc, id desc'

    incident_id = fields.Many2one('security.incident.report', required=True,
                                  ondelete='cascade', index=True)
    name = fields.Char(string='Caption')
    kind = fields.Selection([('photo', 'Photo'), ('video', 'Video')],
                            string='Type', default='photo', required=True)
    file = fields.Binary(string='File', attachment=True, required=True)
    filename = fields.Char(string='File name')
    taken_at = fields.Datetime(string='Taken at', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='By', default=lambda s: s.env.user)


class SecurityIncidentUpdate(models.Model):
    """What happened next — kept on the incident, in order."""
    _name = 'security.incident.update'
    _description = 'Incident Update'
    _order = 'create_date desc, id desc'

    incident_id = fields.Many2one('security.incident.report', required=True,
                                  ondelete='cascade', index=True)
    body = fields.Text(string='Update', required=True)
    user_id = fields.Many2one('res.users', string='By', default=lambda s: s.env.user)
    at = fields.Datetime(string='At', default=fields.Datetime.now)
