from odoo import  api, models,_


class ServiceTripXlsxReport(models.AbstractModel):
  _name = 'report.service_order.service_trip_xlsx_report'
  _inherit = 'report.report_xlsx_dynamic.abstract'
  _description = 'Service Trip Xlsx Report'

  @api.model
  def _prepare_report_data(self, docids, data):
    pass

  def generate_xlsx_report(self, workbook, form_data, docids):

    def prepare_custom_cell(cell_value, colspan=1, rowspan=1, style=None):
      cell_format = workbook.add_format(style or {})
      return {
          'cell_value': cell_value,
          'colspan': colspan,
          'rowspan': rowspan,
          'cell_format': cell_format,
      }

    primary_color = "#f2f2f2"
    report_header = [
        [None],
        [
            prepare_custom_cell("Client Name", style={"bg_color": primary_color}),
            "TEst",
            None,
            None,
            prepare_custom_cell("Pick-up Time", style={"bg_color": primary_color}),
            prepare_custom_cell(docids.pickuped_datetime,style={'num_format': 'dd/mm/yy hh:mm:ss'}),
        ],
        [
            prepare_custom_cell("Contract No", style={"bg_color": primary_color}),
            docids.project_id.experience_id.x_studio_contract_no,
            None,
            None,
            prepare_custom_cell("Total Weight (KG)", style={"bg_color": primary_color}),
            docids.total_weight,
        ],
        [
            prepare_custom_cell("Trip No", style={"bg_color": primary_color}),
            docids.sequence,
            None,
            None,
            prepare_custom_cell("Total Quantity", style={"bg_color": primary_color}),
            docids.total_quantity,
        ],
        [
            prepare_custom_cell("Trip Date", style={"bg_color": primary_color}),
            prepare_custom_cell(docids.trip_date, style={'num_format': 'dd/mm/yy'}),
            None,
            None,
            prepare_custom_cell("Status", style={"bg_color": primary_color}),
            docids.states,
        ],
        [
            prepare_custom_cell(
                "Disposable Equipment's Report",
                colspan=7,
                style={
                    'bold': True,
                    'align': 'center'
                },
            )
        ],
        [None],
        [
            prepare_custom_cell(value, style={
                'bold': True,
                'border': 1,
            }) for value in
            ["Item", "Quantity", "Weight (KG)", "Total Weight (KG)", "Total Pickup", "Remarks"]
        ],
        *[[
            line.item_id.name,
            line.quantity,
            line.weight,
            docids.total_weight,
            docids.total_weight,
            "Remarks",
        ] for line in docids.trip_line_ids],
        ["Totals", docids.total_quantity, None, docids.total_weight, None, None],
        [None],
        [None],
        [
            prepare_custom_cell("PHOTOS AND VIDEOS", colspan=2),
            None,
            None,
            None,
            prepare_custom_cell("CARE STAMP", colspan=2),
        ],
        [None],
        [
            prepare_custom_cell(
                "Notes",
                colspan=7,
            ),
        ],
        [
            prepare_custom_cell(
                "All above Items collected from Talabat Company has been terminated by CARE Company and delivered to the government waste incinerators.",
                colspan=7,
                style={'text_wrap': True},
            )
        ],
    ]
    report_name = _('Service Trip Report')
    sheet = workbook.add_worksheet(report_name[:31])
    sheet.set_column(0, 6, 18)
    self.write_dynamic_report(
        sheet,
        report_header,
    )
