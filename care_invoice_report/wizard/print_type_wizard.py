from odoo import models, fields, _
from odoo.exceptions import ValidationError


class PrintTypeWizard(models.TransientModel):
    
    _name = 'print.type.wizard'
    
    
    lang = fields.Selection(
        string='Lang',
        selection=[('regular', 'Regular'), ('en', 'En'), ('ar', 'AR')]
    )

    headering = fields.Selection(
        string='Headering',
        selection=[('with', 'With Header'), ('without', 'Without Header')]
    )
    

    def action_confirm(self):
        invoice = self.env['account.move'].browse(self.env.context['active_id'])
        if self.lang == 'regular' and self.headering == 'with':
            return self.env.ref('care_invoice_report.action_regular_invoice_report').report_action(invoice)
        if self.lang == 'regular' and self.headering == 'without':
            return self.env.ref('care_invoice_report.action_regular_invoice_without_header_report').report_action(invoice)
        if self.lang == 'en' and self.headering == 'with':
            return self.env.ref('care_invoice_report.action_en_invoice_report').report_action(invoice)
        if self.lang == 'en' and self.headering == 'without':
            return self.env.ref('care_invoice_report.action_en_invoice_without_header_report').report_action(invoice)
        if self.lang == 'ar' and self.headering == 'with':
            return self.env.ref('care_invoice_report.action_ar_invoice_report').report_action(invoice)
        if self.lang == 'ar' and self.headering == 'without':
            return self.env.ref('care_invoice_report.action_ar_invoice_without_header_report').report_action(invoice)
        else:
            pass
        