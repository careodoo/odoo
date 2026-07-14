from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProposalServiceRequest(models.Model):
    """Inbound customer service request (from the portal or back-office).

    A customer describes the service they need; the team reviews/approves it
    and turns it into a priced proposal. Customers follow up by email, by
    request number + email (public tracking), or in their portal."""

    _name = 'proposal.service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Request #', default='/', copy=False,
                       readonly=True, index=True, tracking=True)
    # Requester (a known customer, and/or free contact info for anonymous ones)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    contact_name = fields.Char(tracking=True)
    contact_email = fields.Char(tracking=True)
    contact_phone = fields.Char(tracking=True)
    company_name = fields.Char(string='Company / Entity')
    # What they need
    service_type_id = fields.Many2one('proposal.service.type', string='Service Type', tracking=True)
    site_location = fields.Char(string='Site / Location', tracking=True)
    city = fields.Char(tracking=True)
    description = fields.Text(string='Requirements / Specifications', tracking=True)
    desired_start_date = fields.Date(tracking=True)
    duration = fields.Char(string='Estimated Duration')
    budget_range = fields.Char()
    attachment_ids = fields.Many2many(
        'ir.attachment', 'service_request_attachment_rel',
        'request_id', 'attachment_id', string='Attachments')
    # Workflow
    state = fields.Selection([
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('quoted', 'Quoted'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
    ], default='new', required=True, tracking=True, copy=False)
    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'High'), ('2', 'Urgent'),
    ], default='0', tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    internal_note = fields.Text(string='Internal Note')
    source = fields.Selection([
        ('portal', 'Portal'), ('backend', 'Back-office'),
    ], default='backend', readonly=True)
    proposal_id = fields.Many2one('proposal.proposal', string='Quotation',
                                  readonly=True, copy=False)
    lead_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'proposal.service.request') or '/'
        records = super().create(vals_list)
        for rec in records:
            rec._send_mail('care_proposal.mail_tpl_service_request_ack')
        return records

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/service-request/%s' % rec.id

    # --- recipient & mail helpers ---------------------------------------
    def _recipient_email(self):
        self.ensure_one()
        return self.contact_email or self.partner_id.email or False

    def _send_mail(self, template_xmlid):
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        email = self._recipient_email()
        if template and email:
            template.sudo().send_mail(
                self.id, force_send=False,
                email_values={'email_to': email})

    # --- workflow --------------------------------------------------------
    def action_under_review(self):
        self.write({'state': 'under_review'})
        for rec in self:
            rec._send_mail('care_proposal.mail_tpl_service_request_status')

    def action_approve(self):
        self.write({'state': 'approved'})
        for rec in self:
            rec._send_mail('care_proposal.mail_tpl_service_request_status')

    def action_decline(self):
        self.write({'state': 'declined'})
        for rec in self:
            rec._send_mail('care_proposal.mail_tpl_service_request_status')

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_quotation(self):
        """Turn this request into a draft proposal, mapping the specs across,
        link them both ways, and move the request to 'Quoted'."""
        self.ensure_one()
        if self.proposal_id:
            return self._open_proposal(self.proposal_id)
        proposal = self.env['proposal.proposal'].create({
            'name': self.name,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'service_type_id': self.service_type_id.id if self.service_type_id else False,
            'service_site': self.site_location or '',
            'mobilization_date': self.desired_start_date,
            'notes': self.description or '',
            'proposal_date': fields.Date.context_today(self),
        })
        self.write({'proposal_id': proposal.id, 'state': 'quoted'})
        self._send_mail('care_proposal.mail_tpl_service_request_status')
        self.message_post(body=_("Quotation %s created from this request.") % proposal.name)
        return self._open_proposal(proposal)

    def _open_proposal(self, proposal):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'proposal.proposal',
            'res_id': proposal.id,
            'view_mode': 'form',
            'target': 'current',
        }
