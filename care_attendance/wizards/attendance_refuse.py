from odoo import fields, models, api


class AttendanceRefuseReason(models.TransientModel):
    _name = 'attendance.refuse.reason'
    _description = 'Attendance Refuse Reason'

    reason = fields.Char(required=True)

    def action_refuse(self):
        attendance = self.env['bulk.attendance'].browse(self.env.context.get('active_id'))
        attendance.write({'state': 'refuse', 'refuse_reason': self.reason})
        template = self.env.ref('care_attendance.bulk_attendance_refused_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        attendance.sudo().activity_schedule(
            'care_attendance.mail_act_bulk_attendance_create',
            summary='Bulk Attendance',
            note='Bulk Attendance Refused',
            user_id=attendance.department_manager.id)

