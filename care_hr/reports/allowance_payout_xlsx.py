# -*- coding: utf-8 -*-
# Excel export for the allowance disbursement request, via the OCA report_xlsx
# AbstractModel pattern (report_type="xlsx").
from odoo import models, _


class AllowancePayoutXlsx(models.AbstractModel):
    _name = 'report.care_hr.report_allowance_payout_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, payouts):
        for payout in payouts:
            sheet = workbook.add_worksheet((payout.name or 'Payout')[:31])
            sheet.right_to_left()
            bold = workbook.add_format({'bold': True})
            title = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#0b3ec9'})
            head = workbook.add_format({'bold': True, 'bg_color': '#1e5eff', 'font_color': 'white',
                                        'border': 1, 'align': 'center'})
            cell = workbook.add_format({'border': 1})
            money = workbook.add_format({'border': 1, 'num_format': '#,##0.000'})
            paid_f = workbook.add_format({'border': 1, 'bg_color': '#eafaf1'})
            unpaid_f = workbook.add_format({'border': 1, 'bg_color': '#fdecea'})

            sheet.merge_range(0, 0, 0, 6, _('طلب صرف البدلات — %s') % (payout.name or ''), title)
            method = dict(payout._fields['payment_method'].selection).get(payout.payment_method, '')
            sheet.write(1, 0, _('الفترة'), bold)
            sheet.write(1, 1, '%s ← %s' % (payout.date_from or '', payout.date_to or ''))
            sheet.write(1, 3, _('طريقة الدفع'), bold)
            sheet.write(1, 4, method)
            sheet.write(2, 0, _('القسم/المشروع'), bold)
            sheet.write(2, 1, payout.department_id.name or _('الكل'))
            sheet.write(2, 3, _('المطلوب صرفه'), bold)
            sheet.write(2, 4, payout.to_pay_amount, money)

            headers = [_('العامل'), _('الرقم الوظيفي'), _('القسم/المشروع'), _('نوع الاستحقاق'),
                       _('تاريخ الاستحقاق'), _('المبلغ'), _('الحالة')]
            row = 4
            for col, h in enumerate(headers):
                sheet.write(row, col, h, head)
            widths = [26, 14, 22, 20, 16, 14, 12]
            for col, w in enumerate(widths):
                sheet.set_column(col, col, w)

            row = 5
            total = 0.0
            for l in payout.line_ids:
                fmt = paid_f if l.is_paid else unpaid_f
                sheet.write(row, 0, l.employee_id.name or '', cell)
                sheet.write(row, 1, l.employee_id.employee_code or l.employee_id.barcode or '', cell)
                sheet.write(row, 2, l.department_id.name or '', cell)
                sheet.write(row, 3, l.allowance_type_id.name or '', cell)
                sheet.write(row, 4, str(l.allowance_date or ''), cell)
                sheet.write(row, 5, l.amount, money)
                sheet.write(row, 6, _('مصروف') if l.is_paid else _('غير مصروف'), fmt)
                total += l.amount
                row += 1
            sheet.write(row, 4, _('الإجمالي'), head)
            sheet.write(row, 5, total, money)
