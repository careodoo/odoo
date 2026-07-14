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

        # --- Care HR KPIs (manpower, payroll, compliance) ---
        def _cnt(model, domain):
            M = self.env.get(model)
            return M.search_count(domain) if M is not None else 0
        care_kpi = {'manpower_files': 0, 'quota_total': 0, 'quota_available': 0}
        MF = self.env.get('care.manpower.file')
        if MF is not None:
            files = MF.search([])
            care_kpi['manpower_files'] = len(files)
            care_kpi['quota_total'] = sum(files.mapped('quota'))
            care_kpi['quota_available'] = sum(files.mapped('available_count'))
        care_kpi['coverage_alerts'] = _cnt('care.coverage.alert', [('state', '=', 'open')])
        care_kpi['pending_penalties'] = _cnt('care.penalty', [('state', 'in', ('submitted', 'approved'))])
        care_kpi['pending_allowances'] = _cnt('care.allowance', [('state', 'in', ('submitted', 'dept'))])
        care_kpi['open_violations'] = _cnt('care.traffic.violation', [('state', 'in', ('submitted', 'approved'))])
        care_kpi['gov_tx_overdue'] = _cnt('care.gov.transaction', [('overdue', '=', True)])
        care_kpi['permits_invalid'] = _cnt('care.site.permit', [('state', 'in', ('expired', 'revoked'))])
        care_kpi['open_grievances'] = _cnt('care.grievance', [('state', 'not in', ('closed', 'refused'))])
        # passports
        care_kpi['passports_total'] = _cnt('care.passport', [])
        care_kpi['passports_in_archive'] = _cnt('care.passport', [('state', '=', 'in_archive')])
        care_kpi['passports_out'] = _cnt('care.passport', [('state', '=', 'out')])
        care_kpi['passports_with_pro'] = _cnt('care.passport', [('state', '=', 'out'), ('out_reason', '=', 'pro_residency')])
        care_kpi['passports_expiring'] = _cnt('care.passport', [('expiry_state', '=', 'expiring')])
        care_kpi['passports_expired'] = _cnt('care.passport', [('expiry_state', '=', 'expired')])
        # residency / documents
        res_soon = today + timedelta(days=60)
        care_kpi['residency_expiring'] = Emp.search_count(
            base + [('residency_end_date', '>=', today), ('residency_end_date', '<=', res_soon)])
        care_kpi['residency_expired'] = Emp.search_count(
            base + [('residency_end_date', '!=', False), ('residency_end_date', '<', today)])
        care_kpi['custody_outstanding'] = _cnt('care.custody', [('state', '=', 'issued')])
        care_kpi['eos_pending'] = _cnt('hr.employee.resignation', [('state', 'in', ('submit', 'hr_dept', 'finance_dept'))])

        # nationality distribution (top 10)
        by_nationality = []
        for g in Emp.read_group(base + [('country_id', '!=', False)],
                                ['country_id'], ['country_id'], limit=12):
            by_nationality.append({
                'name': (g['country_id'][1] if g['country_id'] else 'غير محدد'),
                'count': g.get('__count') or g.get('country_id_count') or 0})
        by_nationality.sort(key=lambda x: x['count'], reverse=True)

        # ---- Skills deep statistics ----
        by_skill_type, top_skills = [], []
        ES = self.env.get('hr.employee.skill')
        if ES is not None:
            care_kpi['emp_skills_total'] = ES.search_count([])
            care_kpi['skills_catalog'] = self.env['hr.skill'].search_count([])
            care_kpi['skill_types'] = self.env['hr.skill.type'].search_count([])
            emp_groups = ES.read_group([], ['employee_id'], ['employee_id'])
            n_emp = len([g for g in emp_groups if g['employee_id']])
            care_kpi['emp_with_skills'] = n_emp
            care_kpi['avg_skills_per_emp'] = round(care_kpi['emp_skills_total'] / n_emp, 1) if n_emp else 0
            for g in ES.read_group([], ['skill_type_id'], ['skill_type_id']):
                if g['skill_type_id']:
                    by_skill_type.append({'name': g['skill_type_id'][1],
                                          'count': g.get('__count') or g.get('skill_type_id_count') or 0})
            by_skill_type.sort(key=lambda x: x['count'], reverse=True)
            tmp = []
            for g in ES.read_group([], ['skill_id'], ['skill_id']):
                if g['skill_id']:
                    tmp.append({'name': g['skill_id'][1],
                                'count': g.get('__count') or g.get('skill_id_count') or 0})
            top_skills = sorted(tmp, key=lambda x: x['count'], reverse=True)[:12]

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
            'care': care_kpi,
            'by_nationality': by_nationality,
            'by_skill_type': by_skill_type,
            'top_skills': top_skills,
            'today': str(today),
            'today_60': str(today + timedelta(days=60)),
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
