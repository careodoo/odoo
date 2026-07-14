# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareDisciplinaryType(models.Model):
    _name = 'care.disciplinary.type'
    _description = 'Disciplinary Offense Type'
    _order = 'name'

    name = fields.Char(string='نوع المخالفة', required=True, translate=True)
    default_action = fields.Selection([
        ('notice', 'تنبيه'), ('warning', 'إنذار'), ('deduction', 'خصم'),
        ('suspension', 'إيقاف'), ('termination', 'فصل'),
    ], string='الإجراء الافتراضي', default='notice')
    active = fields.Boolean(default=True)


class CareDisciplinaryAction(models.Model):
    _name = 'care.disciplinary.action'
    _description = 'Disciplinary Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='العامل', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='القسم/المشروع')
    type_id = fields.Many2one('care.disciplinary.type', string='نوع المخالفة', tracking=True)
    date = fields.Date(string='تاريخ المخالفة', default=fields.Date.context_today, required=True, tracking=True)
    action = fields.Selection([
        ('notice', 'تنبيه'), ('warning', 'إنذار'), ('deduction', 'خصم'),
        ('suspension', 'إيقاف'), ('termination', 'فصل'),
    ], string='الإجراء', default='notice', required=True, tracking=True)
    level = fields.Integer(string='درجة التصعيد', compute='_compute_level', store=True,
                           help='ترتيب هذا الإجراء ضمن مخالفات العامل (1 = أول).')
    amount = fields.Monetary(string='قيمة الخصم', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    description = fields.Text(string='وصف المخالفة', tracking=True)
    corrective = fields.Text(string='الإجراء التصحيحي المطلوب')
    attachment_ids = fields.Many2many('ir.attachment', string='مرفقات (محاضر/إثباتات)')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('issued', 'صادر'),
        ('acknowledged', 'أقرّ به العامل'),
        ('appealed', 'تظلّم'),
        ('closed', 'مغلق'),
        ('cancelled', 'ملغى'),
    ], default='draft', tracking=True)
    issued_by = fields.Many2one('res.users', string='أصدره', readonly=True, copy=False)
    ack_date = fields.Date(string='تاريخ الإقرار', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('employee_id', 'date', 'state')
    def _compute_level(self):
        for rec in self:
            if not rec.employee_id:
                rec.level = 1
                continue
            prior = self.search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'not in', ('draft', 'cancelled')),
                ('date', '<', rec.date or fields.Date.today())])
            rec.level = prior + 1

    @api.onchange('type_id')
    def _onchange_type(self):
        if self.type_id and self.type_id.default_action:
            self.action = self.type_id.default_action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.disciplinary.action') or '/'
        return super().create(vals_list)

    def action_issue(self):
        for rec in self:
            if not rec.description:
                raise UserError(_('يرجى كتابة وصف المخالفة قبل الإصدار.'))
            rec.write({'state': 'issued', 'issued_by': self.env.user.id})
            rec.message_post(body=_('📋 صدر إجراء تأديبي (%s) — الدرجة %s.') % (
                dict(rec._fields['action'].selection).get(rec.action), rec.level))
            mgr = rec.employee_id.parent_id.user_id or rec.employee_id.department_id.manager_id.user_id
            if mgr:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('إجراء تأديبي: %s') % (rec.employee_id.name or ''),
                                      user_id=mgr.id)

    def action_acknowledge(self):
        self.write({'state': 'acknowledged', 'ack_date': fields.Date.today()})

    def action_appeal(self):
        self.write({'state': 'appealed'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
