# -*- coding: utf-8 -*-
# Link CAFM into the Project Management system (care_pms projects are project.project).
from odoo import fields, models, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    cafm_facility_ids = fields.One2many('care.cafm.facility', 'project_id', string='مرافق CAFM')
    cafm_team_ids = fields.One2many('care.cafm.team', 'project_id', string='فرق المشروع')
    cafm_building_ids = fields.Many2many('care.cafm.building', compute='_compute_cafm_structure',
                                         string='المباني')
    cafm_facility_count = fields.Integer(compute='_compute_cafm')
    cafm_workorder_count = fields.Integer(compute='_compute_cafm')
    cafm_wo_open = fields.Integer(compute='_compute_cafm')
    cafm_team_count = fields.Integer(compute='_compute_cafm')
    cafm_building_count = fields.Integer(compute='_compute_cafm_structure')
    cafm_location_count = fields.Integer(compute='_compute_cafm_structure')
    is_cafm_project = fields.Boolean(string='مشروع CAFM', index=True, tracking=True,
                                     help='يظهر في قائمة مشاريع CAFM حتى قبل ربط أي مرفق.')

    def _compute_cafm(self):
        WO = self.env['care.cafm.workorder']
        for p in self:
            p.cafm_facility_count = len(p.cafm_facility_ids)
            p.cafm_team_count = len(p.cafm_team_ids)
            p.cafm_workorder_count = WO.search_count([('project_id', '=', p.id)])
            p.cafm_wo_open = WO.search_count([('project_id', '=', p.id),
                                              ('state', 'not in', ('done', 'verified', 'cancelled'))])

    def _compute_cafm_structure(self):
        for p in self:
            buildings = p.cafm_facility_ids.mapped('building_ids')
            p.cafm_building_ids = buildings
            p.cafm_building_count = len(buildings)
            p.cafm_location_count = len(p.cafm_facility_ids.mapped('location_ids'))

    def action_cafm_buildings(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('مباني %s') % (self.name or ''),
                'res_model': 'care.cafm.building', 'view_mode': 'tree,form',
                'domain': [('id', 'in', self.cafm_building_ids.ids)]}

    def action_cafm_teams(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('فرق %s') % (self.name or ''),
                'res_model': 'care.cafm.team', 'view_mode': 'tree,form',
                'domain': [('project_id', '=', self.id)],
                'context': {'default_project_id': self.id}}

    def action_cafm_facilities(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('مرافق %s') % (self.name or ''),
                'res_model': 'care.cafm.facility', 'view_mode': 'tree,form',
                'domain': [('project_id', '=', self.id)],
                'context': {'default_project_id': self.id}}

    def action_cafm_workorders(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('أوامر عمل %s') % (self.name or ''),
                'res_model': 'care.cafm.workorder', 'view_mode': 'tree,form,kanban',
                'domain': [('project_id', '=', self.id)]}


class CafmProjectPick(models.TransientModel):
    """Pick an EXISTING project and register it under CAFM."""
    _name = 'care.cafm.project.pick'
    _description = 'اختيار مشروع موجود'

    project_id = fields.Many2one('project.project', string='المشروع (موجود مسبقاً)', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.project_id.is_cafm_project = True
        return {
            'type': 'ir.actions.act_window', 'name': self.project_id.name,
            'res_model': 'project.project', 'res_id': self.project_id.id,
            'view_mode': 'form', 'target': 'current',
        }
