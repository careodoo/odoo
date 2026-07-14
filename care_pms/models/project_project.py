# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    pms_department_id = fields.Many2one('hr.department', string='Department', tracking=True, index=True)
    project_manager_id = fields.Many2one('res.users', string='Project Manager', tracking=True)
    portal_user_ids = fields.Many2many(
        'res.users', 'pms_project_portal_user_rel', 'project_id', 'user_id',
        string='Portal Users', help='Special users (supervisors/monitors/clients) who can see this project in the portal.')
    pms_state = fields.Selection(
        [('draft', 'Draft'), ('active', 'Active'), ('follow', 'Needs Follow-up'),
         ('overdue', 'Overdue'), ('closed', 'Closed')],
        string='Project Status', default='active', tracking=True, index=True)

    experience_ids = fields.One2many('care.experience', 'project_id', string='Contracts')
    experience_count = fields.Integer(compute='_compute_pms_counts')

    # ----- contract summary for the project kanban card -----
    pms_client_id = fields.Many2one('res.partner', string='الجهة المتعاقدة',
                                    compute='_compute_contract_summary', store=True)
    pms_client_logo = fields.Image(related='pms_client_id.image_128', string='شعار الجهة')
    contract_expiry_date = fields.Date(string='أقرب انتهاء عقد',
                                       compute='_compute_contract_summary', store=True)
    contract_days_to_expiry = fields.Integer(string='أيام حتى الانتهاء',
                                             compute='_compute_contract_summary', store=True)
    contract_expiry_state = fields.Selection(
        [('none', 'لا عقود'), ('ok', 'سارٍ'), ('expiring', 'قريب الانتهاء'), ('expired', 'منتهٍ')],
        string='حالة العقد', compute='_compute_contract_summary', store=True, default='none')
    contract_active_count = fields.Integer(string='عقود سارية',
                                          compute='_compute_contract_summary', store=True)
    contract_summary = fields.Char(string='ملخص العقود',
                                   compute='_compute_contract_summary', store=True)

    @api.depends('experience_ids', 'experience_ids.state', 'experience_ids.expire_date',
                 'experience_ids.expiry_state', 'experience_ids.partner_id',
                 'experience_ids.days_to_expiry', 'partner_id')
    def _compute_contract_summary(self):
        state_labels = {'draft': 'مسودة', 'submit': 'مُقدَّم', 'valid': 'سارٍ',
                        'under_renewal': 'قيد التجديد', 'expired': 'منتهٍ', 'terminated': 'مُنهى'}
        rank = {'expired': 3, 'expiring': 2, 'ok': 1}
        for p in self:
            live = p.experience_ids.filtered(lambda c: c.state not in ('terminated',))
            # client = the contract party (fallback to the project's own partner)
            p.pms_client_id = (live[:1].partner_id or p.partner_id).id if (live or p.partner_id) else False
            active = live.filtered(lambda c: c.state in ('valid', 'under_renewal'))
            p.contract_active_count = len(active)
            # nearest expiry among live contracts that have a date
            dated = live.filtered(lambda c: c.expire_date)
            if dated:
                nearest = min(dated, key=lambda c: c.expire_date)
                p.contract_expiry_date = nearest.expire_date
                p.contract_days_to_expiry = nearest.days_to_expiry
                worst = max((c.expiry_state or 'ok' for c in dated), key=lambda s: rank.get(s, 0))
                p.contract_expiry_state = worst
            else:
                p.contract_expiry_date = False
                p.contract_days_to_expiry = 0
                p.contract_expiry_state = 'ok' if live else 'none'
            # summary text: "2 سارٍ · 1 قيد التجديد"
            if live:
                from collections import Counter
                cnt = Counter(live.mapped('state'))
                p.contract_summary = ' · '.join(
                    '%s %s' % (n, state_labels.get(s, s)) for s, n in cnt.items())
            else:
                p.contract_summary = 'لا يوجد عقد'
    material_ids = fields.One2many('care.pms.material', 'project_id', string='Materials')
    delivery_ids = fields.One2many('care.pms.delivery.note', 'project_id', string='Delivery Notes')
    pettycash_ids = fields.One2many('care.pms.petty.cash', 'project_id', string='Petty Cash')

    # ----- live profitability (P&L) -----
    pms_currency_id = fields.Many2one('res.currency', string='Currency',
                                      default=lambda s: s.env.company.currency_id)
    pms_revenue = fields.Monetary(string='Monthly Revenue', currency_field='pms_currency_id')
    pms_labor_cost = fields.Monetary(string='Labor Cost', currency_field='pms_currency_id')
    pms_fleet_cost = fields.Monetary(string='Fleet Cost', currency_field='pms_currency_id')
    pms_petty_spent = fields.Monetary(string='Petty Cash Spent', currency_field='pms_currency_id',
                                      compute='_compute_pms_pnl')
    pms_total_cost = fields.Monetary(string='Total Cost', currency_field='pms_currency_id',
                                     compute='_compute_pms_pnl')
    pms_margin = fields.Monetary(string='Margin', currency_field='pms_currency_id',
                                 compute='_compute_pms_pnl')
    pms_margin_pct = fields.Float(string='Margin %', compute='_compute_pms_pnl')

    # ----- SLA -----
    sla_resolution_hours = fields.Integer(string='SLA Resolution (hours)')
    sla_compliance_pct = fields.Float(string='SLA Compliance %', compute='_compute_sla', store=False)

    @api.depends('pms_revenue', 'pms_labor_cost', 'pms_fleet_cost', 'pettycash_ids.spent')
    def _compute_pms_pnl(self):
        for p in self:
            petty = sum(p.pettycash_ids.mapped('spent'))
            p.pms_petty_spent = petty
            p.pms_total_cost = p.pms_labor_cost + p.pms_fleet_cost + petty
            p.pms_margin = p.pms_revenue - p.pms_total_cost
            p.pms_margin_pct = (p.pms_margin / p.pms_revenue * 100.0) if p.pms_revenue else 0.0

    def _compute_sla(self):
        Task = self.env['project.task'].sudo()
        for p in self:
            total = Task.search_count([('project_id', '=', p.id)])
            breached = Task.search_count([('project_id', '=', p.id), ('is_overdue', '=', True)])
            p.sla_compliance_pct = (100.0 * (total - breached) / total) if total else 100.0

    # ----- executive risk score (synthesis) -----
    risk_score = fields.Integer(string='Risk Score', compute='_compute_risk')
    risk_level = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Risk Level', compute='_compute_risk')

    def _compute_risk(self):
        Task = self.env['project.task'].sudo()
        for p in self:
            overdue = p.pms_task_overdue
            compliance = p.compliance_count
            pending_fwd = Task.search_count([('project_id', '=', p.id), ('forward_state', '=', 'pending')])
            pts = overdue * 2 + compliance * 3 + pending_fwd
            if p.pms_revenue and p.pms_margin < 0:
                pts += 20
            if p.sla_compliance_pct < 80:
                pts += 15
            p.risk_score = pts
            p.risk_level = 'high' if pts >= 30 else ('medium' if pts >= 10 else 'low')

    worker_count = fields.Integer(compute='_compute_pms_counts')
    vehicle_count = fields.Integer(compute='_compute_pms_counts')
    pms_task_open = fields.Integer(compute='_compute_pms_counts')
    pms_task_overdue = fields.Integer(compute='_compute_pms_counts')
    custody_count = fields.Integer(compute='_compute_pms_counts')
    material_count = fields.Integer(compute='_compute_pms_counts')
    delivery_count = fields.Integer(compute='_compute_pms_counts')
    supply_count = fields.Integer(compute='_compute_pms_counts')
    pettycash_count = fields.Integer(compute='_compute_pms_counts')
    asset_count = fields.Integer(compute='_compute_pms_counts')
    compliance_count = fields.Integer(compute='_compute_pms_counts')
    fuel_count = fields.Integer(compute='_compute_pms_counts')
    shift_request_count = fields.Integer(compute='_compute_pms_counts')

    def _compliance_domain(self):
        from datetime import date, timedelta
        today = fields.Date.to_string(date.today())
        limit = fields.Date.to_string(date.today() + timedelta(days=60))
        docs = ['residency_end_date', 'affairs_permit_end_date',
                'visa_expire', 'work_permit_expiration_date']
        ors = []
        for f in docs:
            ors += ['&', '&', (f, '!=', False), (f, '>=', today), (f, '<=', limit)]
        return ['&', ('department_id', '=', self.pms_department_id.id)] + ['|', '|', '|'] + ors

    def _compute_pms_counts(self):
        Emp = self.env['hr.employee'].sudo()
        Task = self.env['project.task'].sudo()
        for p in self:
            dept = p.pms_department_id
            # child_of so a parent-department project also counts its sub-department workers
            p.worker_count = Emp.search_count([('department_id', 'child_of', dept.id)]) if dept else 0
            p.vehicle_count = (self.env['fleet.vehicle'].sudo().search_count([('department_id', '=', dept.id)])
                               if dept and 'department_id' in self.env['fleet.vehicle']._fields else 0)
            p.custody_count = (self.env['care.custody'].sudo().search_count([('department_id', '=', dept.id)])
                               if dept and 'care.custody' in self.env else 0)
            p.asset_count = (self.env['account.asset'].sudo().search_count([('department_id', '=', dept.id)])
                             if dept and 'account.asset' in self.env
                             and 'department_id' in self.env['account.asset']._fields else 0)
            p.pms_task_open = Task.search_count([('project_id', '=', p.id), ('stage_id.fold', '=', False)])
            p.pms_task_overdue = Task.search_count([('project_id', '=', p.id), ('is_overdue', '=', True)])
            p.experience_count = len(p.experience_ids)
            p.material_count = self.env['care.pms.material'].sudo().search_count([('project_id', '=', p.id)])
            p.delivery_count = self.env['care.pms.delivery.note'].sudo().search_count([('project_id', '=', p.id)])
            p.supply_count = self.env['care.pms.supply'].sudo().search_count([('project_id', '=', p.id)])
            p.pettycash_count = self.env['care.pms.petty.cash'].sudo().search_count([('project_id', '=', p.id)])
            p.compliance_count = Emp.search_count(p._compliance_domain()) if dept else 0
            p.fuel_count = (self.env['petrol.tank.use'].sudo().search_count(
                [('vehicle_id.department_id', '=', dept.id)])
                if dept and 'petrol.tank.use' in self.env else 0)
            p.shift_request_count = (self.env['employee.shift.request'].sudo().search_count(
                ['|', ('current_department', '=', dept.id), ('new_department', '=', dept.id)])
                if dept and 'employee.shift.request' in self.env else 0)

    # ----- smart buttons -----
    def _open_domain(self, model, domain, name, ctx=None, view_mode='tree,form'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': view_mode, 'domain': domain, 'context': ctx or {},
        }

    def action_pms_workers(self):
        # open the project's workers in Kanban by default
        return self._open_domain('hr.employee', [('department_id', 'child_of', self.pms_department_id.id)],
                                 _('عمال %s') % (self.name or ''), view_mode='kanban,tree,form')

    def action_pms_vehicles(self):
        return self._open_domain('fleet.vehicle', [('department_id', '=', self.pms_department_id.id)],
                                 _('سيارات %s') % (self.name or ''))

    def action_pms_tasks(self):
        return self._open_domain('project.task', [('project_id', '=', self.id)],
                                 _('تاسكات %s') % (self.name or ''),
                                 {'default_project_id': self.id})

    def action_pms_overdue(self):
        return self._open_domain('project.task', [('project_id', '=', self.id), ('is_overdue', '=', True)],
                                 _('متأخرات %s') % (self.name or ''))

    def action_pms_custody(self):
        return self._open_domain('care.custody', [('department_id', '=', self.pms_department_id.id)],
                                 _('عُهد %s') % (self.name or ''))

    def action_pms_contracts(self):
        return self._open_domain('care.experience', [('project_id', '=', self.id)],
                                 _('عقود %s') % (self.name or ''))

    def _shift_domain(self):
        self.ensure_one()
        dept = self.pms_department_id.id
        return ['|', ('current_department', '=', dept), ('new_department', '=', dept)]

    def action_pms_shift_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('طلبات النقل — %s') % (self.name or ''),
            'res_model': 'employee.shift.request', 'view_mode': 'kanban,tree,form',
            'domain': self._shift_domain() if self.pms_department_id else [('id', '=', 0)],
        }

    def action_pms_materials(self):
        return self._open_domain('care.pms.material', [('project_id', '=', self.id)],
                                 _('مخزون %s') % (self.name or ''), {'default_project_id': self.id})

    def action_pms_delivery(self):
        return self._open_domain('care.pms.delivery.note', [('project_id', '=', self.id)],
                                 _('سندات تسليم %s') % (self.name or ''), {'default_project_id': self.id})

    def action_pms_supplies(self):
        return self._open_domain('care.pms.supply', [('project_id', '=', self.id)],
                                 _('واردات %s') % (self.name or ''), {'default_project_id': self.id})

    def action_pms_pettycash(self):
        return self._open_domain('care.pms.petty.cash', [('project_id', '=', self.id)],
                                 _('عُهد %s') % (self.name or ''), {'default_project_id': self.id})

    def action_pms_assets(self):
        return self._open_domain('account.asset', [('department_id', '=', self.pms_department_id.id)],
                                 _('أصول %s') % (self.name or ''))

    def action_pms_compliance(self):
        return self._open_domain('hr.employee', self._compliance_domain(),
                                 _('امتثال عمالة %s') % (self.name or ''))

    def action_pms_fuel(self):
        return self._open_domain('petrol.tank.use',
                                 [('vehicle_id.department_id', '=', self.pms_department_id.id)],
                                 _('محروقات %s') % (self.name or ''))

    def action_pms_statement(self):
        return self.env.ref('care_pms.action_report_project_statement').report_action(self)

    def action_pms_clearance(self):
        return self.env.ref('care_pms.action_report_project_clearance').report_action(self)

    # ----- command-center dashboard data -----
    @api.model
    def _pms_dashboard_projects(self):
        """Projects the dashboard should aggregate: overseers see all, everyone
        else sees only the projects they are involved in (manager / assigned to a
        task / portal user / department manager)."""
        user = self.env.user
        if (user.has_group('base.group_system')
                or user.has_group('care_pms.group_pms_admin')
                or user.has_group('care_pms.group_pms_manager')
                or user.has_group('care_pms.group_pms_supervisor')):
            return self.sudo().search([])
        return self.sudo().search([
            '|', '|', '|',
            ('project_manager_id', '=', user.id),
            ('task_ids.user_ids', 'in', [user.id]),
            ('portal_user_ids', 'in', [user.id]),
            ('pms_department_id.manager_id.user_id', '=', user.id),
        ])

    @api.model
    def get_pms_dashboard_data(self):
        Task = self.env['project.task'].sudo()
        projects = self._pms_dashboard_projects()
        pids = projects.ids or [0]
        tdom = [('project_id', 'in', pids)]
        # workers of these projects' departments (child_of), de-duplicated
        dept_ids = projects.mapped('pms_department_id').ids
        worker_dom = [('department_id', 'child_of', dept_ids)] if dept_ids else [('id', '=', 0)]
        contracts = 0
        if 'care.experience' in self.env:
            contracts = self.env['care.experience'].sudo().search_count([('project_id', 'in', pids)])
        kpi = {
            'projects': len(projects),
            'contracts': contracts,
            'tasks_open': Task.search_count(tdom + [('stage_id.fold', '=', False)]),
            'tasks_overdue': Task.search_count(tdom + [('is_overdue', '=', True)]),
            'forwards_pending': Task.search_count(tdom + [('forward_state', '=', 'pending')]),
            'workers': self.env['hr.employee'].sudo().search_count(worker_dom),
        }
        kind_labels = dict(Task._fields['task_kind'].selection)
        by_kind = []
        for g in Task.read_group(tdom + [('task_kind', '!=', False)], ['task_kind'], ['task_kind']):
            by_kind.append({'key': g['task_kind'], 'label': kind_labels.get(g['task_kind'], g['task_kind']),
                            'value': g['task_kind_count']})
        by_cat = []
        for g in Task.read_group(tdom + [('pms_category_id', '!=', False), ('is_overdue', '=', True)],
                                 ['pms_category_id'], ['pms_category_id'], orderby='pms_category_id_count desc', limit=8):
            by_cat.append({'id': g['pms_category_id'][0], 'label': g['pms_category_id'][1],
                           'value': g['pms_category_id_count']})
        by_dept = []
        for g in Task.read_group(tdom + [('pms_department_id', '!=', False), ('is_overdue', '=', True)],
                                 ['pms_department_id'], ['pms_department_id'], orderby='pms_department_id_count desc', limit=8):
            by_dept.append({'id': g['pms_department_id'][0], 'label': g['pms_department_id'][1],
                            'value': g['pms_department_id_count']})
        top_projects = []
        at_risk = 0
        for p in projects:
            if p.risk_level == 'high':
                at_risk += 1
            top_projects.append({'id': p.id, 'name': p.name, 'open': p.pms_task_open,
                                 'overdue': p.pms_task_overdue, 'workers': p.worker_count,
                                 'vehicles': p.vehicle_count, 'risk': p.risk_level or 'low',
                                 'risk_score': p.risk_score})
        top_projects = sorted(top_projects, key=lambda x: x['risk_score'], reverse=True)[:10]
        kpi['at_risk'] = at_risk
        return {'kpi': kpi, 'by_kind': by_kind, 'by_cat': by_cat, 'by_dept': by_dept,
                'top_projects': top_projects}

