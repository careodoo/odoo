from odoo import _, api, fields, models


class ProposalApproval(models.Model):
    _name = 'proposal.approval'
    _description = 'Proposal Approval'
    _order = 'sequence'

    proposal_id = fields.Many2one('proposal.proposal')
    sequence = fields.Integer()
    user_id = fields.Many2one('res.users')
    approved = fields.Boolean()
    date_approved = fields.Datetime(string='Approved Date')

    def send_approve_request(self):
        template = self.env.ref('care_proposal.email_template_proposal_won')
        email_values = {'email_to': self.user_id.email}
        self.env['mail.template'].browse(
            template.id).with_context(name_to=self.user_id.name).send_mail(
                self.proposal_id.id,
                email_values=email_values,
                force_send=True,
                notif_layout='mail.mail_notification_light',
            )
