from odoo import models, fields, tools, _
from num2words import num2words
import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

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
                        amt_word="دينار",
                        )
        if not self.currency_id.is_zero(amount - integer_value):
            amount_words += ' ' + _('و') + tools.ustr(' {amt_value} {amt_word}').format(
                        amt_value=_num2words(fractional_value, lang=lang.iso_code),
                        amt_word="فلس",
                        )
        return amount_words + ' فقط لا غير '


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    unit_no = fields.Float(string='Unit') 