import io
import base64
from odoo import models
from datetime import date


class ProposalSheetReportXlsx(models.AbstractModel):
    _name = 'report.care_proposal.proposal_sheet_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        header_style = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'
        })
        header_style1 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left'
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
        header_style5 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left', 'bg_color': '#c5e0b4'
        })
        header_style6 = workbook.add_format({
            'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left', 'font_size': 20, 'valign': 'vcenter'
        })
        sheet = workbook.add_worksheet('Proposal Sheet Report')
        proposal = objs[0]
        # header
        sheet.set_row(0, 100)
        if proposal.logo:
            proposal_logo = io.BytesIO(base64.b64decode(proposal.logo))
            sheet.insert_image(0, 0, "proposal_logo.png", {'image_data': proposal_logo, 'x_scale': 0.5, 'y_scale': 0.5})
        if proposal.barcode:
            barcode = self.env['ir.actions.report'].barcode(barcode_type='auto', value=proposal.barcode, width=300, height=100)
            barcode = base64.b64encode(barcode)
            proposal_barcode = io.BytesIO(base64.b64decode(barcode))
            sheet.insert_image(0, 1, "proposal_barcode.png", {'image_data': proposal_barcode, 'x_scale': 0.48, 'y_scale': 0.6})
        sheet.write(0, 2, 'Service Pricing', header_style6)
        if proposal.qr_image:
            proposal_qr = io.BytesIO(base64.b64decode(proposal.qr_image))
            sheet.insert_image(0, 3, "proposal_qr.png", {'image_data': proposal_qr, 'x_scale': 0.15, 'y_scale': 0.15})
        sheet.write(0, 4, str(date.today()), header_style6)

        sheet.merge_range('A2:G2', f'Pricing for Provide Cleaning Services For {proposal.partner_id.name}', header_style2)
        # services
        sheet.merge_range('A4:G4', 'Services', header_style3)

        sheet.write('A6:A6', 'Description', header_style5)
        sheet.write('A7:A7', 'Salary', header_style1)
        sheet.write('A8:A8', 'Residency', header_style1)
        sheet.write('A9:A9', 'Accommodation', header_style1)
        sheet.write('A10:A10', 'Uniform', header_style1)
        sheet.write('A11:A11', 'Leave & Indemnity', header_style1)
        sheet.write('A12:A12', 'Staff Insurance', header_style1)
        sheet.write('A13:A13', 'Bank Charge', header_style1)
        sheet.write('A14:A14', 'Medical Certificate', header_style1)
        sheet.write('A15:A15', 'Faced Cleaning', header_style1)
        sheet.write('A16:A16', 'Commission', header_style1)
        sheet.write('A17:A17', 'Other', header_style1)
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
        sheet.write('A21:A21', 'Name', header_style5)
        sheet.write('B21:B21', 'Cost', header_style4)
        sheet.write('C21:C21', 'Profit%', header_style4)
        sheet.write('D21:D21', 'Sales Price', header_style4)
        sheet.write('E21:E21', 'Net Profit', header_style4)
        sheet.write('F21:F21', '', header_style4)
        sheet.write('G21:G21', '', header_style4)

        row = 21
        total_net_profit = 0
        for pricing_line in proposal.pricing_ids:
            net_profit = pricing_line.sales_price - pricing_line.cost
            total_net_profit += net_profit
            sheet.write(row, 0, pricing_line.name, header_style1)
            sheet.write(row, 1, pricing_line.cost, header_style)
            sheet.write(row, 2, pricing_line.profit_percentage, header_style)
            sheet.write(row, 3, pricing_line.sales_price, header_style)
            sheet.write(row, 4, net_profit, header_style)
            sheet.write(row, 5, '', header_style)
            sheet.write(row, 6, '', header_style)
            row += 1
        sheet.merge_range(row, 0, row, 2, 'Totals', header_style2)
        total_sales_price = sum(proposal.pricing_ids.mapped('sales_price'))
        sheet.write(row, 3, total_sales_price, header_style)
        sheet.write(row, 4, total_net_profit, header_style)

        # summary
        row += 1
        sheet.merge_range(row, 0, row, 6, 'Summary', header_style3)
        row += 1
        sheet.write(row, 0, 'Manpower Quantity', header_style4)
        sheet.write(row, 1, 'Material Amount', header_style4)
        sheet.write(row, 2, 'Equipment Amount', header_style4)
        sheet.write(row, 3, 'Transportation Amount', header_style4)
        sheet.write(row, 4, 'Salary Amount', header_style4)
        sheet.write(row, 5, 'Total Cost', header_style4)
        sheet.write(row, 6, 'Total Sales', header_style4)

        row += 1
        sheet.write(row, 0, proposal.manpower_quantity, header_style)
        sheet.write(row, 1, proposal.material_amount, header_style)
        sheet.write(row, 2, proposal.equipment_amount, header_style)
        sheet.write(row, 3, proposal.transportation_amount, header_style)
        sheet.write(row, 4, proposal.salary_amount, header_style)
        sheet.write(row, 5, proposal.total_cost, header_style)
        sheet.write(row, 6, sum(proposal.pricing_ids.mapped('sales_price')), header_style)

        sheet.set_column(0, 6, 20)

    def get_service_item_cost(self, service, type):
        item = service.line_ids.filtered(lambda l: l.type == type)
        return item.cost if item else ''
