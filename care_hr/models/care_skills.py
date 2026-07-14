# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrSkill(models.Model):
    _inherit = 'hr.skill'

    criticality = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Criticality', default='medium')


class HrEmployeeSkill(models.Model):
    """Add certification tracking to employee skills (valid-until + state)."""
    _inherit = 'hr.employee.skill'

    certified = fields.Boolean(string='Certified')
    cert_reference = fields.Char(string='Certificate Ref')
    cert_issue_date = fields.Date(string='Certificate Issue')
    cert_expiry = fields.Date(string='Certificate Expiry')
    cert_state = fields.Selection([
        ('none', 'No Certificate'), ('valid', 'Valid'),
        ('expiring', 'Expiring'), ('expired', 'Expired'),
    ], compute='_compute_cert_state', store=True)

    @api.depends('certified', 'cert_expiry')
    def _compute_cert_state(self):
        today = fields.Date.today()
        soon = today + timedelta(days=60)
        for rec in self:
            if not rec.certified:
                rec.cert_state = 'none'
            elif not rec.cert_expiry:
                rec.cert_state = 'valid'
            elif rec.cert_expiry < today:
                rec.cert_state = 'expired'
            elif rec.cert_expiry <= soon:
                rec.cert_state = 'expiring'
            else:
                rec.cert_state = 'valid'

    @api.model
    def get_skills_dashboard_data(self):
        """Data for the Skills Command Center (OWL dashboard)."""
        ES = self
        total = ES.search_count([])
        catalog = self.env['hr.skill'].search_count([])
        types = self.env['hr.skill.type'].search_count([])
        emp_groups = ES.read_group([], ['employee_id'], ['employee_id'])
        n_emp = len([g for g in emp_groups if g['employee_id']])

        def grp(field):
            out = []
            for g in ES.read_group([], [field], [field]):
                if g[field]:
                    out.append({'name': g[field][1],
                                'count': g.get('__count') or g.get(field + '_count') or 0})
            return sorted(out, key=lambda x: x['count'], reverse=True)

        by_type = grp('skill_type_id')
        top_skills = grp('skill_id')[:12]
        # languages
        langs = []
        for g in ES.read_group([('skill_type_id.name', 'in', ('Language', 'Languages'))],
                               ['skill_id'], ['skill_id']):
            if g['skill_id']:
                langs.append({'name': g['skill_id'][1],
                              'count': g.get('__count') or g.get('skill_id_count') or 0})
        langs = sorted(langs, key=lambda x: x['count'], reverse=True)[:8]
        # certifications
        certified = ES.search_count([('certified', '=', True)])
        cert_expiring = ES.search_count([('cert_state', '=', 'expiring')])
        cert_expired = ES.search_count([('cert_state', '=', 'expired')])
        # level distribution
        levels = []
        for g in ES.read_group([], ['skill_level_id'], ['skill_level_id'], limit=20):
            if g['skill_level_id']:
                levels.append({'name': g['skill_level_id'][1],
                               'count': g.get('__count') or g.get('skill_level_id_count') or 0})
        levels = sorted(levels, key=lambda x: x['count'], reverse=True)[:8]
        # gap summary (job requirements under 90% coverage)
        gaps = []
        JS = self.env['care.job.skill']
        for js in JS.search([]):
            js._compute_coverage()
            if js.coverage < 90:
                gaps.append({'job': js.job_id.name or '-', 'skill': js.skill_id.name or '-',
                             'coverage': js.coverage, 'gap': js.gap_count})
        gaps = sorted(gaps, key=lambda x: x['coverage'])[:10]

        return {
            'kpi': {
                'total': total, 'catalog': catalog, 'types': types, 'emp_with_skills': n_emp,
                'avg': round(total / n_emp, 1) if n_emp else 0,
                'certified': certified, 'cert_expiring': cert_expiring, 'cert_expired': cert_expired,
                'critical_gaps': len(gaps),
            },
            'by_type': by_type, 'top_skills': top_skills, 'languages': langs,
            'levels': levels, 'gaps': gaps,
        }

    @api.model
    def _cron_cert_reminder(self):
        today = fields.Date.today()
        soon = today + timedelta(days=30)
        recs = self.search([('certified', '=', True), ('cert_expiry', '>=', today),
                            ('cert_expiry', '<=', soon)])
        for rec in recs:
            emp = rec.employee_id
            if emp and emp.user_id:
                rec.employee_id.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=emp.user_id.id,
                    summary=_('Certificate expiring'),
                    note=_('%s certificate (%s) expires on %s') % (
                        rec.skill_id.name, rec.cert_reference or '', rec.cert_expiry))


class CareJobSkill(models.Model):
    """Required skill per job position — drives the Skill Gap Analysis."""
    _name = 'care.job.skill'
    _description = 'Job Skill Requirement'
    _order = 'job_id, skill_id'

    job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade')
    skill_id = fields.Many2one('hr.skill', string='Skill', required=True)
    skill_type_id = fields.Many2one(related='skill_id.skill_type_id', store=True)
    required_level_id = fields.Many2one(
        'hr.skill.level', string='Required Level',
        domain="[('skill_type_id','=',skill_type_id)]")
    required_progress = fields.Integer(related='required_level_id.level_progress', store=True)
    criticality = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], default='high')
    employees_count = fields.Integer(compute='_compute_coverage', store=False)
    covered_count = fields.Integer(compute='_compute_coverage', store=False)
    gap_count = fields.Integer(compute='_compute_coverage', store=False)
    coverage = fields.Float(string='Coverage %', compute='_compute_coverage', store=False)

    _sql_constraints = [
        ('uniq', 'unique(job_id, skill_id)', 'This skill is already required for this job.'),
    ]

    def _compute_coverage(self):
        Emp = self.env['hr.employee']
        ES = self.env['hr.employee.skill']
        for rec in self:
            emps = Emp.search([('job_id', '=', rec.job_id.id), ('active', '=', True)])
            rec.employees_count = len(emps)
            if not rec.skill_id or not emps:
                rec.covered_count = rec.gap_count = 0
                rec.coverage = 0.0
                continue
            skilled = ES.search([
                ('employee_id', 'in', emps.ids), ('skill_id', '=', rec.skill_id.id),
                ('level_progress', '>=', rec.required_progress or 0.0)])
            covered = len(set(skilled.mapped('employee_id').ids))
            rec.covered_count = covered
            rec.gap_count = len(emps) - covered
            rec.coverage = round(covered / len(emps) * 100.0, 1) if emps else 0.0

    def action_view_gap_employees(self):
        """Employees in this job who DON'T meet the required level."""
        self.ensure_one()
        emps = self.env['hr.employee'].search(
            [('job_id', '=', self.job_id.id), ('active', '=', True)])
        ok = self.env['hr.employee.skill'].search([
            ('employee_id', 'in', emps.ids), ('skill_id', '=', self.skill_id.id),
            ('level_progress', '>=', self.required_progress or 0.0)]).mapped('employee_id')
        missing = emps - ok
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missing: %s') % self.skill_id.name,
            'res_model': 'hr.employee', 'view_mode': 'tree,form',
            'domain': [('id', 'in', missing.ids)],
        }


class CareSkillAssessment(models.Model):
    """Periodic skill assessment — records and (on apply) updates the employee's
    skill level."""
    _name = 'care.skill.assessment'
    _description = 'Skill Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    skill_id = fields.Many2one('hr.skill', required=True, tracking=True)
    skill_type_id = fields.Many2one(related='skill_id.skill_type_id', store=True)
    assessor_id = fields.Many2one('res.users', string='Assessor',
                                  default=lambda self: self.env.user, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    previous_level_id = fields.Many2one('hr.skill.level', string='Previous Level', readonly=True)
    new_level_id = fields.Many2one('hr.skill.level', string='New Level',
                                   domain="[('skill_type_id','=',skill_type_id)]", tracking=True)
    notes = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('done', 'Applied')],
                             default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.onchange('employee_id', 'skill_id')
    def _onchange_current_level(self):
        if self.employee_id and self.skill_id:
            es = self.env['hr.employee.skill'].search([
                ('employee_id', '=', self.employee_id.id),
                ('skill_id', '=', self.skill_id.id)], limit=1)
            self.previous_level_id = es.skill_level_id.id if es else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.skill.assessment') or 'New'
        return super().create(vals_list)

    def action_apply(self):
        for rec in self:
            if not rec.new_level_id:
                raise UserError(_('Select the new level first.'))
            ES = self.env['hr.employee.skill']
            es = ES.search([('employee_id', '=', rec.employee_id.id),
                            ('skill_id', '=', rec.skill_id.id)], limit=1)
            if es:
                es.skill_level_id = rec.new_level_id.id
            else:
                ES.create({
                    'employee_id': rec.employee_id.id, 'skill_id': rec.skill_id.id,
                    'skill_type_id': rec.skill_type_id.id, 'skill_level_id': rec.new_level_id.id,
                })
            rec.state = 'done'
        return True


class CareSkillEndorsement(models.Model):
    """Peer/manager endorsement of an employee's skill."""
    _name = 'care.skill.endorsement'
    _description = 'Skill Endorsement'
    _order = 'date desc, id desc'

    employee_id = fields.Many2one('hr.employee', required=True)
    skill_id = fields.Many2one('hr.skill', required=True)
    endorsed_by = fields.Many2one('res.users', string='Endorsed By',
                                  default=lambda self: self.env.user, required=True)
    date = fields.Date(default=fields.Date.context_today)
    comment = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
