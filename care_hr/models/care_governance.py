# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _


class CareHseIncident(models.Model):
    """Health, Safety & Environment incident."""
    _name = 'care.hse.incident'
    _description = 'HSE Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    location = fields.Char()
    incident_type = fields.Selection([
        ('injury', 'Injury'), ('near_miss', 'Near Miss'), ('property', 'Property Damage'),
        ('violation', 'Safety Violation'), ('fire', 'Fire'), ('other', 'Other'),
    ], default='near_miss', required=True, tracking=True)
    severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], default='low', required=True, tracking=True)
    description = fields.Text(required=True)
    root_cause = fields.Text()
    corrective_action = fields.Text()
    reported_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    state = fields.Selection([
        ('reported', 'Reported'), ('investigating', 'Investigating'), ('closed', 'Closed'),
    ], default='reported', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.hse.incident') or 'New'
        return super().create(vals_list)

    def action_investigate(self):
        self.write({'state': 'investigating'})

    def action_close(self):
        self.write({'state': 'closed'})


class CareEquipment(models.Model):
    """Project equipment / PPE / tools assigned to workers."""
    _name = 'care.equipment'
    _description = 'Equipment / Asset'
    _inherit = ['mail.thread']
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Asset Tag', default='New', copy=False, readonly=True)
    asset_name = fields.Char(string='Asset', required=True)
    category = fields.Selection([
        ('ppe', 'PPE'), ('tool', 'Tool'), ('device', 'Device'), ('gear', 'Gear'), ('other', 'Other'),
    ], default='tool', required=True)
    employee_id = fields.Many2one('hr.employee', string='Assigned To', tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    issue_date = fields.Date(default=fields.Date.context_today, tracking=True)
    return_date = fields.Date(tracking=True)
    expiry_date = fields.Date(string='Expiry (PPE)')
    condition = fields.Selection([
        ('new', 'New'), ('good', 'Good'), ('damaged', 'Damaged'), ('lost', 'Lost'),
    ], default='new', tracking=True)
    state = fields.Selection([
        ('assigned', 'Assigned'), ('returned', 'Returned'), ('retired', 'Retired'),
    ], default='assigned', required=True, tracking=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.equipment') or 'New'
        return super().create(vals_list)

    def action_return(self):
        self.write({'state': 'returned', 'return_date': fields.Date.today()})


class HrJob(models.Model):
    _inherit = 'hr.job'

    job_grade_id = fields.Many2one('care.job.grade', string='Job Grade',
                                   help='Pay tier / grade this position belongs to.')


class CareWorkforcePlan(models.Model):
    """Workforce establishment plan: required vs actual headcount per job."""
    _name = 'care.workforce.plan'
    _description = 'Workforce Plan'
    _order = 'job_id'

    job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='job_id.department_id', store=True)
    job_grade_id = fields.Many2one(related='job_id.job_grade_id', store=True, string='Grade')
    required_headcount = fields.Integer(string='Required', default=0)
    actual_headcount = fields.Integer(compute='_compute_actual', store=False)
    gap = fields.Integer(compute='_compute_actual', store=False)
    fill_rate = fields.Float(string='Fill %', compute='_compute_actual', store=False)
    note = fields.Char()

    _sql_constraints = [('job_uniq', 'unique(job_id)', 'One plan line per job.')]

    def _compute_actual(self):
        Emp = self.env['hr.employee']
        for rec in self:
            actual = Emp.search_count([('job_id', '=', rec.job_id.id), ('active', '=', True)])
            rec.actual_headcount = actual
            rec.gap = (rec.required_headcount or 0) - actual
            rec.fill_rate = round(actual / rec.required_headcount * 100.0, 1) if rec.required_headcount else 0.0


class CareOrgStructure(models.Model):
    """Organization structure & establishment dashboard (mockup 76):
    single landing screen with the headline KPIs and quick links to the
    department org chart, the establishment (workforce plan) and grades."""
    _name = 'care.org.structure'
    _description = 'Organization Structure Dashboard'

    name = fields.Char(default='Organization')
    department_count = fields.Integer(compute='_compute_kpis')
    job_count = fields.Integer(compute='_compute_kpis')
    grade_count = fields.Integer(compute='_compute_kpis')
    approved_total = fields.Integer(string='Approved Establishment', compute='_compute_kpis')
    filled_total = fields.Integer(string='Filled', compute='_compute_kpis')
    vacant_total = fields.Integer(string='Vacant', compute='_compute_kpis')
    fill_rate = fields.Float(string='Fill %', compute='_compute_kpis')

    def _compute_kpis(self):
        Dept = self.env['hr.department']
        Job = self.env['hr.job']
        Grade = self.env['care.job.grade']
        Plan = self.env['care.workforce.plan']
        for rec in self:
            rec.department_count = Dept.search_count([])
            rec.job_count = Job.search_count([])
            rec.grade_count = Grade.search_count([])
            plans = Plan.search([])
            approved = sum(plans.mapped('required_headcount'))
            filled = sum(plans.mapped('actual_headcount'))
            rec.approved_total = approved
            rec.filled_total = filled
            rec.vacant_total = max(approved - filled, 0)
            rec.fill_rate = round(filled * 100.0 / approved, 1) if approved else 0.0

    @api.model
    def _get_singleton(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({'name': 'Organization'})
        return rec

    def action_open_departments(self):
        return {
            'type': 'ir.actions.act_window', 'name': _('Org Chart'),
            'res_model': 'hr.department', 'view_mode': 'kanban,tree,form',
        }

    def action_open_establishment(self):
        return self.env['ir.actions.act_window']._for_xml_id('care_hr.action_care_wfp')

    def action_open_grades(self):
        return self.env['ir.actions.act_window']._for_xml_id('care_hr.action_care_job_grade')
