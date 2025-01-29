from odoo import models, fields, api
from num2words import num2words

class AccountMove(models.Model):
    _inherit = 'account.move'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    def number_to_arabic(self,number):
        float_number = str(number).split('.')
        float_num = num2words(float_number[0], lang='ar')
        float_num_s = num2words(float_number[1], lang='ar')
        return 'فقط / ' + float_num + ' و ' + float_num_s + ' دينار كويتي لا غير.'

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    unit_no = fields.Float(string='Unit') 