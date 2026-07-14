# -*- coding: utf-8 -*-
"""Live occupancy: where each worker is (by their last QR scan) and their
status — feeds the 3D/isometric building view in the app and portal."""
from datetime import timedelta
from odoo import fields
from odoo.http import Controller, route

from .api import _auth, _ok, _err, _abs, API


class OccupancyApi(Controller):

    @route(API + '/facilities', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facilities(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        Fac = env['care.cafm.facility'].sudo()
        user = env.user
        if user.has_group('base.group_erp_manager') or user.has_group('base.group_system'):
            facs = Fac.search([])
        elif user.partner_id:
            pids = {user.partner_id.id, user.partner_id.commercial_partner_id.id}
            facs = Fac.search([('partner_id', 'in', list(pids))])
            if not facs and user.employee_id:
                facs = env['care.cafm.workorder'].sudo().search(
                    [('employee_id', '=', user.employee_id.id)]).mapped('facility_id')
        else:
            facs = Fac.search([])
        return _ok([{'id': f.id, 'name': f.name} for f in facs])

    @route(API + '/facility/<int:fid>/occupancy', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def occupancy(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        Scan = env['care.cafm.scan'].sudo()
        WO = env['care.cafm.workorder'].sudo()
        Shift = env['care.cafm.shift'].sudo()
        fac = env['care.cafm.facility'].sudo().browse(fid).exists()
        if not fac:
            return _err('غير موجود', 404)
        now = fields.Datetime.now()

        # last scan per employee within this facility
        scans = Scan.search([('facility_id', '=', fid)], order='scan_datetime desc')
        last = {}
        for s in scans:
            if s.employee_id and s.employee_id.id not in last:
                last[s.employee_id.id] = s

        # live signals
        on_task = {}  # emp_id -> wo title
        for w in WO.search([('facility_id', '=', fid), ('state', '=', 'in_progress'), ('employee_id', '!=', False)]):
            on_task[w.employee_id.id] = w.title
        on_shift = set(Shift.search([('facility_id', '=', fid), ('state', '=', 'open')]).mapped('employee_id').ids)
        # employee → shift name (from CAFM team-member records)
        emp_shift = {}
        if 'care.cafm.team.member' in env:
            for m in env['care.cafm.team.member'].sudo().search([('facility_id', '=', fid)]):
                if m.employee_id and m.employee_id.id not in emp_shift and m.shift_type_id:
                    emp_shift[m.employee_id.id] = m.shift_type_id.display_name

        def _status(emp_id, scan):
            if emp_id in on_task:
                return 'on_task'
            if emp_id in on_shift:
                return 'available'
            if scan.scan_datetime and (now - scan.scan_datetime) <= timedelta(hours=1):
                return 'recent'
            return 'off'

        def _photo(emp):
            img = emp.image_128
            if img:
                return 'data:image/png;base64,%s' % (img.decode() if isinstance(img, bytes) else img)
            return None

        scan_lbl = dict(Scan._fields['scan_type'].selection) if 'scan_type' in Scan._fields else {}

        def _ago(dt):
            if not dt:
                return None
            secs = (now - dt).total_seconds()
            if secs < 90:
                return 'الآن'
            if secs < 3600:
                return 'منذ %d دقيقة' % (secs // 60)
            if secs < 86400:
                return 'منذ %d ساعة' % (secs // 3600)
            return 'منذ %d يوم' % (secs // 86400)

        # group workers by floor
        floor_workers = {}
        for emp_id, s in last.items():
            emp = s.employee_id
            floor = s.location_id.floor_id
            fkey = floor.id if floor else 0
            last_activity = {
                'type': scan_lbl.get(s.scan_type, s.scan_type) if s.scan_type else 'مسح',
                'location': s.location_id.name or None,
                'when': s.scan_datetime or None,
                'ago': _ago(s.scan_datetime),
            }
            floor_workers.setdefault(fkey, []).append({
                'employee': emp.name,
                'employee_id': emp.id,
                'job': emp.job_title or None,
                'department': emp.department_id.name or None,
                'phone': emp.work_phone or emp.mobile_phone or None,
                'shift': emp_shift.get(emp.id),
                'photo': _photo(emp),
                'location': s.location_id.name or None,
                'building': (s.location_id.building_id.name if s.location_id.building_id else None),
                'last_seen': s.scan_datetime or None,
                'last_activity': last_activity,
                'status': _status(emp_id, s),
                'task': on_task.get(emp_id),
                'shift_open': emp_id in on_shift,
            })

        def _floor_dict(fl):
            ws = floor_workers.get(fl.id, [])
            rooms = [{'name': r.name, 'x': r.plan_x, 'y': r.plan_y, 'w': r.plan_w,
                      'h': r.plan_h, 'color': r.plan_color or '#dbeafe', 'type': r.room_type}
                     for r in fl.location_ids if r.plan_w and r.plan_h]
            return {'id': fl.id, 'name': fl.name, 'sequence': fl.sequence,
                    'cols': fl.grid_cols or 20, 'rows': fl.grid_rows or 14,
                    'rooms': rooms, 'workers': ws,
                    'total': len(ws),
                    'on_task': len([w for w in ws if w['status'] == 'on_task'])}

        # project logo → shown on the building when the building has no explicit logo
        proj_logo = None
        if 'care.cafm.project' in env:
            proj = env['care.cafm.project'].sudo().search([('facility_ids', 'in', fac.id)], limit=1)
            if proj and proj.logo:
                proj_logo = '/web/image/care.cafm.project/%s/logo' % proj.id

        buildings = []
        for b in fac.building_ids:
            floors = b.floor_ids.sorted(lambda f: f.sequence, reverse=True)  # top floor first
            buildings.append({
                'id': b.id, 'name': b.name,
                'type': b.building_type, 'width': b.width_m or 24, 'depth': b.depth_m or 18,
                'floor_height': b.floor_height_m or 3.4, 'color': b.color or '#9ac2ff',
                'has_basement': b.has_basement, 'basement_count': b.basement_count or 0,
                'elevators': b.elevators or 0, 'stairs': b.stairs or 0,
                'entrances': b.entrances or 1, 'rooms_per_floor': b.rooms_per_floor or 0,
                'facade_style': b.facade_style or 'glass', 'roof_type': b.roof_type or 'flat',
                'night_lights': b.night_lights,
                'logo_url': _abs(b.logo_url) if b.logo_url else (_abs(proj_logo) if proj_logo else None),
                'floors': [_floor_dict(fl) for fl in floors],
            })
        # workers whose scan location has no floor (ground / outdoor)
        ground = floor_workers.get(0, [])
        totals = {
            'workers': len(last),
            'on_task': len(on_task),
            'available': len([e for e in on_shift if e not in on_task]),
        }
        return _ok({
            'facility': fac.name, 'facility_id': fac.id,
            'buildings': buildings, 'ground': ground, 'totals': totals,
        })
