from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class AssetListReportXlsx(models.AbstractModel):
    _name = 'report.care_asset.asset_list_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 13, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format(
            {'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        text_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        number_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})

        sheet = workbook.add_worksheet('Asset')
        asset_wizard = objs[0]
        header_text = 'List of Assets'
        if asset_wizard.department_ids or asset_wizard.category_ids:
            header_text = 'List of Assets for '
            if asset_wizard.department_ids:
                header_text += 'Departments: '
                header_text += ','.join(asset_wizard.department_ids.mapped('name'))
            if asset_wizard.category_ids:
                header_text += ' Categories: '
                header_text += ','.join(asset_wizard.category_ids.mapped('name'))
            sheet.merge_range('A1:H1', header_text, header_style)

        sheet.write('A2:A2', 'Asset Name', header_style)
        sheet.write('B2:B2', 'Asset Barcode', header_style)
        sheet.write('C2:C2', 'Asset Category', header_style)
        sheet.write('D2:D2', 'Department', header_style)
        sheet.write('E2:E2', 'Original Value', header_style)
        sheet.write('F2:F2', 'Book Value', header_style)
        sheet.write('G2:G2', 'Duration', header_style)
        sheet.write('H2:H2', 'Start Depreciation', header_style)

        row = 2
        for line in asset_wizard.line_ids:
            sheet.write(row, 0, line.name, header_style)
            sheet.write(row, 1, line.asset_id.barcode or '', header_style)
            sheet.write(row, 2, line.asset_id.category_id.name or '', header_style)
            sheet.write(row, 3, line.asset_id.department_id.name or '', header_style)
            sheet.write(row, 4, line.original_value or '', header_style)
            sheet.write(row, 5, line.asset_id.book_value or '', header_style)
            sheet.write(row, 6, line.asset_id.method_number or '', header_style)
            sheet.write(row, 7, str(line.first_depreciation_date) or '', header_style)
            # sheet.write(1, column, d.strftime('%a'), header_style)
            row += 1
        sheet.set_column(0, 7, 15)
        # sheet.merge_range(0, column, 1, column, 'ABSENTS', header_style)

        # # lines
        # sequence = 0
        # row = 2
        # for manager in managers:
        #     sequence += 1
        #     column = 3
        #     sheet.write(row, 0, sequence, number_style)
        #     sheet.write(row, 1, manager.barcode, number_style)
        #     sheet.write(row, 2, manager.name, number_style)
        #     manager_attendance_domain = [
        #         ('employee_id', '=', manager.id), ('check_in', '>=', date_from),
        #         ('check_in', '<=', date_to)
        #     ]
        #     if objs.department_ids:
        #         manager_attendance_domain.append(('employee_id.department_id', 'in', objs.department_ids.ids))
        #     manager_attendance = self.env['hr.attendance'].search(manager_attendance_domain).mapped('check_in')
        #     manager_attendance = [att.date() for att in manager_attendance]
        #     manager_off = {'0', '1', '2', '3', '4', '5', '6'}.difference(set(manager.resource_calendar_id.attendance_ids.mapped('dayofweek')))
        #     manager_sick_off = self.env['hr.leave'].search([
        #         ('holiday_status_id', '=', sick_off.id), ('employee_ids', 'in', manager.ids)
        #     ])
        #     absents = 0
        #     for d in date_list:
        #         if d.date() in manager_attendance:
        #             sheet.write(row, column, 'P', number_style)
        #             day_present[d.date()] += 1
        #         elif str(d.weekday()) in manager_off:
        #             sheet.write(row, column, 'OFF', yellow_number_style)
        #         # elif d.date() >= manager_sick_off:
        #         #     sheet.write(row, column, 'OFF', number_style)
        #         else:
        #             sheet.write(row, column, 'A', absent_style)
        #             day_absent[d.date()] += 1
        #             absents += 1
        #         column += 1
        #     sheet.write(row, column, absents, number_style)
        #     row += 1
        # sheet.write(row, 2, 'Total', yellow_number_style)
        # column = 3
        # for key, value in day_present.items():
        #     sheet.write(row, column, value, yellow_number_style)
        #     column += 1
        # sheet.write(row, column, sum(day_present.values()), yellow_number_style)
        # row += 1
        # column = 3
        # for key, value in day_absent.items():
        #     sheet.write(row, column, value, yellow_number_style)
        #     column += 1
        # sheet.write(row, column, sum(day_absent.values()), yellow_number_style)