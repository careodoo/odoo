# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    personal_id = fields.Integer(string="Personal ID", required=False, related="employee_id.personal_id")

# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    # TODO Social Insurance fields
    insurance_salary = fields.Float(string="الراتب التأميني")
    company_percent = fields.Float(string="نسبة الشركة")
    incremental_insurance_salary = fields.Float()
    # TODO Allowances fields
    house_allowances = fields.Float(string="منحة غلاء معيشه")
    overtime_allowance = fields.Float(string="علاوة اضافيه")
    treatment_allowance = fields.Float(string="علاوة سنوات سابقه")
    transport_allowances = fields.Float(string="بدل انتقال")
    living_allowances = fields.Float(string="علاوة يوليو")
    nature_of_work_allowances = fields.Float(string="غلاء معيشة")
    telephone_allowance = fields.Float(string="بدل تليفون")

    # TODO NEW Allowances fields
    Regular_bonus_for_managers = fields.Float(string="مكافئة انتظام للمديرين",  required=False, )
    Regular_regularity_equivalent = fields.Float(string="مكافئة انتظام عادية",  required=False, )
    Incentive_bonus = fields.Float(string="مكافئات تشجيعيه",  required=False, )
    motivation = fields.Float(string="الحافز",  required=False, )
    profit_account = fields.Float(string="حساب ارباح",  required=False, )

    # TODO Deductions fields
    general_deductions = fields.Float()


    social_insurance_deductions = fields.Float(string="سلفة تأمينات")
    medical_insurance_deductions = fields.Float(string="سلفة ايصال نقدية")
    fingerprint_deductions = fields.Float(string="صندوق طوارئ")
    administrative_deductions = fields.Float(string="صندوق زماله")
    absence_without_permission_deductions = fields.Float(string="تأمين اجتماعي")
    absence_discount_without_credit_deductions = fields.Float(string="رعاية صحيه")
    profit_tax_percent = fields.Float(string="اشتراك جمعية")

    # @api.constrains('insurance_salary')
    # def check_insurance_salary(self):
    #     if self.insurance_salary < 1200:
    #         raise ValidationError(_('Minimum insurance salary 1200'))
    #     else:
    #         return

    @api.model
    def _cron_update_insurance_salary(self):
        contracts_object = self.env['hr.contract'].search([('state', '=', 'open'), ('active', '=', True)])
        print("contracts_object", contracts_object)
        for contract in contracts_object:
            if contract.insurance_salary:
                contract.incremental_insurance_salary += contract.insurance_salary * 0.07 + contract.insurance_salary
