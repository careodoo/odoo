from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class CareTimesheet(models.Model):
    _name = 'care.timesheet'
    _description = 'Care Timesheet'

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

        result = super(CareTimesheet, self).create(vals)
        return result

    def button_generate_timesheet(self):
        self.line_ids = [(5, 0, 0)]
        cr = self.env.cr
        cr.execute("""
            SELECT employee_id, count(id)
            FROM hr_attendance
            WHERE department_id = %s AND check_in::date >= %s AND check_in::date <= %s
            GROUP BY employee_id
        """, (self.department_id.id, self.date_from, self.date_to))
        lines = self.env.cr.dictfetchall()
        for line in lines:
            self.line_ids = [(0, 0, {
                'employee_id': line['employee_id'],
                'actual': line['count'],
            })]

    def button_submit(self):
        self.state = 'submit'

    def button_approve(self):
        for line in self.line_ids.filtered(lambda l: l.diff > 0):
            emp = line.employee_id
            calendar = emp.resource_calendar_id
            hours = calendar.hours_per_day
            calendar_lines = list(set(calendar.attendance_ids.mapped('dayofweek')))

            all_possible_days = []
            start = self.date_from
            end = self.date_to
            worked_days = self.get_worked_days(emp, start, end)
            while start <= end:
                if str(start.weekday()) in calendar_lines:
                    all_possible_days.append(start)
                start += relativedelta(days=1)
            worked_set = set(worked_days)
            available_days = [d for d in all_possible_days if d not in worked_set]
            for i in range(min(line.diff, len(available_days))):
                self.env['hr.attendance'].create({
                    'employee_id': emp.id,
                    'check_in': available_days[i],
                    'check_out': available_days[i] + relativedelta(hours=hours),
                    'care_timesheet_id': self.id,
                })
            line.actual += line.diff
            line.count = 0
        self.state = 'approved'

    def get_worked_days(self, emp, start, end):
        self.env.cr.execute("""
            SELECT check_in
            FROM hr_attendance
            WHERE employee_id = %s AND check_in::date >= %s AND check_in::date <= %s
        """, (emp.id, start, end))
        lines = self.env.cr.dictfetchall()
        days = []
        for line in lines:
            days.append(line['check_in'].date())
        return days


class CareTimesheetLine(models.Model):
    _name = 'care.timesheet.line'
    _description = 'Care Timesheet Line'

    timesheet_id = fields.Many2one('care.timesheet')
    employee_id = fields.Many2one('hr.employee')
    actual = fields.Integer()
    count = fields.Integer()
    diff = fields.Integer(compute='compute_diff', store=True)

    @api.constrains('diff')
    def check_diff(self):
        for rec in self:
            if rec.diff < 0:
                raise UserError(f'{rec.employee_id.name} count should be more than actual!')

    @api.depends('actual', 'count')
    def compute_diff(self):
        for rec in self:
            rec.diff = 0
            if rec.count:
                rec.diff = rec.count - rec.actual
