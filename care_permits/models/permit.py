# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


PERMIT_TYPES = [
    ('security', 'تصريح أمني'),
    ('health', 'تصريح صحي'),
    ('food', 'تصريح أغذية'),
    ('civil_defense', 'دفاع مدني'),
    ('environment', 'بيئي'),
    ('municipality', 'بلدية'),
    ('other', 'أخرى'),
]


class CareProjectPermit(models.Model):
    _name = 'care.project.permit'
    _description = 'تصريح مشروع'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date, id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True, index=True)
    title = fields.Char(string='اسم التصريح', required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='المشروع', required=True, index=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='project_id.pms_department_id',
                                    string='القسم', store=True)
    permit_type = fields.Selection(PERMIT_TYPES, string='نوع التصريح', required=True,
                                   default='security', tracking=True, index=True)
    authority = fields.Char(string='الجهة المُصدِرة', tracking=True)
    permit_number = fields.Char(string='رقم التصريح', tracking=True)
    responsible_id = fields.Many2one('hr.employee', string='المسؤول')

    issue_date = fields.Date(string='تاريخ الإصدار', tracking=True)
    expiry_date = fields.Date(string='تاريخ الانتهاء', tracking=True)
    days_to_expiry = fields.Integer(string='أيام حتى الانتهاء', compute='_compute_status', store=True)
    status = fields.Selection([
        ('valid', 'ساري'),
        ('expiring', 'قارب الانتهاء'),
        ('expired', 'منتهٍ'),
        ('none', 'بدون تاريخ'),
    ], string='الصلاحية', compute='_compute_status', store=True, index=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'ساري المفعول'),
        ('renewing', 'قيد التجديد'),
        ('archived', 'مؤرشف'),
    ], string='الحالة', default='draft', tracking=True, index=True)

    attachment = fields.Binary(string='صورة/ملف التصريح', attachment=True)
    attachment_filename = fields.Char()
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.expiry_date:
                rec.days_to_expiry = 0
                rec.status = 'none'
                continue
            d = (rec.expiry_date - today).days
            rec.days_to_expiry = d
            rec.status = 'expired' if d < 0 else ('expiring' if d <= 30 else 'valid')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.project.permit') or '/'
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_start_renewal(self):
        self.write({'state': 'renewing'})
        for rec in self:
            rec.message_post(body=_('بدأ تجديد التصريح «%s».') % rec.title)

    def action_archive_permit(self):
        self.write({'state': 'archived'})

    def action_print(self):
        return self.env.ref('care_permits.action_report_permit').report_action(self)

    @api.model
    def _cron_expiry_alert(self):
        """Post an activity on permits expiring within 30 days (or expired)."""
        today = fields.Date.today()
        soon = self.search([('expiry_date', '!=', False), ('state', '=', 'active'),
                            ('expiry_date', '<=', fields.Date.add(today, days=30))])
        for rec in soon:
            if not rec.responsible_id and not rec.project_id.user_id:
                continue
            user = (rec.project_id.user_id
                    or (rec.responsible_id.user_id if rec.responsible_id else False))
            if user:
                try:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('تصريح %s ينتهي خلال %s يوم') % (rec.title, rec.days_to_expiry),
                        user_id=user.id)
                except Exception:
                    pass
