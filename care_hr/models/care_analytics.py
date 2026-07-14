# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _


class CareException(models.Model):
    """Unified data-quality + operational-exception scanner. One row per check;
    re-run the scan to refresh counts. Powers both the Data Quality center
    (category='data') and the Exceptions center (operational/compliance)."""
    _name = 'care.exception'
    _description = 'Data Quality / Exception'
    _order = 'severity desc, count desc'

    name = fields.Char(required=True)
    check_code = fields.Char(required=True, index=True)
    category = fields.Selection([
        ('data', 'Data Quality'), ('compliance', 'Compliance'),
        ('payroll', 'Payroll'), ('operational', 'Operational'),
    ], required=True)
    severity = fields.Selection([
        ('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical'),
    ], default='warning', required=True)
    count = fields.Integer()
    impact = fields.Char()
    res_model = fields.Char()
    res_domain = fields.Char()
    state = fields.Selection([('open', 'Open'), ('handled', 'Handled')],
                             default='open')
    scan_date = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [('code_uniq', 'unique(check_code)', 'One row per check.')]

    # --- check registry -------------------------------------------------
    @api.model
    def _checks(self):
        today = fields.Date.context_today(self)
        emp_active = [('active', '=', True)]
        return [
            # code, name, category, severity, impact, model, domain
            ('emp_no_contract', _('Workers without a contract'), 'data', 'critical',
             _('Payslip cannot be computed'), 'hr.employee', emp_active + [('contract_id', '=', False)]),
            ('emp_no_bank', _('Workers without IBAN / bank account'), 'data', 'warning',
             _('Breaks WPS / salary transfer'), 'hr.employee', emp_active + [('bank_account_id', '=', False)]),
            ('emp_no_civilid', _('Workers without Civil ID'), 'data', 'warning',
             _('Government transactions blocked'), 'hr.employee',
             emp_active + ['|', ('identification_id', '=', False), ('identification_id', '=', '')]),
            ('emp_no_nationality', _('Workers without nationality'), 'data', 'info',
             _('Incomplete reports'), 'hr.employee', emp_active + [('country_id', '=', False)]),
            ('emp_no_job', _('Workers without job position'), 'data', 'info',
             _('Workforce planning gaps'), 'hr.employee', emp_active + [('job_id', '=', False)]),
            ('emp_no_department', _('Workers without department / project'), 'data', 'warning',
             _('Cannot bill / allocate cost'), 'hr.employee', emp_active + [('department_id', '=', False)]),
            ('emp_no_passport_date', _('Workers without passport expiry date'), 'data', 'warning',
             _('Residency alerts break'), 'hr.employee', emp_active + [('end_date', '=', False)]),
            ('emp_passport_expired', _('Workers with EXPIRED passport / residency'), 'compliance', 'critical',
             _('Legal exposure'), 'hr.employee', emp_active + [('end_date', '!=', False), ('end_date', '<', today)]),
            ('emp_passport_expiring', _('Passport / residency expiring within 60 days'), 'compliance', 'warning',
             _('Renew now'), 'hr.employee',
             emp_active + [('end_date', '>=', today), ('end_date', '<=', today + relativedelta(days=60))]),
        ]

    @api.model
    def action_run_scan(self):
        now = fields.Datetime.now()
        seen = []
        for code, name, cat, sev, impact, model, domain in self._checks():
            seen.append(code)
            try:
                cnt = self.env[model].search_count(domain)
            except Exception:
                cnt = 0
            vals = {
                'name': name, 'check_code': code, 'category': cat, 'severity': sev,
                'impact': impact, 'res_model': model, 'res_domain': repr(domain),
                'count': cnt, 'scan_date': now,
                'state': 'open' if cnt else 'handled',
            }
            rec = self.search([('check_code', '=', code)], limit=1)
            if rec:
                rec.write(vals)
            else:
                self.create(vals)
        # special: duplicate passports (same passport_no on >1 active worker)
        self.env.cr.execute("""
            SELECT count(*) FROM (
                SELECT passport_no FROM hr_employee
                WHERE active AND passport_no IS NOT NULL AND passport_no <> ''
                GROUP BY passport_no HAVING count(*) > 1
            ) t""")
        dup = self.env.cr.fetchone()[0] or 0
        seen.append('emp_dup_passport')
        dvals = {
            'name': _('Duplicate passport numbers'), 'check_code': 'emp_dup_passport',
            'category': 'data', 'severity': 'warning', 'impact': _('Possible duplicate worker'),
            'res_model': 'hr.employee', 'res_domain': "[('active','=',True)]",
            'count': dup, 'scan_date': now, 'state': 'open' if dup else 'handled',
        }
        drec = self.search([('check_code', '=', 'emp_dup_passport')], limit=1)
        (drec.write(dvals) if drec else self.create(dvals))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Scan complete'),
                       'message': _('%s checks evaluated.') % len(seen),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }

    def action_view_records(self):
        self.ensure_one()
        domain = []
        try:
            domain = eval(self.res_domain or '[]')  # noqa: stored by us, safe
        except Exception:
            domain = []
        return {
            'type': 'ir.actions.act_window', 'name': self.name,
            'res_model': self.res_model, 'view_mode': 'tree,form', 'domain': domain,
        }

    def action_handle(self):
        self.write({'state': 'handled'})

    # core checks that reflect true per-record quality (exclude IBAN / Civil ID,
    # which are bulk-missing infrastructure gaps, not record-level quality)
    _CORE_QUALITY_CODES = (
        'emp_no_department', 'emp_no_passport_date',
        'emp_no_nationality', 'emp_no_job',
    )

    @api.model
    def get_quality_score(self):
        """% of active workers with NO core data issue (distinct, deduplicated)."""
        E = self.env['hr.employee']
        total = E.search_count([('active', '=', True)]) or 1
        flawed = set()
        for code, name, cat, sev, impact, model, domain in self._checks():
            if code in self._CORE_QUALITY_CODES and model == 'hr.employee':
                flawed |= set(E.search(domain).ids)
        return round((1 - len(flawed) / total) * 100.0, 1)


class CareAttrition(models.Model):
    """Attrition rate per dimension (departures / headcount) over a window."""
    _name = 'care.attrition'
    _description = 'Attrition Analysis'
    _order = 'rate desc'

    name = fields.Char()
    dimension = fields.Selection([
        ('department', 'Department / Project'), ('country', 'Nationality'), ('job', 'Job'),
    ], required=True)
    dimension_label = fields.Char(string='Group')
    headcount = fields.Integer()
    departures = fields.Integer(string='Departures')
    rate = fields.Float(string='Attrition %')
    scan_date = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def action_run_scan(self):
        self.search([]).unlink()
        now = fields.Datetime.now()
        E = self.env['hr.employee']
        groupers = [
            ('department', 'department_id'),
            ('country', 'country_id'),
            ('job', 'job_id'),
        ]
        rows = []
        for dim, field in groupers:
            active = E.read_group([('active', '=', True)], [field], [field])
            # departure_date is sparse on historical leavers, so count all
            # departed (active=False) per dimension for a meaningful rate.
            left = E.with_context(active_test=False).read_group(
                [('active', '=', False)], [field], [field])
            left_map = {(g[field][0] if g.get(field) else False): (g.get('__count') or g.get(field + '_count') or 0)
                        for g in left}
            for g in active:
                key = g[field][0] if g.get(field) else False
                label = g[field][1] if g.get(field) else _('(none)')
                hc = g.get('__count') or g.get(field + '_count') or 0
                dep = left_map.get(key, 0)
                base = hc + dep
                rate = round(dep / base * 100.0, 1) if base else 0.0
                if hc or dep:
                    rows.append({
                        'name': label, 'dimension': dim, 'dimension_label': label,
                        'headcount': hc, 'departures': dep, 'rate': rate, 'scan_date': now,
                    })
        self.create(rows)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Attrition'), 'message': _('%s groups analysed.') % len(rows),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }


class CareAttritionRisk(models.Model):
    """At-risk active workers scored from grievances + loans + penalties."""
    _name = 'care.attrition.risk'
    _description = 'Attrition Risk'
    _order = 'score desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    indicators = fields.Char()
    score = fields.Integer()
    risk = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    scan_date = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def action_run_scan(self):
        self.search([]).unlink()
        now = fields.Datetime.now()
        Griev = self.env['care.grievance']
        Pen = self.env['care.penalty']
        emps = self.env['hr.employee'].search([('active', '=', True)])
        rows = []
        for e in emps:
            score, ind = 0, []
            g = Griev.search_count([('employee_id', '=', e.id)])
            if g:
                score += g * 2
                ind.append(_('%s grievance(s)') % g)
            p = Pen.search_count([('employee_id', '=', e.id)])
            if p:
                score += p
                ind.append(_('%s penalty(ies)') % p)
            if e.end_date and e.end_date < fields.Date.context_today(self):
                score += 3
                ind.append(_('expired residency'))
            if score >= 2:
                rows.append({
                    'employee_id': e.id, 'indicators': ', '.join(ind), 'score': score,
                    'risk': 'high' if score >= 5 else 'medium', 'scan_date': now,
                })
        self.create(rows)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Attrition Risk'), 'message': _('%s at-risk workers.') % len(rows),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }
