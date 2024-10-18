from odoo import _, models


class ReportXlsxAbstract(models.AbstractModel):
  _name = "report.report_xlsx_dynamic.abstract"
  _description = "Abstract XLSX Dynamic Report"
  _inherit = "report.report_xlsx.abstract"

  def write_dynamic_report(self, sheet, data):
    for row_num, row in enumerate(data):
      col_shift = 0  # Initialize column shift for each row
      for col_num, cell in enumerate(row):
        adjusted_col_num = col_num + col_shift
        if isinstance(cell, dict):
          rowspan = cell.get('rowspan', 1)  # Default to 1 to cover the cell itself
          colspan = cell.get('colspan', 1)  # Default to 1 to cover the cell itself
          if colspan > 1 or rowspan > 1:
            sheet.merge_range(
                row_num,
                adjusted_col_num,
                row_num + rowspan - 1,
                adjusted_col_num + colspan - 1,
                cell['cell_value'],
                cell.get('cell_format')
            )
          else:
            sheet.write(
                row_num,
                adjusted_col_num,
                cell['cell_value'],
                cell.get('cell_format'),
            )
          col_shift += colspan - 1  # Increase shift by colspan minus 1 (for the current cell)
        else:
          sheet.write(
              row_num,
              adjusted_col_num,
              cell,
          )
