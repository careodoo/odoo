from odoo import models


class ProposalScopeReportXlsx(models.AbstractModel):
    _name = 'report.care_proposal.proposal_scope_xlsx_report'
    _description = 'Proposal Scope Report XLSX'
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
        sheet.merge_range('A2:B2', f'Provide Cleaning Services For {proposal.partner_id.name}', header_style2)

        # scopes
        row = 5
        sheet.merge_range(row, 0, row, 1, 'Scopes', header_style3)
        row += 1
        sheet.write(row, 0, 'Scope', header_style4)
        sheet.write(row, 1, 'Schedule', header_style5)
        row += 1
        for scope_line in proposal.scope_ids:
            if scope_line.schedule == 'daily':
                schedule = 'Daily'
            elif scope_line.schedule == 'weekly':
                schedule = 'Weekly'
            elif scope_line.schedule == 'monthly':
                schedule = 'Monthly'
            elif scope_line.schedule == 'custom':
                schedule = 'As Per Request'
            else:
                schedule = 'Other'
            sheet.write(row, 0, scope_line.proposal_scope_id.name, header_style)
            sheet.write(row, 1, schedule, header_style1)
            row += 1
        sheet.set_column(0, 0, 100)
        sheet.set_column(1, 1, 15)
