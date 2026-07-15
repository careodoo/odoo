# -*- coding: utf-8 -*-
"""One-shot, idempotent migration of legacy ``service_order`` data into the new
``cafm.waste.*`` models. Safe to re-run — records already migrated (matched by
serial / sequence / name) are skipped. Trigger from Settings ▸ Technical ▸
Server Actions ▸ «ترحيل بيانات النفايات», or::

    env['cafm.waste.order'].migrate_from_service_order()
"""
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class WasteMigrate(models.AbstractModel):
    _name = 'cafm.waste.migrate'
    _description = 'ترحيل بيانات النفايات من service_order'

    @api.model
    def run(self):
        return self.env['cafm.waste.order'].migrate_from_service_order()


class WasteOrderMigrate(models.Model):
    _inherit = 'cafm.waste.order'

    @api.model
    def _map_by_name(self, legacy_recs, target_model, extra=None):
        """Ensure a target record exists per legacy record (matched by name);
        return {legacy_id: new_id}."""
        Target = self.env[target_model].sudo()
        out = {}
        for r in legacy_recs:
            new = Target.search([('name', '=', r.name)], limit=1)
            if not new:
                vals = {'name': r.name}
                if extra:
                    vals.update(extra(r))
                new = Target.create(vals)
            out[r.id] = new.id
        return out

    @api.model
    def migrate_from_service_order(self):
        env = self.env
        if 'service.order' not in env:
            _logger.warning('service_order not installed — nothing to migrate')
            return {'skipped': True}

        S = lambda m: env[m].sudo()
        # ---- reference data (dedupe by name) --------------------------------
        type_map = self._map_by_name(S('service.type').search([]), 'cafm.waste.type')
        center_map = self._map_by_name(
            S('service.center').search([]), 'cafm.waste.center',
            extra=lambda r: {'is_incinerator': True} if 'حكوم' in (r.name or '') or 'incinerat' in (r.name or '').lower() else {})
        item_map = {}
        for it in S('service.item').search([]):
            new = S('cafm.waste.item').search([('name', '=', it.name)], limit=1)
            if not new:
                new = S('cafm.waste.item').create({
                    'name': it.name, 'image': it.image, 'width': it.width,
                    'height': it.height, 'weight': it.weight,
                    'type_id': type_map.get(it.type_id.id) if it.type_id else False})
            item_map[it.id] = new.id

        # ---- projects (preserve sequence) -----------------------------------
        project_map = {}
        for p in S('service.project').search([]):
            new = S('cafm.waste.project').search(
                ['|', ('sequence', '=', p.sequence), ('name', '=', p.name)], limit=1)
            if not new:
                new = S('cafm.waste.project').create({
                    'name': p.name, 'sequence': p.sequence, 'contact_id': p.contact_id.id,
                    'start_date': p.start_date, 'end_date': p.end_date,
                    'image': p.image, 'notes': p.notes})
            project_map[p.id] = new.id

        # pickups + teams (belong to project)
        pickup_map = {}
        for pl in S('service.pickup.location').search([]):
            new = S('cafm.waste.pickup.location').search(
                [('name', '=', pl.name), ('project_id', '=', project_map.get(pl.project_id.id))], limit=1)
            if not new:
                new = S('cafm.waste.pickup.location').create({
                    'name': pl.name, 'address': pl.address,
                    'project_id': project_map.get(pl.project_id.id)})
            pickup_map[pl.id] = new.id
        team_map = {}
        for t in S('service.team').search([]):
            new = S('cafm.waste.team').search([('name', '=', t.name)], limit=1)
            if not new:
                new = S('cafm.waste.team').create({
                    'name': t.name, 'project_id': project_map.get(t.project_id.id),
                    'employee_ids': [(6, 0, t.employee_ids.ids)]})
            team_map[t.id] = new.id

        # ---- orders (no trip yet) -------------------------------------------
        Order = S('cafm.waste.order')
        order_map, n_orders = {}, 0
        for o in S('service.order').search([]):
            new = Order.search([('serial', '=', o.serial)], limit=1)
            if not new:
                new = Order.create({
                    'serial': o.serial,
                    'project_id': project_map.get(o.project_id.id),
                    'type_id': type_map.get(o.type_id.id) if o.type_id else False,
                    'pickup_location_id': pickup_map.get(o.pickup_location_id.id) if o.pickup_location_id else False,
                    'request_datetime': o.request_datetime,
                    'order_datetime': o.order_datetime,
                    'notes': o.notes,
                    'states': o.states,
                    'ops_manager_id': o.ops_manager_id.id if 'ops_manager_id' in o._fields else False,
                    'driver_id': o.driver_id.id if 'driver_id' in o._fields else False,
                    'receiver_id': o.receiver_id.id if 'receiver_id' in o._fields else False,
                    'proof_image': o.proof_image if 'proof_image' in o._fields else False,
                    'final_weight': o.final_weight if 'final_weight' in o._fields else 0.0,
                    'final_note': o.final_note if 'final_note' in o._fields else False,
                    'order_line_ids': [(0, 0, {'item_id': item_map.get(l.item_id.id), 'quantity': l.quantity})
                                       for l in o.order_line_ids if item_map.get(l.item_id.id)],
                })
                n_orders += 1
            order_map[o.id] = new.id

        # ---- trips (link to order + lines) ----------------------------------
        Trip = S('cafm.waste.trip')
        n_trips = 0
        for t in S('service.trip').search([]):
            new = Trip.search([('sequence', '=', t.sequence)], limit=1)
            if not new:
                new = Trip.create({
                    'sequence': t.sequence,
                    'project_id': project_map.get(t.project_id.id),
                    'pickup_location_id': pickup_map.get(t.pickup_location_id.id) if t.pickup_location_id else False,
                    'center_id': center_map.get(t.center_id.id) if t.center_id else False,
                    'type_id': type_map.get(t.type_id.id) if t.type_id else False,
                    'team_id': team_map.get(t.team_id.id) if t.team_id else False,
                    'pickuped_datetime': t.pickuped_datetime,
                    'contact_id': t.contact_id.id,
                    'trip_date': t.trip_date,
                    'states': t.states,
                    'order_id': order_map.get(t.order_id.id) if t.order_id else False,
                    'trip_line_ids': [(0, 0, {'item_id': item_map.get(l.item_id.id), 'quantity': l.quantity,
                                              'order_id': order_map.get(l.order_id.id) if l.order_id else False})
                                      for l in t.trip_line_ids if item_map.get(l.item_id.id)],
                })
                n_trips += 1
            # link order.trip_id back
            if t.order_id and order_map.get(t.order_id.id):
                Order.browse(order_map[t.order_id.id]).write({'trip_id': new.id})

        env.cr.commit()
        result = {'orders': n_orders, 'trips': n_trips, 'projects': len(project_map),
                  'items': len(item_map)}
        _logger.info('CAFM waste migration done: %s', result)
        return result
