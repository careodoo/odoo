# models/inspection.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SecurityInspection(models.Model):
    _name = 'security.inspection'
    _description = 'Security Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'timestamp desc'

    name = fields.Char(string='Inspection Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))

    guard_id = fields.Many2one('security.guard', string='Guard', required=True, tracking=True)
    inspector_id = fields.Many2one('security.employee', string='Inspector', tracking=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True, tracking=True)
    scheduled_date = fields.Date(string='Scheduled Date', tracking=True)

    # Inspection type
    inspection_type = fields.Selection([
        ('routine', 'Routine Inspection'),
        ('special', 'Special Inspection'),
        ('follow_up', 'Follow-up Inspection'),
        ('audit', 'Audit Inspection'),
        ('incident', 'Incident Investigation')
    ], string='Inspection Type', default='routine', required=True, tracking=True)

    # Priority
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True)

    # Location hierarchy
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    floor_id = fields.Many2one('security.floor', string='Floor', tracking=True,
                              domain="[('premise_id', '=', premise_id or False)]")
    unit_id = fields.Many2one('security.unit', string='Unit', tracking=True,
                             domain="[('floor_id', '=', floor_id or False)]")
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)

    # Inspection details
    issue_type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('security', 'Security'),
        ('safety', 'Safety'),
        ('power', 'Power/Electricity'),
        ('water', 'Water/Plumbing'),
        ('fire', 'Fire System'),
        ('other', 'Other')
    ], string='Issue Type', required=True, tracking=True)

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity', required=True, default='medium', tracking=True)

    issue_description = fields.Text(string='Issue Description', required=True)

    # Photo evidence
    image = fields.Binary(string='Photo Evidence', attachment=True)
    image_filename = fields.Char(string='Image Filename')

    # Images
    image_ids = fields.Many2many('security.inspection.image', string='Images')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Resolution details
    assigned_to = fields.Many2one('hr.employee', string='Assigned To', tracking=True)
    resolution_date = fields.Datetime(string='Resolution Date')
    resolution_notes = fields.Text(string='Resolution Notes')

    # Link to patrol log if created during patrol
    patrol_log_id = fields.Many2one('security.patrol.log', string='Patrol Log')

    # Related issues and tasks
    issue_count = fields.Integer(string='Issue Count', compute='_compute_issue_count', store=True)
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')

    # Inspection areas
    inspection_area_ids = fields.One2many('security.inspection.area', 'inspection_id', string='Inspection Areas')

    # Checklist items
    checklist_item_ids = fields.One2many('security.inspection.checklist.item', 'inspection_id', string='Checklist Items')

    # Issues
    issue_ids = fields.One2many('security.inspection.issue', 'inspection_id', string='Issues')

    # Timing fields for inspection
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    notes = fields.Text(string='Notes')


    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute the duration of the inspection in hours"""
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds() / 3600
                record.duration = round(duration, 2)
            else:
                record.duration = 0.0

    @api.depends('inspection_area_ids', 'issue_ids')
    def _compute_issue_count(self):
        """Compute the number of issues related to this inspection"""
        for record in self:
            # Count both issues from inspection areas and dedicated issue records
            area_issues = len([area for area in record.inspection_area_ids if area.status == 'issue'])
            record.issue_count = area_issues + len(record.issue_ids)

    @api.depends()
    def _compute_task_count(self):
        """Compute the number of tasks related to this inspection"""
        for record in self:
            record.task_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.inspection') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        """Submit the inspection for assignment"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft inspections can be submitted"))

        self.write({
            'state': 'submitted',
        })
        return True

    def action_start(self):
        """Start the inspection process"""
        self.ensure_one()
        if self.state != 'assigned':
            raise UserError(_("Only assigned inspections can be started"))

        self.write({
            'state': 'in_progress',
        })
        return True

    def action_complete(self):
        """Complete the inspection"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Only in-progress inspections can be completed"))

        if not self.end_time:
            raise UserError(_("You must end the inspection before completing it"))

        self.write({
            'state': 'completed',
        })
        return True

    def action_cancel(self):
        """Cancel the inspection"""
        self.ensure_one()
        if self.state in ['completed', 'cancelled']:
            raise UserError(_("Cannot cancel an inspection that is already completed or cancelled"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_reopen(self):
        """Reopen a completed inspection"""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_("Only completed inspections can be reopened"))

        self.write({
            'state': 'in_progress',
        })
        return True

    def action_assign(self):
        """Assign the inspection to an employee"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_("Only submitted inspections can be assigned"))

        if not self.assigned_to:
            return {
                'name': _('Assign Inspection'),
                'view_mode': 'form',
                'res_model': 'security.inspection.assign.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {'default_inspection_id': self.id},
            }
        else:
            self.write({
                'state': 'assigned',
            })
            return True

    def action_start_inspection(self):
        """Start the inspection by recording the start time"""
        self.ensure_one()
        if self.start_time:
            raise UserError(_('This inspection has already been started'))

        self.write({
            'start_time': fields.Datetime.now(),
            'state': 'in_progress',
        })
        return True

    def action_end_inspection(self):
        """End the inspection by recording the end time"""
        self.ensure_one()
        if not self.start_time:
            raise UserError(_('You must start the inspection before ending it'))

        if self.end_time:
            raise UserError(_('This inspection has already been ended'))

        # Check if all areas have been inspected
        if self.inspection_area_ids and any(area.status not in ['ok', 'issue', 'na'] for area in self.inspection_area_ids):
            raise UserError(_('All inspection areas must be marked as OK, Issue Found, or Not Applicable'))

        self.write({
            'end_time': fields.Datetime.now(),
        })
        return True

    def action_view_issues(self):
        """View issues related to this inspection"""
        self.ensure_one()
        return {
            'name': _('Issues'),
            'view_mode': 'tree,form',
            'res_model': 'security.inspection.issue',
            'domain': [('inspection_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {
                'default_inspection_idaction_start_inspection': self.id,
                'default_reported_by': self.env.user.employee_id.id,
            },
            'views': [[False, 'list'], [False, 'form']],
        }

    def action_view_tasks(self):
        """View tasks related to this inspection"""
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'domain': [('inspection_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_inspection_id': self.id},
        }

    def action_generate_report(self):
        """Generate a report for this inspection"""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_("Only completed inspections can have reports generated"))

        return {
            'name': _('Inspection Report'),
            'type': 'ir.actions.report',
            'report_name': 'security_management.report_inspection',
            'report_type': 'qweb-pdf',
            'res_model': 'security.inspection',
            'res_id': self.id,
        }


class SecurityIncidenceReport(models.Model):
    _name = 'security.incidence.report'
    _description = 'Incidence Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'incident_date desc, id desc'

    name = fields.Char(string='Report Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))

    # Date and time
    incident_date = fields.Date(string='Incident Date', required=True, default=fields.Date.today, tracking=True)
    incident_time = fields.Float(string='Incident Time', required=True, tracking=True)

    # Location
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    floor_id = fields.Many2one('security.floor', string='Floor', tracking=True,
                              domain="[('premise_id', '=', premise_id or False)]")
    unit_id = fields.Many2one('security.unit', string='Unit', tracking=True,
                             domain="[('floor_id', '=', floor_id or False)]")
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)
    location = fields.Char(string='Specific Location', help="Specific location within the premise/unit")

    # Incident details
    incident_type = fields.Selection([
        ('theft', 'Theft/Burglary'),
        ('damage', 'Property Damage'),
        ('injury', 'Injury/Medical'),
        ('fire', 'Fire Incident'),
        ('flood', 'Water/Flood Damage'),
        ('power', 'Power Outage'),
        ('trespass', 'Trespassing'),
        ('vandalism', 'Vandalism'),
        ('other', 'Other')
    ], string='Incident Type', required=True, tracking=True)

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity', required=True, default='medium', tracking=True)

    description = fields.Text(string='Incident Description', required=True)
    action_taken = fields.Text(string='Immediate Action Taken', required=True)

    # People involved
    reporter_id = fields.Many2one('hr.employee', string='Reported By', required=True, tracking=True)
    investigator_id = fields.Many2one('hr.employee', string='Investigator', tracking=True)
    team_id = fields.Many2one('security.team', string='Team Involved', tracking=True)
    witnesses = fields.Text(string='Witnesses')
    involved_person_ids = fields.One2many('security.incidence.involved.person', 'incidence_id', string='Persons Involved')

    # Investigation details
    investigation_start_date = fields.Datetime(string='Investigation Started', readonly=True)
    investigation_notes = fields.Text(string='Investigation Notes')
    resolution_date = fields.Datetime(string='Resolution Date', readonly=True)
    closure_date = fields.Datetime(string='Closure Date', readonly=True)
    resolution = fields.Text(string='Resolution')
    preventive_measures = fields.Text(string='Preventive Measures')

    # Evidence
    image_ids = fields.Many2many('ir.attachment', string='Images',
                               domain="[('mimetype', 'ilike', 'image')]")
    evidence_ids = fields.One2many('security.incidence.evidence', 'incidence_id', string='Evidence Items')

    # External involvement
    authorities_contacted = fields.Boolean(string='Authorities Contacted', tracking=True)
    authority_type = fields.Selection([
        ('police', 'Police'),
        ('fire', 'Fire Department'),
        ('ambulance', 'Ambulance/Medical'),
        ('other', 'Other')
    ], string='Authority Type')
    authority_reference = fields.Char(string='Authority Reference')

    # Follow up
    requires_follow_up = fields.Boolean(string='Requires Follow-up', default=False, tracking=True)
    follow_up_date = fields.Date(string='Follow-up Date')
    follow_up_notes = fields.Text(string='Follow-up Notes')
    follow_up_assigned_to = fields.Many2one('hr.employee', string='Follow-up Assigned To')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True, copy=False)

    # Related tasks
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')
    reported_by_id = fields.Many2one('hr.employee', string='Reported By')
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.incidence.report') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        """Submit the report"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft reports can be submitted"))

        self.write({
            'state': 'submitted',
        })

        # Send notification to client
        if self.client_id and self.client_id.contact_id:
            template = self.env.ref('security_management.email_template_incidence_report', False)
            if template:
                template.send_mail(self.id, force_send=True)

        return True

    def action_investigate(self):
        """Mark as investigating"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_("Only submitted reports can be marked as investigating"))

        self.write({
            'state': 'investigating',
            'investigator_id': self.env.user.employee_id.id,
            'investigation_start_date': fields.Datetime.now(),
        })
        return True

    def action_resolve(self):
        """Mark as resolved"""
        self.ensure_one()
        if self.state != 'investigating':
            raise UserError(_("Only incidents under investigation can be resolved"))

        if not self.resolution:
            raise UserError(_("Please provide a resolution before marking as resolved"))

        self.write({
            'state': 'resolved',
            'resolution_date': fields.Datetime.now(),
        })
        return True

    def action_close(self):
        """Close the report"""
        self.ensure_one()
        if self.state != 'resolved':
            raise UserError(_("Only resolved incidents can be closed"))

        self.write({
            'state': 'closed',
            'closure_date': fields.Datetime.now(),
        })
        return True

    def action_reopen(self):
        """Reopen a closed report"""
        self.ensure_one()
        if self.state != 'closed':
            raise UserError(_("Only closed reports can be reopened"))

        self.write({
            'state': 'investigating',
        })
        return True

    def action_print_report(self):
        """Print the incidence report"""
        self.ensure_one()
        return self.env.ref('security_management.action_report_incidence').report_action(self)

    @api.depends()
    def _compute_task_count(self):
        """Compute the number of tasks related to this incidence report"""
        for record in self:
            # This is a placeholder - in a real implementation, you would count related tasks
            # For example: record.task_count = self.env['security.task'].search_count([('incidence_report_id', '=', record.id)])
            record.task_count = 0

    def action_view_tasks(self):
        """View tasks related to this incidence report"""
        self.ensure_one()
        # This is a placeholder - in a real implementation, you would return an action to view related tasks
        return {
            'name': _('Tasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'domain': [('incidence_report_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_incidence_report_id': self.id},
        }

    def action_generate_report(self):
        """Generate a PDF report for this incidence report"""
        self.ensure_one()
        if self.state in ('draft', 'submitted'):
            raise UserError(_("Cannot generate a report for incidents that are still in draft or just submitted"))

        # This is a placeholder - in a real implementation, you would return an action to generate a report
        return {
            'name': _('Incidence Report'),
            'type': 'ir.actions.report',
            'report_name': 'security_management.report_incidence_detailed',
            'report_type': 'qweb-pdf',
            'res_model': 'security.incidence.report',
            'res_id': self.id,
        }


class SecurityIncidenceInvolvedPerson(models.Model):
    _name = 'security.incidence.involved.person'
    _description = 'Person Involved in Incidence'

    incidence_id = fields.Many2one('security.incidence.report', string='Incidence Report', required=True, ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    role = fields.Selection([
        ('witness', 'Witness'),
        ('victim', 'Victim'),
        ('suspect', 'Suspect'),
        ('employee', 'Employee'),
        ('visitor', 'Visitor'),
        ('contractor', 'Contractor'),
        ('other', 'Other')
    ], string='Role', required=True)
    contact_info = fields.Char(string='Contact Information')
    statement = fields.Text(string='Statement')
    notes = fields.Text(string='Additional Notes')


class SecurityIncidenceEvidence(models.Model):
    _name = 'security.incidence.evidence'
    _description = 'Incidence Evidence'
    _order = 'collection_date desc, id desc'

    incidence_id = fields.Many2one('security.incidence.report', string='Incidence Report', required=True, ondelete='cascade')
    name = fields.Char(string='Evidence Name', required=True)
    type = fields.Selection([
        ('photo', 'Photograph'),
        ('video', 'Video Recording'),
        ('document', 'Document'),
        ('statement', 'Written Statement'),
        ('physical', 'Physical Item'),
        ('digital', 'Digital Evidence'),
        ('other', 'Other')
    ], string='Evidence Type', required=True)
    description = fields.Text(string='Description')
    collection_date = fields.Datetime(string='Collection Date', default=fields.Datetime.now)
    collected_by = fields.Many2one('hr.employee', string='Collected By', default=lambda self: self.env.user.employee_id.id)

    location = fields.Char(string='Location Found')
    storage_location = fields.Char(string='Storage Location')
    reference = fields.Char(string='Reference Number')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    notes = fields.Text(string='Notes')


class SecurityCashierReport(models.Model):
    _name = 'security.cashier.report'
    _description = 'Cashier Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Report Reference', required=True, readonly=True, copy=False,
                     default=lambda self: _('New'))

    date = fields.Date(string='Report Date', required=True, default=fields.Date.today, tracking=True)
    cashier_id = fields.Many2one('hr.employee', string='Cashier', required=True, tracking=True)

    # Location
    premise_id = fields.Many2one('security.premise', string='Premise', required=True, tracking=True)
    client_id = fields.Many2one(related='premise_id.client_id', string='Client', store=True)

    # Financial details
    line_ids = fields.One2many('security.cashier.report.line', 'report_id', string='Report Lines')

    # Computed fields
    total_amount = fields.Monetary(compute='_compute_total_amount', string='Total Amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                default=lambda self: self.env.company.currency_id)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved')
    ], string='Status', default='draft', tracking=True)

    @api.depends('line_ids', 'line_ids.amount')
    def _compute_total_amount(self):
        for report in self:
            report.total_amount = sum(report.line_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('security.cashier.report') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the report"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft reports can be confirmed"))

        if not self.line_ids:
            raise UserError(_("Cannot confirm an empty report. Please add at least one line."))

        self.write({
            'state': 'confirmed',
        })
        return True

    def action_approve(self):
        """Approve the report"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Only confirmed reports can be approved"))

        self.write({
            'state': 'approved',
        })
        return True

    def action_print_report(self):
        """Print the cashier report"""
        self.ensure_one()
        return self.env.ref('security_management.action_report_cashier').report_action(self)


class SecurityInspectionArea(models.Model):
    _name = 'security.inspection.area'
    _description = 'Inspection Area'
    _order = 'sequence, id'
    _rec_name = 'area_name'

    inspection_id = fields.Many2one('security.inspection', string='Inspection', required=True, ondelete='cascade')
    area_name = fields.Char(string='Area Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    status = fields.Selection([
        ('ok', 'OK'),
        ('issue', 'Issue Found'),
        ('na', 'Not Applicable')
    ], string='Status', required=True, default='ok')
    notes = fields.Text(string='Notes')

    @api.onchange('status')
    def _onchange_status(self):
        """Set focus to notes field when status is changed to 'issue'"""
        if self.status == 'issue':
            return {
                'warning': {
                    'title': _('Issue Found'),
                    'message': _('Please provide details about the issue in the notes field.')
                }
            }


class SecurityInspectionChecklistItem(models.Model):
    _name = 'security.inspection.checklist.item'
    _description = 'Inspection Checklist Item'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'security.inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.context.get('default_inspection_id')
    )
    name = fields.Char(string='Item Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_completed = fields.Boolean(string='Completed', default=False)
    has_issue = fields.Boolean(string='Has Issue', default=False)
    notes = fields.Text(string='Notes')

    @api.onchange('has_issue')
    def _onchange_has_issue(self):
        """Set focus to notes field when has_issue is checked"""
        if self.has_issue:
            return {
                'warning': {
                    'title': _('Issue Detected'),
                    'message': _('Please provide details about the issue in the notes field.')
                }
            }


class SecurityCashierReportLine(models.Model):
    _name = 'security.cashier.report.line'
    _description = 'Cashier Report Line'

    report_id = fields.Many2one('security.cashier.report', string='Report', required=True, ondelete='cascade')
    category = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card Payment'),
        ('mobile', 'Mobile Payment'),
        ('check', 'Check'),
        ('other', 'Other')
    ], string='Category', required=True)
    description = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one(related='report_id.currency_id', string='Currency', readonly=True)


class SecurityInspectionImage(models.Model):
    _name = 'security.inspection.image'
    _description = 'Inspection Image'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Name')
    image = fields.Binary(string='Image', attachment=True, required=True)
    image_128 = fields.Image(string='Image 128', related='image', max_width=128, max_height=128, store=True)
    mimetype = fields.Char(string='Mimetype', compute='_compute_mimetype', store=True)
    inspection_id = fields.Many2one('security.inspection', string='Inspection')
    area_id = fields.Many2one('security.inspection.area', string='Area')
    notes = fields.Text(string='Notes')
    create_date = fields.Datetime(string='Created On', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)

    @api.depends('image')
    def _compute_mimetype(self):
        for record in self:
            if record.image:
                record.mimetype = 'image/jpeg'  # Default to JPEG, can be enhanced to detect actual mimetype
            else:
                record.mimetype = False


class SecurityInspectionIssue(models.Model):
    _name = 'security.inspection.issue'
    _description = 'Inspection Issue'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Issue', required=True)
    inspection_id = fields.Many2one(
        'security.inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.context.get('default_inspection_id')
    )
    area_id = fields.Many2one('security.inspection.area', string='Area',
                                 domain="[('inspection_id', '=', inspection_id)]")

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity', required=True, default='medium', tracking=True)

    reported_by = fields.Many2one('hr.employee', string='Reported By', default=lambda self: self.env.user.employee_id.id,
                                 required=True, tracking=True)

    description = fields.Text(string='Description')

    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status', default='new', tracking=True)

    resolution_notes = fields.Text(string='Resolution Notes')
    resolution_date = fields.Datetime(string='Resolution Date')

    # Link to task if created for this issue
    task_id = fields.Many2one('security.task', string='Related Task')

    def action_mark_in_progress(self):
        """Mark issue as in progress"""
        self.ensure_one()
        self.write({
            'status': 'in_progress',
        })
        return True

    def action_mark_resolved(self):
        """Mark issue as resolved"""
        self.ensure_one()
        self.write({
            'status': 'resolved',
            'resolution_date': fields.Datetime.now(),
        })
        return True

    def action_close(self):
        """Close the issue"""
        self.ensure_one()
        if not self.resolution_notes:
            raise UserError(_("Please provide resolution notes before closing the issue"))

        self.write({
            'status': 'closed',
        })
        return True

    def action_create_task(self):
        """Create a task for this issue"""
        self.ensure_one()
        if self.task_id:
            raise UserError(_("A task already exists for this issue"))

        # This is a placeholder - in a real implementation, you would create a task
        # For example:
        # task = self.env['security.task'].create({
        #     'name': _('Task for issue: %s') % self.name,
        #     'description': self.description,
        #     'issue_id': self.id,
        # })
        # self.task_id = task.id
        return True

    def action_view_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'security.task',
            'res_id': self.task_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
