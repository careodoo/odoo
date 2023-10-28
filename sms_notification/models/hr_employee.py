from odoo import fields, models, api
from datetime import datetime, date


class Employee(models.Model):
    _inherit = 'hr.employee'

    sms_notified = fields.Boolean()
    disable_notification = fields.Boolean()

    @api.model
    def remind_birthday(self):
        employees = self.env['hr.employee'].search([
            ('birthday', '!=', False), ('sms_notified', '=', False), ('disable_notification', '=', False)
        ])
        for rec in employees:
            if rec.birthday == date.today():
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'employee_birthday'), ('globally_access', '=', False)])
                for sms_template_obj in sms_template_objs:
                    company_country_calling_code = self.env.user.company_id.country_id.phone_code
                    mobile = rec.phone or rec.mobile_phone or rec.work_phone
                    emp_mobile = "+{code}{mobile}".format(code=company_country_calling_code, mobile=mobile)
                    if emp_mobile:
                        sms_template_obj.send_birthday_sms_using_template(
                            emp_mobile, sms_template_obj, obj=rec)
                        rec.sms_notified = True

