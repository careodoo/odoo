# -*- coding: utf-8 -*-
"""Hierarchical statistics for the facility structure (Facility › Building ›
Floor › Location). Each node reports its OWN stats and the ROLLED-UP totals of
everything beneath it: a floor sums its offices, a building sums its floors, a
facility sums its buildings — while every leaf keeps its separate stats."""
from odoo import api, fields, models

# the stat fields every hierarchy node exposes
_STAT_FIELDS = {
    'stat_buildings': 'مبانٍ',
    'stat_floors': 'أدوار',
    'stat_locations': 'مواقع/غرف',
    'stat_offices': 'مكاتب',
    'stat_restrooms': 'دورات مياه',
    'stat_assets': 'أصول',
    'stat_wo_total': 'أوامر عمل',
    'stat_wo_open': 'أوامر مفتوحة',
    'stat_wo_overdue': 'متأخرة SLA',
    'stat_requests_open': 'طلبات مفتوحة',
    'stat_consumption_qty': 'استهلاك (كمية)',
    'stat_consumption_value': 'استهلاك (قيمة)',
}


def _blank():
    return {k: 0 for k in _STAT_FIELDS}


def _compute_stats(records, locs_getter, extra_dom_getter=None):
    """Fill the stat fields on each record. `locs_getter(rec)` returns the set
    of care.cafm.location under the node; `extra_dom_getter(rec)` (optional)
    adds records tied directly to the node (e.g. by facility_id)."""
    env = records.env
    WO = env['care.cafm.workorder'].sudo() if 'care.cafm.workorder' in env else None
    Asset = env['care.cafm.asset'].sudo() if 'care.cafm.asset' in env else None
    Req = env['care.cafm.service.request'].sudo() if 'care.cafm.service.request' in env else None
    Move = env['care.cafm.stock.move'].sudo() if 'care.cafm.stock.move' in env else None
    Loc = env['care.cafm.location'].sudo()
    open_states = ('new', 'assigned', 'in_progress', 'scheduled', 'open')
    for rec in records:
        vals = _blank()
        locs = locs_getter(rec)
        lids = locs.ids
        # structure
        vals['stat_locations'] = len(locs)
        vals['stat_offices'] = len(locs.filtered(lambda l: l.location_type == 'office'))
        vals['stat_restrooms'] = len(locs.filtered(lambda l: l.location_type == 'restroom'))
        if 'floor_ids' in rec._fields:
            vals['stat_floors'] = len(rec.floor_ids) if rec._name == 'care.cafm.building' else vals['stat_floors']
        # per-model domain: locations under the node, plus any node-direct extra
        loc_dom = [('location_id', 'in', lids)] if lids else [('id', '=', 0)]
        extra = extra_dom_getter(rec) if extra_dom_getter else None
        wo_dom = (['|'] + extra + [('location_id', 'in', lids)]) if (extra and lids) else (extra or loc_dom)
        if WO is not None:
            vals['stat_wo_total'] = WO.search_count(wo_dom)
            vals['stat_wo_open'] = WO.search_count(wo_dom + [('state', 'in', open_states)])
            vals['stat_wo_overdue'] = len(WO.search(wo_dom).filtered('is_overdue'))
        if Asset is not None:
            vals['stat_assets'] = Asset.search_count(wo_dom)
        if Req is not None:
            vals['stat_requests_open'] = Req.search_count(wo_dom + [('state', 'in', ('new', 'assigned', 'in_progress'))]) if 'state' in Req._fields else Req.search_count(wo_dom)
        if Move is not None:
            mv = Move.search((['|'] + extra + [('location_id', 'in', lids)]) if (extra and lids) else (loc_dom)).filtered(lambda m: m.move_type == 'issue')
            vals['stat_consumption_qty'] = round(sum(mv.mapped('quantity')), 1)
            vals['stat_consumption_value'] = round(sum(mv.mapped('total_cost')), 2)
        for k, v in vals.items():
            rec[k] = v


class _StatsMixinFields(models.AbstractModel):
    _name = 'care.cafm.stats.mixin'
    _description = 'CAFM hierarchical stats fields'

    stat_buildings = fields.Integer('مبانٍ', compute='_compute_stats')
    stat_floors = fields.Integer('أدوار', compute='_compute_stats')
    stat_locations = fields.Integer('مواقع/غرف', compute='_compute_stats')
    stat_offices = fields.Integer('مكاتب', compute='_compute_stats')
    stat_restrooms = fields.Integer('دورات مياه', compute='_compute_stats')
    stat_assets = fields.Integer('أصول', compute='_compute_stats')
    stat_wo_total = fields.Integer('أوامر عمل', compute='_compute_stats')
    stat_wo_open = fields.Integer('أوامر مفتوحة', compute='_compute_stats')
    stat_wo_overdue = fields.Integer('متأخرة SLA', compute='_compute_stats')
    stat_requests_open = fields.Integer('طلبات مفتوحة', compute='_compute_stats')
    stat_consumption_qty = fields.Float('استهلاك (كمية)', compute='_compute_stats')
    stat_consumption_value = fields.Float('استهلاك (قيمة)', compute='_compute_stats')

    def _compute_stats(self):
        raise NotImplementedError


class CafmFacilityStats(models.Model):
    _name = 'care.cafm.facility'
    _inherit = ['care.cafm.facility', 'care.cafm.stats.mixin']

    def _compute_stats(self):
        Loc = self.env['care.cafm.location'].sudo()

        def locs(rec):
            return Loc.search([('facility_id', '=', rec.id)])
        _compute_stats(self, locs, lambda rec: [('facility_id', '=', rec.id)])
        for rec in self:
            rec.stat_buildings = len(rec.building_ids)
            rec.stat_floors = sum(len(b.floor_ids) for b in rec.building_ids)


class CafmBuildingStats(models.Model):
    _name = 'care.cafm.building'
    _inherit = ['care.cafm.building', 'care.cafm.stats.mixin']

    def _compute_stats(self):
        Loc = self.env['care.cafm.location'].sudo()

        def locs(rec):
            return Loc.search([('building_id', '=', rec.id)])
        _compute_stats(self, locs)
        for rec in self:
            rec.stat_buildings = 1
            rec.stat_floors = len(rec.floor_ids)


class CafmFloorStats(models.Model):
    _name = 'care.cafm.floor'
    _inherit = ['care.cafm.floor', 'care.cafm.stats.mixin']

    def _compute_stats(self):
        _compute_stats(self, lambda rec: rec.location_ids)
        for rec in self:
            rec.stat_floors = 1


class CafmLocationStats(models.Model):
    _name = 'care.cafm.location'
    _inherit = ['care.cafm.location', 'care.cafm.stats.mixin']

    def _compute_stats(self):
        _compute_stats(self, lambda rec: rec)
