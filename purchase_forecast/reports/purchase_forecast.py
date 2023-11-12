from odoo import models, fields, api


class PurchaseForecastReportXlsx(models.AbstractModel):
    _name = 'report.purchase_forecast.purchase_forecast_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        header_style = workbook.add_format(
            {'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})

        sheet = workbook.add_worksheet('Purchase Forecast')
        wizard = objs[0]
        sheet.merge_range('A1:C1', 'Purchase Forecast', header_style)

        sheet.write('A2:A2', 'Date', header_style)
        sheet.write('B2:B2', 'Product', header_style)
        sheet.write('C2:C2', 'Total', header_style)

        row = 2
        for line in wizard.line_ids:
            sheet.write(row, 0, str(line.date) or '', header_style)
            sheet.write(row, 1, line.product_id.name or '', header_style)
            sheet.write(row, 2, line.total or '', header_style)
            row += 1
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 50)
