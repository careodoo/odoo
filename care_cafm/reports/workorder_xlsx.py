# -*- coding: utf-8 -*-
from odoo import models, _


class WorkorderXlsx(models.AbstractModel):
    _name = 'report.care_cafm.report_workorder_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, workorders):
        sheet = workbook.add_worksheet('Work Orders')
        sheet.right_to_left()
        bold = workbook.add_format({'bold': True})
        head = workbook.add_format({'bold': True, 'bg_color': '#1e5eff', 'font_color': 'white',
                                    'border': 1, 'align': 'center'})
        cell = workbook.add_format({'border': 1})
        over = workbook.add_format({'border': 1, 'bg_color': '#fdecea'})
        title = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#0b3ec9'})
        sheet.merge_range(0, 0, 0, 9, _('أوامر العمل — CAFM'), title)
        headers = [_('الرقم'), _('العنوان'), _('المرفق'), _('الموقع'), _('الخدمة'),
                   _('المُسنَد إليه'), _('الحالة'), _('الموعد النهائي'), _('المدة (د)'), _('متأخر؟')]
        for c, h in enumerate(headers):
            sheet.write(2, c, h, head)
        widths = [16, 26, 18, 18, 16, 18, 12, 18, 12, 10]
        for c, w in enumerate(widths):
            sheet.set_column(c, c, w)
        row = 3
        state_lbl = dict(self.env['care.cafm.workorder']._fields['state'].selection)
        for wo in workorders:
            fmt = over if wo.is_overdue else cell
            sheet.write(row, 0, wo.name or '', cell)
            sheet.write(row, 1, wo.title or '', cell)
            sheet.write(row, 2, wo.facility_id.name or '', cell)
            sheet.write(row, 3, wo.location_id.name or '', cell)
            sheet.write(row, 4, wo.service_id.name or '', cell)
            sheet.write(row, 5, wo.employee_id.name or '', cell)
            sheet.write(row, 6, state_lbl.get(wo.state, ''), cell)
            sheet.write(row, 7, str(wo.deadline or ''), cell)
            sheet.write(row, 8, round(wo.duration_minutes, 1), cell)
            sheet.write(row, 9, _('نعم') if wo.is_overdue else _('لا'), fmt)
            row += 1
