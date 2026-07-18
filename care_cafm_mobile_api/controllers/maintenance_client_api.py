# -*- coding: utf-8 -*-
"""Client-facing MAINTENANCE endpoints — dashboard, fault/breakdown reports
(raise + convert), periodic inspections, spare-parts store, departments &
technicians — scoped to the caller's facilities."""
from odoo import fields, _
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, _body, API


def _d(v):
    return v and str(v) or None


class MaintenanceClientApi(Controller):

    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        if 'care.cafm.client' in env:
            for c in env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])]):
                for cp in c.mapped('partner_id'):
                    pids.add(cp.id)
                    pids.update(env['res.partner'].sudo().search([('commercial_partner_id', '=', cp.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _fac_ids(self, env):
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _can_manage(self, env):
        cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        return bool(env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
                    or (cp and cp.sudo().cafm_can_add_workers))

    def _guard(self, env):
        if 'care.cafm.maint.fault' not in env:
            return _err('خدمة الصيانة غير مفعّلة', 404)
        return None

    # ---- dashboard --------------------------------------------------------
    @route(API + '/client/maint/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.maint.fault' not in env:
            return _ok({'available': False})
        fids = self._fac_ids(env)
        F = env['care.cafm.maint.fault'].sudo()
        I = env['care.cafm.maint.inspection'].sudo()
        P = env['care.cafm.maint.part'].sudo()
        faults = F.search([('facility_id', 'in', fids)])
        insp = I.search([('facility_id', 'in', fids)])
        open_f = faults.filtered(lambda f: f.state not in ('resolved', 'closed', 'cancelled'))
        parts = P.search([])
        # by-department breakdown
        by_dep = {}
        for f in faults:
            k = f.department_id.id or 0
            g = by_dep.setdefault(k, {'name': f.department_id.name or 'غير محدّد', 'total': 0, 'open': 0})
            g['total'] += 1
            if f in open_f:
                g['open'] += 1
        return _ok({
            'available': True,
            'faults_total': len(faults),
            'faults_open': len(open_f),
            'faults_critical': len(open_f.filtered(lambda f: f.severity == 'critical')),
            'faults_resolved': len(faults.filtered(lambda f: f.state in ('resolved', 'closed'))),
            'inspections': len(insp),
            'inspections_due': len(insp.filtered('is_due')),
            'parts': len(parts),
            'parts_low': len(parts.filtered('low_stock')),
            'parts_value': round(sum(parts.mapped('stock_value')), 2),
            'downtime_hours': round(sum(faults.mapped('downtime_hours')), 1),
            'by_department': sorted(by_dep.values(), key=lambda g: -g['total']),
        })

    def _fault_dict(self, f, full=False):
        d = {
            'id': f.id, 'name': f.name, 'title': f.title,
            'facility': f.facility_id.name or None, 'location': f.location_id.name or None,
            'asset': f.asset_id.name or None, 'department': f.department_id.name or None,
            'trade': dict(f._fields['trade'].selection).get(f.trade) if f.trade else None,
            'severity': f.severity, 'severity_label': dict(f._fields['severity'].selection).get(f.severity),
            'state': f.state, 'state_label': dict(f._fields['state'].selection).get(f.state),
            'assignee': f.assignee_id.name or None, 'reported': _d(f.reported_date),
            'workorder': f.workorder_id.name or None, 'workorder_id': f.workorder_id.id or None,
            'downtime_hours': f.downtime_hours,
            'can_convert': bool(self._can_manage(request.env(user=f.env.uid)) and not f.workorder_id
                                and f.state not in ('closed', 'cancelled')),
            'can_cancel': bool(f.state in ('reported', 'diagnosed')),
        }
        if full:
            d.update({'description': f.description or None, 'diagnosis': f.diagnosis or None,
                      'resolution': f.resolution or None, 'parts_cost': f.parts_cost,
                      'parts': [{'name': l.part_id.name, 'qty': l.quantity, 'subtotal': l.subtotal}
                                for l in f.part_line_ids]})
        return d

    # ---- faults -----------------------------------------------------------
    @route(API + '/client/maint/faults', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_faults(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        a = request.httprequest.args
        dom = [('facility_id', 'in', self._fac_ids(env))]
        if a.get('state') and a['state'] != 'all':
            if a['state'] == 'open':
                dom.append(('state', 'not in', ('resolved', 'closed', 'cancelled')))
            else:
                dom.append(('state', '=', a['state']))
        if a.get('department_id') and a['department_id'].isdigit():
            dom.append(('department_id', '=', int(a['department_id'])))
        q = (a.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('title', 'ilike', q), ('name', 'ilike', q), ('asset_id.name', 'ilike', q)]
        recs = env['care.cafm.maint.fault'].sudo().search(dom, limit=300)
        return _ok([self._fault_dict(f) for f in recs])

    @route(API + '/client/maint/fault/<int:fid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_fault_detail(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        f = env['care.cafm.maint.fault'].sudo().browse(fid).exists()
        if not f or f.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        return _ok(self._fault_dict(f, full=True))

    @route(API + '/client/maint/fault/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def maint_fault_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        b = _body()
        if not (b.get('title') or '').strip():
            return _err('عنوان العطل مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        vals = {
            'title': b['title'].strip(), 'facility_id': fid,
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'asset_id': int(b['asset_id']) if b.get('asset_id') else False,
            'department_id': int(b['department_id']) if b.get('department_id') else False,
            'trade': b.get('trade') or False, 'severity': b.get('severity') or 'medium',
            'description': b.get('description') or None,
            'reporter_name': b.get('reporter_name') or env.user.name,
        }
        if b.get('assignee_id'):
            vals['assignee_id'] = int(b['assignee_id'])
        f = env['care.cafm.maint.fault'].sudo().create(vals)
        # attach media (base64 photos/videos)
        for i, m in enumerate(b.get('media') or []):
            data = (m.get('data') if isinstance(m, dict) else None) or ''
            if not data:
                continue
            try:
                env['ir.attachment'].sudo().create({
                    'name': (m.get('name') if isinstance(m, dict) else None) or ('media-%d' % (i + 1)),
                    'datas': data, 'res_model': 'care.cafm.maint.fault', 'res_id': f.id,
                    'mimetype': (m.get('mimetype') if isinstance(m, dict) else None) or 'image/jpeg'})
            except Exception:
                pass
        return _ok(self._fault_dict(f, full=True))

    @route(API + '/client/maint/fault/<int:fid>/convert', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def maint_fault_convert(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مسموح', 403)
        f = env['care.cafm.maint.fault'].sudo().browse(fid).exists()
        if not f or f.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        try:
            f.action_make_workorder()
        except Exception as e:
            return _err(str(e), 400)
        return _ok(self._fault_dict(f, full=True))

    @route(API + '/client/maint/fault/<int:fid>/cancel', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def maint_fault_cancel(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        f = env['care.cafm.maint.fault'].sudo().browse(fid).exists()
        if not f or f.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        f.write({'state': 'cancelled'})
        return _ok(self._fault_dict(f, full=True))

    # ---- inspections ------------------------------------------------------
    @route(API + '/client/maint/inspections', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_inspections(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        recs = env['care.cafm.maint.inspection'].sudo().search([('facility_id', 'in', self._fac_ids(env))])
        fr = dict(env['care.cafm.maint.inspection']._fields['frequency'].selection)
        res = dict(env['care.cafm.maint.inspection']._fields['last_result'].selection)
        return _ok([{
            'id': r.id, 'name': r.name, 'facility': r.facility_id.name or None,
            'asset': r.asset_id.name or None, 'location': r.location_id.name or None,
            'department': r.department_id.name or None, 'assignee': r.assignee_id.name or None,
            'frequency': fr.get(r.frequency, r.frequency), 'last_date': _d(r.last_date),
            'next_date': _d(r.next_date), 'is_due': r.is_due,
            'last_result': res.get(r.last_result) if r.last_result else None,
            'checklist': [{'name': c.name, 'result': c.result} for c in r.checklist_ids],
        } for r in recs.sorted(lambda x: (not x.is_due, x.next_date or fields.Date.today()))])

    @route(API + '/client/maint/inspection/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def maint_inspection_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_manage(env):
            return _err('غير مسموح', 403)
        if 'care.cafm.maint.inspection' not in env:
            return _err('غير متاح', 404)
        b = _body()
        if not (b.get('name') or '').strip():
            return _err('اسم الفحص مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        vals = {
            'name': b['name'].strip(), 'facility_id': fid,
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'asset_id': int(b['asset_id']) if b.get('asset_id') else False,
            'department_id': int(b['department_id']) if b.get('department_id') else False,
            'assignee_id': int(b['assignee_id']) if b.get('assignee_id') else False,
            'frequency': b.get('frequency') or 'monthly',
        }
        if b.get('checklist'):
            vals['checklist_ids'] = [(0, 0, {'name': it, 'sequence': i * 10})
                                     for i, it in enumerate(b['checklist']) if it]
        r = env['care.cafm.maint.inspection'].sudo().create(vals)
        return _ok({'id': r.id, 'name': r.name})

    @route(API + '/client/maint/inspection/<int:iid>/done', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def maint_inspection_done(self, iid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = env['care.cafm.maint.inspection'].sudo().browse(iid).exists()
        if not r or r.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        r.action_mark_done(_body().get('result') or 'pass')
        return _ok({'id': r.id, 'next_date': _d(r.next_date)})

    # ---- parts store ------------------------------------------------------
    @route(API + '/client/maint/parts', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_parts(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.maint.part' not in env:
            return _ok([])
        P = env['care.cafm.maint.part'].sudo()
        cat = dict(P._fields['category'].selection)
        recs = P.search([], order='low_stock desc, name')
        return _ok([{
            'id': p.id, 'name': p.name, 'code': p.code or None,
            'category': cat.get(p.category, p.category), 'department': p.department_id.name or None,
            'on_hand': p.on_hand, 'uom': p.uom_name, 'min_qty': p.min_qty, 'low_stock': p.low_stock,
            'unit_cost': p.unit_cost, 'stock_value': p.stock_value, 'location': p.location or None,
            'supplier': p.supplier or None,
        } for p in recs])

    # ---- options (for the forms) ------------------------------------------
    @route(API + '/client/maint/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.maint.fault' not in env:
            return _err('غير متاح', 404)
        facs = self._facilities(env)
        Loc = env['care.cafm.location'].sudo()
        locs = {}
        for l in Loc.search([('facility_id', 'in', facs.ids)]):
            locs.setdefault(l.facility_id.id, []).append({'id': l.id, 'name': l.name})
        assets = {}
        if 'care.cafm.asset' in env:
            for a in env['care.cafm.asset'].sudo().search([('facility_id', 'in', facs.ids)]):
                assets.setdefault(a.facility_id.id, []).append({'id': a.id, 'name': a.name, 'code': a.code or None})
        deps = env['care.cafm.maint.department'].sudo().search([])
        trades = dict(env['care.cafm.maint.fault']._fields['trade'].selection)
        # technicians = employees with a maintenance trade, or all client workers
        techs = env['hr.employee'].sudo().search([('maint_trade', '!=', False)])
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name, 'locations': locs.get(f.id, []),
                            'assets': assets.get(f.id, [])} for f in facs],
            'departments': [{'id': d.id, 'name': d.name, 'trade': d.trade} for d in deps],
            'trades': [{'v': k, 'l': v} for k, v in trades.items()],
            'technicians': [{'id': e.id, 'name': e.name,
                             'trade': trades.get(e.maint_trade) if e.maint_trade else None} for e in techs],
            'severities': [{'v': k, 'l': v} for k, v in env['care.cafm.maint.fault']._fields['severity'].selection],
            'frequencies': [{'v': k, 'l': v} for k, v in env['care.cafm.maint.inspection']._fields['frequency'].selection],
        })

    @route(API + '/client/maint/departments', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def maint_departments(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.maint.department' not in env:
            return _ok([])
        deps = env['care.cafm.maint.department'].sudo().search([])
        trades = dict(env['care.cafm.maint.department']._fields['trade'].selection)
        return _ok([{
            'id': d.id, 'name': d.name, 'code': d.code or None,
            'trade': trades.get(d.trade) if d.trade else None,
            'head': d.head_id.name or None, 'techs': d.tech_count, 'faults': d.fault_count,
        } for d in deps])
