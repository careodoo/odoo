from odoo import fields, models, api, _
import base64


class Proposal(models.Model):
    _inherit = 'proposal.proposal'

    contract_ids = fields.One2many('care.experience', 'proposal_id')

    def button_create_contract(self):
        sequence = self.env['ir.sequence'].next_by_code('project.contract')
        contract = self.env['care.experience'].create({
            "sequence": sequence,
            "proposal_id": self.id,
            "partner_id": self.partner_id.id,
            # "state": 'valid',
        })
        self.prepare_attachments(contract, 'pricing')
        self.prepare_attachments(contract, 'customer_proposal')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Contract'),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'care.experience',
            'res_id': contract.id,
            'target': 'current'
        }

    def prepare_attachments(self, contract, report):
        if report == 'pricing':
            report_template_id = self.env.ref('care_proposal.action_proposal_pdf_report')._render_qweb_pdf(self.id)
        else:
            report_template_id = self.env.ref('care_proposal.action_proposal_report')._render_qweb_pdf(self.id)
        data_record = base64.b64encode(report_template_id[0])
        attachment_values = {
            'name': self.name,
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
            'res_model': 'care.experience',
            'res_id': contract.id
        }
        self.env['ir.attachment'].create(attachment_values)
