# -*- coding: utf-8 -*-
"""Client-facing AGRICULTURE / LANDSCAPING endpoints — a full mirror of the
care_cafm_agri module's client-relevant data (irrigation zones, tree register,
tree works and species catalogue), hard-scoped to the caller's facilities so a
client only ever sees the greenery ops for their own sites.

Everything is read with sudo() and scoped through care.cafm.facility.partner_id."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, _body, API

# requested tree-work → human label used in the raised service request
_OP_LABELS = {
    'prune': 'تقليم', 'fertilize': 'تسميد', 'pest': 'مكافحة آفات',
    'inspect': 'فحص', 'weed': 'إزالة أعشاب', 'water': 'ريّ إضافي',
    'remove': 'إزالة/قطع', 'other': 'عمل زراعي',
}


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class AgriClientApi(Controller):

    # ---- scoping ----------------------------------------------------------
    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        # CAFM client sub-users: bridge to the client company's partner
        if 'care.cafm.client' in env:
            clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])])
            for cp in clients.mapped('partner_id'):
                pids.add(cp.id)
                pids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _fac_ids(self, env):
        # optional ?facility_id= / ?project_id= scoping like the rest of the portal
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _guard(self, env):
        if 'care.cafm.agri.zone' not in env:
            return _err('خدمة الزراعة غير مفعّلة', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/agri/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.agri.zone' not in env:
            return _ok({'available': False})
        fids = self._fac_ids(env)
        Zone = env['care.cafm.agri.zone'].sudo()
        Plant = env['care.cafm.agri.plant'].sudo()
        Op = env['care.cafm.agri.operation'].sudo()
        from odoo import fields as F
        tdy = F.Date.context_today(Zone)
        first = tdy.replace(day=1)
        zones = Zone.search([('facility_id', 'in', fids)])
        plants = Plant.search([('facility_id', 'in', fids)])
        water_month = sum(zones.mapped('water_month_m3'))
        return _ok({
            'available': True,
            'zones': len(zones),
            'zones_due': len(zones.filtered('is_due')),
            'valve_faults': len(zones.filtered(lambda z: z.valve_state == 'fault')),
            'water_month_m3': round(water_month, 2),
            'plants': len(plants),
            'plants_poor': len(plants.filtered(lambda p: p.health in ('poor', 'fair'))),
            'inspections_overdue': len(plants.filtered('inspection_overdue')),
            'prune_due': len(plants.filtered(lambda p: p.next_prune and p.next_prune <= tdy)),
            'fertilize_due': len(plants.filtered(lambda p: p.next_fertilize and p.next_fertilize <= tdy)),
            'operations_month': Op.search_count([('facility_id', 'in', fids), ('date', '>=', first)]),
        })

    # ---- irrigation zones -------------------------------------------------
    @route(API + '/client/agri/zones', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_zones(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        Zone = env['care.cafm.agri.zone'].sudo()
        mth, val = _sel(Zone, 'method'), _sel(Zone, 'valve_state')
        recs = Zone.search([('facility_id', 'in', self._fac_ids(env))], order='facility_id, name')
        return _ok([{
            'id': z.id, 'name': z.name, 'facility': z.facility_id.name or None,
            'method': mth.get(z.method, z.method or ''), 'method_raw': z.method,
            'frequency': z.frequency,
            'duration_min': z.duration_min, 'flow_lpm': z.flow_lpm, 'area_m2': z.area_m2,
            'weather_based': z.weather_based,
            'valve_state': z.valve_state, 'valve_label': val.get(z.valve_state, z.valve_state or ''),
            'moisture_pct': z.moisture_pct, 'plant_count': z.plant_count,
            'last_run': _d(z.last_run), 'next_run': _d(z.next_run), 'is_due': z.is_due,
            'water_month_m3': round(z.water_month_m3, 2), 'water_m3': round(z.water_m3, 2),
            'start_time': z.start_time,
            'plan_state': z.client_plan_state, 'plan_comment': z.client_plan_comment or None,
            'plan_date': _d(z.client_plan_date),
        } for z in recs])

    # ---- client approves / rejects a zone's irrigation plan ---------------
    @route(API + '/client/agri/zone/<int:zid>/approve', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def agri_zone_approve(self, zid, **kw):
        return self._zone_decision(zid, 'approved')

    @route(API + '/client/agri/zone/<int:zid>/reject', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def agri_zone_reject(self, zid, **kw):
        return self._zone_decision(zid, 'rejected')

    def _zone_decision(self, zid, state):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        z = env['care.cafm.agri.zone'].sudo().browse(int(zid)).exists()
        if not z or z.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        from odoo import fields as F
        comment = (_body().get('comment') or '').strip()
        z.write({'client_plan_state': state, 'client_plan_comment': comment or z.client_plan_comment,
                 'client_plan_date': F.Datetime.now()})
        verb = 'اعتمد' if state == 'approved' else 'رفض'
        body = 'العميل %s خطة الريّ لهذه المنطقة.' % verb
        if comment:
            body += ' — التعليق: %s' % comment
        z.message_post(body=body)
        return _ok({'id': z.id, 'plan_state': z.client_plan_state, 'plan_date': _d(z.client_plan_date)})

    # ---- plants / trees ---------------------------------------------------
    @route(API + '/client/agri/plants', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_plants(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        Plant = env['care.cafm.agri.plant'].sudo()
        hl = _sel(Plant, 'health')
        dom = [('facility_id', 'in', self._fac_ids(env))]
        if kw.get('health'):
            dom.append(('health', '=', kw['health']))
        if kw.get('overdue') in ('1', 'true'):
            dom.append(('inspection_overdue', '=', True))
        recs = Plant.search(dom, order='facility_id, name', limit=500)
        return _ok([{
            'id': p.id, 'name': p.name, 'code': p.code or None,
            'species': p.species_id.name or p.species or None,
            'category': p.category or None,
            'facility': p.facility_id.name or None, 'zone': p.zone_id.name or None,
            'location': p.location_id.name or None, 'gps': p.gps or None,
            'image': _abs('/web/image/care.cafm.agri.plant/%s/image' % p.id) if p.image else None,
            'health': p.health, 'health_label': hl.get(p.health, p.health or ''),
            'planted_date': _d(p.planted_date), 'age_years': p.age_years,
            'height_m': p.height_m, 'trunk_cm': p.trunk_cm,
            'last_inspection': _d(p.last_inspection), 'next_inspection': _d(p.next_inspection),
            'inspection_overdue': p.inspection_overdue,
            'next_prune': _d(p.next_prune), 'next_fertilize': _d(p.next_fertilize),
            'operation_count': p.operation_count, 'care_note': p.care_note or None,
        } for p in recs])

    # ---- single plant + works history -------------------------------------
    @route(API + '/client/agri/plant/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_plant(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        p = env['care.cafm.agri.plant'].sudo().browse(pid).exists()
        if not p or p.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        Op = env['care.cafm.agri.operation'].sudo()
        ot, rs = _sel(Op, 'operation_type'), _sel(Op, 'result')
        ops = [{
            'id': o.id, 'type': ot.get(o.operation_type, o.operation_type or ''),
            'type_raw': o.operation_type, 'date': _d(o.date),
            'done_by': o.done_by.name or None, 'material': o.material or None,
            'quantity': o.quantity, 'unit': o.unit or None, 'cost': o.cost,
            'result': rs.get(o.result, o.result or ''), 'next_due': _d(o.next_due),
            'photo_before': _abs('/web/image/care.cafm.agri.operation/%s/photo_before' % o.id) if o.photo_before else None,
            'photo_after': _abs('/web/image/care.cafm.agri.operation/%s/photo_after' % o.id) if o.photo_after else None,
            'note': o.note or None,
        } for o in p.operation_ids.sorted(lambda r: r.date or '', reverse=True)]
        hl = _sel(env['care.cafm.agri.plant'].sudo(), 'health')
        return _ok({
            'id': p.id, 'name': p.name, 'code': p.code or None,
            'species': p.species_id.name or p.species or None, 'category': p.category or None,
            'image': _abs('/web/image/care.cafm.agri.plant/%s/image' % p.id) if p.image else None,
            'facility': p.facility_id.name or None, 'zone': p.zone_id.name or None,
            'gps': p.gps or None, 'health': p.health, 'health_label': hl.get(p.health, p.health or ''),
            'planted_date': _d(p.planted_date), 'age_years': p.age_years,
            'height_m': p.height_m, 'trunk_cm': p.trunk_cm,
            'last_inspection': _d(p.last_inspection), 'next_inspection': _d(p.next_inspection),
            'next_prune': _d(p.next_prune), 'next_fertilize': _d(p.next_fertilize),
            'care_note': p.care_note or None, 'operations': ops,
        })

    # ---- operations (works log) -------------------------------------------
    @route(API + '/client/agri/operations', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_operations(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        Op = env['care.cafm.agri.operation'].sudo()
        ot, rs = _sel(Op, 'operation_type'), _sel(Op, 'result')
        dom = [('facility_id', 'in', self._fac_ids(env))]
        if kw.get('type'):
            dom.append(('operation_type', '=', kw['type']))
        recs = Op.search(dom, order='date desc, id desc', limit=300)
        return _ok([{
            'id': o.id, 'name': o.name,
            'type': ot.get(o.operation_type, o.operation_type or ''), 'type_raw': o.operation_type,
            'plant': o.plant_id.name or None, 'facility': o.facility_id.name or None,
            'zone': o.zone_id.name or None, 'date': _d(o.date), 'done_by': o.done_by.name or None,
            'material': o.material or None, 'quantity': o.quantity, 'unit': o.unit or None,
            'cost': o.cost, 'result': rs.get(o.result, o.result or ''), 'result_raw': o.result,
            'next_due': _d(o.next_due),
            'photo_before': _abs('/web/image/care.cafm.agri.operation/%s/photo_before' % o.id) if o.photo_before else None,
            'photo_after': _abs('/web/image/care.cafm.agri.operation/%s/photo_after' % o.id) if o.photo_after else None,
            'note': o.note or None,
        } for o in recs])

    # ---- client requests a tree work (prune/inspect/pest…) ----------------
    @route(API + '/client/agri/request', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def agri_request(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if 'care.cafm.service.request' not in env:
            return _err('نظام الطلبات غير متاح', 404)
        b = _body()
        op = b.get('op_type') or 'other'
        note = (b.get('note') or '').strip()
        Plant = env['care.cafm.agri.plant'].sudo()
        plant = Plant.browse(int(b['plant_id'])).exists() if b.get('plant_id') else Plant.browse()
        fids = self._fac_ids(env)
        fid = plant.facility_id.id if plant else (int(b['facility_id']) if b.get('facility_id') else (fids[0] if fids else None))
        if not fid or fid not in fids:
            return _err('المرفق مطلوب', 422)
        if plant and plant.facility_id.id not in fids:
            return _err('غير موجود', 404)
        label = _OP_LABELS.get(op, _OP_LABELS['other'])
        target = plant.name or ''
        title = ('%s — %s' % (label, target)) if target else label
        # attach the agriculture service line if one is configured
        svc = env['care.cafm.service'].sudo().search(
            [('service_type', 'in', ('agriculture', 'landscape'))], limit=1) if 'care.cafm.service' in env else None
        desc_bits = []
        if plant:
            desc_bits.append('الشجرة/النبتة: %s%s' % (plant.name, (' (%s)' % plant.code) if plant.code else ''))
            if plant.zone_id:
                desc_bits.append('منطقة الريّ: %s' % plant.zone_id.name)
        desc_bits.append('العمل المطلوب: %s' % label)
        if note:
            desc_bits.append('ملاحظات العميل: %s' % note)
        cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        vals = {
            'title': title, 'facility_id': fid,
            'location_id': plant.location_id.id if plant and plant.location_id else False,
            'service_id': svc.id if svc else False,
            'description': '\n'.join(desc_bits),
            'priority': str(b.get('priority') or '1'),
            'partner_id': cp.id if cp else False,
            'requested_by': env.user.id,
        }
        r = env['care.cafm.service.request'].sudo().create(vals)
        return _ok({'id': r.id, 'name': getattr(r, 'name', False) or r.title, 'title': r.title,
                    'state': getattr(r, 'state', None)})

    # ---- species catalogue (global reference) -----------------------------
    @route(API + '/client/agri/species', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def agri_species(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        Sp = env['care.cafm.agri.species'].sudo()
        cat, wn, sun = _sel(Sp, 'category'), _sel(Sp, 'water_need'), _sel(Sp, 'sun_exposure')
        recs = Sp.search([], order='name')
        return _ok([{
            'id': s.id, 'name': s.name, 'scientific_name': s.scientific_name or None,
            'category': cat.get(s.category, s.category or ''), 'category_raw': s.category,
            'image': _abs('/web/image/care.cafm.agri.species/%s/image' % s.id) if s.image else None,
            'water_need': wn.get(s.water_need, s.water_need or ''),
            'sun_exposure': sun.get(s.sun_exposure, s.sun_exposure or ''),
            'prune_interval_days': s.prune_interval_days, 'fertilize_interval_days': s.fertilize_interval_days,
            'heat_tolerant': s.heat_tolerant, 'salt_tolerant': s.salt_tolerant,
            'care_guide': s.care_guide or None, 'plant_count': s.plant_count,
        } for s in recs])
