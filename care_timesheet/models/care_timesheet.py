from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


AR_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
             'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']


class CareTimesheet(models.Model):
    _name = 'care.timesheet'
    _description = 'Care Timesheet'
    _order = 'date_from desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    line_ids = fields.One2many('care.timesheet.line', 'timesheet_id')
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    department_id = fields.Many2one('hr.department')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submit', 'Submitted'), ('approved', 'Approved'),
    ], default='draft')
    active = fields.Boolean(default=True)

    # period label (month + year) for lists — "يوليو 2026"
    period_label = fields.Char(string='الفترة', compute='_compute_period', store=True)
    month = fields.Integer(compute='_compute_period', store=True)
    year = fields.Integer(compute='_compute_period', store=True)

    # roll-up statistics
    emp_count = fields.Integer(string='عدد العمال', compute='_compute_stats')
    total_biometric = fields.Integer(string='إجمالي أيام البصمة', compute='_compute_stats')
    total_approved = fields.Integer(string='إجمالي الأيام المعتمدة', compute='_compute_stats')
    pending_count = fields.Integer(string='بانتظار الاعتماد', compute='_compute_stats')

    @api.depends('date_from')
    def _compute_period(self):
        for rec in self:
            if rec.date_from:
                rec.month = rec.date_from.month
                rec.year = rec.date_from.year
                rec.period_label = '%s %s' % (AR_MONTHS[rec.date_from.month - 1], rec.date_from.year)
            else:
                rec.month = rec.year = 0
                rec.period_label = False

    @api.depends('line_ids.actual', 'line_ids.approved_days', 'line_ids.line_state')
    def _compute_stats(self):
        for rec in self:
            rec.emp_count = len(rec.line_ids)
            rec.total_biometric = sum(rec.line_ids.mapped('actual'))
            rec.total_approved = sum(rec.line_ids.filtered(lambda l: l.line_state == 'approved').mapped('approved_days'))
            rec.pending_count = len(rec.line_ids.filtered(lambda l: l.line_state == 'pending'))

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise UserError("Date From shouldn't before Date To !")

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('care.timesheet') or _('New')
        return super(CareTimesheet, self).create(vals)

    def button_generate_timesheet(self):
        """Pull each employee's biometric (fingerprint) day-count for the period.
        The biometric value seeds the adjustable value; HR approves per line.

        Biometric rows (from the ZK devices) often have no department_id set, so
        the count is scoped by the EMPLOYEE's department, not the attendance row's.
        """
        self.line_ids = [(5, 0, 0)]
        cr = self.env.cr
        cr.execute("""
            SELECT a.employee_id AS employee_id,
                   count(DISTINCT a.check_in::date) AS cnt
            FROM hr_attendance a
            JOIN hr_employee e ON e.id = a.employee_id
            WHERE e.department_id = %s
              AND a.check_in::date >= %s AND a.check_in::date <= %s
            GROUP BY a.employee_id
        """, (self.department_id.id, self.date_from, self.date_to))
        counts = {r['employee_id']: r['cnt'] for r in cr.dictfetchall()}
        # include every active employee of the department, even zero-attendance
        emps = self.env['hr.employee'].search([('department_id', '=', self.department_id.id)])
        for emp in emps:
            bio = counts.get(emp.id, 0)
            self.line_ids = [(0, 0, {
                'employee_id': emp.id,
                'actual': bio,
                'adjusted_days': bio,
            })]

    def button_submit(self):
        self.state = 'submit'

    def button_approve(self):
        """Approve every pending line (approved = adjusted) and close the sheet."""
        for line in self.line_ids.filtered(lambda l: l.line_state != 'rejected'):
            line._do_approve()
        self.state = 'approved'

    def button_approve_all(self):
        for line in self.line_ids.filtered(lambda l: l.line_state == 'pending'):
            line._do_approve()

    def button_reject_all(self):
        for line in self.line_ids.filtered(lambda l: l.line_state == 'pending'):
            line._do_reject()

    def button_reset_draft(self):
        self.state = 'draft'

    def get_worked_days(self, emp, start, end):
        self.env.cr.execute("""
            SELECT check_in FROM hr_attendance
            WHERE employee_id = %s AND check_in::date >= %s AND check_in::date <= %s
        """, (emp.id, start, end))
        return [l['check_in'].date() for l in self.env.cr.dictfetchall()]


class CareTimesheetLine(models.Model):
    _name = 'care.timesheet.line'
    _description = 'Care Timesheet Line'
    _order = 'employee_id'

    timesheet_id = fields.Many2one('care.timesheet', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee')
    badge = fields.Char(related='employee_id.barcode', string='البادج', store=True)

    # biometric (fingerprint) days — the source of truth, read-only
    actual = fields.Integer(string='أيام البصمة')
    # HR-adjustable value + the approved (salary) value
    adjusted_days = fields.Integer(string='المعدّل')
    approved_days = fields.Integer(string='المعتمد (أيام الراتب)', readonly=True)
    diff = fields.Integer(string='الفرق', compute='compute_diff', store=True)

    # legacy field kept for compatibility (old target)
    count = fields.Integer()

    line_state = fields.Selection([
        ('pending', 'بانتظار الاعتماد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
    ], string='حالة السطر', default='pending', index=True)
    note = fields.Char(string='ملاحظة التعديل')
    document = fields.Binary(string='مستند مرفق', attachment=True)
    document_filename = fields.Char()
    approved_by = fields.Many2one('res.users', string='اعتمده', readonly=True)
    approval_date = fields.Datetime(string='تاريخ الاعتماد', readonly=True)

    @api.depends('actual', 'adjusted_days')
    def compute_diff(self):
        for rec in self:
            rec.diff = (rec.adjusted_days or 0) - (rec.actual or 0)

    def _do_approve(self):
        for rec in self:
            rec.write({
                'approved_days': rec.adjusted_days if rec.adjusted_days else rec.actual,
                'line_state': 'approved',
                'approved_by': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })

    def _do_reject(self):
        for rec in self:
            rec.write({'line_state': 'rejected', 'approved_days': 0,
                       'approved_by': self.env.uid, 'approval_date': fields.Datetime.now()})

    def action_approve_line(self):
        self._do_approve()

    def action_reject_line(self):
        self._do_reject()
