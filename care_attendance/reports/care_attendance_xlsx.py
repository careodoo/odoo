from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class CareAttendanceReportXlsx(models.AbstractModel):
    _name = 'report.care_attendance.care_attendance_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 13, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format(
            {'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        text_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        number_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        yellow_number_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': 'yellow', 'color': 'red'})
        red_number_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': 'red', 'color': 'black'})
        absent_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#7030a0', 'color': 'white'})

        sheet = workbook.add_worksheet('Management')
        date_from = datetime.combine(objs.date_from, datetime.min.time())
        date_to = datetime.combine(objs.date_to, datetime.min.time())
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', date_from), ('check_in', '<=', date_to)
        ])
        departments = self.env['hr.department'].search([])
        managers = set(departments.mapped('manager_id'))
        sick_off = self.env['hr.leave.type'].search([('name', '=', 'Sick Time Off')])
        if not sick_off:
            raise UserError("please set sick time off type!")
        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=i)) for i in range(0, days_between + 1)]

        sheet.merge_range('A1:A2', 'S.No.', header_style)
        sheet.merge_range('B1:B2', 'EID', header_style)
        sheet.merge_range('C1:C2', 'Name', header_style)
        column = 3
        day_present = {}
        day_absent = {}
        for d in date_list:
            sheet.write(0, column, d.day, header_style)
            sheet.write(1, column, d.strftime('%a'), header_style)
            sheet.set_column(0, column, 3)
            sheet.set_column(1, column, 3)
            day_present[d.date()] = 0
            day_absent[d.date()] = 0
            column += 1
        sheet.set_column(0, 2, 20)
        sheet.merge_range(0, column, 1, column, 'ABSENTS', header_style)

        # lines
        sequence = 0
        row = 2
        for manager in managers:
            sequence += 1
            column = 3
            sheet.write(row, 0, sequence, number_style)
            sheet.write(row, 1, manager.barcode, number_style)
            sheet.write(row, 2, manager.name, number_style)
            manager_attendance_domain = [
                ('employee_id', '=', manager.id), ('check_in', '>=', date_from),
                ('check_in', '<=', date_to)
            ]
            if objs.department_ids:
                manager_attendance_domain.append(('employee_id.department_id', 'in', objs.department_ids.ids))
            manager_attendance = self.env['hr.attendance'].search(manager_attendance_domain).mapped('check_in')
            manager_attendance = [att.date() for att in manager_attendance]
            manager_off = {'0', '1', '2', '3', '4', '5', '6'}.difference(set(manager.resource_calendar_id.attendance_ids.mapped('dayofweek')))
            manager_sick_off = self.env['hr.leave'].search([
                ('holiday_status_id', '=', sick_off.id), ('employee_ids', 'in', manager.ids)
            ])
            absents = 0
            for d in date_list:
                if d.date() in manager_attendance:
                    sheet.write(row, column, 'P', number_style)
                    day_present[d.date()] += 1
                elif str(d.weekday()) in manager_off:
                    sheet.write(row, column, 'OFF', yellow_number_style)
                # elif d.date() >= manager_sick_off:
                #     sheet.write(row, column, 'OFF', number_style)
                else:
                    sheet.write(row, column, 'A', absent_style)
                    day_absent[d.date()] += 1
                    absents += 1
                column += 1
            sheet.write(row, column, absents, number_style)
            row += 1
        sheet.write(row, 2, 'Total', yellow_number_style)
        column = 3
        for key, value in day_present.items():
            sheet.write(row, column, value, yellow_number_style)
            column += 1
        sheet.write(row, column, sum(day_present.values()), yellow_number_style)
        row += 1
        column = 3
        for key, value in day_absent.items():
            sheet.write(row, column, value, yellow_number_style)
            column += 1
        sheet.write(row, column, sum(day_absent.values()), yellow_number_style)
        # Day-Shift Male
        sheet = workbook.add_worksheet('Day-Shift Male')
        date_from = datetime.combine(objs.date_from, datetime.min.time())
        date_to = datetime.combine(objs.date_to, datetime.min.time())
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', date_from), ('check_in', '<=', date_to)
        ])
        male_employees = set(self.env['hr.employee'].search([('gender', '=', 'male')])).difference(managers)
        sick_off = self.env['hr.leave.type'].search([('name', '=', 'Sick Time Off')])
        if not sick_off:
            raise UserError("please set sick time off type!")
        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=i)) for i in range(0, days_between + 1)]

        sheet.merge_range('A1:A2', 'S.No.', header_style)
        sheet.merge_range('B1:B2', 'EID', header_style)
        sheet.merge_range('C1:C2', 'Name', header_style)
        column = 3
        day_present = {}
        day_absent = {}
        for d in date_list:
            sheet.write(0, column, d.day, header_style)
            sheet.write(1, column, d.strftime('%a'), header_style)
            sheet.set_column(0, column, 3)
            sheet.set_column(1, column, 3)
            day_present[d.date()] = 0
            day_absent[d.date()] = 0
            column += 1
        sheet.set_column(0, 2, 20)
        sheet.merge_range(0, column, 1, column, 'ABSENTS', header_style)

        # lines
        sequence = 0
        row = 2
        for emp in male_employees:
            sequence += 1
            column = 3
            sheet.write(row, 0, sequence, number_style)
            sheet.write(row, 1, emp.barcode, number_style)
            sheet.write(row, 2, emp.name, number_style)
            manager_attendance_domain = [
                ('employee_id', '=', emp.id), ('check_in', '>=', date_from), ('check_in', '<=', date_to)
            ]
            if objs.department_ids:
                manager_attendance_domain.append(('employee_id.department_id', 'in', objs.department_ids.ids))
            manager_attendance = self.env['hr.attendance'].search(manager_attendance_domain).mapped('check_in')
            manager_attendance = [att.date() for att in manager_attendance]
            manager_off = {'0', '1', '2', '3', '4', '5', '6'}.difference(set(emp.resource_calendar_id.attendance_ids.mapped('dayofweek')))
            manager_sick_off = self.env['hr.leave'].search([
                ('holiday_status_id', '=', sick_off.id), ('employee_ids', 'in', emp.ids)
            ])
            absents = 0
            for d in date_list:
                if d.date() in manager_attendance:
                    sheet.write(row, column, 'P', number_style)
                    day_present[d.date()] += 1
                elif str(d.weekday()) in manager_off:
                    sheet.write(row, column, 'OFF', yellow_number_style)
                # elif d.date() >= manager_sick_off:
                #     sheet.write(row, column, 'OFF', number_style)
                else:
                    sheet.write(row, column, 'A', absent_style)
                    day_absent[d.date()] += 1
                    absents += 1
                column += 1
            sheet.write(row, column, absents, number_style)
            row += 1
        sheet.write(row, 2, 'Total', yellow_number_style)
        column = 3
        for key, value in day_present.items():
            sheet.write(row, column, value, yellow_number_style)
            column += 1
        sheet.write(row, column, sum(day_present.values()), yellow_number_style)
        row += 1
        column = 3
        for key, value in day_absent.items():
            sheet.write(row, column, value, yellow_number_style)
            column += 1
        sheet.write(row, column, sum(day_absent.values()), yellow_number_style)
        # Day-Shift Female
        sheet = workbook.add_worksheet('Day-Shift Female')
        date_from = datetime.combine(objs.date_from, datetime.min.time())
        date_to = datetime.combine(objs.date_to, datetime.min.time())
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', date_from), ('check_in', '<=', date_to)
        ])
        female_employees = set(self.env['hr.employee'].search([('gender', '=', 'female')])).difference(managers)
        sick_off = self.env['hr.leave.type'].search([('name', '=', 'Sick Time Off')])
        if not sick_off:
            raise UserError("please set sick time off type!")
        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=i)) for i in range(0, days_between + 1)]

        sheet.merge_range('A1:A2', 'S.No.', header_style)
        sheet.merge_range('B1:B2', 'EID', header_style)
        sheet.merge_range('C1:C2', 'Name', header_style)
        column = 3
        day_present = {}
        day_absent = {}
        for d in date_list:
            sheet.write(0, column, d.day, header_style)
            sheet.write(1, column, d.strftime('%a'), header_style)
            sheet.set_column(0, column, 3)
            sheet.set_column(1, column, 3)
            day_present[d.date()] = 0
            day_absent[d.date()] = 0
            column += 1
        sheet.set_column(0, 2, 20)
        sheet.merge_range(0, column, 1, column, 'ABSENTS', header_style)

        # lines
        sequence = 0
        row = 2
        for emp in female_employees:
            sequence += 1
            column = 3
            sheet.write(row, 0, sequence, number_style)
            sheet.write(row, 1, emp.barcode, number_style)
            sheet.write(row, 2, emp.name, number_style)
            manager_attendance_domain = [
                ('employee_id', '=', emp.id), ('check_in', '>=', date_from), ('check_in', '<=', date_to)
            ]
            if objs.department_ids:
                manager_attendance_domain.append(('employee_id.department_id', 'in', objs.department_ids.ids))
            manager_attendance = self.env['hr.attendance'].search(manager_attendance_domain).mapped('check_in')
            manager_attendance = [att.date() for att in manager_attendance]
            manager_off = {'0', '1', '2', '3', '4', '5', '6'}.difference(set(emp.resource_calendar_id.attendance_ids.mapped('dayofweek')))
            manager_sick_off = self.env['hr.leave'].search([
                ('holiday_status_id', '=', sick_off.id), ('employee_ids', 'in', emp.ids)
            ])
            absents = 0
            for d in date_list:
                if d.date() in manager_attendance:
                    sheet.write(row, column, 'P', number_style)
                    day_present[d.date()] += 1
                elif str(d.weekday()) in manager_off:
                    sheet.write(row, column, 'OFF', yellow_number_style)
                # elif d.date() >= manager_sick_off:
                #     sheet.write(row, column, 'OFF', number_style)
                else:
                    sheet.write(row, column, 'A', absent_style)
                    day_absent[d.date()] += 1
                    absents += 1
                column += 1
            sheet.write(row, column, absents, number_style)
            row += 1
        sheet.write(row, 2, 'Total Present Staff', yellow_number_style)
        column = 3
        for key, value in day_present.items():
            sheet.write(row, column, value, yellow_number_style)
            column += 1
        sheet.write(row, column, sum(day_present.values()), yellow_number_style)
        row += 1
        column = 3
        sheet.write(row, 2, 'Total Absent Staff', red_number_style)
        for key, value in day_absent.items():
            sheet.write(row, column, value, red_number_style)
            column += 1
        sheet.write(row, column, sum(day_absent.values()), red_number_style)
