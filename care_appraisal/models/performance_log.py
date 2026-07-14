# -*- coding: utf-8 -*-
from markupsafe import Markup, escape
from odoo import api, fields, models, _

# Default point rules (overridable via ir.config_parameter care_perf.<key>)
DEFAULTS = {
    'task_ontime': 2.0,
    'task_overdue': -3.0,
    'att_present': 0.2,
    'att_short': -1.0,
    'att_min_hours': 6.0,
    'att_overtime_bonus': 0.5,
    'penalty_points': -3.0,
    'bonus_points': 3.0,
    'notify_disabled': 0.0,
    'notify_threshold': 3.0,
    'reward_threshold': 15.0,
    'reward_per_point': 2.0,
    'low_threshold': -10.0,
}


class PerformanceLog(models.Model):
    _name = 'care.performance.log'
    _description = 'Employee Performance Event'
    _order = 'date desc, id desc'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  index=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id',
                                    store=True, string='Department')
    date = fields.Date(string='Date', default=fields.Date.context_today, index=True)
    source = fields.Selection([
        ('task', 'Task / Deadline'),
        ('attendance', 'Attendance'),
        ('penalty', 'Penalty'),
        ('bonus', 'Bonus'),
        ('manual', 'Manual'),
        ('other', 'Other'),
    ], string='Source', default='manual', required=True)
    name = fields.Char(string='Description', required=True)
    points = fields.Float(string='Impact Points', help='Positive = reward, negative = penalty.')
    polarity = fields.Selection([('pos', 'Positive'), ('neg', 'Negative'), ('neu', 'Neutral')],
                                string='Effect', compute='_compute_polarity', store=True)
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source ID')
    appraisal_id = fields.Many2one('hr.appraisal', string='Appraisal', index=True, ondelete='set null')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('points')
    def _compute_polarity(self):
        for rec in self:
            rec.polarity = 'pos' if rec.points > 0 else ('neg' if rec.points < 0 else 'neu')

    @api.model
    def _get_param(self, key):
        val = self.env['ir.config_parameter'].sudo().get_param('care_perf.%s' % key)
        if val in (False, None, ''):
            return DEFAULTS.get(key, 0.0)
        s = str(val).strip().lower()
        if s in ('true', 'yes'):
            return 1.0
        if s in ('false', 'no'):
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return DEFAULTS.get(key, 0.0)

    @api.model
    def record_event(self, employee_id, points, source, name, res_model=False, res_id=False, date=False):
        """Public entry point — ANY module/feature can log a performance event here
        so it automatically flows into the employee's appraisal."""
        if not employee_id:
            return self.browse()
        log = self.sudo().create({
            'employee_id': employee_id,
            'points': points,
            'source': source,
            'name': name or _('Performance event'),
            'res_model': res_model,
            'res_id': res_id,
            'date': date or fields.Date.context_today(self),
        })
        log._notify_significant()
        return log

    def _notify_significant(self):
        """Notify the employee (and their manager) when a notable event is logged."""
        if self._get_param('notify_disabled'):
            return
        threshold = abs(self._get_param('notify_threshold'))
        for log in self:
            if abs(log.points) < threshold:
                continue
            emp = log.employee_id
            partners = emp.user_id.partner_id
            manager = emp.parent_id.user_id.partner_id or emp.department_id.manager_id.user_id.partner_id
            if manager:
                partners |= manager
            if not partners:
                continue
            positive = log.points > 0
            accent = '#27ae60' if positive else '#e2513f'
            head = _('👏 أداء إيجابي') if positive else _('⚠️ ملاحظة أداء')
            sign = '+' if positive else ''
            body = Markup(
                '<div style="max-width:540px;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
                'border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">'
                '<div style="background:#15213b;padding:13px 18px;">'
                '<span style="color:#f0663c;font-weight:bold;font-size:17px;">CARE</span>'
                '<span style="color:#aeb8cc;font-size:12px;"> · نظام تقييم الأداء</span></div>'
                '<div style="background:%s;height:5px;"></div>'
                '<div style="padding:18px;">'
                '<h2 style="margin:0 0 8px;color:#15213b;font-size:17px;">%s</h2>'
                '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 12px;">'
                'الموظف: <b>%s</b><br/>الحدث: %s<br/>التأثير في التقييم: '
                '<b style="color:%s;font-size:16px;">%s%s نقطة</b></p>'
                '</div></div>') % (
                    accent, head, escape(emp.name or ''), escape(log.name or ''),
                    accent, sign, escape(('%g' % log.points)))
            try:
                emp.with_context(mail_notify_force_send=False).message_post(
                    body=body, subject=_('تقييم الأداء: %s') % (emp.name or ''),
                    partner_ids=partners.ids, message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light')
            except Exception:
                continue

    @api.model
    def cron_low_performance_alert(self):
        """Monthly digest to HR managers listing employees whose YTD performance
        score is below the configured low threshold."""
        low = self._get_param('low_threshold')
        year_start = fields.Date.today().replace(month=1, day=1)
        data = self.read_group([('date', '>=', year_start)], ['points:sum'], ['employee_id'])
        rows = []
        for d in data:
            emp = d.get('employee_id')
            pts = d.get('points')
            if emp and pts is not None and pts < low:
                rows.append((emp[1], pts))
        if not rows:
            return True
        rows.sort(key=lambda r: r[1])
        managers = self.env.ref('hr.group_hr_manager').users.filtered(lambda u: u.email)
        if not managers:
            return True
        items = ''.join(
            '<tr><td style="padding:6px 10px;border-bottom:1px solid #eef1f6;">%s</td>'
            '<td style="padding:6px 10px;border-bottom:1px solid #eef1f6;text-align:center;'
            'color:#c0392b;font-weight:bold;">%s</td></tr>' % (escape(n), escape('%g' % p))
            for n, p in rows)
        body = Markup(
            '<div style="max-width:560px;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
            'border:1px solid #e4e8f0;border-radius:12px;overflow:hidden;">'
            '<div style="background:#15213b;padding:14px 20px;">'
            '<span style="color:#f0663c;font-weight:bold;font-size:18px;">CARE</span>'
            '<span style="color:#aeb8cc;font-size:12px;"> · متابعة الأداء</span></div>'
            '<div style="background:#e2513f;height:5px;"></div>'
            '<div style="padding:18px;">'
            '<h2 style="margin:0 0 6px;color:#15213b;font-size:17px;">⚠️ موظفون بأداء منخفض (%s)</h2>'
            '<p style="color:#555;font-size:13px;margin:0 0 12px;">الموظفون التالية أسماؤهم نتيجة أدائهم '
            'لهذا العام أقل من الحد (%s نقطة) ويحتاجون متابعة:</p>'
            '<table style="width:100%%;border-collapse:collapse;font-size:13px;">'
            '<tr style="background:#f6f8fc;"><th style="padding:6px 10px;text-align:right;">الموظف</th>'
            '<th style="padding:6px 10px;">النقاط</th></tr>%s</table>'
            '</div></div>') % (escape(str(len(rows))), escape('%g' % low), Markup(items))
        self.env['mail.mail'].sudo().create({
            'subject': 'تنبيه: %s موظف بأداء منخفض' % len(rows),
            'body_html': body,
            'email_to': ','.join(managers.mapped('email')),
            'auto_delete': True,
        }).send()
        return True

    def action_open_source(self):
        self.ensure_one()
        if self.res_model and self.res_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.res_model,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
