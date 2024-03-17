from odoo import fields, models, api, _
from odoo.exceptions import UserError


class EmployeeBadgeReport(models.AbstractModel):
    _name = 'report.hr.print_employee_badge'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.employee'].browse(docids)
        for doc in docs:
            if doc.suspend_date:
                if not doc.can_print_reports:
                    raise UserError(f"you can't print report for suspended employee {doc.name}")
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.employee',
            'docs': docs,
        }
