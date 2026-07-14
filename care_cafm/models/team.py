# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CafmTeam(models.Model):
    """A service team on a facility: supervisor + quality officer + members."""
    _name = 'care.cafm.team'
    _description = 'CAFM Service Team'
    _order = 'facility_id, service_id'

    name = fields.Char(string='الفريق', required=True, translate=True)
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', required=True)
    service_type = fields.Selection(related='service_id.service_type', store=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    # the project the team serves — auto-derived from its facility, still editable
    project_id = fields.Many2one('project.project', string='المشروع',
                                 compute='_compute_project', store=True, readonly=False, index=True)
    supervisor_id = fields.Many2one('res.users', string='المشرف')
    quality_user_id = fields.Many2one('res.users', string='موظف الجودة')
    # Membership is user-based (the user is the unit of access/login); each user
    # can be linked to an HR employee. member_ids kept for the employee view.
    user_member_ids = fields.Many2many('res.users', 'cafm_team_user_rel', 'team_id', 'user_id',
                                       string='المستخدمون الأعضاء')
    member_ids = fields.Many2many('hr.employee', string='الأعضاء')
    member_count = fields.Integer(compute='_compute_counts', store=True)
    reserve_ids = fields.Many2many('hr.employee', 'cafm_team_reserve_rel', 'team_id', 'emp_id',
                                   string='الاحتياطي')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('facility_id')
    def _compute_project(self):
        for t in self:
            if t.facility_id.project_id:
                t.project_id = t.facility_id.project_id

    @api.onchange('user_member_ids')
    def _onchange_user_members(self):
        """Users are the basis of dealing — when users are added, pull their
        linked HR employees into the employee list so both views stay aligned."""
        emps = self.user_member_ids.mapped('employee_id')
        if emps:
            self.member_ids = [(4, e.id) for e in emps]

    @api.depends('member_ids', 'user_member_ids')
    def _compute_counts(self):
        for rec in self:
            rec.member_count = len(rec.member_ids | rec.user_member_ids.mapped('employee_id'))
