from odoo import fields, models, api
from datetime import date


class Employee(models.Model):
    _inherit = 'hr.employee'

    social_affairs_title_eng = fields.Char()
    work_department = fields.Char(related='social_contract_id.work_department')
    work_department_eng = fields.Char(related='social_contract_id.work_department_eng')
    country_id_translated = fields.Char(compute='translate_country_to_arabic', store=True)
    company_country_id_translated = fields.Char(default='الكويت')
    day_translated = fields.Char(compute='translate_day_to_arabic')
    passport_type_translated = fields.Char(compute='translate_passport_type')
    gender_translated = fields.Char(compute='translate_gender')

    def translate_day_to_arabic(self):
        for rec in self:
            if date.today().strftime("%A") == 'Saturday':
                rec.day_translated = 'السبت'
            elif date.today().strftime("%A") == 'Sunday':
                rec.day_translated = 'الأحد'
            elif date.today().strftime("%A") == 'Monday':
                rec.day_translated = 'الأثنين'
            elif date.today().strftime("%A") == 'Tuesday':
                rec.day_translated = 'الثلاثاء'
            elif date.today().strftime("%A") == 'Wednesday':
                rec.day_translated = 'الأربعاء'
            elif date.today().strftime("%A") == 'Thursday':
                rec.day_translated = 'الخميس'
            else:
                rec.day_translated = 'الجمعة'


    def translate_gender(self):
        for rec in self:
            if rec.gender == 'male':
                rec.gender_translated = 'ذكر'
            elif rec.gender == 'female':
                rec.gender_translated = 'انثى'
            else:
                rec.gender_translated = False

    def translate_passport_type(self):
        for rec in self:
            if rec.passport_type == 'normal':
                rec.passport_type_translated = 'عادي'
            elif rec.passport_type == 'diplomat':
                rec.passport_type_translated = 'دبلوماسي'
            else:
                rec.passport_type_translated = False

    @api.depends('country_id')
    def translate_country_to_arabic(self):
        for rec in self:
            if rec.country_id.name == 'Bangladesh':
                rec.country_id_translated = 'بنغلادش'
            elif rec.country_id.name == 'Eritrea':
                rec.country_id_translated = 'إريتريا'
            elif rec.country_id.name == 'Ethiopia':
                rec.country_id_translated = 'أثيوبيا'
            elif rec.country_id.name == 'France':
                rec.country_id_translated = 'فرنسا'
            elif rec.country_id.name in ['India', 'india']:
                rec.country_id_translated = 'الهند'
            elif rec.country_id.name == 'Jordan':
                rec.country_id_translated = 'الأردن'
            elif rec.country_id.name == 'Lebanon':
                rec.country_id_translated = 'لبنان'
            elif rec.country_id.name == 'Nepal':
                rec.country_id_translated = 'نيبال'
            elif rec.country_id.name == 'Pakistan':
                rec.country_id_translated = 'باكستان'
            elif rec.country_id.name == 'Philippines':
                rec.country_id_translated = 'الفلبين'
            elif rec.country_id.name == 'Somalia':
                rec.country_id_translated = 'الصومال'
            elif rec.country_id.name == 'Sri Lanka':
                rec.country_id_translated = 'سريلانكا'
            elif rec.country_id.name in ['iraq', 'Iraq']:
                rec.country_id_translated = 'العراق'
            elif rec.country_id.name in ['egypt', 'Egypt', 'مصر']:
                rec.country_id_translated = 'مصر'
            elif rec.country_id.name in ['الكويت', 'Kuwait', 'kuwait']:
                rec.country_id_translated = 'الكويت'
            else:
                rec.country_id_translated = False

    def action_open_resident_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Arrival Resident',
            'view_mode': 'form',
            'res_model': 'arrival.resident.wizard',
            'context': {
                'default_employee_id': self.id
            },
            'target': 'new',
        }


class Department(models.Model):
    _inherit = 'hr.department'

    short_code = fields.Char()
