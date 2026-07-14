# -*- coding: utf-8 -*-
from markupsafe import Markup, escape
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

# (field, arabic label) for the documents we track
EXPIRY_DOCS = [
    ('residency_end_date', 'الإقامة'),
    ('affairs_permit_end_date', 'تصريح الشؤون'),
    ('work_permit_expiration_date', 'تصريح العمل'),
    ('visa_expire', 'التأشيرة'),
]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    doc_expiry_next = fields.Date(compute='_compute_doc_expiry_next', store=True,
                                  string='أقرب انتهاء مستند')
    doc_expiry_days = fields.Integer(compute='_compute_doc_expiry_days',
                                     string='أيام حتى الانتهاء')

    @api.depends('residency_end_date', 'affairs_permit_end_date',
                 'work_permit_expiration_date', 'visa_expire')
    def _compute_doc_expiry_next(self):
        for emp in self:
            dates = [getattr(emp, f) for f, _l in EXPIRY_DOCS if getattr(emp, f, False)]
            emp.doc_expiry_next = min(dates) if dates else False

    def _compute_doc_expiry_days(self):
        today = fields.Date.today()
        for emp in self:
            emp.doc_expiry_days = (emp.doc_expiry_next - today).days if emp.doc_expiry_next else 0

    @api.model
    def _expiry_window_days(self):
        val = self.env['ir.config_parameter'].sudo().get_param('care_expiry.window_days')
        try:
            return int(val) if val else 30
        except (TypeError, ValueError):
            return 30

    @api.model
    def cron_document_expiry_alert(self):
        """Weekly digest to HR managers of documents expiring within the window."""
        window = self._expiry_window_days()
        today = fields.Date.today()
        limit = today + relativedelta(days=window)
        sections = []
        for field, label in EXPIRY_DOCS:
            emps = self.sudo().search(
                [(field, '>=', today), (field, '<=', limit)], order=field)
            if not emps:
                continue
            rows = ''.join(
                '<tr><td style="padding:5px 9px;border-bottom:1px solid #eef1f6;">%s</td>'
                '<td style="padding:5px 9px;border-bottom:1px solid #eef1f6;">%s</td>'
                '<td style="padding:5px 9px;border-bottom:1px solid #eef1f6;text-align:center;font-weight:bold;color:%s;">%s</td></tr>' % (
                    escape(e.name or ''), escape(e.barcode or '—'),
                    '#c0392b' if (getattr(e, field) - today).days <= 15 else '#e08a00',
                    escape(str(getattr(e, field))))
                for e in emps)
            sections.append(
                '<h3 style="margin:14px 0 4px;color:#15213b;font-size:15px;">%s (%d)</h3>'
                '<table style="width:100%%;border-collapse:collapse;font-size:13px;">'
                '<tr style="background:#f6f8fc;"><th style="padding:6px 9px;text-align:right;">الموظف</th>'
                '<th style="padding:6px 9px;text-align:right;">رقم العامل</th>'
                '<th style="padding:6px 9px;">تاريخ الانتهاء</th></tr>%s</table>' % (
                    escape(label), len(emps), rows))
        if not sections:
            return True
        managers = self.env.ref('hr.group_hr_manager').users.filtered(lambda u: u.email)
        if not managers:
            return True
        body = Markup(
            '<div style="max-width:640px;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
            'border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">'
            '<div style="background:#15213b;padding:14px 20px;">'
            '<span style="color:#f0663c;font-weight:bold;font-size:18px;">CARE</span>'
            '<span style="color:#aeb8cc;font-size:12px;"> · متابعة انتهاء المستندات</span></div>'
            '<div style="background:#e2513f;height:5px;"></div>'
            '<div style="padding:18px;">'
            '<h2 style="margin:0 0 6px;color:#15213b;font-size:17px;">⏳ مستندات تنتهي خلال %s يوم</h2>'
            '<p style="color:#555;font-size:13px;margin:0 0 6px;">برجاء المبادرة بإجراءات التجديد لتجنّب الغرامات:</p>'
            '%s</div></div>') % (escape(str(window)), Markup(''.join(sections)))
        self.env['mail.mail'].sudo().create({
            'subject': 'تنبيه: مستندات تنتهي خلال %s يوم' % window,
            'body_html': body,
            'email_to': ','.join(managers.mapped('email')),
            'auto_delete': True,
        }).send()
        return True
