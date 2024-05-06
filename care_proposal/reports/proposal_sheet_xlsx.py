from odoo import models


class ProposalSheetReportXlsx(models.AbstractModel):
    _name = 'report.care_proposal.proposal_sheet_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        header_style = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'
        })
        header_style2 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#d9d9d9'
        })
        header_style3 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#fbe5d6'
        })
        header_style4 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'bg_color': '#c5e0b4'
        })
        sheet = workbook.add_worksheet('Proposal Sheet Report')
        proposal = objs[0]
        sheet.merge_range('A2:G2', f'Provide Cleaning Services For {proposal.partner_id.name}', header_style2)
        # services
        sheet.merge_range('A4:G4', 'Services', header_style3)

        sheet.write('A6:A6', 'Description', header_style4)
        sheet.write('A7:A7', 'Salary', header_style)
        sheet.write('A8:A8', 'Residency', header_style)
        sheet.write('A9:A9', 'Accommodation', header_style)
        sheet.write('A10:A10', 'Uniform', header_style)
        sheet.write('A11:A11', 'Leave & Indemnity', header_style)
        sheet.write('A12:A12', 'Staff Insurance', header_style)
        sheet.write('A13:A13', 'Bank Charge', header_style)
        sheet.write('A14:A14', 'Medical Certificate', header_style)
        sheet.write('A15:A15', 'Faced Cleaning', header_style)
        sheet.write('A16:A16', 'Commission', header_style)
        sheet.write('A17:A17', 'Other', header_style)
        sheet.write('A18:A18', 'Total', header_style2)

        col = 1
        for service_line in proposal.service_ids:
            service = service_line.proposal_service_id
            sheet.write(5, col, service.name, header_style4)
            sheet.write(6, col, self.get_service_item_cost(service, 'salary'), header_style)
            sheet.write(7, col, self.get_service_item_cost(service, 'residency'), header_style)
            sheet.write(8, col, self.get_service_item_cost(service, 'accommodation'), header_style)
            sheet.write(9, col, self.get_service_item_cost(service, 'uniform'), header_style)
            sheet.write(10, col, self.get_service_item_cost(service, 'leave'), header_style)
            sheet.write(11, col, self.get_service_item_cost(service, 'insurance'), header_style)
            sheet.write(12, col, self.get_service_item_cost(service, 'bank_charge'), header_style)
            sheet.write(13, col, self.get_service_item_cost(service, 'medical'), header_style)
            sheet.write(14, col, self.get_service_item_cost(service, 'cleaning'), header_style)
            sheet.write(15, col, self.get_service_item_cost(service, 'commission'), header_style)
            sheet.write(16, col, self.get_service_item_cost(service, 'other'), header_style)
            sheet.write(17, col, service_line.total_cost, header_style2)
            col += 1

        # pricing
        sheet.merge_range('A20:G20', 'Pricing', header_style3)
        sheet.write('A21:A21', 'Name', header_style4)
        sheet.write('B21:B21', 'Cost', header_style4)
        sheet.write('C21:C21', 'Profit%', header_style4)
        sheet.write('D21:D21', 'Sales Price', header_style4)
        sheet.write('E21:E21', '', header_style4)
        sheet.write('F21:F21', '', header_style4)
        sheet.write('G21:G21', '', header_style4)

        row = 21
        for pricing_line in proposal.pricing_ids:
            sheet.write(row, 0, pricing_line.name, header_style)
            sheet.write(row, 1, pricing_line.cost, header_style)
            sheet.write(row, 2, pricing_line.profit_percentage, header_style)
            sheet.write(row, 3, pricing_line.sales_price, header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1

        # scopes
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Scopes', header_style3)
        row += 1
        sheet.write(row, 0, 'Scope', header_style4)
        sheet.write(row, 1, 'Schedule', header_style4)
        sheet.write(row, 2, '', header_style4)
        sheet.write(row, 3, '', header_style4)
        sheet.write(row, 4, '', header_style4)
        sheet.write(row, 5, '', header_style4)
        sheet.write(row, 6, '', header_style4)
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
            sheet.write(row, 1, schedule, header_style)
            sheet.write(row, 2, '', header_style)
            sheet.write(row, 3, '', header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1
        # manpower
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Manpower', header_style3)
        row += 1
        sheet.write(row, 0, 'Manpower', header_style4)
        sheet.write(row, 1, 'Nationality', header_style4)
        sheet.write(row, 2, 'Gender', header_style4)
        sheet.write(row, 3, 'Quantity', header_style4)
        sheet.write(row, 4, 'Service', header_style4)
        sheet.write(row, 5, 'Salary', header_style4)
        sheet.write(row, 6, 'Total Salary', header_style4)
        row += 1
        for man_line in proposal.manpower_ids:
            sheet.write(row, 0, man_line.proposal_manpower_id.name, header_style)
            sheet.write(row, 1, man_line.nationality.name, header_style)
            sheet.write(row, 2, man_line.gender, header_style)
            sheet.write(row, 3, man_line.quantity, header_style)
            sheet.write(row, 4, man_line.service_id.proposal_service_id.name, header_style)
            sheet.write(row, 5, man_line.salary, header_style)
            sheet.write(row, 6, man_line.total_salary, header_style)
            row += 1
        # material
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Materials', header_style3)
        row += 1
        sheet.write(row, 0, 'Material', header_style4)
        sheet.write(row, 1, 'Quantity', header_style4)
        sheet.write(row, 2, 'Cost', header_style4)
        sheet.write(row, 3, 'Total', header_style4)
        sheet.write(row, 4, '', header_style4)
        sheet.write(row, 5, '', header_style4)
        sheet.write(row, 6, '', header_style4)
        row += 1
        for mat_line in proposal.material_ids:
            sheet.write(row, 0, mat_line.product_id.name, header_style)
            sheet.write(row, 1, mat_line.quantity, header_style)
            sheet.write(row, 2, mat_line.cost, header_style)
            sheet.write(row, 3, mat_line.total_amount, header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1

        # equipments
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Equipments', header_style3)
        row += 1
        sheet.write(row, 0, 'Equipment', header_style4)
        sheet.write(row, 1, 'Quantity', header_style4)
        sheet.write(row, 2, 'Cost', header_style4)
        sheet.write(row, 3, 'Total', header_style4)
        sheet.write(row, 4, '', header_style4)
        sheet.write(row, 5, '', header_style4)
        sheet.write(row, 6, '', header_style4)
        row += 1
        for eq_line in proposal.equipment_ids:
            sheet.write(row, 0, eq_line.product_id.name, header_style)
            sheet.write(row, 1, eq_line.quantity, header_style)
            sheet.write(row, 2, eq_line.cost, header_style)
            sheet.write(row, 3, eq_line.total_amount, header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1

        # transportations
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Transportations', header_style3)
        row += 1
        sheet.write(row, 0, 'Transportation', header_style4)
        sheet.write(row, 1, 'Cost', header_style4)
        sheet.write(row, 2, 'Period', header_style4)
        sheet.write(row, 3, '', header_style4)
        sheet.write(row, 4, '', header_style4)
        sheet.write(row, 5, '', header_style4)
        sheet.write(row, 6, '', header_style4)

        row += 1
        for tr_line in proposal.transportation_ids:
            sheet.write(row, 0, tr_line.transportation_id.name, header_style)
            sheet.write(row, 1, tr_line.cost, header_style)
            sheet.write(row, 2, tr_line.period, header_style)
            sheet.write(row, 3, '', header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1

        # terms
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Terms', header_style3)
        row += 1
        sheet.write(row, 0, 'Term', header_style4)
        sheet.write(row, 1, '', header_style4)
        sheet.write(row, 2, '', header_style4)
        sheet.write(row, 3, '', header_style4)
        sheet.write(row, 4, '', header_style4)
        sheet.write(row, 5, '', header_style4)
        sheet.write(row, 6, '', header_style4)

        row += 1
        for term_line in proposal.term_ids:
            sheet.write(row, 0, term_line.term_id.name, header_style)
            sheet.write(row, 1, '', header_style)
            sheet.write(row, 2, '', header_style)
            sheet.write(row, 3, '', header_style)
            sheet.write(row, 4, '', header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)

            row += 1

        # summary
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Summary', header_style3)
        row += 1
        sheet.write(row, 0, 'Service Quantity', header_style4)
        sheet.write(row, 1, 'Manpower Quantity', header_style4)
        sheet.write(row, 2, 'Material Amount', header_style4)
        sheet.write(row, 3, 'Equipment Amount', header_style4)
        sheet.write(row, 4, 'Transportation Amount', header_style4)
        sheet.write(row, 5, 'Salary Amount', header_style4)
        sheet.write(row, 6, 'Total Cost', header_style4)

        row += 1
        sheet.write(row, 0, proposal.service_quantity, header_style)
        sheet.write(row, 1, proposal.manpower_quantity, header_style)
        sheet.write(row, 2, proposal.material_amount, header_style)
        sheet.write(row, 3, proposal.equipment_amount, header_style)
        sheet.write(row, 4, proposal.transportation_amount, header_style)
        sheet.write(row, 5, proposal.salary_amount, header_style)
        sheet.write(row, 6, proposal.total_cost, header_style)

        sheet.set_column(0, 6, 20)

    def get_service_item_cost(self, service, type):
        item = service.line_ids.filtered(lambda l: l.type == type)
        return item.cost if item else ''
