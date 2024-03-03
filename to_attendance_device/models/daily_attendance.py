import datetime

from odoo import models, fields, api
from datetime import timedelta, datetime
from pytz import timezone

import logging
_logger = logging.getLogger(__name__)


class HrAttendanceInh(models.Model):
    _inherit = 'hr.attendance'

    def action_create_daily_attendance(self):
        # dates = self.env['user.attendance'].search([('daily_att_created', '=', True)])
        # for ff in dates:
        #     ff.daily_att_created = False
        users = self.env['attendance.device.user'].search([])
        dates = self.env['user.attendance'].search([('daily_att_created', '=', False)])
        date_list = []
        for date in dates:
            if date.timestamp.date() not in date_list:
                date_list.append(date.timestamp.date())
        for d in date_list:
            for user in users:
                user_attendance = self.env['user.attendance'].search([('user_id', '=', user.id), ('daily_att_created', '=', False)])
                data = []
                for att in user_attendance:
                    if att.timestamp.date() == d:
                        data.append(att.timestamp)
                        att.daily_att_created = True
                employee = self.env['hr.employee'].search([('barcode', '=', user.user_id)], limit=1)
                if len(data) > 1:
                    if data[-1].date() == d and data[0].date() == d and employee:
                        rec = self.env['hr.attendance'].create({
                           'employee_id': employee.id,
                           'check_in': data[-1],
                           'check_out': data[0], })
                if len(data) == 1:
                    if employee.shift_id:
                        out = str(int(employee.shift_id.check_out))
                        out = int(out.split(':')[0])-6
                        if out < 10:
                            out = '0' + str(out)
                        out = str(out) + ':00'
                        out_time = str(data[0].date()) + ' ' + out + ':00'
                        date_time_obj = datetime.strptime(out_time, '%Y-%m-%d %H:%M:%S')
                        d = date_time_obj.strftime("%d-%m-%Y %H:%M:%S")
                        s = datetime.strptime(d, '%d-%m-%Y %H:%M:%S')
                        rec = self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'check_in': data[-1],
                            'check_out': s
                        })
#
# class DailyUserAttendance(models.Model):
#     _name = 'daily.user.attendance'
#     _rec_name = 'employee_id'
#
#     check_in = fields.Datetime('Check In')
#     check_out = fields.Datetime('Check Out')
#     employee_id = fields.Many2one('attendance.device.user')
#     company_id = fields.Many2one('res.company', related="employee_id.employee_id.company_id")
#     user_id = fields.Char(string="User ID", related="employee_id.user_id")
#     check = fields.Boolean("Check")
#
#     def action_create_daily_attendance(self):
#         dates = self.env['user.attendance'].search([('daily_att_created', '=', True)])
#         for ff in dates:
#             ff.daily_att_created = False
#         users = self.env['attendance.device.user'].search([])
#         dates = self.env['user.attendance'].search([('daily_att_created', '=', False)])
#         date_list = []
#         for date in dates:
#             if date.timestamp.date() not in date_list:
#                 date_list.append(date.timestamp.date())
#         for d in date_list:
#             for user in users:
#                 user_attendance = self.env['user.attendance'].search([('user_id', '=', user.id), ('daily_att_created', '=', False)])
#                 data = []
#                 for att in user_attendance:
#                     if att.timestamp.date() == d:
#                         data.append(att.timestamp)
#                 employee = self.env['hr.employee'].search([('barcode', '=', user.user_id)], limit=1)
#                 if len(data) > 1:
#                     # duration = data[0] - data[-1]
#                     # duration_in_s = duration.total_seconds()
#                     # hours = divmod(duration_in_s, 3600)[0]
#                     # if hours > 4 and hours < 11:
#                     #     user_check = self.env['user.attendance'].search([('user_id', '=', user.id)])
#                     #     for ch in user_check:
#                     #         if ch.timestamp >= data[-1] and ch.timestamp <= data[0]:
#                     #             ch.daily_att_created = True
#
#                     if data[-1].date() == d and data[0].date() == d and employee:
#                         rec = self.env['hr.attendance'].create({
#                            'employee_id': employee.id,
#                            'check_in': data[-1],
#                            'check_out': data[0], })
#                 if len(data) == 1:
#                     if employee.shift_id:
#                         out = str(int(employee.shift_id.check_out))
#                         out = int(out.split(':')[0])-6
#                         if out < 10:
#                             out = '0' + str(out)
#                         out = str(out) + ':00'
#                         out_time = str(data[0].date()) + ' ' + out + ':00'
#                         date_time_obj = datetime.strptime(out_time, '%Y-%m-%d %H:%M:%S')
#                         d = date_time_obj.strftime("%d-%m-%Y %H:%M:%S")
#                         s = datetime.strptime(d, '%d-%m-%Y %H:%M:%S')
#                         rec = self.env['hr.attendance'].create({
#                             'employee_id': employee.id,
#                             'check_in': data[-1],
#                             'check_out': s
#                         })
#
#     # def action_create_attendance(self):
#     #     print("Running!!!!!!")
#     #     daily_attendance = self.env['daily.user.attendance'].search([('check', '=', False)])
#     #     print(daily_attendance)
#     #     if daily_attendance:
#     #         for rec in daily_attendance:
#     #             if rec.user_id:
#     #                 employee = self.env['hr.employee'].search([('barcode', '=', rec.user_id)])
#     #                 if employee:
#     #                     try:
#     #                         atten = self.env['hr.attendance'].create({
#     #                             'employee_id': employee.id,
#     #                             'check_in': rec.check_in,
#     #                             'check_out': rec.check_out,
#     #                             # 'employee_batch_id': rec.user_id,
#     #                         })
#     #                         rec.check = True
#     #                     except Exception as error:
#     #                         _logger.critical('Error : ' + str(error))
#
#     # def action_create_daily_attendance(self):
#     #     # dates = self.env['user.attendance'].search([('daily_att_created', '=', True)])
#     #     # for ff in dates:
#     #     #     ff.daily_att_created = False
#     #     users = self.env['attendance.device.user'].search([])
#     #     dates = self.env['user.attendance'].search([('daily_att_created', '=', False)])
#     #     date_list = []
#     #     for date in dates:
#     #         if date.timestamp.date() not in date_list:
#     #             date_list.append(date.timestamp.date())
#     #     for d in date_list:
#     #         for user in users:
#     #             user_attendance = self.env['user.attendance'].search([('user_id', '=', user.id), ('daily_att_created', '=', False)])
#     #             data = []
#     #             for att in user_attendance:
#     #                 if att.timestamp.date() == d:
#     #                     data.append(att.timestamp)
#     #             if len(data) > 1:
#     #                 duration = data[0] - data[-1]
#     #                 duration_in_s = duration.total_seconds()
#     #                 hours = divmod(duration_in_s, 3600)[0]
#     #                 if hours > 4 and hours < 11:
#     #                     user_check = self.env['user.attendance'].search([('user_id', '=', user.id)])
#     #                     for ch in user_check:
#     #                         if ch.timestamp >= data[-1] and ch.timestamp <= data[0]:
#     #                             ch.daily_att_created = True
#     #                     #     if ch.user_id.name == 'Jlt.Ashfaq':
#     #                     #         print(data)
#     #                     if data[-1].date() == d and data[0].date() == d:
#     #                         rec = self.env['daily.user.attendance'].create({
#     #                            'employee_id': user.id,
#     #                            'check_in': data[-1],
#     #                            'check_out': data[0], })
#             # break
#
#     def action_auto_check_out(self):
#         for rec in self:
#             if not rec.check_out:
#                 print("Check Out")
#                 next_date = rec.check_in.date() + timedelta(days=1)
#                 next_checkin = self.env['daily.user.attendance'].search([('employee_id', '=', rec.employee_id.id)])
#                 for res in next_checkin:
#                     if res.id != rec.id and res.check_in.date() == next_date:
#                         add_four_hours = rec.check_in + timedelta(hours=8)
#                         rec.write({
#                             'check_out': add_four_hours
#                         })
