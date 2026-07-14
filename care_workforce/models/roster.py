# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CareShiftTemplate(models.Model):
    _name = 'care.shift.template'
    _description = 'Shift Template'
    _order = 'start_time'

    name = fields.Char(string='الوردية', required=True, translate=True)
    code = fields.Char(string='الرمز')
    start_time = fields.Float(string='من الساعة', required=True)
    end_time = fields.Float(string='إلى الساعة', required=True)
    hours = fields.Float(string='عدد الساعات', compute='_compute_hours', store=True)
    color = fields.Integer(string='لون')
    active = fields.Boolean(default=True)

    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for r in self:
            h = (r.end_time or 0.0) - (r.start_time or 0.0)
            r.hours = h if h >= 0 else h + 24.0


class CareRoster(models.Model):
    _name = 'care.roster'
    _description = 'Shift Roster'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    department_id = fields.Many2one('hr.department', string='القسم/المشروع', required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='المشروع')
    date_from = fields.Date(string='من تاريخ', required=True, tracking=True,
                            default=lambda s: fields.Date.today())
    date_to = fields.Date(string='إلى تاريخ', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'مسودة'), ('confirmed', 'معتمد'), ('done', 'منفّذ'), ('cancelled', 'ملغى'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('care.roster.line', 'roster_id', string='الجدول')
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    scheduled_count = fields.Integer(compute='_compute_counts', store=True)
    reserve_count = fields.Integer(compute='_compute_counts', store=True)
    line_count = fields.Integer(compute='_compute_counts', store=True)

    @api.depends('line_ids', 'line_ids.assignment')
    def _compute_counts(self):
        for r in self:
            r.line_count = len(r.line_ids)
            r.scheduled_count = len(r.line_ids.filtered(lambda l: l.assignment == 'scheduled'))
            r.reserve_count = len(r.line_ids.filtered(lambda l: l.assignment == 'reserve'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for r in self:
            if r.date_from and r.date_to and r.date_to < r.date_from:
                raise ValidationError(_('تاريخ النهاية يجب أن يكون بعد البداية.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.roster') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_fill_department(self):
        """Prefill one scheduled line per active employee of the department."""
        for r in self:
            existing = r.line_ids.mapped('employee_id')
            emps = self.env['hr.employee'].search([('department_id', '=', r.department_id.id)])
            vals = [(0, 0, {'employee_id': e.id, 'assignment': 'scheduled'})
                    for e in emps if e not in existing]
            if vals:
                r.line_ids = vals


class CareRosterLine(models.Model):
    _name = 'care.roster.line'
    _description = 'Roster Line'
    _order = 'work_date, id'

    roster_id = fields.Many2one('care.roster', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='العامل', required=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='القسم')
    work_date = fields.Date(string='التاريخ')
    shift_id = fields.Many2one('care.shift.template', string='الوردية')
    assignment = fields.Selection([
        ('scheduled', 'مجدول'),
        ('reserve', 'احتياطي'),
        ('leave', 'إجازة'),
        ('off', 'راحة'),
        ('absent', 'غياب'),
    ], default='scheduled', required=True, string='الحالة')
    backup_for_id = fields.Many2one('hr.employee', string='بديل عن',
                                    help='العامل الأساسي الذي يحل هذا الاحتياطي محله.')
    note = fields.Char(string='ملاحظة')
