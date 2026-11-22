# -*- coding: utf-8 -*-
# توسعة ملف الموظف: سجلّات اعتماد التوقيع الإلكتروني + حالة مختصرة (محميّة بالعرض).
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    esign_enrollment_ids = fields.One2many(
        'care.esign.enrollment', 'employee_id', string='اعتمادات التوقيع الإلكتروني')
    esign_enrollment_count = fields.Integer(
        string='عدد الاعتمادات', compute='_compute_esign_enrollment')
    esign_state = fields.Selection([
        ('none', 'لا يوجد'),
        ('draft', 'طلب'),
        ('to_approve', 'بانتظار الاعتماد'),
        ('approved', 'بانتظار توقيع الموظف'),
        ('active', 'فعّال'),
        ('disabled', 'معطّل'),
        ('rejected', 'مرفوض'),
    ], string='حالة التوقيع الإلكتروني', compute='_compute_esign_enrollment')

    @api.depends('esign_enrollment_ids.state')
    def _compute_esign_enrollment(self):
        for emp in self:
            recs = emp.esign_enrollment_ids
            emp.esign_enrollment_count = len(recs)
            # الأحدث غير المرفوض يحدّد الحالة الظاهرة
            current = recs.filtered(lambda r: r.state != 'rejected')[:1] or recs[:1]
            emp.esign_state = current.state if current else 'none'

    def action_open_esign_enrollments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'اعتماد التوقيع الإلكتروني',
            'res_model': 'care.esign.enrollment',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
