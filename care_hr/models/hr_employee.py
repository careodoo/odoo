from datetime import datetime, time, timedelta

from odoo import fields, models, api, Command
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    # ------------------------------------------------------------------
    # HR 360 dashboard data (consumed by the OWL client action)
    # Defensive: optional models (attendance, loans, documents) are read
    # through self.env.get() so the dashboard works regardless of which
    # add-on modules are installed.
    # ------------------------------------------------------------------
    @api.model
    def get_hr_dashboard_data(self):
        Emp = self.env['hr.employee']
        today = fields.Date.today()
        year = today.year
        t_start = datetime.combine(today, time.min)
        t_end = datetime.combine(today, time.max)
        base = [('active', '=', True)]
        emps = Emp.search(base)
        total = len(emps)

        # --- joiners trend (12 months of current year) + new joiners ---
        months = [0] * 12
        for e in emps:
            d = e.joining_date or (e.create_date.date() if e.create_date else False)
            if d and d.year == year:
                months[d.month - 1] += 1
        new_joiners_year = sum(months)

        suspended = Emp.search_count([('suspend_date', '!=', False)] + base)
        departures_year = Emp.search_count(
            [('suspend_date', '>=', datetime(year, 1, 1).date()),
             ('suspend_date', '<=', today)])

        # --- gender split ---
        gender = {'male': 0, 'female': 0, 'other': 0}
        for e in emps:
            g = e.gender if e.gender in gender else 'other'
            gender[g] += 1

        def _count(g, field):
            return g.get('__count') or g.get('%s_count' % field) or 0

        def grp_counts(field, limit=12, placeholder='غير محدّد'):
            out = []
            for g in Emp.read_group(base, [field], [field], limit=limit):
                val = g.get(field)
                name = val[1] if isinstance(val, (list, tuple)) else (val or placeholder)
                out.append({'name': name, 'count': _count(g, field)})
            return out

        by_department = grp_counts('department_id', placeholder='بدون قسم')
        by_job = grp_counts('job_id', placeholder='بدون مسمّى')
        by_category = grp_counts('category_ids', placeholder='بدون تصنيف')

        # --- leaves (hr_holidays is a hard dependency) ---
        Leave = self.env['hr.leave']
        on_leave_today = Leave.search_count(
            [('state', '=', 'validate'), ('date_from', '<=', t_end), ('date_to', '>=', t_start)])
        pending_leaves = Leave.search_count([('state', 'in', ('confirm', 'validate1'))])
        by_leave_type = []
        for g in Leave.read_group(
                [('state', '=', 'validate'), ('date_from', '>=', datetime(year, 1, 1))],
                ['holiday_status_id'], ['holiday_status_id'], limit=10):
            val = g.get('holiday_status_id')
            by_leave_type.append({
                'name': val[1] if val else 'أخرى',
                'count': g.get('__count') or g.get('holiday_status_id_count') or 0})
        upcoming_leaves = []
        for lv in Leave.search(
                [('state', '=', 'validate'), ('date_from', '>=', t_start),
                 ('date_from', '<=', t_end + timedelta(days=7))],
                order='date_from', limit=8):
            upcoming_leaves.append({
                'employee': lv.employee_id.name,
                'type': lv.holiday_status_id.name or '—',
                'date_from': str(lv.date_from.date()) if lv.date_from else '',
                'date_to': str(lv.date_to.date()) if lv.date_to else '',
                'days': lv.number_of_days,
            })

        # --- attendance (optional module) ---
        Att = self.env.get('hr.attendance')
        present_today = currently_in = 0
        if Att is not None:
            present_today = len({
                a['employee_id'][0]
                for a in Att.read_group(
                    [('check_in', '>=', t_start), ('check_in', '<=', t_end)],
                    ['employee_id'], ['employee_id'], lazy=False) if a.get('employee_id')})
            currently_in = Att.search_count([('check_out', '=', False)])

        # --- care_hr action documents pending approval (state == 'submit') ---
        action_models = [
            ('hr.action.joining', 'أمر التحاق'),
            ('hr.action.clearance', 'إخلاء طرف'),
            ('hr.action.absence', 'غياب'),
            ('hr.action.leave.return', 'عودة من إجازة'),
        ]
        pending_docs = []
        pending_docs_total = 0
        for model, label in action_models:
            M = self.env.get(model)
            if M is None:
                continue
            cnt = M.search_count([('state', '=', 'submit')])
            pending_docs_total += cnt
            if cnt:
                pending_docs.append({'type': label, 'count': cnt})

        # --- loans (optional ohrms_loan) ---
        active_loans = 0
        Loan = self.env.get('hr.loan')
        if Loan is not None:
            active_loans = Loan.search_count([('state', '=', 'approve')])

        # --- recent joiners list ---
        recent = emps.sorted(
            key=lambda e: (e.joining_date or (e.create_date.date() if e.create_date else today)),
            reverse=True)[:8]
        new_joiners = [{
            'name': e.name,
            'department': e.department_id.name or '—',
            'job': e.job_id.name or '—',
            'date': str(e.joining_date) if e.joining_date else (
                str(e.create_date.date()) if e.create_date else ''),
        } for e in recent]

        return {
            'kpi': {
                'total': total,
                'new_joiners_year': new_joiners_year,
                'departures_year': departures_year,
                'on_leave_today': on_leave_today,
                'present_today': present_today,
                'currently_in': currently_in,
                'pending_approvals': pending_docs_total + pending_leaves,
                'suspended': suspended,
                'departments': len([d for d in by_department if d['name'] != 'بدون قسم']),
                'active_loans': active_loans,
            },
            'by_department': by_department,
            'by_job': by_job,
            'by_gender': gender,
            'by_category': by_category,
            'joiners_trend': months,
            'by_leave_type': by_leave_type,
            'upcoming_leaves': upcoming_leaves,
            'pending_docs': pending_docs,
            'new_joiners': new_joiners,
            'year': year,
        }

    category_ids = fields.Many2many('hr.employee.category', tracking=True)
    joining_ids = fields.One2many('hr.action.joining', 'employee_id')
    joining_date = fields.Date(compute='compute_joining_date', store=True)
    suspend_date = fields.Date(tracking=True)
    suspend_reason = fields.Text(tracking=True)
    suspend_by = fields.Many2one('res.users', tracking=True)
    can_print_reports = fields.Boolean()
    can_edit = fields.Boolean()

    def write(self, vals):
        if not self.env.context.get('ignore_suspend', False):
            for rec in self:
                if rec.suspend_date and not rec.can_edit:
                    raise ValidationError(f"you can't edit suspended employee {rec.name}!")
        res = super(Employee, self).write(vals)
        return res

    def button_suspend(self):
        return {
            'name': 'Suspend Employee',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'hr.employee.suspend',
            'context': {
                'default_employee_id': self.id,
                'default_date': fields.Date.today(),
            },
            'target': 'new',
        }

    def button_unsuspend(self):
        return {
            'name': 'Unsuspend Employee',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'hr.employee.suspend',
            'context': {
                'default_employee_id': self.id,
                'default_unsuspend': True,
            },
            'target': 'new',
        }

    @api.depends('joining_ids')
    def compute_joining_date(self):
        for rec in self:
            rec.joining_date = False
            if rec.joining_ids:
                rec.joining_date = rec.joining_ids.sorted(key='join_date', reverse=True)[0].join_date

    def _mail_track(self, tracked_fields, initial_values):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial_values)
        # Many2many tracking
        if len(changes) > len(tracking_value_ids):
            for changed_field in changes:
                if tracked_fields[changed_field]['type'] == 'many2many':
                    field = self.env['ir.model.fields']._get(self._name, changed_field)
                    vals = {
                        'field': field.id,
                        'field_desc': field.field_description,
                        'field_type': field.ttype,
                        'tracking_sequence': field.tracking,
                        'old_value_char': ', '.join(initial_values[changed_field].mapped('name')),
                        'new_value_char': ', '.join(self[changed_field].mapped('name')),
                    }
                    tracking_value_ids.append(Command.create(vals))
        return changes, tracking_value_ids
