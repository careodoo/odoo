from odoo import models, fields, api, tools, _
from num2words import num2words
import logging
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    barcode = fields.Char(default=generate_barcode)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    internal_ref = fields.Char(string='Internal Referance')
    labor_service = fields.Boolean()

    def action_print_care(self):
        return {
            'name': _('Print Type'),
            'type': 'ir.actions.act_window',
            'res_model': 'print.type.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('care_invoice_report.print_type_wizard_view_form').id,
            'context': {
                'active_id': self.id,
                'refuse': True,
            }
        }

    def number_to_arabic(self, amount):
        self.ensure_one()
        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()
        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(self.currency_id.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang = self.env['res.lang'].search([('code', '=', 'ar_001')])
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
                        amt_value=_num2words(integer_value, lang=lang.iso_code),
                        amt_word="دينار كويتي",
                        )
        if not self.currency_id.is_zero(amount - integer_value):
            amount_words += ' ' + _('و') + tools.ustr(' {amt_value} {amt_word}').format(
                        amt_value=_num2words(fractional_value, lang=lang.iso_code),
                        amt_word="فلس",
                        )
        return ' فقط ' + amount_words + ' فقط لا غير '
    
    def number_to_english(self, amount):
        self.ensure_one()
        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()
        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(self.currency_id.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang = self.env['res.lang'].search([('iso_code', '=', 'en')])
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
                        amt_value=_num2words(integer_value, lang=lang.iso_code),
                        amt_word=self.currency_id.currency_unit_label or self.currency_id.name,
                        )
        if not self.currency_id.is_zero(amount - integer_value):
            amount_words += ' ' + _('and') + tools.ustr(' {amt_value} {amt_word}').format(
                        amt_value=_num2words(fractional_value, lang=lang.iso_code),
                        amt_word=self.currency_id.currency_subunit_label or 'Cents',
                        )
        return ' Only ' + amount_words + ' Only '

    def get_invoice_portal_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = base_url + self.get_portal_url()
        return url


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    unit_no = fields.Float(string='Unit')
    labors = fields.Integer(default=1)
    days = fields.Integer(default=1)
    date_from = fields.Date(string='Date From', compute='_compute_dates', readonly=False, store=True)
    date_to = fields.Date(string='Date To', compute='_compute_dates', readonly=False, store=True)

    @api.depends('move_id','move_id.date_from', 'move_id.date_to')
    def _compute_dates(self):
        for rec in self.move_id:
            if rec.date_from and rec.date_to:
                self.date_from = rec.date_from
                self.date_to = rec.date_to
            else:
                self.date_from = False
                self.date_to = False

    @api.onchange('product_id')
    def onchange_labors_service(self):
        if self.product_id.labor_service:
            self.days = self.product_id.days_per_month

