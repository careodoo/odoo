# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareSla(models.Model):
    """Site-coverage SLA per project: contracted headcount vs actually-present
    workers on a given day. Surfaces understaffing (breach) and penalty risk."""
    _name = 'care.sla'
    _description = 'Coverage SLA'
    _inherit = ['mail.thread']
    _order = 'date desc, gap desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True)
    contract_id = fields.Many2one('care.experience', string='Contract')
    partner_id = fields.Many2one('res.partner', string='Client')
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    required_headcount = fields.Integer(string='Required', tracking=True)
    present_count = fields.Integer(string='Present', compute='_compute_coverage', store=True)
    gap = fields.Integer(string='Gap', compute='_compute_coverage', store=True)
    coverage_pct = fields.Float(string='Coverage %', compute='_compute_coverage', store=True)
    penalty_per_head = fields.Monetary(string='Penalty / Missing Head',
                                       help="Client SLA penalty charged per missing worker per day.")
    penalty_risk = fields.Monetary(string='Penalty Risk', compute='_compute_coverage', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    state = fields.Selection([
        ('ok', 'Covered'), ('warning', 'Under Target'), ('breach', 'Breach'),
    ], compute='_compute_coverage', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.sla') or 'New'
        return super().create(vals_list)

    def _present_count(self):
        """Distinct project workers (via department->project) present on `date`."""
        self.ensure_one()
        if not self.project_id or not self.date:
            return 0
        depts = self.env['hr.department'].search([('project_id', '=', self.project_id.id)])
        emp_ids = set(self.env['care.deployment'].search(
            [('project_id', '=', self.project_id.id)]).employee_id.ids)
        if depts:
            emp_ids |= set(self.env['hr.employee'].search([('department_id', 'in', depts.ids)]).ids)
        if not emp_ids:
            return 0
        self.env.cr.execute("""
            SELECT count(DISTINCT adu.employee_id)
            FROM user_attendance ua JOIN attendance_device_user adu ON adu.id = ua.user_id
            WHERE adu.employee_id IN %s AND ua.timestamp::date = %s
        """, (tuple(emp_ids), self.date))
        return self.env.cr.fetchone()[0] or 0

    @api.depends('project_id', 'date', 'required_headcount', 'penalty_per_head')
    def _compute_coverage(self):
        for r in self:
            r.present_count = r._present_count()
            r.gap = max((r.required_headcount or 0) - r.present_count, 0)
            r.coverage_pct = round(r.present_count / r.required_headcount * 100.0, 1) if r.required_headcount else 0.0
            r.penalty_risk = r.gap * (r.penalty_per_head or 0.0)
            if not r.required_headcount or r.coverage_pct >= 100:
                r.state = 'ok'
            elif r.coverage_pct >= 90:
                r.state = 'warning'
            else:
                r.state = 'breach'

    @api.model
    def action_run_scan(self):
        """Create today's SLA row per contracted project (skip duplicates)."""
        today = fields.Date.context_today(self)
        contracts = self.env['care.experience'].search([('project_id', '!=', False)])
        created = 0
        for c in contracts:
            if self.search_count([('project_id', '=', c.project_id.id), ('date', '=', today)]):
                continue
            self.create({
                'project_id': c.project_id.id, 'contract_id': c.id,
                'partner_id': c.partner_id.id, 'date': today,
                'required_headcount': c.labor_quantity or 0,
            })
            created += 1
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Coverage SLA'),
                       'message': _('%s SLA rows computed for %s.') % (created, today),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }

    @api.model
    def _cron_daily_sla(self):
        self.action_run_scan()
        return True
