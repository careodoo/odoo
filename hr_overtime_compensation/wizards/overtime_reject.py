from odoo import fields, models, api


class OvertimeReject(models.TransientModel):
    _name = 'overtime.reject'
    _description = 'Overtime Reject'

    overtime_request_id = fields.Many2one('overtime.request', required=True)
    reason = fields.Char(required=True)

    def button_reject(self):
        approvals = self.overtime_request_id.approval_ids
        line = approvals.filtered(lambda l: l.user_id.id == self.env.user.id)
        if line:
            line.write({
                'rejected': True,
                'date_rejected': fields.Datetime.now(),
                'reject_reason': self.reason,
            })
            self.overtime_request_id.write({
                'state': 'reject',
            })
