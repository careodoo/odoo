from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    proposal_approver_id = fields.Many2one(
        'res.users',
        config_parameter='care_proposal.proposal_approver_id',
    )

    # --- Proposal email customization ---
    proposal_email_accent = fields.Char(
        string='Email accent color', default='#875a7b',
        config_parameter='care_proposal.email_accent')
    proposal_email_show_summary = fields.Boolean(
        string='Show quotation summary in email', default=True,
        config_parameter='care_proposal.email_show_summary')
    proposal_email_show_header = fields.Boolean(
        string='Show branded header', default=True,
        config_parameter='care_proposal.email_show_header')
    proposal_email_intro = fields.Char(
        string='Email intro text',
        config_parameter='care_proposal.email_intro',
        default="It's great to send you our proposal today; we hope you'll be our valued customer. "
                "Care for Buildings & Cities Cleaning Contracting Co. (\"Care Cleaning Co.\") is one of "
                "Kuwait's leading premier cleaning companies, established in 1991 with three decades of "
                "experience, innovation and quality.")
    proposal_email_footer = fields.Char(
        string='Email footer text',
        config_parameter='care_proposal.email_footer',
        default="We look forward to hearing from you soon.")
    proposal_email_signature = fields.Char(
        string='Email signature',
        config_parameter='care_proposal.email_signature',
        default='Care Cleaning Co. — Sales Team')
