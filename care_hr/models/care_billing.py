# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


def _month_bounds(d):
    """Return (first, last) day of the month containing date d."""
    first = d.replace(day=1)
    last = first + relativedelta(months=1) - relativedelta(days=1)
    return first, last


class CareClientBilling(models.Model):
    """Client billing line: contracted price x actual attendance days, per
    project per period. Feeds the existing invoice flow (request.invoice)."""
    _name = 'care.client.billing'
    _description = 'Client Billing (from Attendance)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True)
    contract_id = fields.Many2one('care.experience', string='Contract', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Client', tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True,
                            default=lambda s: _month_bounds(fields.Date.context_today(s))[0])
    date_to = fields.Date(string='To', required=True, tracking=True,
                          default=lambda s: _month_bounds(fields.Date.context_today(s))[1])
    billing_basis = fields.Selection([
        ('annual_contract', 'Annual Contract'),
        ('contract', 'Contract'),
        ('work_order', 'Work Order'),
    ], default='contract', required=True, tracking=True)
    price_type = fields.Selection([
        ('per_day', 'Per Worker-Day'),
        ('fixed', 'Fixed / Month'),
    ], default='per_day', required=True, tracking=True)
    price_unit = fields.Float(string='Rate', tracking=True,
                              help="Per worker-day rate, or the fixed monthly amount.")
    worker_count = fields.Integer(string='Workers', compute='_compute_attendance', store=True)
    work_days = fields.Integer(string='Worker-Days', compute='_compute_attendance', store=True,
                               help="Sum of actual attendance days of the project's deployed workers in the period.")
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('awaiting_client', 'Awaiting Client'),
        ('approved', 'Client Approved'),
        ('invoiced', 'Invoiced'),
    ], default='draft', required=True, tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.client.billing') or 'New'
        return super().create(vals_list)

    @api.onchange('contract_id')
    def _onchange_contract(self):
        if self.contract_id:
            self.project_id = self.contract_id.project_id
            self.partner_id = self.contract_id.partner_id

    # --- attendance-driven figures -------------------------------------
    def _project_employee_ids(self):
        """Employees on this project: via care.deployment, and via the
        department->project link (hr.department.project_id), unioned."""
        self.ensure_one()
        if not self.project_id:
            return []
        emp_ids = set()
        deps = self.env['care.deployment'].search([
            ('project_id', '=', self.project_id.id),
            ('start_date', '<=', self.date_to),
            '|', ('end_date', '=', False), ('end_date', '>=', self.date_from),
        ])
        emp_ids |= set(deps.employee_id.ids)
        depts = self.env['hr.department'].search([('project_id', '=', self.project_id.id)])
        if depts:
            emp_ids |= set(self.env['hr.employee'].search(
                [('department_id', 'in', depts.ids)]).ids)
        return list(emp_ids)

    @api.depends('project_id', 'date_from', 'date_to')
    def _compute_attendance(self):
        for r in self:
            emp_ids = r._project_employee_ids()
            r.worker_count = len(set(emp_ids))
            if emp_ids and r.date_from and r.date_to:
                # Count distinct (employee, day) from the raw device punches
                # (user.attendance -> attendance.device.user -> employee).
                self.env.cr.execute("""
                    SELECT COUNT(*) FROM (
                        SELECT adu.employee_id, ua.timestamp::date AS d
                        FROM user_attendance ua
                        JOIN attendance_device_user adu ON adu.id = ua.user_id
                        WHERE adu.employee_id IN %s
                          AND ua.timestamp::date >= %s AND ua.timestamp::date <= %s
                        GROUP BY adu.employee_id, ua.timestamp::date
                    ) t
                """, (tuple(emp_ids), r.date_from, r.date_to))
                r.work_days = self.env.cr.fetchone()[0] or 0
            else:
                r.work_days = 0

    @api.depends('price_type', 'price_unit', 'work_days')
    def _compute_amount(self):
        for r in self:
            r.amount = r.price_unit if r.price_type == 'fixed' else (r.price_unit * r.work_days)

    # --- workflow ------------------------------------------------------
    def action_submit_client(self):
        self.write({'state': 'awaiting_client'})

    def action_client_approve(self):
        self.write({'state': 'approved'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_generate_invoice(self):
        """Create a draft customer invoice (account.move) for the approved line."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Only client-approved billing lines can be invoiced."))
        if not self.partner_id:
            raise UserError(_("Set the client (partner) first."))
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_("No sales journal configured."))
        label = _("Manpower services %s — %s..%s") % (
            self.project_id.display_name, self.date_from, self.date_to)
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'journal_id': journal.id,
            'project_id': self.project_id.id if 'project_id' in self.env['account.move']._fields else False,
            'invoice_line_ids': [(0, 0, {
                'name': label,
                'quantity': self.work_days if self.price_type == 'per_day' else 1,
                'price_unit': self.price_unit,
            })],
        })
        self.write({'state': 'invoiced', 'invoice_id': move.id})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': move.id, 'view_mode': 'form', 'target': 'current',
        }

    # --- bulk scan -----------------------------------------------------
    @api.model
    def action_run_scan(self):
        """Create a draft billing line per active contract/project for the
        current month (skips ones already present for the period)."""
        first, last = _month_bounds(fields.Date.context_today(self))
        contracts = self.env['care.experience'].search([('project_id', '!=', False)])
        created = 0
        for c in contracts:
            exists = self.search_count([
                ('project_id', '=', c.project_id.id),
                ('date_from', '=', first), ('date_to', '=', last)])
            if exists:
                continue
            monthly = (c.contract_amount / c.period) if c.period else c.contract_amount
            self.create({
                'project_id': c.project_id.id,
                'contract_id': c.id,
                'partner_id': c.partner_id.id,
                'date_from': first, 'date_to': last,
                'price_type': 'fixed',
                'price_unit': monthly or 0.0,
            })
            created += 1
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Client Billing'),
                       'message': _('%s billing line(s) created for %s..%s.') % (created, first, last),
                       'type': 'success', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}},
        }


class CareContractPnl(models.Model):
    """Per-project monthly P&L: revenue vs fully-loaded worker cost."""
    _name = 'care.contract.pnl'
    _description = 'Contract Profitability (P&L)'
    _order = 'date_from desc, margin'

    name = fields.Char(default='New', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    partner_id = fields.Many2one('res.partner', string='Client')
    sector = fields.Selection([('gov', 'Government'), ('private', 'Private')],
                              default='private', string='Sector')
    date_from = fields.Date(string='From', required=True,
                            default=lambda s: _month_bounds(fields.Date.context_today(s))[0])
    date_to = fields.Date(string='To', required=True,
                          default=lambda s: _month_bounds(fields.Date.context_today(s))[1])
    worker_count = fields.Integer(string='Workers', compute='_compute_pnl', store=True)
    revenue = fields.Monetary(string='Revenue', compute='_compute_pnl', store=True)
    cost_wages = fields.Monetary(string='Wages', compute='_compute_pnl', store=True)
    cost_allowances = fields.Monetary(string='Allowances', compute='_compute_pnl', store=True)
    cost_eos = fields.Monetary(string='EOS Accrual', compute='_compute_pnl', store=True)
    cost_total = fields.Monetary(string='Total Cost', compute='_compute_pnl', store=True)
    cost_per_worker = fields.Monetary(string='Cost / Worker', compute='_compute_pnl', store=True)
    margin = fields.Monetary(string='Margin', compute='_compute_pnl', store=True)
    margin_pct = fields.Float(string='Margin %', compute='_compute_pnl', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.contract.pnl') or 'New'
        return super().create(vals_list)

    def _project_employees(self):
        self.ensure_one()
        if not self.project_id:
            return self.env['hr.employee']
        emp_ids = set()
        deps = self.env['care.deployment'].search([
            ('project_id', '=', self.project_id.id),
            ('start_date', '<=', self.date_to),
            '|', ('end_date', '=', False), ('end_date', '>=', self.date_from),
        ])
        emp_ids |= set(deps.employee_id.ids)
        depts = self.env['hr.department'].search([('project_id', '=', self.project_id.id)])
        if depts:
            emp_ids |= set(self.env['hr.employee'].search(
                [('department_id', 'in', depts.ids)]).ids)
        return self.env['hr.employee'].browse(list(emp_ids))

    @api.depends('project_id', 'date_from', 'date_to')
    def _compute_pnl(self):
        Allow = self.env['care.allowance']
        for r in self:
            emps = r._project_employees()
            r.worker_count = len(emps)
            # --- wages (monthly basic from current contract) ---
            wages = 0.0
            for e in emps:
                c = e.contract_id
                wages += (c.wage if c else 0.0)
            r.cost_wages = wages
            # --- allowances recorded in the period (approved/done) ---
            alw = 0.0
            if emps:
                alws = Allow.search([
                    ('employee_id', 'in', emps.ids),
                    ('date', '>=', r.date_from), ('date', '<=', r.date_to),
                    ('state', 'in', ('approved', 'done'))])
                alw = sum(alws.mapped('amount'))
            r.cost_allowances = alw
            # --- EOS monthly accrual: daily(wage/26) * 15 days/yr / 12 ---
            r.cost_eos = round(wages / 26.0 * 15.0 / 12.0, 3) if wages else 0.0
            r.cost_total = r.cost_wages + r.cost_allowances + r.cost_eos
            r.cost_per_worker = (r.cost_total / r.worker_count) if r.worker_count else 0.0
            # --- revenue: matching client billing else monthly contract value ---
            bill = self.env['care.client.billing'].search([
                ('project_id', '=', r.project_id.id),
                ('date_from', '=', r.date_from), ('date_to', '=', r.date_to)], limit=1)
            if bill:
                r.revenue = bill.amount
            else:
                c = self.env['care.experience'].search(
                    [('project_id', '=', r.project_id.id)], limit=1)
                r.revenue = (c.contract_amount / c.period) if (c and c.period) else (c.contract_amount if c else 0.0)
            r.margin = r.revenue - r.cost_total
            r.margin_pct = round(r.margin / r.revenue * 100.0, 1) if r.revenue else 0.0

    @api.model
    def action_run_scan(self):
        """Build a P&L row per project that has deployed workers, current month."""
        first, last = _month_bounds(fields.Date.context_today(self))
        # projects that have a contract OR a department mapped to them
        projects = self.env['care.experience'].search([('project_id', '!=', False)]).project_id
        projects |= self.env['hr.department'].search([('project_id', '!=', False)]).project_id
        created = 0
        for p in projects:
            if self.search_count([('project_id', '=', p.id),
                                  ('date_from', '=', first), ('date_to', '=', last)]):
                continue
            c = self.env['care.experience'].search([('project_id', '=', p.id)], limit=1)
            self.create({
                'project_id': p.id,
                'partner_id': c.partner_id.id if c else False,
                'date_from': first, 'date_to': last,
            })
            created += 1
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Contract P&L'),
                       'message': _('%s P&L row(s) computed for %s..%s.') % (created, first, last),
                       'type': 'success', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}},
        }
