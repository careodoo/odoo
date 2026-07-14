# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class EmployeeShiftRequest(models.Model):
    _name = 'employee.shift.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Request for Shifting'
    _order = 'id desc'

    def _default_approver_1(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_1 = False
        approver_1_str = IPC.get_param('hr_employee_shift.employee_shift_approval_1')
        if approver_1_str:
            approver_1 = self.env['res.users'].browse(int(approver_1_str))
        return approver_1.id if approver_1 else False

    def _default_approver_2(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_2 = False
        approver_2_str = IPC.get_param('hr_employee_shift.employee_shift_approval_2')
        if approver_2_str:
            approver_2 = self.env['res.users'].browse(int(approver_2_str))
        return approver_2.id if approver_2 else False

    def _default_approver_3(self):
        IPC = self.env['ir.config_parameter'].sudo()
        approver_3 = False
        approver_3_str = IPC.get_param('hr_employee_shift.employee_shift_approval_3')
        if approver_3_str:
            approver_3 = self.env['res.users'].browse(int(approver_3_str))
        return approver_3.id if approver_3 else False

    employee_id = fields.Many2one('hr.employee', required=True)
    image_128 = fields.Image("Image 128", related='employee_id.image_128', compute_sudo=True)
    avatar_128 = fields.Image("Avatar 128", related='employee_id.avatar_128', compute_sudo=True)
    current_department = fields.Many2one('hr.department', string='Old Department')
    new_department = fields.Many2one('hr.department', domain="[('id', '!=', current_department)]", required=True)
    date = fields.Date(string="Request Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Manager'),
        ('confirm', 'Submitted'),
        ('approval_1', 'First Approved'), ('refuse_1', 'First Refused'),
        ('approval_2', 'Second Approved'), ('refuse_2', 'Second Refused'),
        ('approval_3', 'Third Approved'), ('refuse_3', 'Third Refused'),
        ('hr_review', 'HR Final Approval'), ('hr_refuse', 'HR Refused'),
        ('done', 'Shifted'),
        ], string='State',default='draft', required=True, tracking=True)

    approver_1 = fields.Many2one('res.users', default=_default_approver_1)
    approver_2 = fields.Many2one('res.users', default=_default_approver_2)
    approver_3 = fields.Many2one('res.users', default=_default_approver_3)
    old_department_manager = fields.Many2one('res.users')
    new_department_manager = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    refuse_reason = fields.Char()
    working_hours_modifier = fields.Many2one('res.users', related='current_department.working_hours_modifier', store=True)
    working_hours = fields.Many2one('resource.calendar', related='employee_id.resource_calendar_id',
                                    store=True, readonly=False)
    active = fields.Boolean(default=True)
    show_shift_department = fields.Boolean()
    hr_approved = fields.Boolean(string='HR Approved', copy=False, tracking=True)
    hr_approved_by = fields.Many2one('res.users', string='HR Approver', readonly=True, copy=False)
    hr_approved_date = fields.Date(readonly=True, copy=False)

    # ---------- financial impact of the transfer (compensation snapshot) ----------
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    current_wage = fields.Monetary(string='الراتب الحالي', compute='_compute_financials',
                                   currency_field='currency_id')
    total_allowance = fields.Monetary(string='إجمالي البدلات الحالية', compute='_compute_financials',
                                      currency_field='currency_id')
    allowance_count = fields.Integer(string='عدد البدلات', compute='_compute_financials')
    allowance_summary = fields.Html(string='البدلات الحالية', compute='_compute_financials', sanitize=False)
    # impact assessment (surfaced to approvers)
    salary_same = fields.Boolean(string='نفس الراتب في المشروع الجديد؟', default=True, tracking=True)
    new_wage = fields.Monetary(string='الراتب الجديد المقترح', currency_field='currency_id', tracking=True)
    allowances_same = fields.Boolean(string='نفس البدلات؟', default=True, tracking=True)
    impact_notes = fields.Text(string='ملاحظات على الأثر المالي')

    def _employee_active_allowances(self):
        self.ensure_one()
        if 'care.allowance' not in self.env or not self.employee_id:
            return self.env['care.allowance'].browse() if 'care.allowance' in self.env else None
        return self.env['care.allowance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ('approved', 'done')),
        ]).filtered(lambda a: getattr(a, 'stop_state', 'running') != 'stopped')

    @api.depends('employee_id')
    def _compute_financials(self):
        for rec in self:
            wage = 0.0
            emp = rec.employee_id
            # wage from the running contract, if hr_payroll/hr_contract is present
            if emp and 'hr.contract' in self.env and getattr(emp, 'contract_id', False):
                wage = emp.contract_id.wage or 0.0
            rec.current_wage = wage
            allos = rec._employee_active_allowances()
            if allos is None:
                rec.total_allowance = 0.0
                rec.allowance_count = 0
                rec.allowance_summary = '<p style="color:#8a93a1">لا يوجد نظام بدلات.</p>'
                continue
            rec.total_allowance = sum(allos.mapped('amount'))
            rec.allowance_count = len(allos)
            if allos:
                def _cell(v):
                    return '<td style="padding:4px 8px;border:1px solid #e6e9ef;">%s</td>' % v
                rows = ''.join(
                    '<tr>' + _cell(a.allowance_type_id.name or a.name or '-')
                    + _cell('{:,.3f}'.format(a.amount or 0.0))
                    + _cell(dict(a._fields['payment_method'].selection).get(a.payment_method, ''))
                    + _cell(dict(a._fields['frequency'].selection).get(a.frequency, '') if 'frequency' in a._fields else ('متكرر' if getattr(a, 'is_recurring', False) else 'مرة واحدة'))
                    + _cell(dict(a._fields['scope'].selection).get(a.scope, '') if 'scope' in a._fields else '-')
                    + _cell(getattr(a, 'next_accrual_date', '') or '-')
                    + '</tr>'
                    for a in allos)
                rec.allowance_summary = (
                    '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
                    '<tr style="background:#f4f7ff;font-weight:700;">'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">البدل</td>'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">المبلغ</td>'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">طريقة الصرف</td>'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">التكرار</td>'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">النطاق</td>'
                    '<td style="padding:4px 8px;border:1px solid #e6e9ef;">الاستحقاق القادم</td></tr>'
                    + rows + '</table>')
            else:
                rec.allowance_summary = '<p style="color:#8a93a1">لا توجد بدلات نشطة لهذا العامل.</p>'

    # ---------- branded notification helper ----------
    def _notify_card(self, users, title, subtitle, cta=None):
        """Post a formatted HTML card to the given users (emails them too)."""
        self.ensure_one()
        users = users.filtered(lambda u: u and u.partner_id)
        if not users:
            return
        rows = [
            (_('Employee'), self.employee_id.name or '-'),
            (_('From (current)'), self.current_department.name or '-'),
            (_('To (new)'), self.new_department.name or '-'),
            (_('Request'), self.display_name or '-'),
        ]
        tr = Markup('').join(
            Markup('<tr><td style="padding:6px 12px;color:#5a6472;font-size:13px;'
                   'border-bottom:1px solid #eef1f5;white-space:nowrap;">%s</td>'
                   '<td style="padding:6px 12px;color:#1a2330;font-size:13px;font-weight:600;'
                   'border-bottom:1px solid #eef1f5;">%s</td></tr>') % (k, v) for k, v in rows)
        body = Markup(
            '<div style="max-width:560px;font-family:Tajawal,Arial,sans-serif;direction:rtl;'
            'text-align:right;border:1px solid #e6e9ef;border-radius:12px;overflow:hidden;">'
            '<div style="background:linear-gradient(135deg,#7a5cf0,#4a2fd0);padding:16px 18px;color:#fff;">'
            '<div style="font-size:12px;opacity:.85;letter-spacing:1px;">نقل عامل بين المشاريع/الأقسام</div>'
            '<div style="font-size:18px;font-weight:800;margin-top:3px;">%(title)s</div></div>'
            '<div style="padding:14px 18px;">'
            '<p style="color:#333;font-size:14px;margin:0 0 10px;">%(subtitle)s</p>'
            '<table style="width:100%%;border-collapse:collapse;background:#fbfcfe;'
            'border:1px solid #eef1f5;border-radius:8px;">%(rows)s</table>'
            '%(cta)s'
            '<p style="color:#8a93a1;font-size:12px;margin:12px 0 0;">رسالة آلية من نظام نقل العمالة — care.</p>'
            '</div></div>'
        ) % {'title': title, 'subtitle': subtitle, 'rows': tr,
             'cta': Markup('<p style="margin:10px 0 0;color:#4a2fd0;font-weight:700;">%s</p>') % cta if cta else Markup('')}
        self.message_post(body=body, subject=title,
                          partner_ids=users.mapped('partner_id').ids,
                          message_type='notification', subtype_xmlid='mail.mt_comment')

    @api.model_create_multi
    def create(self, vals_list):
        closed = ['refuse_1', 'refuse_2', 'refuse_3', 'hr_refuse', 'done']
        for vals in vals_list:
            if vals.get('employee_id'):
                # a worker may have only ONE in-progress transfer at a time:
                # no new request until the previous one is approved/closed.
                open_any = self.env['employee.shift.request'].search([
                    ('employee_id', '=', vals.get('employee_id')),
                    ('state', 'not in', closed)], limit=1)
                if open_any:
                    emp = self.env['hr.employee'].browse(vals['employee_id'])
                    raise ValidationError(_(
                        'لا يمكن إنشاء طلب نقل جديد للعامل %s: يوجد طلب سارٍ (%s) لم يُعتمد/يُغلق بعد.'
                    ) % (emp.name, open_any.display_name))
        res = super(EmployeeShiftRequest, self).create(vals_list)
        return res

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            dept = self.employee_id.department_id
            self.current_department = dept.id
            if not dept.manager_id:
                raise ValidationError("{} is not linked to manager".format(dept.name))
            if not dept.manager_id.user_id:
                raise ValidationError("{} manager is not linked to user".format(dept.name))
            self.old_department_manager = dept.manager_id.user_id.id
            # in case department has approver users replace global approvers
            if dept.employee_shift_approval_1:
                self.approver_1 = dept.employee_shift_approval_1.id
                self.approver_2 = dept.employee_shift_approval_2.id if dept.employee_shift_approval_2 else False
                self.approver_3 = dept.employee_shift_approval_3.id if dept.employee_shift_approval_3 else False
            else:
                self.approver_1 = self._default_approver_1()
                self.approver_2 = self._default_approver_2()
                self.approver_3 = self._default_approver_3()

    @api.onchange('new_department')
    def onchange_new_department(self):
        if self.new_department:
            dept = self.new_department
            if not dept.manager_id:
                raise ValidationError("{} is not linked to manager".format(dept.name))
            if not dept.manager_id.user_id:
                raise ValidationError("{} manager is not linked to user".format(dept.name))
            self.new_department_manager = dept.manager_id.user_id.id

    def _prepare_request_record(self, approver):
        return {
            'employee_id': self.employee_id.id,
            'old_department': self.current_department.id,
            'new_department': self.new_department.id,
            'state': self.state,
            'approver': approver.id
        }

    # department manager must have access to his department request
    def send_to_manager(self):
        if not self.current_department.old_manager_approval:
            self.shift_confirm()
        else:
            self.write({'state': 'sent'})
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_manager_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Submit Department Shift Request',
                user_id=self.old_department_manager.id)

    def shift_confirm(self):
        self.write({'state': 'confirm'})
        record = self._prepare_request_record(self.old_department_manager)
        self.env['employee.shift.request.record'].create(record)
        template = self.env.ref('hr_employee_shift.dept_shift_send_to_1_approve_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        self.sudo().activity_schedule(
            'hr_employee_shift.mail_act_shift_create',
            summary='Department Shift Request',
            note='Ask To First Approve Department Shift Request',
            user_id=self.approver_1.id)

    def get_request_followers(self):
        followers = [self.new_department_manager.id]
        if self.approver_2:
            followers.append(self.approver_2.id)
        if self.approver_3:
            followers.append(self.approver_3.id)
        return followers

    def first_approve(self):
        if self.approver_2:
            self.write({'state': 'approval_1'})
            record = self._prepare_request_record(self.approver_1)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_2_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Second Approve Department Shift Request',
                user_id=self.approver_2.id)
        elif self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_1',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_1)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def first_refuse(self):
        return {
            'name': 'Refuse Reason',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.refuse.reason',
            'target': 'new',
        }

    def second_approve(self):
        if self.approver_3:
            self.write({'state': 'approval_2'})
            record = self._prepare_request_record(self.approver_2)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_3_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To Third Approve Department Shift Request',
                user_id=self.approver_3.id)
        elif self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_2',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_2)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def third_approve(self):
        if self.current_department.new_manager_approval:
            self.write({
                'state': 'approval_3',
                'show_shift_department': True,
            })
            record = self._prepare_request_record(self.approver_3)
            self.env['employee.shift.request.record'].create(record)
            template = self.env.ref('hr_employee_shift.dept_shift_send_to_new_dept_approve_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Request',
                note='Ask To New Manager Approve Department Shift Request',
                user_id=self.new_department_manager.id)
        else:
            self.shift_department()

    def shift_department(self):
        """After all department approvals, route to HR for the FINAL approval
        instead of moving the worker immediately. HR approval then performs the
        actual move via _do_shift()."""
        for rec in self:
            if rec.hr_approved:
                rec._do_shift()
                continue
            rec.write({'state': 'hr_review', 'show_shift_department': False})
            hr_users = rec._hr_approver_users()
            rec._notify_card(
                hr_users,
                _('طلب نقل عامل — بانتظار اعتماد الموارد البشرية'),
                _('اكتملت موافقات الأقسام على نقل العامل. برجاء الاعتماد النهائي من الموارد البشرية لإتمام النقل.'),
                cta=_('يرجى فتح الطلب واعتماده.'))
            for u in hr_users:
                rec.sudo().activity_schedule(
                    'hr_employee_shift.mail_act_shift_create',
                    summary=_('اعتماد HR نهائي لنقل عامل'),
                    note=_('نقل %s من %s إلى %s') % (
                        rec.employee_id.name, rec.current_department.name, rec.new_department.name),
                    user_id=u.id)

    def _hr_approver_users(self):
        self.ensure_one()
        grp = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        return grp.users if grp else self.env['res.users']

    def action_hr_approve(self):
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_manager'):
                raise UserError(_('الاعتماد النهائي من مدير الموارد البشرية فقط.'))
            rec.write({'hr_approved': True, 'hr_approved_by': self.env.user.id,
                       'hr_approved_date': fields.Date.today()})
            rec._do_shift()

    def action_hr_refuse(self):
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_manager'):
                raise UserError(_('الرفض من مدير الموارد البشرية فقط.'))
            rec.write({'state': 'hr_refuse'})
            rec._notify_card(rec.old_department_manager | rec.new_department_manager,
                             _('رُفض طلب نقل العامل من الموارد البشرية'),
                             _('لم يُعتمد النقل من الموارد البشرية. لم يتم تغيير قسم العامل.'))

    def _do_shift(self):
        """Perform the actual department move + notify both managers (branded)."""
        self.ensure_one()
        # capture project-scoped allowances of the CURRENT project before the move
        scoped = self.env['care.allowance'].browse()
        Allow = self.env.get('care.allowance')
        if Allow is not None and 'scope' in Allow._fields:
            scoped = Allow.search([
                ('employee_id', '=', self.employee_id.id),
                ('scope', '=', 'project'),
                ('stop_state', 'not in', ('stopped',))])
        self.employee_id.with_context(shift_request=True).write({'department_id': self.new_department.id})
        # project-only allowances don't follow the worker to the new project
        if scoped:
            scoped.write({'stop_state': 'stopped', 'stop_effective_date': fields.Date.today(),
                          'stop_reason': _('توقف تلقائي: نقل العامل من المشروع %s') % (self.current_department.name or '')})
            for a in scoped:
                a.message_post(body=_('🛑 أُوقف البدل تلقائياً بسبب نقل العامل لمشروع آخر.'))
        self.write({'state': 'done', 'show_shift_department': False})
        record = self._prepare_request_record(self.env.user)
        self.env['employee.shift.request.record'].create(record)
        # formatted completion notice to BOTH the current and new managers
        self._notify_card(self.old_department_manager | self.new_department_manager,
                          _('تم نقل العامل بنجاح ✅'),
                          _('تم اعتماد النقل وتنفيذه، وأصبح العامل ضمن القسم/المشروع الجديد.'))
        for follower in self.get_request_followers():
            self.sudo().activity_schedule(
                'hr_employee_shift.mail_act_shift_create',
                summary='Department Shift Completed',
                note='Employee {} shifted from {} to {}'.format(
                    self.employee_id.name, self.current_department.name, self.new_department.name),
                user_id=follower)
