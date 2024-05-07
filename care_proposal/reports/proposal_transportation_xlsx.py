from odoo import models


class ProposalTransportationReportXlsx(models.AbstractModel):
    _name = 'report.care_proposal.proposal_transportation_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        header_style = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left'
        })
        header_style1 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'
        })
        header_style2 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#d9d9d9'
        })
        header_style3 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#fbe5d6'
        })
        header_style4 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left', 'bg_color': '#c5e0b4'
        })
        header_style5 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#c5e0b4'
        })
        sheet = workbook.add_worksheet('Proposal Sheet Report')
        proposal = objs[0]
        sheet.merge_range('A2:C2', f'Provide Cleaning Services For {proposal.partner_id.name}', header_style2)

        # transportation
        row = 5
        sheet.merge_range(row, 0, row, 2, 'Transportation', header_style3)
        row += 1
        sheet.write(row, 0, 'Transportation', header_style4)
        sheet.write(row, 1, 'Cost', header_style5)
        sheet.write(row, 2, 'Period', header_style5)
        row += 1
        for line in proposal.transportation_ids:
            sheet.write(row, 0, line.transportation_id.name, header_style)
            sheet.write(row, 1, line.cost, header_style1)
            sheet.write(row, 2, line.period, header_style1)
            row += 1

        sheet.set_column(0, 0, 40)
        sheet.set_column(1, 2, 20)
