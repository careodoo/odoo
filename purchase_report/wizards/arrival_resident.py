from odoo import fields, models, api


class ArrivalResident(models.Model):
    _name = 'arrival.resident.wizard'
    _description = 'Arrival Resident Wizard'

    employee_ids = fields.Many2many('hr.employee')
    state = fields.Selection(selection=[
        ('asimah', 'العاصمة'),
        ('hawalli', 'حولي'),
        ('farwaniyah', 'الفروانية'),
        ('mubarak', 'مبارك الكبير'),
        ('ahmadi', 'اﻷحمدي'),
        ('jahra', 'الجهراء'),
    ], default='asimah')
    order_type = fields.Selection(selection=[
        ('enter', 'سمة دخول'),
        ('residence', 'إقامة'),
        ('absence', 'إذن غياب'),
    ], default='enter')
    order_reason = fields.Selection(selection=[
        ('1', 'عمالة منزلية'),
        ('2', 'عمل أهلي'),
        ('3', 'عمل بالحكومة'),
        ('4', 'إلتحاق بعائل'),
        ('5', 'للعلاج'),
        ('6', 'للدراسة'),
        ('7', 'للسياحة'),
        ('8', 'للمرور'),
        ('9', 'زيارة عائلية'),
        ('10', 'زيارة تجارية'),
        ('11', 'زيارة حكومية'),
        ('12', 'زيارة لعقود حكومية'),
        ('13', 'زيارة لسفارة'),
        ('14', 'سمة عودة'),
        ('15', 'سمة عودة عدة سفارت'),
        ('16', 'عودة عدة سفارت لسائق'),
        ('17', 'نشاط تجاري'),
        ('18', 'سائقي مركبات نقل'),
    ], default='1')
    order_reason2 = fields.Selection(selection=[
        ('1', 'إشعار مغادرة'),
        ('14', 'مؤقتة'),
        ('17', 'حكومة'),
        ('18', 'عمل أهلي'),
        ('19', 'شريك'),
        ('20', 'عمالة منزلية'),
        ('22', 'إلتحاق بعائل'),
        ('23', 'دراسة'),
        ('24', 'كفيل نفسه'),
    ], default='1')
    order_reason3 = fields.Selection(selection=[
        ('1', 'للدراسة'),
        ('2', 'للعلاج'),
        ('3', 'مرافق رب عمل'),
        ('4', 'حالات أخرى'),
    ], default='1')
    order_type2 = fields.Selection(selection=[
        ('1', 'إصدار'),
        ('2', 'إضافة'),
        ('3', 'إلغاء'),
        ('4', 'تجديد'),
        ('5', 'تعديل بيانات'),
        ('6', 'حذف'),
        ('7', 'نقل كفالة'),
        ('8', 'نقل معلومات'),
        ('9', 'تمديد'),
        ('10', 'تمديد + نقل معلومات'),
    ], default='1')

    def action_print_report(self):
        self.employee_ids = self.env['hr.employee'].search([('id', 'in', self._context.get('active_ids', []))])
        return self.env.ref('purchase_report.action_report_arrival_resident').report_action(self)