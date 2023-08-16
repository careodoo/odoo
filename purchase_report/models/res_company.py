from odoo import fields, models, api


class Company(models.Model):
    _inherit = 'res.company'

    company_identification_id = fields.Char()
    company_english_name = fields.Char()
    company_ref = fields.Char(string='رقم المرجع/الشخصية الاعتبارية')
    auto_number = fields.Char(string='الرقم الآلي للعنوان')
    address_zone = fields.Char('المنطقة')
    address_block = fields.Char('القطعة')
    address_building = fields.Char('المبنى')
