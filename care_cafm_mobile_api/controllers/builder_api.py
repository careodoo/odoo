# -*- coding: utf-8 -*-
"""CAD-style building builder: load/save floor plans (rooms as grid geometry)."""
from odoo.http import Controller, route

from .api import _auth, _ok, _err, _body, API, _abs


def _room(l):
    return {'id': l.id, 'name': l.name, 'code': l.code, 'room_type': l.room_type,
            'x': l.plan_x, 'y': l.plan_y, 'w': l.plan_w, 'h': l.plan_h,
            'color': l.plan_color or '#dbeafe', 'checkpoint': l.is_checkpoint}


def _is_admin(env):
    return env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')


class BuilderApi(Controller):

    @route(API + '/builder/building/<int:bid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def building(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = env['care.cafm.building'].sudo().browse(bid).exists()
        if not b:
            return _err('غير موجود', 404)
        floors = []
        for f in b.floor_ids.sorted('sequence'):
            rooms = env['care.cafm.location'].sudo().search([('floor_id', '=', f.id)])
            floors.append({'id': f.id, 'name': f.name, 'sequence': f.sequence,
                           'cols': f.grid_cols or 20, 'rows': f.grid_rows or 14,
                           'plan_url': _abs(f.plan_image_url) if f.plan_image_url else None,
                           'rooms': [_room(r) for r in rooms]})
        return _ok({
            'id': b.id, 'name': b.name, 'facility_id': b.facility_id.id,
            'type': b.building_type, 'width': b.width_m, 'depth': b.depth_m,
            'basement_count': b.basement_count or 0, 'color': b.color,
            'floors': floors,
        })

    @route(API + '/builder/building/<int:bid>/logo', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def upload_logo(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not _is_admin(env):
            return _err('التصميم للمشرفين فقط', 403)
        b = env['care.cafm.building'].sudo().browse(bid).exists()
        if not b:
            return _err('غير موجود', 404)
        data = _body().get('data')
        if not data:
            return _err('data مطلوب', 422)
        att = env['ir.attachment'].sudo().create({
            'name': 'logo-%s.png' % bid, 'datas': data,
            'res_model': 'care.cafm.building', 'res_id': b.id, 'public': True})
        b.logo_url = '/web/content/%s?download=false' % att.id
        return _ok({'logo_url': _abs(b.logo_url)})

    @route(API + '/builder/floor/<int:fid>/plan', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def upload_plan(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not _is_admin(env):
            return _err('التصميم للمشرفين فقط', 403)
        fl = env['care.cafm.floor'].sudo().browse(fid).exists()
        if not fl:
            return _err('الدور غير موجود', 404)
        b = _body()
        data = b.get('data')
        if not data:
            return _err('data (base64) مطلوب', 422)
        att = env['ir.attachment'].sudo().create({
            'name': b.get('filename') or ('plan-%s.png' % fid),
            'datas': data, 'res_model': 'care.cafm.floor', 'res_id': fl.id, 'public': True})
        fl.plan_image_url = '/web/content/%s?download=false' % att.id
        return _ok({'plan_url': _abs(fl.plan_image_url)})

    @route(API + '/builder/floor/<int:fid>/save', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def save_floor(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not _is_admin(env):
            return _err('التصميم للمشرفين فقط', 403)
        fl = env['care.cafm.floor'].sudo().browse(fid).exists()
        if not fl:
            return _err('الدور غير موجود', 404)
        b = _body()
        if b.get('cols') or b.get('rows'):
            fl.write({'grid_cols': int(b.get('cols') or 20), 'grid_rows': int(b.get('rows') or 14)})
        Loc = env['care.cafm.location'].sudo()
        facility_id = fl.building_id.facility_id.id
        # deletions (only rooms with no work history are removed)
        WO = env['care.cafm.workorder'].sudo()
        Scan = env['care.cafm.scan'].sudo()
        for did in (b.get('delete') or []):
            r = Loc.browse(int(did)).exists()
            if r and not WO.search_count([('location_id', '=', r.id)]) \
                    and not Scan.search_count([('location_id', '=', r.id)]):
                r.unlink()
        saved = []
        for rm in (b.get('rooms') or []):
            vals = {
                'name': rm.get('name') or 'غرفة', 'room_type': rm.get('room_type') or 'office',
                'plan_x': int(rm.get('x', 0)), 'plan_y': int(rm.get('y', 0)),
                'plan_w': int(rm.get('w', 4)), 'plan_h': int(rm.get('h', 3)),
                'plan_color': rm.get('color') or '#dbeafe',
                'is_checkpoint': bool(rm.get('checkpoint')),
                'floor_id': fl.id, 'facility_id': facility_id,
            }
            if rm.get('id'):
                r = Loc.browse(int(rm['id'])).exists()
                if r:
                    r.write(vals)
                    saved.append(_room(r))
                    continue
            saved.append(_room(Loc.create(vals)))
        return _ok(saved)
