# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


REASONS = [
    ('client_request', 'طلب من العميل'),
    ('misconduct', 'مخالفة / خطأ من العامل'),
    ('absence', 'غياب متكرّر'),
    ('performance', 'ضعف الأداء'),
    ('behaviour', 'سوء سلوك'),
    ('investigation', 'تحت التحقيق'),
    ('other', 'أخرى'),
]


class CareSuspensionRequest(models.Model):
    _name = 'care.suspension.request'
    _description = 'طلب إيقاف عن العمل'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='العامل', required=True, tracking=True, index=True)
    project_id = fields.Many2one('project.project', string='المشروع', tracking=True, index=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id',
                                    string='القسم', store=True)
    badge = fields.Char(related='employee_id.barcode', string='البادج', store=True)

    reason = fields.Selection(REASONS, string='سبب الإيقاف', required=True, default='misconduct', tracking=True)
    other_reason = fields.Char(string='سبب آخر')
    date = fields.Date(string='تاريخ الطلب', default=fields.Date.context_today, tracking=True)
    effective_date = fields.Date(string='تاريخ سريان الإيقاف', default=fields.Date.context_today, tracking=True)
    note = fields.Text(string='تفاصيل / ملاحظات')

    requested_by = fields.Many2one('res.users', string='مقدّم الطلب (مدير المشروع)',
                                   default=lambda s: s.env.user, readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='اعتمده (HR)', readonly=True, tracking=True)
    approval_date = fields.Datetime(string='تاريخ الاعتماد', readonly=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مُرسل للموارد البشرية'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
    ], string='الحالة', default='draft', tracking=True, index=True)

    # snapshot of the worker's situation, printed on the report
    job_title = fields.Char(related='employee_id.job_title', string='المسمى الوظيفي')
    wage = fields.Monetary(string='الأجر', compute='_compute_worker_info', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    has_allowance = fields.Boolean(string='لديه بدلات', compute='_compute_worker_info')
    allowance_note = fields.Char(string='تفاصيل البدلات', compute='_compute_worker_info')

    @api.depends('employee_id')
    def _compute_worker_info(self):
        for rec in self:
            emp = rec.employee_id
            ct = emp.contract_id if emp else False
            rec.wage = ct.wage if ct else 0.0
            allow = 0.0
            details = []
            if ct:
                for fld, lbl in (('transport_allowance', 'مواصلات'),
                                 ('housing_allowance', 'سكن'), ('allowance', 'بدل')):
                    if fld in ct._fields and ct[fld]:
                        allow += ct[fld]
                        details.append('%s: %s' % (lbl, ct[fld]))
            rec.has_allowance = bool(allow)
            rec.allowance_note = ' · '.join(details) or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.suspension.request') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            rec._notify_hr()

    def action_approve(self):
        for rec in self:
            rec.write({'state': 'approved', 'approved_by': self.env.uid,
                       'approval_date': fields.Datetime.now()})
            # reflect on the employee: suspended, and pulled off the project
            emp = rec.employee_id
            vals = {}
            if 'worker_status' in emp._fields:
                vals['worker_status'] = 'suspended'
            if vals:
                emp.sudo().write(vals)
            emp.message_post(body=_('⛔ تم إيقاف العامل عن العمل باعتماد الموارد البشرية (طلب %s).') % rec.name)

    def action_reject(self):
        self.write({'state': 'rejected', 'approved_by': self.env.uid,
                    'approval_date': fields.Datetime.now()})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_print(self):
        return self.env.ref('care_suspension.action_report_suspension').report_action(self)

    def _notify_hr(self):
        """Post a chatter note; HR managers see it on the record."""
        for rec in self:
            try:
                rec.message_post(
                    body=_('طلب إيقاف عن العمل بانتظار اعتماد الموارد البشرية — العامل: %s، السبب: %s.')
                    % (rec.employee_id.name, dict(REASONS).get(rec.reason, rec.reason)),
                    subject=_('طلب إيقاف: %s') % rec.name,
                    message_type='notification', subtype_xmlid='mail.mt_comment')
            except Exception:
                pass
