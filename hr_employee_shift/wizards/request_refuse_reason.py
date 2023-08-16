from odoo import fields, models, api


class RequestRefuseReason(models.TransientModel):
    _name = 'request.refuse.reason'
    _description = 'Request Refuse Reason'

    reason = fields.Char(required=True)

    def action_refuse(self):
        request = self.env['employee.shift.request'].browse(self.env.context.get('active_id'))
        if request.state == 'confirm':
            state = 'refuse_1'
            approver = request.approver_1
        elif request.state == 'approval_1':
            state = 'refuse_2'
            approver = request.approver_2
        else:
            state = 'refuse_3'
            approver = request.approver_3
        request.write({'state': state, 'refuse_reason': self.reason})
        record = request._prepare_request_record(approver)
        self.env['employee.shift.request.record'].create(record)

        # request.sudo().activity_schedule(
        #     'hr_attendance_approval.mail_act_letter_create',
        #     summary='Letter Refused!',
        #     note='Your Letter has been refused',
        #     user_id=request.create_uid.id)


