# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CareProbation(models.Model):
    """Probation period engine with auto end-date + pre-end review alert."""
    _name = 'care.probation'
    _description = 'Probation Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'end_date'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    start_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    duration_days = fields.Integer(string='Duration (days)', tracking=True,
                                   default=lambda s: int(s.env['ir.config_parameter'].sudo()
                                   .get_param('care_hr.probation_days') or 100))
    end_date = fields.Date(compute='_compute_dates', store=True)
    review_date = fields.Date(compute='_compute_dates', store=True)
    days_left = fields.Integer(compute='_compute_left')
    state = fields.Selection([
        ('running', 'Running'), ('passed', 'Passed'),
        ('extended', 'Extended'), ('failed', 'Failed'),
    ], default='running', tracking=True)
    evaluator_id = fields.Many2one('res.users', string='Evaluator')
    evaluation = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('start_date', 'duration_days')
    def _compute_dates(self):
        for rec in self:
            if rec.start_date and rec.duration_days:
                rec.end_date = rec.start_date + timedelta(days=rec.duration_days)
                rec.review_date = rec.end_date - timedelta(days=14)
            else:
                rec.end_date = rec.review_date = False

    def _compute_left(self):
        today = fields.Date.today()
        for rec in self:
            rec.days_left = (rec.end_date - today).days if rec.end_date else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.probation') or 'New'
        return super().create(vals_list)

    def action_pass(self):
        self.write({'state': 'passed'})

    def action_fail(self):
        self.write({'state': 'failed'})

    def action_extend(self):
        for rec in self:
            rec.write({'duration_days': rec.duration_days + 30, 'state': 'extended'})

    @api.model
    def _cron_probation_review(self):
        today = fields.Date.today()
        recs = self.search([('state', 'in', ('running', 'extended')),
                            ('review_date', '<=', today), ('end_date', '>=', today)])
        for rec in recs:
            mgr = rec.employee_id.parent_id.user_id or rec.evaluator_id
            if mgr and not rec.activity_ids:
                rec.activity_schedule('mail.mail_activity_data_todo', user_id=mgr.id,
                                      summary=_('Probation review due'),
                                      note=_('Probation of %s ends on %s') % (
                                          rec.employee_id.name, rec.end_date))


class CareEos(models.Model):
    """End-of-Service settlement with Kuwait indemnity calculation."""
    _name = 'care.eos'
    _description = 'End of Service Settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'last_working_day desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    join_date = fields.Date(tracking=True)
    last_working_day = fields.Date(required=True, tracking=True)
    reason = fields.Selection([
        ('resignation', 'Resignation'), ('termination', 'Termination / End of Contract'),
    ], default='resignation', required=True, tracking=True)
    basic_wage = fields.Monetary(tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    service_years = fields.Float(compute='_compute_eos', store=True)
    eos_days = fields.Float(string='Indemnity Days', compute='_compute_eos', store=True)
    eos_amount = fields.Monetary(string='EOS Indemnity', compute='_compute_eos', store=True)
    leave_balance_days = fields.Float()
    leave_amount = fields.Monetary(compute='_compute_eos', store=True)
    other_dues = fields.Monetary(string='Other Dues')
    deductions = fields.Monetary()
    net_amount = fields.Monetary(string='Net Settlement', compute='_compute_eos', store=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('paid', 'Paid')],
                             default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.join_date = (self.employee_id.first_contract_date
                              or self.employee_id.joining_date)
            if self.employee_id.contract_id:
                self.basic_wage = self.employee_id.contract_id.wage

    @api.depends('join_date', 'last_working_day', 'basic_wage', 'reason',
                 'leave_balance_days', 'other_dues', 'deductions')
    def _compute_eos(self):
        ICP = self.env['ir.config_parameter'].sudo()
        f5 = int(ICP.get_param('care_hr.eos_first5_days') or 15)
        a5 = int(ICP.get_param('care_hr.eos_after5_days') or 30)
        cap_years = float(ICP.get_param('care_hr.eos_cap_years') or 1.5)
        for rec in self:
            if rec.join_date and rec.last_working_day and rec.last_working_day > rec.join_date:
                years = (rec.last_working_day - rec.join_date).days / 365.25
            else:
                years = 0.0
            rec.service_years = round(years, 2)
            daily = (rec.basic_wage or 0.0) / 26.0
            if years <= 5:
                days = years * f5
            else:
                days = 5 * f5 + (years - 5) * a5
            gross = days * daily
            cap = cap_years * 12 * (rec.basic_wage or 0.0)
            if cap and gross > cap:
                gross = cap
            # Kuwait resignation scale
            if rec.reason == 'resignation':
                if years < 3:
                    factor = 0.0
                elif years < 5:
                    factor = 0.5
                elif years < 10:
                    factor = 2.0 / 3.0
                else:
                    factor = 1.0
                gross *= factor
            rec.eos_days = round(days, 1)
            rec.eos_amount = round(gross, 3)
            rec.leave_amount = round((rec.leave_balance_days or 0.0) * daily, 3)
            rec.net_amount = round(rec.eos_amount + rec.leave_amount
                                   + (rec.other_dues or 0.0) - (rec.deductions or 0.0), 3)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.eos') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_paid(self):
        self.write({'state': 'paid'})


class CareMovement(models.Model):
    """Internal employee movement: transfer / promotion / redeployment."""
    _name = 'care.movement'
    _description = 'Employee Movement'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    movement_type = fields.Selection([
        ('transfer', 'Transfer'), ('promotion', 'Promotion'),
        ('redeployment', 'Redeployment'), ('demotion', 'Demotion'),
    ], default='transfer', required=True, tracking=True)
    from_department_id = fields.Many2one('hr.department', string='From Department')
    to_department_id = fields.Many2one('hr.department', string='To Department')
    from_job_id = fields.Many2one('hr.job', string='From Job')
    to_job_id = fields.Many2one('hr.job', string='To Job')
    reason = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('done', 'Applied')], default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.from_department_id = self.employee_id.department_id
            self.from_job_id = self.employee_id.job_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.movement') or 'New'
        return super().create(vals_list)

    def action_apply(self):
        for rec in self:
            vals = {}
            if rec.to_department_id:
                vals['department_id'] = rec.to_department_id.id
            if rec.to_job_id:
                vals['job_id'] = rec.to_job_id.id
            if vals:
                # bypass the hr_employee_shift direct-department guard (same flag it uses)
                rec.employee_id.with_context(shift_request=True).write(vals)
            rec.state = 'done'
        return True


class CareLetter(models.Model):
    """Official letters / certificates (salary, experience, NOC...) on letterhead."""
    _name = 'care.letter'
    _description = 'HR Letter / Certificate'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    letter_type = fields.Selection([
        ('salary', 'Salary Certificate'),
        ('experience', 'Experience Certificate'),
        ('to_whom', 'To Whom It May Concern'),
        ('noc', 'No Objection Certificate'),
        ('other', 'Other'),
    ], default='salary', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    addressed_to = fields.Char(string='Addressed To', default='To Whom It May Concern')
    body = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('issued', 'Issued')], default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.onchange('employee_id', 'letter_type')
    def _onchange_generate(self):
        e = self.employee_id
        if not e:
            return
        job = e.job_id.name or '-'
        wage = e.contract_id.wage if e.contract_id else 0.0
        join = e.first_contract_date or e.joining_date or ''
        if self.letter_type == 'salary':
            self.body = (_("This is to certify that %s, holding the position of %s, is "
                           "currently employed with CARE since %s with a total monthly salary "
                           "of %s KWD. This certificate is issued upon the employee's request.")
                         % (e.english_name or e.name, job, join, wage))
        elif self.letter_type == 'experience':
            self.body = (_("This is to certify that %s worked with CARE as %s since %s. "
                           "We wish the employee continued success.")
                         % (e.english_name or e.name, job, join))
        else:
            self.body = (_("This is to certify that %s is employed with CARE as %s.")
                         % (e.english_name or e.name, job))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.letter') or 'New'
        return super().create(vals_list)

    def action_issue(self):
        self.write({'state': 'issued'})
