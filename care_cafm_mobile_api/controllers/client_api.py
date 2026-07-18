# -*- coding: utf-8 -*-
"""Client-facing endpoints + public branding. The client app is data-driven:
whatever exists in the module for this customer (buildings, services, teams,
work orders) shows up automatically — nothing is hard-coded in the app."""
import base64
import io
import re
import uuid
from datetime import timedelta
from odoo import fields, SUPERUSER_ID, _
from odoo.http import request, Controller, route, content_disposition

from .api import _auth, _ok, _err, _body, _abs, API, _wo_dict


def _xlsx_response(title, columns, rows, filename, meta=None):
    """Build a styled .xlsx and return it as an inline HTTP response. `columns`
    is a list of header strings; `rows` a list of value-lists (same width).
    `meta` is an optional list of (label, value) shown above the table. Shared by
    every client export so they all look the same."""
    import xlsxwriter
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet((title or 'Report')[:31])
    ws.right_to_left()
    f_title = wb.add_format({'bold': True, 'font_size': 15, 'font_color': '#0E3A5F'})
    f_meta = wb.add_format({'font_size': 10, 'font_color': '#555555'})
    f_hdr = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#C0392B',
                           'border': 1, 'align': 'center', 'valign': 'vcenter'})
    f_cell = wb.add_format({'border': 1, 'font_size': 10, 'valign': 'vcenter'})
    f_alt = wb.add_format({'border': 1, 'font_size': 10, 'valign': 'vcenter', 'bg_color': '#F4F6F8'})
    r = 0
    ws.merge_range(r, 0, r, max(len(columns) - 1, 1), title or 'Report', f_title)
    r += 1
    for lbl, val in (meta or []):
        ws.write(r, 0, '%s: %s' % (lbl, val), f_meta)
        r += 1
    r += 1
    for c, h in enumerate(columns):
        ws.write(r, c, h, f_hdr)
    ws.set_row(r, 22)
    widths = [max(12, len(str(h)) + 2) for h in columns]
    def _cell(v):
        # xlsxwriter only writes str/number/bool/None cleanly; coerce anything
        # else (dates, recordsets, False from empty relations) to text so a
        # single odd value can never crash the whole export.
        if v is None or v is False:
            return ''
        if isinstance(v, (str, int, float, bool)):
            return v
        return str(v)
    for i, row in enumerate(rows):
        r += 1
        fmt = f_alt if i % 2 else f_cell
        for c, v in enumerate(row):
            cv = _cell(v)
            try:
                ws.write(r, c, cv, fmt)
            except Exception:
                ws.write_string(r, c, str(cv), fmt)
            widths[c] = min(48, max(widths[c], len(str(cv)) + 2))
    for c, w in enumerate(widths):
        ws.set_column(c, c, w)
    ws.freeze_panes(r - len(rows), 0)
    wb.close()
    buf.seek(0)
    return request.make_response(buf.read(), headers=[
        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        ('Content-Disposition', content_disposition(filename).replace('attachment', 'inline')),
    ])


def _logo_data_uri(company):
    if company.logo:
        raw = company.logo
        if isinstance(raw, bytes):
            raw = raw.decode()
        return 'data:image/png;base64,%s' % raw
    return None


def _emp_photo(emp, field='image_256'):
    img = emp[field] if field in emp._fields else emp.image_128
    if img:
        return 'data:image/png;base64,%s' % (img.decode() if isinstance(img, bytes) else img)
    return None


def _report_env():
    """Resolve the acting user for a printable/exportable route.

    The app fetches these with package:http, which does NOT carry the session
    cookie across the /web/sso redirect — so relying on auth='user' fails. We
    therefore accept the mobile token directly on the query string and fall back
    to an established session. Returns an env bound to that user, or None."""
    if request.session.uid:
        return request.env
    tok = request.httprequest.args.get('token')
    user = request.env['care.cafm.mobile.token'].sudo().resolve(tok) if tok else None
    if user:
        return request.env(user=user.id)
    return None


class ClientApi(Controller):

    # ---- clean public URL for the web portal (instead of .../static/mockups) --
    @route(['/cafm', '/portal'], type='http', auth='public', methods=['GET'], csrf=False)
    def cafm_portal(self, **kw):
        from odoo.modules.module import get_module_resource
        path = get_module_resource('care_hr', 'static', 'mockups', 'cafm-portal.html')
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-cache'),
        ])

    # ---- public branding (used by the login screen, no token) ----------------
    @route(API + '/branding', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def branding(self, **kw):
        co = request.env['res.company'].sudo().search([], limit=1)
        return _ok({
            'company': co.name,
            'logo': _logo_data_uri(co),
            'app_name': 'CARE',
        })

    def _client_partners(self, env):
        p = env.user.partner_id
        ids = {p.id}
        if p.commercial_partner_id:
            ids.add(p.commercial_partner_id.id)
            # include sibling contacts of the same company
            ids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        # ALSO: any CAFM client this user is a member of (user_ids) — a portal
        # sub-user whose own partner isn't a contact of the client company still
        # gets the client's partner (and its contacts) in scope.
        if 'care.cafm.client' in env:
            clients = env['care.cafm.client'].sudo().search([('user_ids', 'in', [env.user.id])])
            for cp in clients.mapped('partner_id'):
                ids.add(cp.id)
                ids.update(env['res.partner'].sudo().search(
                    [('commercial_partner_id', '=', cp.id)]).ids)
        return list(ids)

    def _facilities(self, env):
        # managers/admin (and impersonation testing) see every facility;
        # a real client is scoped to the facilities their partner owns.
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            facs = env['care.cafm.facility'].sudo().search([])
        else:
            pids = self._client_partners(env)
            facs = env['care.cafm.facility'].sudo().search([('partner_id', 'in', pids)])
            # fall back to facilities where this client's contact has work orders
            if not facs and env.user.employee_id:
                facs = env['care.cafm.workorder'].sudo().search(
                    [('employee_id', '=', env.user.employee_id.id)]).mapped('facility_id')
        # optional: narrow to a single selected project (header selector)
        try:
            pid = request.httprequest.args.get('project_id')
        except Exception:
            pid = None
        if pid and pid not in ('all', '') and 'care.cafm.project' in env:
            proj = env['care.cafm.project'].sudo().browse(int(pid)).exists()
            if proj:
                facs = facs & proj.facility_ids
        return facs

    @route(API + '/client/schedules', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_schedules(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.schedule' not in env:
            return _ok({'schedules': [], 'occurrences': []})
        facs = self._facilities(env)
        Sch = env['care.cafm.schedule'].sudo()
        scheds = Sch.search([('facility_id', 'in', facs.ids)]) if facs else Sch.browse()
        st_lbl = {'pending': 'قيد الانتظار', 'done': 'منجزة في الوقت', 'late': 'متأخرة', 'missed': 'فائتة'}
        out = []
        for s in scheds:
            out.append({
                'id': s.id, 'code': s.code, 'name': s.name, 'active': s.active,
                'service': s.service_id.name or None, 'service_type': s.service_type,
                'location': s.location_id.name or s.facility_id.name or None,
                'employee': s.employee_id.name or None,
                'every_minutes': s.every_minutes,
                'compliance': s.compliance,
                'done': s.occ_done, 'late': s.occ_late, 'missed': s.occ_missed, 'total': s.occ_total,
                'require_photo': s.require_photo, 'require_presence': s.require_presence,
            })
        out.sort(key=lambda d: d['compliance'])
        # recent occurrences (across the client's schedules)
        Occ = env['care.cafm.schedule.occurrence'].sudo()
        occs = Occ.search([('schedule_id', 'in', scheds.ids)], order='planned_time desc', limit=60) if scheds else Occ.browse()
        occ_out = [{
            'id': o.id, 'schedule': o.schedule_id.name, 'employee': o.employee_id.name or None,
            'location': o.location_id.name or None,
            'planned': o.planned_time or None, 'actual': o.actual_time or None,
            'delay': o.response_delay_minutes, 'presence': o.presence_verified,
            'state': o.state, 'state_label': st_lbl.get(o.state, o.state),
        } for o in occs]
        return _ok({'schedules': out, 'occurrences': occ_out})

    @route(API + '/client/schedule/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def schedule_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        Loc = env['care.cafm.location'].sudo()
        locs_by_fac = {}
        for l in Loc.search([('facility_id', 'in', facs.ids)]):
            locs_by_fac.setdefault(l.facility_id.id, []).append({'id': l.id, 'name': l.name})
        services = env['care.cafm.service'].sudo().search([])
        _, allowed = self._client_service_types(env)
        services = services.filtered(lambda s: not allowed or s.service_type in allowed)
        workers = self._client_workers(env, facs)
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name, 'locations': locs_by_fac.get(f.id, [])} for f in facs],
            'services': [{'id': s.id, 'name': s.name, 'type': s.service_type} for s in services],
            'workers': [{'id': e.id, 'name': e.name, 'job': e.job_title or None} for e in workers],
        })

    @route(API + '/client/schedule/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def schedule_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح لك بإضافة جداول', 403)
        if 'care.cafm.schedule' not in env:
            return _err('غير متاح', 404)
        b = _body()
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اسم الجدول مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else None
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        if not b.get('service_id'):
            return _err('الخدمة مطلوبة', 422)
        if not b.get('employee_id'):
            return _err('العامل المسنَد مطلوب', 422)
        vals = {
            'name': name, 'facility_id': fid, 'service_id': int(b['service_id']),
            'employee_id': int(b['employee_id']),
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'every_minutes': int(b.get('every_minutes') or 60),
            'window_start': float(b.get('window_start') or 7.0),
            'window_end': float(b.get('window_end') or 19.0),
            'require_presence': bool(b.get('require_presence', True)),
            'require_photo': bool(b.get('require_photo', True)),
        }
        s = env['care.cafm.schedule'].with_user(SUPERUSER_ID).create(vals)
        return _ok({'id': s.id, 'name': s.name, 'code': s.code})

    @route(API + '/client/schedule/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def schedule_detail(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = env['care.cafm.schedule'].sudo().browse(sid).exists()
        if not s or s.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        st_lbl = {'pending': 'قيد الانتظار', 'done': 'منجزة في الوقت', 'late': 'متأخرة', 'missed': 'فائتة'}
        occs = env['care.cafm.schedule.occurrence'].sudo().search(
            [('schedule_id', '=', s.id)], order='planned_time desc', limit=100)
        return _ok({
            'id': s.id, 'name': s.name, 'code': s.code, 'active': s.active,
            'service': s.service_id.name or None, 'service_type': s.service_type,
            'facility': s.facility_id.name or None,
            'location': s.location_id.name or None, 'employee': s.employee_id.name or None,
            'employee_id': s.employee_id.id or None,
            'every_minutes': s.every_minutes, 'compliance': s.compliance,
            'window': '%02d:00 – %02d:00' % (int(s.window_start), int(s.window_end)),
            'done': s.occ_done, 'late': s.occ_late, 'missed': s.occ_missed, 'total': s.occ_total,
            'require_photo': s.require_photo, 'require_presence': s.require_presence,
            'occurrences': [{
                'id': o.id, 'employee': o.employee_id.name or None, 'location': o.location_id.name or None,
                'planned': o.planned_time or None, 'actual': o.actual_time or None,
                'delay': o.response_delay_minutes, 'presence': o.presence_verified,
                'state': o.state, 'state_label': st_lbl.get(o.state, o.state),
            } for o in occs],
        })

    # ==== ASSETS (care.cafm.asset) — full client-facing register ============
    def _asset_dict(self, a, full=False):
        cat = dict(a._fields['category'].selection)
        st = dict(a._fields['status'].selection)
        own = dict(a._fields['ownership'].selection)
        d = {
            'id': a.id, 'name': a.name, 'code': a.code or None,
            'category': a.category, 'category_label': cat.get(a.category, a.category or ''),
            'status': a.status, 'status_label': st.get(a.status, a.status or ''),
            'facility': a.facility_id.name or None, 'facility_id': a.facility_id.id or None,
            'building': a.building_id.name or None, 'location': a.location_id.name or None,
            'brand': a.brand or None, 'model': a.model_name or None,
            'serial': a.serial or None, 'barcode': a.barcode or None,
            'ownership': own.get(a.ownership, a.ownership or ''),
            'ownership_raw': a.ownership,
            'can_manage': a.ownership == 'client',
            'warranty_end': str(a.warranty_end) if a.warranty_end else None,
            'next_inspection': str(a.next_inspection_date) if a.next_inspection_date else None,
            'image': ('/web/image/care.cafm.asset/%s/image' % a.id) if a.image else None,
            'wo_count': a.workorder_count,
        }
        if full:
            d.update({
                'install_date': str(a.install_date) if a.install_date else None,
                'last_inspection': str(a.last_inspection_date) if a.last_inspection_date else None,
                'last_audit': str(a.last_audit_date) if a.last_audit_date else None,
                'qr_value': a.qr_value or a.code or None,
                'notes': a.notes or None,
                'workorders': [{
                    'id': w.id, 'name': w.name, 'title': w.title,
                    'state': w.state, 'date': str(w.request_datetime)[:16] if w.request_datetime else None,
                } for w in a.workorder_ids.sorted(lambda w: w.id, reverse=True)[:20]],
            })
        return d

    @route(API + '/client/assets/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def assets_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.asset' not in env:
            return _ok({'available': False})
        A = env['care.cafm.asset'].sudo()
        recs = A.search([('facility_id', 'in', self._fac_ids(env))])
        cat = dict(A._fields['category'].selection)
        today = fields.Date.today()
        soon = fields.Date.to_string(today + timedelta(days=60))
        by_cat = {}
        for a in recs:
            g = by_cat.setdefault(a.category, {'v': a.category, 'l': cat.get(a.category, a.category or ''), 'count': 0})
            g['count'] += 1
        return _ok({
            'available': True, 'total': len(recs),
            'operational': len(recs.filtered(lambda a: a.status == 'operational')),
            'maintenance': len(recs.filtered(lambda a: a.status == 'maintenance')),
            'faulty': len(recs.filtered(lambda a: a.status == 'faulty')),
            'retired': len(recs.filtered(lambda a: a.status == 'retired')),
            'warranty_soon': len(recs.filtered(lambda a: a.warranty_end and str(a.warranty_end) <= soon and str(a.warranty_end) >= str(today))),
            'inspection_due': len(recs.filtered(lambda a: a.next_inspection_date and str(a.next_inspection_date) <= str(today))),
            'by_category': sorted(by_cat.values(), key=lambda g: -g['count']),
        })

    @route(API + '/client/assets', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def assets(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.asset' not in env:
            return _ok([])
        a = request.httprequest.args
        dom = [('facility_id', 'in', self._fac_ids(env))]
        for key, field in (('category', 'category'), ('status', 'status')):
            v = a.get(key)
            if v and v != 'all':
                dom.append((field, '=', v))
        q = (a.get('q') or '').strip()
        if q:
            dom += ['|', '|', '|', ('name', 'ilike', q), ('code', 'ilike', q),
                    ('serial', 'ilike', q), ('barcode', 'ilike', q)]
        recs = env['care.cafm.asset'].sudo().search(dom, order='facility_id, name', limit=600)
        return _ok([self._asset_dict(a) for a in recs])

    @route(API + '/client/asset/<int:aid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def asset_detail(self, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = env['care.cafm.asset'].sudo().browse(aid).exists()
        if not a or a.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        return _ok(self._asset_dict(a, full=True))

    @route(API + '/client/asset/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def asset_options(self, **kw):
        """Facilities (+locations), categories and statuses for the client's
        asset add/edit form."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.asset' not in env:
            return _err('غير متاح', 404)
        facs = self._facilities(env)
        Loc = env['care.cafm.location'].sudo()
        locs = {}
        for l in Loc.search([('facility_id', 'in', facs.ids)]):
            locs.setdefault(l.facility_id.id, []).append({'id': l.id, 'name': l.name})
        A = env['care.cafm.asset']
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name, 'locations': locs.get(f.id, [])} for f in facs],
            'categories': [{'v': k, 'l': v} for k, v in A._fields['category'].selection],
            'statuses': [{'v': k, 'l': v} for k, v in A._fields['status'].selection],
        })

    def _asset_vals(self, env, b):
        vals = {'name': (b.get('name') or '').strip(),
                'category': b.get('category') or 'other',
                'status': b.get('status') or 'operational',
                'brand': b.get('brand') or None, 'model_name': b.get('model') or None,
                'serial': b.get('serial') or None, 'barcode': b.get('barcode') or None,
                'notes': b.get('notes') or None}
        if b.get('location_id'):
            vals['location_id'] = int(b['location_id'])
        if b.get('warranty_end'):
            try:
                vals['warranty_end'] = fields.Date.to_date(b['warranty_end'])
            except Exception:
                pass
        return vals

    @route(API + '/client/asset/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def asset_create(self, **kw):
        """Client adds an asset THEY OWN (ownership is forced to 'client')."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح لك بإضافة أصول', 403)
        if 'care.cafm.asset' not in env:
            return _err('غير متاح', 404)
        b = _body()
        if not (b.get('name') or '').strip():
            return _err('اسم الأصل مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        vals = self._asset_vals(env, b)
        vals.update({'facility_id': fid, 'ownership': 'client'})  # client-owned only
        a = env['care.cafm.asset'].with_user(SUPERUSER_ID).create(vals)
        return _ok(self._asset_dict(a, full=True))

    @route(API + '/client/asset/<int:aid>/update', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def asset_update(self, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        a = env['care.cafm.asset'].sudo().browse(aid).exists()
        if not a or a.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        if a.ownership != 'client':
            return _err('يمكنك تعديل أصولك فقط', 403)
        a.write(self._asset_vals(env, _body()))
        return _ok(self._asset_dict(a, full=True))

    @route(API + '/client/asset/<int:aid>/delete', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def asset_delete(self, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        a = env['care.cafm.asset'].sudo().browse(aid).exists()
        if not a or a.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        if a.ownership != 'client':
            return _err('يمكنك حذف أصولك فقط', 403)
        if a.workorder_count:
            return _err('لا يمكن الحذف — يوجد أوامر عمل على هذا الأصل', 400)
        a.unlink()
        return _ok({'deleted': aid})

    @route('/cafm/assets/export', type='http', auth='public', methods=['GET'], csrf=False)
    def assets_export(self, **kw):
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        A = env['care.cafm.asset'].sudo()
        cat, st = dict(A._fields['category'].selection), dict(A._fields['status'].selection)
        recs = A.search([('facility_id', 'in', self._fac_ids(env))], order='facility_id, name', limit=5000)
        columns = [_('#'), _('الرمز'), _('الأصل'), _('الفئة'), _('الحالة'), _('المرفق'),
                   _('المبنى'), _('الموقع'), _('الماركة'), _('الموديل'), _('الرقم التسلسلي'),
                   _('انتهاء الضمان'), _('الفحص القادم')]
        rows = []
        for i, a in enumerate(recs, 1):
            rows.append([i, a.code or '', a.name, cat.get(a.category, a.category or ''),
                         st.get(a.status, a.status or ''), a.facility_id.name or '',
                         a.building_id.name or '', a.location_id.name or '', a.brand or '',
                         a.model_name or '', a.serial or '',
                         str(a.warranty_end) if a.warranty_end else '',
                         str(a.next_inspection_date) if a.next_inspection_date else ''])
        meta = [(_('العميل'), env.user.partner_id.commercial_partner_id.name), (_('عدد الأصول'), len(recs))]
        return _xlsx_response(_('سجل الأصول'), columns, rows, 'assets.xlsx', meta)

    @route('/cafm/asset/<int:aid>/label', type='http', auth='public', methods=['GET'], csrf=False)
    def asset_label(self, aid, **kw):
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        a = env['care.cafm.asset'].sudo().browse(aid).exists()
        if not a or a.facility_id.id not in self._fac_ids(env):
            return request.not_found()
        report = env.ref('care_cafm.action_report_cafm_asset_label').with_user(SUPERUSER_ID)
        pdf = env['ir.actions.report'].sudo()._render_qweb_pdf(report, res_ids=[a.id])[0]
        fname = 'asset-label-%s.pdf' % (a.code or a.id)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(fname).replace('attachment', 'inline')),
        ])

    def _attendance_data(self, env, a):
        """Attendance for the client's sites, organised by shift: who was
        expected, who actually punched in, who is missing, and every record.
        Shared by the API and the printed report so the two can never disagree."""
        facs = self._facilities(env)
        empty = {'records': [], 'workers': [], 'totals': {}, 'shifts': [], 'facets': {'employees': [], 'facilities': []}}
        if 'care.cafm.shift' not in env or not facs:
            return empty
        now = fields.Datetime.now()
        dstart, dend, period_label = self._range(a)
        fac_filter = a.get('facility_id')
        fac_filter = int(fac_filter) if (fac_filter or '').isdigit() else None
        fac_ids = [fac_filter] if fac_filter and fac_filter in facs.ids else facs.ids
        emp_filter = a.get('employee_id')
        emp_filter = int(emp_filter) if (emp_filter or '').isdigit() else None

        dom = [('facility_id', 'in', fac_ids)]
        if emp_filter:
            dom.append(('employee_id', '=', emp_filter))
        if dstart:
            dom.append(('check_in', '>=', dstart))
        if dend:
            dom.append(('check_in', '<=', dend))
        recs = env['care.cafm.shift'].sudo().search(dom, order='check_in desc', limit=2000)

        records, per_emp = [], {}
        for s in recs:
            eid = s.employee_id.id
            g = per_emp.setdefault(eid, {
                'id': eid, 'name': s.employee_id.name,
                'job': s.employee_id.job_title or None,
                'photo': _emp_photo(s.employee_id, 'image_128'),
                'days': set(), 'hours': 0.0, 'open': False, 'shifts': 0, 'incomplete': 0,
            })
            g['shifts'] += 1
            if s.check_in:
                g['days'].add(str(s.check_in)[:10])
                g['hours'] += (s.duration_hours or 0.0)
            if s.state == 'open':
                g['open'] = True
            # A punch-in with no punch-out on a past day is a data gap worth
            # surfacing rather than silently counting as zero hours.
            if s.state == 'closed' and not s.check_out:
                g['incomplete'] += 1
            records.append({
                'id': s.id, 'employee': s.employee_id.name, 'employee_id': eid,
                'job': s.employee_id.job_title or None,
                'photo': _emp_photo(s.employee_id, 'image_128'),
                'facility': s.facility_id.name or None, 'facility_id': s.facility_id.id or None,
                'check_in': s.check_in or None, 'check_out': s.check_out or None,
                'date': str(s.check_in)[:10] if s.check_in else None,
                'hours': round(s.duration_hours or 0.0, 1),
                'state': s.state, 'open': s.state == 'open',
                'in_distance': s.in_distance or 0,
                'within_hours': bool(s.within_hours),
            })

        workers = [{'id': g['id'], 'name': g['name'], 'job': g['job'], 'photo': g['photo'],
                    'days': len(g['days']), 'hours': round(g['hours'], 1),
                    'shifts': g['shifts'], 'incomplete': g['incomplete'],
                    'avg_hours': round(g['hours'] / len(g['days']), 1) if g['days'] else 0.0,
                    'open': g['open']} for g in per_emp.values()]
        workers.sort(key=lambda w: -w['hours'])

        # ---- roster by shift: expected vs actually here ---------------------
        open_ids = set(env['care.cafm.shift'].sudo().search(
            [('facility_id', 'in', fac_ids), ('state', '=', 'open')]).mapped('employee_id').ids)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # "Turned up for this shift" cannot be a midnight cut: the night shift
        # runs 23:00→07:00, so someone who punched in at 23:00 yesterday and is
        # still on site is present now — counting them absent because their
        # check-in has yesterday's date is exactly wrong. Anyone with an open
        # shift counts as here, as does anyone who punched in since midnight.
        today_ids = set(env['care.cafm.shift'].sudo().search(
            [('facility_id', 'in', fac_ids), ('check_in', '>=', day_start)]).mapped('employee_id').ids)
        today_ids |= open_ids

        def _hhmm(f):
            """Float 8.5 -> '08:30'. Odoo stores shift times as hours."""
            if not f:
                return None
            h, m = int(f), int(round((f - int(f)) * 60))
            return '%02d:%02d' % (h % 24, m)

        shifts = []
        if 'care.cafm.team.member' in env:
            mem_dom = [('facility_id', 'in', fac_ids)]
            if emp_filter:
                mem_dom.append(('employee_id', '=', emp_filter))
            by_shift = {}
            for m in env['care.cafm.team.member'].sudo().search(mem_dom):
                if not m.employee_id:
                    continue
                st = m.shift_type_id
                key = st.id or 0
                g = by_shift.setdefault(key, {
                    'id': st.id or 0,
                    'name': st.name if st else 'بدون وردية محددة',
                    'code': (st.code if st else None),
                    'start': _hhmm(st.start_time) if st else None,
                    'end': _hhmm(st.end_time) if st else None,
                    'days': (st.days if st else None),
                    'members': [], 'seen': set(),
                })
                if m.employee_id.id in g['seen']:
                    continue
                g['seen'].add(m.employee_id.id)
                g['members'].append({
                    'id': m.employee_id.id, 'name': m.employee_id.name,
                    'job': m.employee_id.job_title or None,
                    'photo': _emp_photo(m.employee_id, 'image_128'),
                    'team': m.team_id.name or None,
                    'role': dict(m._fields['role'].selection).get(m.role, m.role),
                    'present_now': m.employee_id.id in open_ids,
                    'came_today': m.employee_id.id in today_ids,
                    'hours': next((w['hours'] for w in workers if w['id'] == m.employee_id.id), 0.0),
                    'days': next((w['days'] for w in workers if w['id'] == m.employee_id.id), 0),
                })
            for g in by_shift.values():
                g.pop('seen', None)
                g['members'].sort(key=lambda x: (not x['present_now'], not x['came_today'], x['name'] or ''))
                g['expected'] = len(g['members'])
                g['present'] = sum(1 for x in g['members'] if x['present_now'])
                g['came'] = sum(1 for x in g['members'] if x['came_today'])
                g['absent'] = g['expected'] - g['came']
                g['present_rate'] = round(g['came'] * 100.0 / g['expected'], 1) if g['expected'] else 0.0
            shifts = sorted(by_shift.values(), key=lambda g: (g['start'] or 'zz'))

        totals = {
            'records': len(records),
            'present_now': len(open_ids),
            'workers': len(per_emp),
            'total_hours': round(sum(g['hours'] for g in per_emp.values()), 1),
            'avg_hours': round(sum(g['hours'] for g in per_emp.values()) / len(per_emp), 1) if per_emp else 0.0,
            'days_covered': len({r['date'] for r in records if r['date']}),
            'incomplete': sum(g['incomplete'] for g in per_emp.values()),
            'expected': sum(s['expected'] for s in shifts),
            'came_today': sum(s['came'] for s in shifts),
            'absent_today': sum(s['absent'] for s in shifts),
            'period_label': period_label,
        }
        emps = {w['id']: w['name'] for w in workers}
        for s in shifts:
            for m in s['members']:
                emps.setdefault(m['id'], m['name'])
        return {
            'records': records[:800], 'workers': workers, 'totals': totals, 'shifts': shifts,
            'facets': {
                'employees': [{'value': k, 'label': v} for k, v in sorted(emps.items(), key=lambda i: i[1] or '')],
                'facilities': [{'value': f.id, 'label': f.name} for f in facs],
            },
        }

    @route(API + '/client/attendance', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_attendance(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        return _ok(self._attendance_data(env, request.httprequest.args))

    @route(API + '/client/employee/<int:eid>/attendance', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_employee_attendance(self, eid, **kw):
        """Every attendance record for one worker on this client's sites."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = dict(request.httprequest.args)
        a['employee_id'] = str(eid)
        d = self._attendance_data(env, a)
        # A client must not be able to pull a worker who never served them.
        if not d['records'] and not any(
                m['id'] == eid for s in d['shifts'] for m in s['members']):
            return _err('لا سجلات لهذا الموظف في منشآتك', 404)
        emp = env['hr.employee'].sudo().browse(eid)
        d['employee'] = {'id': emp.id, 'name': emp.name, 'job': emp.job_title or None,
                         'photo': _emp_photo(emp, 'image_256')}
        return _ok(d)

    @route('/cafm/attendance/report', type='http', auth='public', methods=['GET'], csrf=False)
    def attendance_report_pdf(self, **kw):
        """The attendance PDF. auth='user' (not the bearer token) because the
        app opens it through /web/sso, which establishes a real session — that
        way the browser, the portal and the app all take the same path."""
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        a = request.httprequest.args
        d = self._attendance_data(env, a)
        d['client'] = env.user.partner_id.commercial_partner_id.name
        d['period_label'] = d['totals'].get('period_label')
        eid = a.get('employee_id')
        if (eid or '').isdigit():
            d['employee_name'] = env['hr.employee'].sudo().browse(int(eid)).name
        # The PDF lists at most 400 rows; say so rather than let a cut read as
        # the whole set.
        d['records'] = d['records'][:400]
        # The API hands these to json (which stringifies datetimes); the report
        # renders the raw dicts, so times arrive as datetime objects. Format
        # them here rather than slicing strings inside the template.
        for r in d['records']:
            for key, dest in (('check_in', 'in_t'), ('check_out', 'out_t')):
                v = r.get(key)
                r[dest] = fields.Datetime.to_string(v)[11:16] if v else '—'
            if r.get('date') is None and r.get('check_in'):
                r['date'] = fields.Datetime.to_string(r['check_in'])[:10]
        report = request.env.ref('care_cafm.action_report_attendance').with_user(SUPERUSER_ID)
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report, res_ids=[], data=d)[0]
        label = re.sub(r'[^\w-]+', '-', (d.get('period_label') or 'all'))
        fname = 'attendance-%s.pdf' % label
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(fname).replace('attachment', 'inline')),
        ])

    @route('/cafm/attendance/export', type='http', auth='public', methods=['GET'], csrf=False)
    def attendance_export_xlsx(self, **kw):
        """Attendance records as Excel. auth='user' via /web/sso, same as the PDF."""
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        a = request.httprequest.args
        d = self._attendance_data(env, a)
        columns = [_('#'), _('الموظف'), _('المسمى'), _('المنشأة'), _('التاريخ'),
                   _('الدخول'), _('الخروج'), _('الساعات'), _('الحالة')]

        def _t(v):
            return fields.Datetime.to_string(v)[11:16] if v else '—'
        rows = []
        for i, r in enumerate(d['records'], 1):
            rows.append([i, r['employee'], r.get('job') or '', r.get('facility') or '',
                         r.get('date') or '', _t(r.get('check_in')), _t(r.get('check_out')),
                         r.get('hours') or 0, _('مفتوحة') if r.get('open') else _('مغلقة')])
        t = d.get('totals', {})
        meta = [
            (_('العميل'), env.user.partner_id.commercial_partner_id.name),
            (_('الفترة'), t.get('period_label') or ''),
            (_('عدد السجلات'), t.get('records', 0)),
            (_('إجمالي الساعات'), t.get('total_hours', 0)),
            (_('عدد العاملين'), t.get('workers', 0)),
        ]
        label = re.sub(r'[^\w-]+', '-', (t.get('period_label') or 'all'))
        return _xlsx_response(_('سجل الحضور والانصراف'), columns, rows,
                              'attendance-%s.xlsx' % label, meta)

    @route(API + '/client/offboard/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def offboard_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.offboard.request' not in env:
            return _err('غير متاح', 404)
        b = _body()
        eid = b.get('employee_id')
        reason = (b.get('reason') or '').strip()
        if not eid:
            return _err('العامل مطلوب', 422)
        if not reason:
            return _err('يرجى كتابة أسباب الإنهاء', 422)
        emp = env['hr.employee'].sudo().browse(int(eid)).exists()
        if not emp:
            return _err('العامل غير موجود', 404)
        cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        facs = self._facilities(env)
        r = env['care.cafm.offboard.request'].sudo().create({
            'request_type': 'offboard', 'employee_id': emp.id, 'reason': reason,
            'end_date': b.get('end_date') or False,
            'partner_id': cp.id if cp else False,
            'facility_id': facs[:1].id if facs else False,
            'requested_by': env.user.id,
        })
        return _ok({'id': r.id, 'name': r.name, 'state': r.state})

    @route(API + '/client/onboard/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def onboard_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.offboard.request' not in env:
            return _err('غير متاح', 404)
        b = _body()
        eid = b.get('employee_id')
        if not eid:
            return _err('العامل مطلوب', 422)
        emp = env['hr.employee'].sudo().browse(int(eid)).exists()
        if not emp:
            return _err('العامل غير موجود', 404)
        cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        facs = self._facilities(env)
        r = env['care.cafm.offboard.request'].sudo().create({
            'request_type': 'onboard', 'employee_id': emp.id,
            'job_requested': b.get('job_requested') or None,
            'start_date': b.get('start_date') or False,
            'reason': b.get('reason') or None,
            'partner_id': cp.id if cp else False,
            'facility_id': facs[:1].id if facs else False,
            'requested_by': env.user.id,
        })
        return _ok({'id': r.id, 'name': r.name, 'state': r.state})

    @route(API + '/client/projects', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_projects(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.project' not in env:
            return _ok([])
        pids = self._client_partners(env)
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        dom = [] if is_mgr else [('partner_id', 'in', pids)]
        projs = env['care.cafm.project'].sudo().search(dom)
        return _ok([{'id': p.id, 'name': p.name, 'code': p.code,
                     'facilities': len(p.facility_ids)} for p in projs])

    @route(API + '/client/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        WO = env['care.cafm.workorder'].sudo()
        wos = WO.search([('facility_id', 'in', facs.ids)])
        open_wos = wos.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))
        # teams serving these facilities
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)])
        # services actually delivered to this client (from their work orders) — dynamic
        svc_types = sorted(set(w.service_type for w in wos if w.service_type))
        type_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        services = env['care.cafm.service'].sudo().search([('service_type', 'in', svc_types)]) if svc_types else env['care.cafm.service'].sudo().browse()

        def _fac(f):
            return {
                'id': f.id, 'name': f.name,
                'address': f.address or None,
                'buildings': len(f.building_ids),
                'locations': len(f.location_ids),
                'open_workorders': WO.search_count([('facility_id', '=', f.id),
                                                     ('state', 'not in', ('done', 'verified', 'cancelled'))]),
            }

        def _team(t):
            return {'id': t.id, 'name': t.name,
                    'service': t.service_id.name or None,
                    'facility': t.facility_id.name or None,
                    'supervisor': t.supervisor_id.name or None,
                    'members': t.member_count}

        # ---- a richer KPI set for the portal cockpit ----
        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        done_wos = wos.filtered(lambda w: w.state in ('done', 'verified'))
        done_month = done_wos.filtered(lambda w: w.done_datetime and w.done_datetime >= month_start)
        new_month = wos.filtered(lambda w: w.request_datetime and w.request_datetime >= month_start)
        overdue = wos.filtered('is_overdue')
        urgent = open_wos.filtered(lambda w: w.priority in ('2', '3'))
        # Average time from request to done, in hours — only over orders that
        # actually have both stamps, so a half-filled record can't skew it.
        closed = [w for w in done_wos if w.done_datetime and w.request_datetime]
        avg_hours = round(
            sum((w.done_datetime - w.request_datetime).total_seconds() / 3600.0 for w in closed) / len(closed), 1
        ) if closed else 0.0
        # Workers on this client's sites + who is punched in right now.
        workers = teams.mapped('member_ids')
        present_now = 0
        if 'care.cafm.shift' in env and facs:
            present_now = env['care.cafm.shift'].sudo().search_count(
                [('facility_id', 'in', facs.ids), ('state', '=', 'open')])
        return _ok({
            'client': env.user.partner_id.commercial_partner_id.name,
            'client_ref': env.user.partner_id.commercial_partner_id.ref or None,
            'contact': env.user.partner_id.name,
            'kpis': {
                'facilities': len(facs),
                'buildings': sum(len(f.building_ids) for f in facs),
                'locations': sum(len(f.location_ids) for f in facs),
                'open_workorders': len(open_wos),
                'services': len(svc_types),
                'teams': len(teams),
                'total_workorders': len(wos),
                'overdue': len(overdue),
                'urgent': len(urgent),
                'done_month': len(done_month),
                'new_month': len(new_month),
                # Share of this client's orders that reached done/verified.
                'completion_rate': round(len(done_wos) * 100.0 / len(wos), 1) if wos else 0.0,
                # Of the orders with a deadline, the share that did not blow it.
                'sla_rate': round((len(wos) - len(overdue)) * 100.0 / len(wos), 1) if wos else 0.0,
                'avg_hours': avg_hours,
                'workers': len(workers),
                'present_now': present_now,
            },
            'facilities': [_fac(f) for f in facs],
            'services': [{'id': s.id, 'name': s.name, 'type': s.service_type, 'icon': s.icon} for s in services],
            'teams': [_team(t) for t in teams],
            'recent_workorders': [_wo_dict(w) for w in wos[:15]],
        })

    @route(API + '/client/analytics', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def analytics(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        WO = env['care.cafm.workorder'].sudo()
        wos = WO.search([('facility_id', 'in', facs.ids)])
        # optional filters: ?period=day|week|month|year|all and ?service_type=cleaning|...
        dstart, dend, period_label = self._range(kw)
        if dstart or dend:
            wos = self._in_range(wos, dstart, dend)
        a = request.httprequest.args
        svc_filter = a.get('service_type') or kw.get('service_type')
        if svc_filter and svc_filter != 'all':
            wos = wos.filtered(lambda w: w.service_type == svc_filter)
        prio = a.get('priority')
        if prio and prio != 'all':
            wos = wos.filtered(lambda w: w.priority == prio)
        st_f = a.get('state')
        if st_f and st_f != 'all':
            wos = wos.filtered(lambda w: w.state == st_f)
        for key, getter in (('facility_id', lambda w: w.facility_id.id),
                            ('employee_id', lambda w: w.employee_id.id)):
            v = a.get(key)
            if (v or '').isdigit():
                iv = int(v)
                wos = wos.filtered(lambda w, g=getter, iv=iv: g(w) == iv)

        def _is_open(w):
            return w.state not in ('done', 'verified', 'cancelled')
        open_wos = wos.filtered(_is_open)
        done_wos = wos.filtered(lambda w: w.state in ('done', 'verified'))
        overdue = wos.filtered('is_overdue')

        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        state_lbl = dict(WO._fields['state'].selection)
        prio_lbl = dict(WO._fields['priority'].selection)

        by_service = {}
        for w in wos:
            key = svc_lbl.get(w.service_type, w.service_type or 'أخرى')
            d = by_service.setdefault(key, {'total': 0, 'open': 0, 'done': 0, 'overdue': 0})
            d['total'] += 1
            if _is_open(w): d['open'] += 1
            if w.state in ('done', 'verified'): d['done'] += 1
            if w.is_overdue: d['overdue'] += 1

        by_state = {lbl: len(wos.filtered(lambda w, s=st: w.state == s)) for st, lbl in state_lbl.items()}
        by_priority = {lbl: len(wos.filtered(lambda w, p=pr: w.priority == p)) for pr, lbl in prio_lbl.items()}

        # per-employee performance on this client's sites
        emps = wos.mapped('employee_id')
        employees = []
        for e in emps:
            ew = wos.filtered(lambda w, e=e: w.employee_id == e)
            ed = ew.filtered(lambda w: w.state in ('done', 'verified'))
            employees.append({
                'name': e.name, 'job_title': e.job_title or None,
                'total': len(ew), 'open': len(ew.filtered(_is_open)),
                'done': len(ed), 'overdue': len(ew.filtered('is_overdue')),
                'completion_pct': round(100.0 * len(ed) / len(ew), 0) if ew else 0,
            })
        employees.sort(key=lambda d: -d['total'])

        # SLA + averages
        done_dl = done_wos.filtered(lambda w: w.done_datetime and w.deadline)
        in_sla = done_dl.filtered(lambda w: w.done_datetime <= w.deadline)
        sla = round(100.0 * len(in_sla) / len(done_dl), 1) if done_dl else 100.0
        durs = done_wos.filtered(lambda w: w.duration_minutes).mapped('duration_minutes')
        resps = wos.filtered(lambda w: w.response_minutes).mapped('response_minutes')

        per_fac = [{
            'id': f.id, 'name': f.name,
            'open': len(open_wos.filtered(lambda w, f=f: w.facility_id == f)),
            'done': len(done_wos.filtered(lambda w, f=f: w.facility_id == f)),
            'overdue': len(overdue.filtered(lambda w, f=f: w.facility_id == f)),
        } for f in facs]

        # ---- where the work actually lands: the busiest locations ----
        by_loc = {}
        for w in wos:
            if not w.location_id:
                continue
            d = by_loc.setdefault(w.location_id.id, {
                'id': w.location_id.id, 'name': w.location_id.name,
                'building': (w.location_id.building_id.name if w.location_id.building_id else None),
                'total': 0, 'open': 0, 'overdue': 0})
            d['total'] += 1
            if _is_open(w): d['open'] += 1
            if w.is_overdue: d['overdue'] += 1
        top_locations = sorted(by_loc.values(), key=lambda d: -d['total'])[:12]

        # ---- roles: which trades carry the load ----
        by_job = {}
        for w in wos:
            if not w.employee_id:
                continue
            jb = w.employee_id.job_title or 'بدون دور'
            d = by_job.setdefault(jb, {'name': jb, 'total': 0, 'overdue': 0, 'done': 0})
            d['total'] += 1
            if w.is_overdue: d['overdue'] += 1
            if w.state in ('done', 'verified'): d['done'] += 1
        by_job = sorted(by_job.values(), key=lambda d: -d['total'])[:12]

        # ---- teams + workforce/attendance, so the analytics tab covers people
        # as well as tickets ----
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)])
        workforce = {'teams': len(teams), 'members': len(teams.mapped('member_ids')),
                     'present_now': 0, 'hours_month': 0.0}
        if 'care.cafm.shift' in env and facs:
            Shift = env['care.cafm.shift'].sudo()
            workforce['present_now'] = Shift.search_count(
                [('facility_id', 'in', facs.ids), ('state', '=', 'open')])
            month_start = fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            workforce['hours_month'] = round(sum(Shift.search(
                [('facility_id', 'in', facs.ids), ('check_in', '>=', month_start)]
            ).mapped('duration_hours')), 1)

        # ---- how late the late work is ----
        now_dt = fields.Datetime.now()
        buckets = {'d1': 0, 'd3': 0, 'w1': 0, 'm1': 0, 'm1p': 0}
        for w in overdue:
            if not w.deadline:
                continue
            dd = (now_dt - w.deadline).total_seconds() / 86400.0
            if dd <= 1: buckets['d1'] += 1
            elif dd <= 3: buckets['d3'] += 1
            elif dd <= 7: buckets['w1'] += 1
            elif dd <= 30: buckets['m1'] += 1
            else: buckets['m1p'] += 1

        return _ok({
            'kpis': {
                'facilities': len(facs),
                'buildings': sum(len(f.building_ids) for f in facs),
                'locations': sum(len(f.location_ids) for f in facs),
                'services': len(by_service),
                'teams': env['care.cafm.team'].sudo().search_count([('facility_id', 'in', facs.ids)]),
                'total': len(wos), 'open': len(open_wos), 'done': len(done_wos),
                'overdue': len(overdue),
                'in_progress': len(wos.filtered(lambda w: w.state == 'in_progress')),
                'unassigned': len(open_wos.filtered(lambda w: not w.employee_id)),
                'completion_pct': round(100.0 * len(done_wos) / len(wos), 0) if wos else 0,
                'verified': len(wos.filtered(lambda w: w.state == 'verified')),
                'assigned': len(wos.filtered(lambda w: w.state == 'assigned')),
                'sla': sla,
                'avg_duration_min': round(sum(durs) / len(durs), 0) if durs else 0,
                'avg_response_min': round(sum(resps) / len(resps), 0) if resps else 0,
                'work_hours': round(sum(durs) / 60.0, 1) if durs else 0,
                'assets': env['care.cafm.asset'].sudo().search_count([('facility_id', 'in', facs.ids)]) if 'care.cafm.asset' in env else 0,
                'ppm': env['care.cafm.ppm'].sudo().search_count([('facility_id', 'in', facs.ids), ('active', '=', True)]) if 'care.cafm.ppm' in env else 0,
                'requests_new': env['care.cafm.service.request'].sudo().search_count([('facility_id', 'in', facs.ids), ('state', '=', 'new')]) if 'care.cafm.service.request' in env else 0,
                'members': env['care.cafm.team.member'].sudo().search_count([('facility_id', 'in', facs.ids)]) if 'care.cafm.team.member' in env else 0,
            },
            'period': period_label,
            'service_types': [{'v': s.service_type, 'l': s.name}
                              for s in env['care.cafm.service'].sudo().search(
                                  [('service_type', 'in', list(self._client_service_types(env)[1])), ('active', '=', True)], order='sequence')],
            'daily': self._daily_series(wos, dstart, dend),
            'by_service': by_service,
            'by_state': by_state,
            'by_priority': by_priority,
            'by_job': by_job,
            'top_locations': top_locations,
            'overdue_buckets': buckets,
            'workforce': workforce,
            'employees': employees,
            'facilities': per_fac,
            # Facet sources so the filters list only what this client has.
            'facets': {
                'facilities': [{'value': f.id, 'label': f.name} for f in facs],
                'employees': [{'value': e.id, 'label': e.name} for e in emps.sorted('name')],
                'states': [{'value': k, 'label': v} for k, v in state_lbl.items()],
                'priorities': [{'value': k, 'label': v} for k, v in prio_lbl.items()],
            },
        })

    # ---- period helpers -----------------------------------------------------
    def _range(self, kw):
        """(start, end, label) from ?period=day|week|month|year|all or ?from&to."""
        now = fields.Datetime.now()
        frm, to = kw.get('from'), kw.get('to')
        if frm or to:
            s = fields.Datetime.from_string(frm) if frm else None
            e = fields.Datetime.from_string(to) if to else None
            return s, e, 'مخصّصة'
        p = kw.get('period') or 'all'
        return {
            'day': (now - timedelta(days=1), None, 'اليوم'),
            'week': (now - timedelta(days=7), None, 'الأسبوع'),
            'month': (now - timedelta(days=30), None, 'الشهر'),
            'year': (now - timedelta(days=365), None, 'السنة'),
        }.get(p, (None, None, 'الكل'))

    def _in_range(self, wos, s, e):
        def ok(w):
            d = w.request_datetime
            if not d:
                return True
            if s and d < s:
                return False
            if e and d > e:
                return False
            return True
        return wos.filtered(ok)

    def _wo_stats(self, wos):
        """Rich KPI block for a set of work orders."""
        def is_open(w):
            return w.state not in ('done', 'verified', 'cancelled')
        done = wos.filtered(lambda w: w.state in ('done', 'verified'))
        done_dl = done.filtered(lambda w: w.done_datetime and w.deadline)
        in_sla = done_dl.filtered(lambda w: w.done_datetime <= w.deadline)
        durs = done.filtered(lambda w: w.duration_minutes).mapped('duration_minutes')
        resps = wos.filtered(lambda w: w.response_minutes).mapped('response_minutes')
        return {
            'total': len(wos), 'open': len(wos.filtered(is_open)),
            'in_progress': len(wos.filtered(lambda w: w.state == 'in_progress')),
            'done': len(done), 'overdue': len(wos.filtered('is_overdue')),
            'cancelled': len(wos.filtered(lambda w: w.state == 'cancelled')),
            'completion_pct': round(100.0 * len(done) / len(wos), 0) if wos else 0,
            'sla': round(100.0 * len(in_sla) / len(done_dl), 1) if done_dl else 100.0,
            'avg_duration_min': round(sum(durs) / len(durs), 0) if durs else 0,
            'avg_response_min': round(sum(resps) / len(resps), 0) if resps else 0,
            # total hours the worker spent executing tasks (sum of durations)
            'work_hours': round(sum(durs) / 60.0, 1) if durs else 0,
        }

    def _daily_series(self, wos, s, e, days=30):
        """Per-day created/done counts for charts."""
        end = e or fields.Datetime.now()
        start = s or (end - timedelta(days=days))
        n = max(1, min(days, (end.date() - start.date()).days + 1))
        base = end.date()
        series = []
        for i in range(n - 1, -1, -1):
            day = base - timedelta(days=i)
            created = len(wos.filtered(lambda w, d=day: w.request_datetime and w.request_datetime.date() == d))
            fin = len(wos.filtered(lambda w, d=day: w.done_datetime and w.done_datetime.date() == d))
            series.append({'date': str(day), 'created': created, 'done': fin})
        return series

    def _client_workers(self, env, facs):
        """Everyone who serves this client's facilities: work-order assignees plus
        the teams' members, user-members and supervisors (users are the base unit,
        resolved to their linked employees)."""
        emps = env['care.cafm.workorder'].sudo().search([('facility_id', 'in', facs.ids)]).mapped('employee_id')
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)])
        emps |= teams.mapped('member_ids')
        if 'user_member_ids' in teams._fields:
            emps |= teams.mapped('user_member_ids.employee_id')
        emps |= teams.mapped('supervisor_id.employee_id')
        return emps

    # ---- team roster with photos + live status ------------------------------
    @route(API + '/client/team', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def team(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        WO = env['care.cafm.workorder'].sudo()
        Scan = env['care.cafm.scan'].sudo()
        now = fields.Datetime.now()
        workers = self._client_workers(env, facs)
        # last scan per worker within the client's facilities → current location
        last = {}
        for sc in Scan.search([('facility_id', 'in', facs.ids)], order='scan_datetime desc'):
            if sc.employee_id and sc.employee_id.id not in last:
                last[sc.employee_id.id] = sc
        on_task = set(WO.search([('facility_id', 'in', facs.ids), ('state', '=', 'in_progress'),
                                 ('employee_id', '!=', False)]).mapped('employee_id').ids)
        # map employee → their team + shift (from the CAFM team-member records)
        emp_team = {}
        if 'care.cafm.team.member' in env:
            for m in env['care.cafm.team.member'].sudo().search([('facility_id', 'in', facs.ids)]):
                if m.employee_id and m.employee_id.id not in emp_team:
                    emp_team[m.employee_id.id] = {
                        'team': m.team_id.name or None,
                        'shift': (m.shift_type_id.display_name if m.shift_type_id else None),
                        'role': dict(m._fields['role'].selection).get(m.role, m.role),
                    }
        out = []
        for e in workers:
            ew = WO.search([('facility_id', 'in', facs.ids), ('employee_id', '=', e.id)])
            sc = last.get(e.id)
            recent = bool(sc and sc.scan_datetime and (now - sc.scan_datetime) <= timedelta(hours=2))
            status = 'on_task' if e.id in on_task else ('recent' if recent else 'off')
            ti = emp_team.get(e.id, {})
            out.append({
                'id': e.id, 'name': e.name, 'job': e.job_title or None,
                'department': e.department_id.name or None,
                'team': ti.get('team'), 'shift': ti.get('shift'), 'role': ti.get('role'),
                'photo': _emp_photo(e, 'image_128'),
                'status': status,
                'available': status != 'off',
                'current_location': (sc.location_id.name if sc and sc.location_id else None),
                'building': (sc.location_id.building_id.name if sc and sc.location_id and sc.location_id.building_id else None),
                'last_seen': (sc.scan_datetime if sc else None),
                'open_tasks': len(ew.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))),
                'done_tasks': len(ew.filtered(lambda w: w.state in ('done', 'verified'))),
            })
        out.sort(key=lambda d: (d['status'] != 'on_task', d['status'] != 'recent', -d['open_tasks']))
        return _ok(out)

    @route(API + '/client/teams', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def teams(self, **kw):
        """Teams as blocks, grouped by service: each one carries its own head
        count, who is on site now, hours worked and work-order load."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        if not facs:
            return _ok({'groups': [], 'totals': {}})
        Team = env['care.cafm.team'].sudo()
        WO = env['care.cafm.workorder'].sudo()
        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        teams = Team.search([('facility_id', 'in', facs.ids)])
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)

        # ---- attendance, in two grouped reads rather than per-member ----
        hours_by_emp, open_shift_emps = {}, set()
        if 'care.cafm.shift' in env:
            Shift = env['care.cafm.shift'].sudo()
            for sh in Shift.search([('facility_id', 'in', facs.ids),
                                    ('check_in', '>=', month_start)]):
                if sh.employee_id:
                    hours_by_emp[sh.employee_id.id] = hours_by_emp.get(sh.employee_id.id, 0.0) + (sh.duration_hours or 0.0)
            open_shift_emps = set(Shift.search(
                [('facility_id', 'in', facs.ids), ('state', '=', 'open')]).mapped('employee_id').ids)

        on_task = set(WO.search([('facility_id', 'in', facs.ids), ('state', '=', 'in_progress'),
                                 ('employee_id', '!=', False)]).mapped('employee_id').ids)

        # Members live in care.cafm.team.member (with role + shift); the team's
        # own member_ids m2m is often empty, so read the membership model and
        # fall back to the m2m only if it has nothing.
        TMbr = env['care.cafm.team.member'].sudo() if 'care.cafm.team.member' in env else None
        mbr_by_team = {}
        if TMbr is not None:
            for m in TMbr.search([('facility_id', 'in', facs.ids)]):
                if m.employee_id:
                    mbr_by_team.setdefault(m.team_id.id, []).append(m)

        def _member(e, m=None):
            return {
                'id': e.id, 'name': e.name, 'job': e.job_title or None,
                'photo': _emp_photo(e, 'image_128'),
                'role': (dict(m._fields['role'].selection).get(m.role, m.role) if (m and 'role' in m._fields) else None),
                'shift': (m.shift_type_id.name if (m and m.shift_type_id) else None),
                'present': e.id in open_shift_emps,
                'on_task': e.id in on_task,
                'hours_month': round(hours_by_emp.get(e.id, 0.0), 1),
                'status': ('on_task' if e.id in on_task
                           else 'available' if e.id in open_shift_emps else 'off'),
            }

        def _team(t):
            tmbrs = mbr_by_team.get(t.id, [])
            if tmbrs:
                members = t.env['hr.employee'].browse([m.employee_id.id for m in tmbrs])
                mbr_of = {m.employee_id.id: m for m in tmbrs}
            else:
                members = t.member_ids
                mbr_of = {}
            twos = WO.search([('facility_id', '=', t.facility_id.id), ('service_id', '=', t.service_id.id)])
            open_wos = twos.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))
            done_wos = twos.filtered(lambda w: w.state in ('done', 'verified'))
            present = [e for e in members if e.id in open_shift_emps]
            return {
                'id': t.id, 'name': t.name,
                'service': t.service_id.name or None,
                'service_type': t.service_type or None,
                'facility': t.facility_id.name or None, 'facility_id': t.facility_id.id or None,
                'supervisor': t.supervisor_id.name or None,
                'quality_user': t.quality_user_id.name or None,
                'members': len(members),
                'reserves': len(t.reserve_ids),
                'present_now': len(present),
                # Attendance rate = who is punched in out of the whole team.
                'present_rate': round(len(present) * 100.0 / len(members), 1) if members else 0.0,
                'hours_month': round(sum(hours_by_emp.get(e.id, 0.0) for e in members), 1),
                'open_workorders': len(open_wos),
                'done_workorders': len(done_wos),
                'overdue': len(twos.filtered('is_overdue')),
                'on_task': len([e for e in members if e.id in on_task]),
                'member_list': [_member(e, mbr_of.get(e.id)) for e in members],
            }

        rows = [_team(t) for t in teams]
        # group into service blocks
        groups = {}
        for r in rows:
            key = r['service_type'] or 'other'
            g = groups.setdefault(key, {
                'service_type': key, 'service': svc_lbl.get(key, r['service'] or 'أخرى'),
                'teams': [], 'members': 0, 'present_now': 0, 'hours_month': 0.0,
                'open_workorders': 0, 'overdue': 0,
            })
            g['teams'].append(r)
            g['members'] += r['members']
            g['present_now'] += r['present_now']
            g['hours_month'] += r['hours_month']
            g['open_workorders'] += r['open_workorders']
            g['overdue'] += r['overdue']
        for g in groups.values():
            g['hours_month'] = round(g['hours_month'], 1)
            g['present_rate'] = round(g['present_now'] * 100.0 / g['members'], 1) if g['members'] else 0.0

        out = sorted(groups.values(), key=lambda g: -g['members'])
        totals = {
            'teams': len(rows),
            'members': sum(r['members'] for r in rows),
            'present_now': sum(r['present_now'] for r in rows),
            'hours_month': round(sum(r['hours_month'] for r in rows), 1),
            'open_workorders': sum(r['open_workorders'] for r in rows),
            'overdue': sum(r['overdue'] for r in rows),
            'services': len(out),
        }
        totals['present_rate'] = round(
            totals['present_now'] * 100.0 / totals['members'], 1) if totals['members'] else 0.0
        return _ok({'groups': out, 'totals': totals})

    # ---- full employee profile + period statistics --------------------------
    @route(API + '/client/employee/<int:eid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def employee(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        emp = env['hr.employee'].sudo().browse(eid).exists()
        if not emp:
            return _err('غير موجود', 404)
        WO = env['care.cafm.workorder'].sudo()
        allwo = WO.search([('facility_id', 'in', facs.ids), ('employee_id', '=', emp.id)])
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not allwo and not is_mgr:
            return _err('هذا الموظف لا يخدم منشآتك', 403)
        s, e, label = self._range(kw)
        wos = self._in_range(allwo, s, e)
        Scan = env['care.cafm.scan'].sudo()
        scans = self._in_range_scans(Scan.search([('facility_id', 'in', facs.ids), ('employee_id', '=', emp.id)]), s, e)
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        by_service = {}
        for w in wos:
            k = svc_lbl.get(w.service_type, w.service_type or 'أخرى')
            by_service[k] = by_service.get(k, 0) + 1
        state_lbl = dict(WO._fields['state'].selection)
        by_state = {lbl: len(wos.filtered(lambda w, st=code: w.state == st)) for code, lbl in state_lbl.items()}
        profile = {
            'id': emp.id, 'name': emp.name, 'job': emp.job_title or None,
            'department': emp.department_id.name or None,
            'manager': emp.parent_id.name or None,
            'work_phone': emp.work_phone or None, 'mobile': emp.mobile_phone or None,
            'work_email': emp.work_email or None,
            'work_location': (emp.work_location_id.name if emp.work_location_id else None),
            'joining': str(emp.joining_date if ('joining_date' in emp._fields and emp.joining_date)
                           else (emp.first_contract_date or (emp.create_date and emp.create_date.date()) or '')) or None,
            'photo': _emp_photo(emp, 'image_256'),
        }
        # attendance (from shift open/close): days present + total hours
        attendance = self._attendance_stats(env, emp, facs, s, e)
        return _ok({
            'period': label,
            'profile': profile,
            'kpis': self._wo_stats(wos),
            'attendance': attendance,
            'activity_scans': len(scans),
            'by_service': by_service,
            'by_state': {k: v for k, v in by_state.items() if v},
            'daily': self._daily_series(wos, s, e),
            'recent': [_wo_dict(w) for w in wos.sorted('request_datetime', reverse=True)[:15]],
        })

    def _attendance_stats(self, env, emp, facs, s, e):
        """Attendance summary from care.cafm.shift open/close records."""
        if 'care.cafm.shift' not in env:
            return {'days': 0, 'hours': 0.0, 'open_now': False, 'shifts': []}
        Shift = env['care.cafm.shift'].sudo()
        dom = [('employee_id', '=', emp.id)]
        if facs:
            dom.append(('facility_id', 'in', facs.ids))
        recs = Shift.search(dom, order='check_in desc')

        def _in(sh):
            d = sh.check_in
            if not d:
                return False
            if s and d < s:
                return False
            if e and d > e:
                return False
            return True
        rng = recs.filtered(_in) if (s or e) else recs
        days = set()
        hours = 0.0
        rows = []
        for sh in rng:
            if sh.check_in:
                days.add(sh.check_in.date())
                hours += (sh.duration_hours or 0.0)
            rows.append({
                'facility': sh.facility_id.name or None,
                'check_in': sh.check_in or None, 'check_out': sh.check_out or None,
                'hours': round(sh.duration_hours or 0.0, 1),
                'state': sh.state, 'open': sh.state == 'open',
            })
        return {
            'days': len(days),
            'hours': round(hours, 1),
            'avg_per_day': round(hours / len(days), 1) if days else 0.0,
            'open_now': any(r['open'] for r in rows),
            'shifts': rows[:20],
        }

    def _in_range_scans(self, scans, s, e):
        def ok(sc):
            d = sc.scan_datetime
            if not d:
                return False
            if s and d < s:
                return False
            if e and d > e:
                return False
            return True
        return scans.filtered(ok)

    # ---- live activity feed + current worker locations ----------------------
    @route(API + '/client/activity', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def activity(self, **kw):
        """A unified activity stream for the client's sites: QR check-ins,
        shift punches and work-order milestones in one timeline, plus who is on
        site right now. Filterable by period / kind / worker / facility."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        if not facs:
            return _ok({'feed': [], 'live': [], 'stats': {}, 'facets': {'employees': [], 'facilities': []}})
        a = request.httprequest.args
        now = fields.Datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        dstart, dend, period_label = self._range(a)
        kind = a.get('kind') or 'all'
        emp_filter = a.get('employee_id')
        emp_filter = int(emp_filter) if (emp_filter or '').isdigit() else None
        fac_filter = a.get('facility_id')
        fac_filter = int(fac_filter) if (fac_filter or '').isdigit() else None
        fac_ids = [fac_filter] if fac_filter and fac_filter in facs.ids else facs.ids

        def _keep(when):
            if dstart and when < dstart:
                return False
            if dend and when > dend:
                return False
            return True

        events = []

        # ---- QR check-ins -------------------------------------------------
        Scan = env['care.cafm.scan'].sudo()
        scan_dom = [('facility_id', 'in', fac_ids)]
        if emp_filter:
            scan_dom.append(('employee_id', '=', emp_filter))
        scans = Scan.search(scan_dom, order='scan_datetime desc', limit=400)
        type_lbl = dict(Scan._fields['scan_type'].selection) if 'scan_type' in Scan._fields else {}
        for sc in scans:
            if not sc.scan_datetime or not _keep(sc.scan_datetime):
                continue
            events.append({
                'kind': 'scan',
                'title': type_lbl.get(sc.scan_type, sc.scan_type) or 'مسح موقع',
                'employee': sc.employee_id.name or None,
                'employee_id': sc.employee_id.id or None,
                'photo': _emp_photo(sc.employee_id, 'image_128') if sc.employee_id else None,
                'location': sc.location_id.name or None,
                'building': (sc.location_id.building_id.name if sc.location_id and sc.location_id.building_id else None),
                'facility': sc.facility_id.name or None,
                'when': sc.scan_datetime,
            })

        # ---- shift punches -------------------------------------------------
        if 'care.cafm.shift' in env:
            sh_dom = [('facility_id', 'in', fac_ids)]
            if emp_filter:
                sh_dom.append(('employee_id', '=', emp_filter))
            for sh in env['care.cafm.shift'].sudo().search(sh_dom, order='check_in desc', limit=300):
                base = {
                    'employee': sh.employee_id.name or None,
                    'employee_id': sh.employee_id.id or None,
                    'photo': _emp_photo(sh.employee_id, 'image_128') if sh.employee_id else None,
                    'facility': sh.facility_id.name or None,
                    'location': None, 'building': None,
                }
                if sh.check_in and _keep(sh.check_in):
                    events.append({**base, 'kind': 'shift_in', 'title': 'بداية وردية', 'when': sh.check_in})
                if sh.check_out and _keep(sh.check_out):
                    events.append({**base, 'kind': 'shift_out', 'title': 'نهاية وردية',
                                   'when': sh.check_out, 'hours': round(sh.duration_hours or 0.0, 1)})

        # ---- work-order milestones ------------------------------------------
        WO = env['care.cafm.workorder'].sudo()
        wo_dom = [('facility_id', 'in', fac_ids)]
        if emp_filter:
            wo_dom.append(('employee_id', '=', emp_filter))
        for w in WO.search(wo_dom, order='request_datetime desc', limit=300):
            base = {
                'employee': w.employee_id.name or None,
                'employee_id': w.employee_id.id or None,
                'photo': _emp_photo(w.employee_id, 'image_128') if w.employee_id else None,
                'facility': w.facility_id.name or None,
                'location': w.location_id.name or None,
                'building': None,
                'wo_id': w.id, 'wo_name': w.name, 'wo_title': w.title,
                'service_type': w.service_type or None,
            }
            if w.request_datetime and _keep(w.request_datetime):
                events.append({**base, 'kind': 'wo_new', 'title': 'أمر عمل جديد', 'when': w.request_datetime})
            if w.start_datetime and _keep(w.start_datetime):
                events.append({**base, 'kind': 'wo_start', 'title': 'بدء التنفيذ', 'when': w.start_datetime})
            if w.done_datetime and _keep(w.done_datetime):
                events.append({**base, 'kind': 'wo_done', 'title': 'إنجاز أمر عمل', 'when': w.done_datetime})

        if kind != 'all':
            events = [e for e in events if e['kind'] == kind]
        events.sort(key=lambda e: e['when'], reverse=True)

        # Stats describe the whole filtered stream, before the display cut.
        def _count(k):
            return sum(1 for e in events if e['kind'] == k)
        today_events = [e for e in events if e['when'] >= day_start]
        stats = {
            'total': len(events),
            'today': len(today_events),
            'scans': _count('scan'),
            'shift_in': _count('shift_in'),
            'wo_new': _count('wo_new'),
            'wo_done': _count('wo_done'),
            'workers': len({e['employee_id'] for e in events if e['employee_id']}),
            'period_label': period_label,
            # Activity by hour of day — shows when the site is actually worked.
            'by_hour': {str(h): sum(1 for e in today_events if e['when'].hour == h) for h in range(24)},
        }

        # ---- who is on site right now ---------------------------------------
        open_emp_ids = set()
        if 'care.cafm.shift' in env:
            open_emp_ids = set(env['care.cafm.shift'].sudo().search(
                [('facility_id', 'in', fac_ids), ('state', '=', 'open')]).mapped('employee_id').ids)
        on_task = {}
        for w in WO.search([('facility_id', 'in', fac_ids), ('state', '=', 'in_progress'),
                            ('employee_id', '!=', False)]):
            on_task.setdefault(w.employee_id.id, w)
        seen, live = set(), []
        for sc in scans:
            if sc.employee_id and sc.employee_id.id not in seen:
                seen.add(sc.employee_id.id)
                eid = sc.employee_id.id
                w = on_task.get(eid)
                live.append({
                    'employee': sc.employee_id.name, 'employee_id': eid,
                    'photo': _emp_photo(sc.employee_id, 'image_128'),
                    'job': sc.employee_id.job_title or None,
                    'location': sc.location_id.name or None,
                    'building': (sc.location_id.building_id.name if sc.location_id and sc.location_id.building_id else None),
                    'facility': sc.facility_id.name or None,
                    'last_seen': sc.scan_datetime or None,
                    'fresh': bool(sc.scan_datetime and (now - sc.scan_datetime) <= timedelta(hours=2)),
                    'on_shift': eid in open_emp_ids,
                    'on_task': bool(w),
                    'task': w.title if w else None,
                    'task_id': w.id if w else None,
                })
        live.sort(key=lambda l: (not l['on_task'], not l['fresh'], not l['on_shift']))
        stats['live_now'] = sum(1 for l in live if l['fresh'])
        stats['on_task_now'] = sum(1 for l in live if l['on_task'])
        stats['on_shift_now'] = len(open_emp_ids)

        emps = {}
        for e in events:
            if e['employee_id']:
                emps[e['employee_id']] = e['employee']
        return _ok({
            'feed': events[:150],
            'shown': min(len(events), 150),
            'live': live,
            'stats': stats,
            'facets': {
                'employees': [{'value': k, 'label': v} for k, v in sorted(emps.items(), key=lambda i: i[1] or '')],
                'facilities': [{'value': f.id, 'label': f.name} for f in facs],
            },
        })

    # ---- building / floor / facility statistics (period-aware) --------------
    @route(API + '/client/structure', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def structure(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        WO = env['care.cafm.workorder'].sudo()
        s, e, label = self._range(kw)
        all_wos = self._in_range(WO.search([('facility_id', 'in', facs.ids)]), s, e)

        def loc_stats(loc_ids):
            ws = all_wos.filtered(lambda w: w.location_id.id in loc_ids)
            return self._wo_stats(ws)

        facilities = []
        for f in facs:
            buildings = []
            for b in f.building_ids:
                floors = []
                for fl in b.floor_ids.sorted('sequence'):
                    lids = fl.location_ids.ids
                    st = loc_stats(lids)
                    floors.append({'id': fl.id, 'name': fl.name, 'locations': len(lids),
                                   'stats': st})
                blids = b.floor_ids.mapped('location_ids').ids
                buildings.append({
                    'id': b.id, 'name': b.name, 'type': b.building_type,
                    'floors_count': len(b.floor_ids), 'locations': len(blids),
                    'stats': loc_stats(blids), 'floors': floors,
                })
            facilities.append({
                'id': f.id, 'name': f.name, 'buildings_count': len(f.building_ids),
                'locations': len(f.location_ids),
                'stats': self._wo_stats(all_wos.filtered(lambda w: w.facility_id == f)),
                'buildings': buildings,
            })
        return _ok({'period': label, 'facilities': facilities})

    # ---- contracts (from the Experience module) -----------------------------
    def _contract_dict(self, env, e):
        sel = lambda f, v: dict(e._fields[f].selection).get(v) if v else None
        return {
            'id': e.id,
            'name': e.name or e.ref or ('عقد #%s' % e.id),
            'ref': e.ref or e.sequence or None,
            'partner': e.partner_id.name or None,
            'type': sel('contract_type', e.contract_type),
            'amount': e.contract_amount or 0.0,
            'currency': e.currency_id.name or '',
            'period_months': e.period or 0,
            'labor': e.labor_quantity or 0,
            'start': e.start_date or None,
            'expire': e.expire_date or None,
            'state': sel('state', e.state),
            'state_raw': e.state,
            'expiry_state': e.expiry_state,
            'days_to_expiry': e.days_to_expiry,
            'project': e.project_id.name or None,
            'department': e.department_id.name or None,
            'notes': e.notes or None,
            'copies': [{'id': a.id, 'name': a.name,
                        'url': _abs('/api/v1/client/contract/%s/attachment/%s' % (e.id, a.id))}
                       for a in e.contract_copy],
            'guarantees': [{'name': g.name, 'bank': g.bank_name, 'amount': g.amount,
                            'expiry': g.expiry_date or None, 'state': g.state} for g in e.guarantee_ids],
            'insurance': ({'company': e.insurance_company, 'policy': e.insurance_policy_no,
                           'amount': e.insurance_amount, 'expiry': e.insurance_expiry or None}
                          if e.insurance_company or e.insurance_policy_no else None),
        }

    @route(API + '/client/contracts', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def contracts(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.experience' not in env:
            return _ok([])
        Exp = env['care.experience'].sudo()
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            exps = Exp.search([])
        else:
            exps = Exp.search([('partner_id', 'in', self._client_partners(env))])
        return _ok([self._contract_dict(env, e) for e in exps])

    @route(API + '/client/contract/<int:eid>/attachment/<int:aid>', type='http', auth='public', methods=['GET'], csrf=False)
    def contract_attachment(self, eid, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        e = env['care.experience'].sudo().browse(eid).exists() if 'care.experience' in env else None
        if not e:
            return _err('غير موجود', 404)
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if not is_mgr and e.partner_id.id not in self._client_partners(env):
            return _err('لا صلاحية', 403)
        att = env['ir.attachment'].sudo().browse(aid).exists()
        if not att or att.id not in e.contract_copy.ids:
            return _err('المرفق غير موجود', 404)
        return request.make_response(att.raw or b'', headers=[
            ('Content-Type', att.mimetype or 'application/octet-stream'),
            ('Content-Disposition', 'inline; filename="%s"' % (att.name or 'contract')),
        ])

    # ---- client service requests (طلبات الخدمة) -----------------------------
    def _request_dict(self, r, env=None):
        can_manage = self._can_add_workers(env) if env else False
        return {'id': r.id, 'name': r.name, 'title': r.title,
                'facility': r.facility_id.name or None, 'location': r.location_id.name or None,
                'service': r.service_id.name or None, 'priority': r.priority,
                'state': dict(r._fields['state'].selection).get(r.state), 'state_raw': r.state,
                'workorder': r.workorder_id.name or None,
                'workorder_id': r.workorder_id.id or None,
                'when': r.request_datetime or None, 'description': r.description or None,
                'reject_reason': r.reject_reason or None,
                'can_convert': bool(can_manage and not r.workorder_id and r.state in ('new', 'in_review')),
                'can_cancel': bool(r.state in ('new', 'in_review'))}

    @route(API + '/client/request/<int:rid>/convert', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def request_convert(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        r = env['care.cafm.service.request'].sudo().browse(rid).exists()
        if not r or r.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        try:
            r.action_convert()
        except Exception as e:
            return _err(str(e), 400)
        return _ok(self._request_dict(r, env))

    @route(API + '/client/request/<int:rid>/cancel', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def request_cancel(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = env['care.cafm.service.request'].sudo().browse(rid).exists()
        if not r or (r.facility_id.id not in self._fac_ids(env) and r.requested_by.id != env.user.id):
            return _err('غير موجود', 404)
        if r.state not in ('new', 'in_review'):
            return _err('لا يمكن إلغاء هذا الطلب', 400)
        r.write({'state': 'closed'})
        return _ok(self._request_dict(r, env))

    @route(API + '/client/requests', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def requests(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.service.request' not in env:
            return _ok([])
        R = env['care.cafm.service.request'].sudo()
        facs = self._facilities(env)
        recs = R.search(['|', ('facility_id', 'in', facs.ids), ('requested_by', '=', env.user.id)], limit=200)
        return _ok([self._request_dict(r, env) for r in recs])

    @route(API + '/client/request/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def request_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.service.request' not in env:
            return _err('غير متاح', 404)
        b = _body()
        title = (b.get('title') or '').strip()
        if not title:
            return _err('عنوان الطلب مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        cp = env.user.partner_id.commercial_partner_id or env.user.partner_id
        vals = {
            'title': title, 'facility_id': fid,
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'service_id': int(b['service_id']) if b.get('service_id') else False,
            'description': b.get('description') or None,
            'priority': str(b.get('priority') or '1'),
            'partner_id': cp.id if cp else False,
            'requested_by': env.user.id,
        }
        if b.get('requested_hours') not in (None, ''):
            try:
                vals['requested_hours'] = float(b.get('requested_hours'))
            except (TypeError, ValueError):
                pass
        if b.get('specifications'):
            vals['specifications'] = b.get('specifications')
        r = env['care.cafm.service.request'].sudo().create(vals)
        return _ok(self._request_dict(r, env))

    # ---- services available to this client (drives the segmented menu) ------
    def _client_service_types(self, env):
        """Which service lines this client actually has. Priority driver: the
        services explicitly assigned to the client's PROJECTS (project.service_ids).
        Falls back to facilities' work orders + teams for legacy setups."""
        facs = self._facilities(env)
        types = set()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        # 1) explicit per-project service assignment — the AUTHORITATIVE driver.
        #    Once any of the client's projects lists services, those alone decide
        #    which service sections show (add/remove on the project ⇒ show/hide).
        proj_types = set()
        if 'care.cafm.project' in env:
            projs = env['care.cafm.project'].sudo().search(
                ['|', ('partner_id', 'in', self._client_partners(env)),
                 ('client_id.user_ids', 'in', [env.user.id])])
            for s in projs.mapped('service_ids'):
                if s.service_type:
                    proj_types.add(s.service_type)
        if proj_types:
            return facs, proj_types
        # 2) legacy fallback: derive from facilities' work orders + teams
        WO = env['care.cafm.workorder'].sudo()
        if facs:
            for w in WO.search([('facility_id', 'in', facs.ids)]):
                if w.service_type:
                    types.add(w.service_type)
            if 'care.cafm.team' in env:
                for t in env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)]):
                    if t.service_id.service_type:
                        types.add(t.service_id.service_type)
        # managers with no explicit setup see every configured service line
        if is_mgr:
            types.update(env['care.cafm.service'].sudo().search([]).mapped('service_type'))
        return facs, types

    @route(API + '/client/services', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_services(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs, types = self._client_service_types(env)
        Service = env['care.cafm.service'].sudo()
        WO = env['care.cafm.workorder'].sudo()
        type_lbl = dict(Service._fields['service_type'].selection)
        out, seen = [], set()
        for s in Service.search([('service_type', 'in', list(types)), ('active', '=', True)], order='sequence') if types else Service.browse():
            if s.service_type in seen:
                continue
            seen.add(s.service_type)
            open_cnt = WO.search_count([('facility_id', 'in', facs.ids),
                                        ('service_id.service_type', '=', s.service_type),
                                        ('state', 'in', ('new', 'assigned', 'in_progress'))]) if facs else 0
            out.append({'id': s.id, 'name': s.name, 'type': s.service_type,
                        'type_label': type_lbl.get(s.service_type, s.service_type),
                        'icon': s.icon or '🧩', 'open': open_cnt})
        return _ok({'services': out})

    # ---- which portal/app sections this client may see ----------------------
    def _cafm_clients(self, env):
        """care.cafm.client records for the logged-in user/partner."""
        if 'care.cafm.client' not in env:
            return None
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
        return env['care.cafm.client'].sudo().search(
            ['|', ('partner_id', 'in', list(pids)), ('user_ids', 'in', [env.user.id])])

    @route(API + '/client/sections', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_sections(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        Section = env['care.cafm.portal.section'].sudo()
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        codes = None
        if is_mgr:
            codes = set(Section.search([]).mapped('code'))
        else:
            _, types = self._client_service_types(env)
            clients = self._cafm_clients(env)
            if clients:
                # union of each client's visible codes (custom allow-list or auto)
                codes = set()
                for c in clients:
                    codes |= c.visible_section_codes(types)
            else:
                codes = Section.auto_codes_for_types(types)
        secs = Section.search([('code', 'in', list(codes)), ('active', '=', True)], order='sequence')
        return _ok({
            'codes': [s.code for s in secs],
            'sections': [{'code': s.code, 'name': s.name, 'icon': s.icon or '🧩',
                          'service_type': s.service_type or None} for s in secs],
        })

    # ---- shop: products (with the client's pricelist) → cart → sale order ----
    def _pricelist(self, env):
        p = env.user.partner_id.commercial_partner_id or env.user.partner_id
        return p.property_product_pricelist or env['product.pricelist'].sudo().search([], limit=1)

    def _fav_ids(self, env):
        p = env.user.partner_id.commercial_partner_id or env.user.partner_id
        return set(p.sudo().cafm_favorite_product_ids.ids)

    @route(API + '/product/<int:pid>/image', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def product_image(self, pid, **kw):
        """Serve a product image via sudo so it renders in <img>/CSS tags that
        carry no auth token. Falls back to Odoo's default placeholder when the
        product has no image, so the grid degrades gracefully."""
        size = request.httprequest.args.get('s') or '256'
        field = 'image_%s' % size if size in ('128', '256', '512', '1024', '1920') else 'image_256'
        p = request.env['product.product'].sudo().browse(int(pid)).exists()
        data = None
        if p:
            data = p[field] or p.image_1920 or p.product_tmpl_id[field] or p.product_tmpl_id.image_1920
        if not data:
            # transparent 1x1 PNG so the frontend fallback (bg colour/icon) shows through
            data = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        raw = base64.b64decode(data)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'public, max-age=86400'),
        ])

    @route(API + '/product/extra-image/<int:iid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def product_extra_image(self, iid, **kw):
        """One of a product's additional gallery images."""
        size = request.httprequest.args.get('s') or '512'
        field = 'image_%s' % size if size in ('128', '256', '512', '1024', '1920') else 'image_512'
        rec = request.env['product.image'].sudo().browse(int(iid)).exists() \
            if 'product.image' in request.env else None
        data = (rec[field] or rec.image_1920) if rec else None
        if not data:
            data = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        raw = base64.b64decode(data)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'public, max-age=86400'),
        ])

    @route(API + '/client/products', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def products(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        Prod = env['product.product'].sudo()
        q = (request.httprequest.args.get('q') or '').strip()
        categ = request.httprequest.args.get('category_id')
        favs_only = request.httprequest.args.get('favorites') in ('1', 'true')
        dom = [('sale_ok', '=', True), ('active', '=', True)]
        if q:
            dom += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        if categ:
            dom += [('categ_id', 'child_of', int(categ))]
        fav = self._fav_ids(env)
        if favs_only:
            dom += [('id', 'in', list(fav))]
        # scope to the client's assigned shop products (+ their projects' materials), if any
        partner = env.user.partner_id.commercial_partner_id or env.user.partner_id
        allowed = set(partner.sudo().cafm_shop_product_ids.ids) if 'cafm_shop_product_ids' in partner._fields else set()
        if 'care.cafm.project' in env:
            projs = env['care.cafm.project'].sudo().search([('partner_id', '=', partner.id)])
            for pr in projs:
                allowed.update(pr.material_ids.ids)
        if allowed:
            dom += [('id', 'in', list(allowed))]
        prods = Prod.search(dom, limit=300)
        pl = self._pricelist(env)
        out = []
        cats = {}
        for p in prods:
            try:
                price = pl._get_product_price(p, 1.0) if pl else p.lst_price
            except Exception:
                price = p.lst_price
            cid = p.categ_id.id or 0
            cats[cid] = {'id': cid, 'name': p.categ_id.name or 'أخرى',
                         'count': cats.get(cid, {}).get('count', 0) + 1}
            out.append({
                'id': p.id, 'name': p.display_name, 'code': p.default_code or None,
                'price': round(price, 3), 'currency': (pl.currency_id.name if pl else env.company.currency_id.name),
                'uom': p.uom_id.name or None,
                'category': p.categ_id.name or None, 'category_id': cid,
                'favorite': p.id in fav,
                'image': _abs('/api/v1/product/%s/image' % p.id),
            })
        categories = sorted(cats.values(), key=lambda c: -c['count'])
        return _ok({'pricelist': pl.name if pl else None, 'products': out,
                    'categories': categories, 'favorite_ids': list(fav)})

    @route(API + '/client/product/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def product_detail(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['product.product'].sudo().browse(pid).exists()
        if not p:
            return _err('غير موجود', 404)
        pl = self._pricelist(env)
        try:
            price = pl._get_product_price(p, 1.0) if pl else p.lst_price
        except Exception:
            price = p.lst_price
        # Descriptions are stored as HTML; the app renders plain text, so an
        # "empty" field like "<p><br></p>" would otherwise show as raw markup.
        from odoo.tools import html2plaintext
        raw = p.description_sale or p.description or ''
        desc = html2plaintext(raw).strip() if raw else ''
        return _ok({
            'id': p.id, 'name': p.display_name, 'code': p.default_code or None,
            'barcode': p.barcode or None,
            'price': round(price, 3), 'list_price': round(p.lst_price, 3),
            'currency': (pl.currency_id.name if pl else env.company.currency_id.name),
            'uom': p.uom_id.name or None, 'category': p.categ_id.name or None,
            'category_id': p.categ_id.id or 0,
            'type': dict(p.fields_get(['type'])['type'].get('selection') or []).get(p.type, p.type),
            'qty_available': p.qty_available if p.type == 'product' else None,
            'weight': p.weight or None, 'volume': p.volume or None,
            'description': desc or None,
            'favorite': p.id in self._fav_ids(env),
            'image': _abs('/api/v1/product/%s/image?s=512' % p.id),
            # The gallery: the main image first, then any extra template images.
            # A product with no image must NOT contribute a URL — that endpoint
            # answers 200 with a transparent 1x1, which the app would render as
            # a blank slide instead of falling back to its placeholder.
            'images': ([_abs('/api/v1/product/%s/image?s=1024' % p.id)]
                       if (p.image_1920 or p.product_tmpl_id.image_1920) else []) + [
                _abs('/api/v1/product/extra-image/%s?s=1024' % i.id)
                for i in (p.product_tmpl_id.product_template_image_ids
                          if 'product_template_image_ids' in p.product_tmpl_id._fields else [])
                if i.image_1920
            ],
            'has_image': bool(p.image_1920 or p.product_tmpl_id.image_1920),
            'attributes': [
                {'name': v.attribute_id.name, 'value': v.name}
                for v in (p.product_template_attribute_value_ids
                          if 'product_template_attribute_value_ids' in p._fields else [])
            ],
            'in_stock': bool(p.qty_available > 0) if p.type == 'product' else True,
        })

    @route(API + '/client/favorite/toggle', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def favorite_toggle(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        pid = _body().get('product_id')
        if not pid:
            return _err('product_id مطلوب', 422)
        partner = (env.user.partner_id.commercial_partner_id or env.user.partner_id).sudo()
        pid = int(pid)
        if pid in partner.cafm_favorite_product_ids.ids:
            partner.cafm_favorite_product_ids = [(3, pid)]
            fav = False
        else:
            partner.cafm_favorite_product_ids = [(4, pid)]
            fav = True
        return _ok({'product_id': pid, 'favorite': fav,
                    'favorite_ids': partner.cafm_favorite_product_ids.ids})

    @route(API + '/client/favorites', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def favorites(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        partner = (env.user.partner_id.commercial_partner_id or env.user.partner_id).sudo()
        pl = self._pricelist(env)
        out = []
        for p in partner.cafm_favorite_product_ids:
            try:
                price = pl._get_product_price(p, 1.0) if pl else p.lst_price
            except Exception:
                price = p.lst_price
            out.append({
                'id': p.id, 'name': p.display_name, 'code': p.default_code or None,
                'price': round(price, 3), 'currency': (pl.currency_id.name if pl else env.company.currency_id.name),
                'uom': p.uom_id.name or None, 'category': p.categ_id.name or None,
                'favorite': True,
                'image': _abs('/api/v1/product/%s/image' % p.id),
            })
        return _ok({'products': out, 'favorite_ids': partner.cafm_favorite_product_ids.ids})

    @route(API + '/client/order/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def order_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        lines = b.get('lines') or []
        if not lines:
            return _err('السلة فارغة', 422)
        partner = env.user.partner_id.commercial_partner_id or env.user.partner_id
        SO = env['sale.order'].sudo()
        vals = {'partner_id': partner.id,
                'order_line': [(0, 0, {'product_id': int(l['product_id']),
                                       'product_uom_qty': float(l.get('qty') or 1)}) for l in lines]}
        # Deliver-to: only an address that actually belongs to this client, so a
        # crafted id can never ship this order to someone else's door.
        addr_id = b.get('address_id')
        if addr_id:
            allowed = self._delivery_addresses(env)
            if int(addr_id) in [a['id'] for a in allowed]:
                vals['partner_shipping_id'] = int(addr_id)
            else:
                return _err('عنوان غير صالح', 422)
        when = b.get('delivery_date')
        if when:
            vals['commitment_date'] = when
        note = (b.get('note') or '').strip()
        if note:
            vals['note'] = note
        pl = self._pricelist(env)
        if pl:
            vals['pricelist_id'] = pl.id
        so = SO.create(vals)
        return _ok({'id': so.id, 'name': so.name, 'amount_total': so.amount_total,
                    'currency': so.currency_id.name, 'state': so.state})

    def _delivery_addresses(self, env):
        """Addresses this client may ship to: their own partner, its delivery
        children, and their facilities' addresses."""
        partner = env.user.partner_id.commercial_partner_id or env.user.partner_id
        out, seen = [], set()

        def _add(p, kind):
            if not p or p.id in seen:
                return
            seen.add(p.id)
            parts = [p.street, p.street2, p.city, p.state_id.name, p.country_id.name]
            out.append({
                'id': p.id, 'name': p.name or partner.name,
                'kind': kind,
                'address': '، '.join([x for x in parts if x]) or None,
                'phone': p.phone or p.mobile or None,
            })

        _add(partner, 'main')
        for c in partner.child_ids.filtered(lambda c: c.type == 'delivery'):
            _add(c, 'delivery')
        for f in self._facilities(env):
            if f.partner_id:
                _add(f.partner_id, 'facility')
        return out

    @route(API + '/client/addresses', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def client_addresses(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        return _ok(self._delivery_addresses(env))

    @route(API + '/client/orders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def orders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        pids = self._client_partners(env)
        sos = env['sale.order'].sudo().search([('partner_id', 'in', pids)], limit=100)
        state_lbl = dict(env['sale.order']._fields['state'].selection)
        inv_lbl = {'no': 'غير مفوترة', 'to invoice': 'بانتظار الفوترة', 'invoiced': 'مفوترة', 'upselling': 'فرصة بيع'}
        dl_lbl = {'nothing': 'لا تسليم', 'to deliver': 'بانتظار التسليم', 'partial': 'تسليم جزئي', 'delivered': 'تم التسليم', 'full': 'تم التسليم'}
        out = []
        for s in sos:
            # delivery status from pickings (if any)
            dstate, dlabel = None, None
            try:
                if hasattr(s, 'delivery_status') and s.delivery_status:
                    dstate = s.delivery_status
                    dlabel = dl_lbl.get(dstate, dstate)
                elif s.picking_ids:
                    pk = s.picking_ids.mapped('state')
                    if all(x == 'done' for x in pk):
                        dstate, dlabel = 'delivered', 'تم التسليم'
                    elif any(x == 'done' for x in pk):
                        dstate, dlabel = 'partial', 'تسليم جزئي'
                    else:
                        dstate, dlabel = 'to deliver', 'بانتظار التسليم'
            except Exception:
                pass
            out.append({
                'id': s.id, 'name': s.name, 'date': s.date_order or None,
                'amount_total': s.amount_total, 'currency': s.currency_id.name,
                'state': s.state, 'state_label': state_lbl.get(s.state),
                'invoice_status': s.invoice_status,
                'invoice_status_label': inv_lbl.get(s.invoice_status, s.invoice_status),
                'invoice_count': len(s.invoice_ids),
                'invoice_id': (s.invoice_ids.filtered(lambda m: m.state == 'posted')[:1].id or None),
                'delivery_status': dstate, 'delivery_label': dlabel,
                'can_cancel': s.state in ('draft', 'sent'),
                'lines': [{'product': l.product_id.display_name, 'qty': l.product_uom_qty,
                           'price': l.price_unit, 'subtotal': l.price_subtotal} for l in s.order_line]})
        return _ok(out)

    def _sale_track(self, s):
        """Delivery / fulfilment tracking steps for a sale order."""
        state_lbl = dict(s._fields['state'].selection)
        steps = [
            {'key': 'draft', 'label': 'عرض سعر', 'done': True},
            {'key': 'sent', 'label': 'مُرسل', 'done': s.state in ('sent', 'sale', 'done')},
            {'key': 'sale', 'label': 'مؤكَّد', 'done': s.state in ('sale', 'done')},
        ]
        picks = []
        try:
            for pk in s.picking_ids:
                picks.append({'name': pk.name, 'state': pk.state,
                              'state_label': dict(pk._fields['state'].selection).get(pk.state),
                              'date': pk.scheduled_date and str(pk.scheduled_date) or None,
                              'done': pk.state == 'done'})
            if picks:
                # "التسليم" is only honest when every picking is done; a partial
                # delivery must not render as complete.
                done_n = sum(1 for p in picks if p['done'])
                steps.append({'key': 'delivery',
                              'label': ('التسليم' if done_n == len(picks)
                                        else 'تسليم جزئي (%s/%s)' % (done_n, len(picks))),
                              'done': done_n == len(picks)})
        except Exception:
            pass
        steps.append({'key': 'invoiced', 'label': 'مفوترة', 'done': s.invoice_status == 'invoiced'})
        return {'state': s.state, 'state_label': state_lbl.get(s.state), 'steps': steps, 'pickings': picks}

    @route(API + '/client/order/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def order_detail(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = env['sale.order'].sudo().browse(sid).exists()
        if not s or s.partner_id.commercial_partner_id.id not in self._client_partners(env):
            is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
            if not is_mgr:
                return _err('لا صلاحية', 403)
        state_lbl = dict(s._fields['state'].selection)
        invs = []
        for m in s.invoice_ids.filtered(lambda x: x.state == 'posted'):
            tok = None
            try:
                tok = m._portal_ensure_token()
            except Exception:
                pass
            invs.append({'id': m.id, 'name': m.name,
                         'amount_total': m.amount_total, 'amount_residual': m.amount_residual,
                         'payment_state': m.payment_state, 'currency': m.currency_id.name,
                         'pay_url': _abs('/my/invoices/%s?access_token=%s' % (m.id, tok)) if tok else None,
                         'pdf_url': _abs('/my/invoices/%s?access_token=%s&report_type=pdf&download=true' % (m.id, tok)) if tok else None})
        return _ok({
            'id': s.id, 'name': s.name, 'date': s.date_order or None,
            'amount_untaxed': s.amount_untaxed, 'amount_tax': s.amount_tax,
            'amount_total': s.amount_total, 'currency': s.currency_id.name,
            'state': s.state, 'state_label': state_lbl.get(s.state),
            'invoice_status': s.invoice_status, 'can_cancel': s.state in ('draft', 'sent'),
            'lines': [{'product': l.product_id.display_name,
                       'product_id': l.product_id.id,
                       'code': l.product_id.default_code or None,
                       'image': (_abs('/api/v1/product/%s/image?s=256' % l.product_id.id)
                                 if (l.product_id.image_1920 or l.product_id.product_tmpl_id.image_1920)
                                 else None),
                       'qty': l.product_uom_qty,
                       'uom': l.product_uom.name, 'price': l.price_unit,
                       'subtotal': l.price_subtotal} for l in s.order_line if not l.display_type],
            'delivery_address': s.partner_shipping_id.contact_address_complete
                                if s.partner_shipping_id and 'contact_address_complete' in s.partner_shipping_id._fields
                                else (s.partner_shipping_id.name if s.partner_shipping_id else None),
            'delivery_date': s.commitment_date or None,
            'note': s.note or None,
            'tracking': self._sale_track(s),
            'invoices': invs,
        })

    @route(API + '/client/order/<int:sid>/cancel', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def order_cancel(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        s = env['sale.order'].sudo().browse(sid).exists()
        if not s or s.partner_id.commercial_partner_id.id not in self._client_partners(env):
            is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
            if not is_mgr:
                return _err('لا صلاحية', 403)
        if s.state not in ('draft', 'sent'):
            return _err('لا يمكن إلغاء طلب مؤكَّد — تواصل مع الإدارة', 422)
        try:
            s._action_cancel()
        except Exception:
            s.state = 'cancel'
        return _ok({'id': s.id, 'name': s.name, 'state': s.state})

    # ---- invoices (client's account.move — paid / unpaid) -------------------
    @route(API + '/client/invoices', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def invoices(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        pids = self._client_partners(env)
        Move = env['account.move'].sudo()
        moves = Move.search([('partner_id', 'in', pids),
                             ('move_type', 'in', ('out_invoice', 'out_refund')),
                             ('state', '=', 'posted')], order='invoice_date desc, id desc', limit=200)
        pay_lbl = {'not_paid': 'غير مدفوعة', 'in_payment': 'قيد الدفع', 'paid': 'مدفوعة',
                   'partial': 'مدفوعة جزئياً', 'reversed': 'معكوسة', 'invoicing_legacy': 'قديمة'}
        appr_lbl = {'pending': 'بانتظار الرد', 'accepted': 'مقبولة', 'rejected': 'مرفوضة'}
        ar_months = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                     'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        out = []
        for m in moves:
            appr = m.cafm_client_approval if 'cafm_client_approval' in m._fields else 'pending'
            d = m.invoice_date
            period = ('فاتورة %s %s' % (ar_months[d.month], d.year)) if d else None
            out.append({
                'id': m.id, 'name': m.name, 'ref': m.ref or None,
                'type': 'refund' if m.move_type == 'out_refund' else 'invoice',
                'date': m.invoice_date or None, 'due': m.invoice_date_due or None,
                'period': period, 'period_key': (('%04d-%02d' % (d.year, d.month)) if d else None),
                'amount_total': m.amount_total, 'amount_residual': m.amount_residual,
                'amount_paid': m.amount_total - m.amount_residual,
                'currency': m.currency_id.name,
                'payment_state': m.payment_state, 'payment_label': pay_lbl.get(m.payment_state, m.payment_state),
                'client_approval': appr, 'approval_label': appr_lbl.get(appr, appr),
                'overdue': bool(m.invoice_date_due and m.amount_residual > 0 and m.invoice_date_due < fields.Date.today()),
            })
        totals = {
            'total': sum(m['amount_total'] for m in out),
            'residual': sum(m['amount_residual'] for m in out),
            'paid': sum(m['amount_paid'] for m in out),
            'count': len(out),
            'currency': moves[:1].currency_id.name if moves else (env.company.currency_id.name),
        }
        return _ok({'invoices': out, 'totals': totals})

    @route(API + '/client/invoice/<int:mid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def invoice_detail(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = env['account.move'].sudo().browse(mid).exists()
        if not m or m.partner_id.commercial_partner_id.id not in [p for p in self._client_partners(env)]:
            is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
            if not is_mgr:
                return _err('لا صلاحية', 403)
        token = None
        try:
            token = m._portal_ensure_token()
        except Exception:
            pass
        # payment records (reconciled) + method
        payments = []
        try:
            for pinfo in m._get_reconciled_info_JSON_values():
                payments.append({
                    'name': pinfo.get('name') or pinfo.get('ref') or '—',
                    'method': pinfo.get('journal_name') or None,
                    'date': str(pinfo.get('date')) if pinfo.get('date') else None,
                    'amount': pinfo.get('amount'),
                })
        except Exception:
            pass
        pay_lbl = {'not_paid': 'غير مدفوعة', 'in_payment': 'قيد الدفع', 'paid': 'مدفوعة',
                   'partial': 'مدفوعة جزئياً', 'reversed': 'معكوسة'}
        return _ok({
            'id': m.id, 'name': m.name, 'ref': m.ref or None,
            'date': m.invoice_date or None, 'due': m.invoice_date_due or None,
            'amount_total': m.amount_total, 'amount_residual': m.amount_residual,
            'amount_untaxed': m.amount_untaxed, 'amount_tax': m.amount_tax,
            'amount_paid': m.amount_total - m.amount_residual, 'currency': m.currency_id.name,
            'payment_state': m.payment_state, 'payment_label': pay_lbl.get(m.payment_state, m.payment_state),
            'partner': m.partner_id.name,
            'client_approval': m.cafm_client_approval if 'cafm_client_approval' in m._fields else 'pending',
            'client_comment': m.cafm_client_comment if 'cafm_client_comment' in m._fields else None,
            'overdue': bool(m.invoice_date_due and m.amount_residual > 0 and m.invoice_date_due < fields.Date.today()),
            'lines': [{'name': l.name, 'qty': l.quantity, 'price': l.price_unit,
                       'subtotal': l.price_subtotal, 'tax': ', '.join(l.tax_ids.mapped('name'))}
                      for l in m.invoice_line_ids if l.display_type in (False, 'product')],
            'payments': payments,
            'pay_url': _abs('/my/invoices/%s?access_token=%s' % (m.id, token)) if token else None,
            'pdf_url': _abs('/my/invoices/%s?access_token=%s&report_type=pdf&download=true' % (m.id, token)) if token else None,
        })

    def _client_invoice(self, env, mid):
        m = env['account.move'].sudo().browse(mid).exists()
        if not m:
            return None
        is_mgr = env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')
        if m.partner_id.commercial_partner_id.id not in self._client_partners(env) and not is_mgr:
            return None
        return m

    @route(API + '/client/invoice/<int:mid>/approve', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def invoice_approve(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = self._client_invoice(env, mid)
        if not m:
            return _err('غير موجود', 404)
        comment = (_body().get('comment') or '').strip()
        m.write({'cafm_client_approval': 'accepted', 'cafm_client_comment': comment or False,
                 'cafm_client_approval_date': fields.Datetime.now(), 'cafm_needs_resend': False})
        try:
            m.message_post(body='✅ قَبِل العميل الفاتورة%s' % ((': ' + comment) if comment else '.'))
        except Exception:
            pass
        return _ok({'id': m.id, 'client_approval': 'accepted'})

    @route(API + '/client/invoice/<int:mid>/reject', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def invoice_reject(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = self._client_invoice(env, mid)
        if not m:
            return _err('غير موجود', 404)
        comment = (_body().get('comment') or '').strip()
        if not comment:
            return _err('يرجى كتابة سبب الرفض', 422)
        m.write({'cafm_client_approval': 'rejected', 'cafm_client_comment': comment,
                 'cafm_client_approval_date': fields.Datetime.now(), 'cafm_needs_resend': True})
        try:
            m.message_post(body='⛔ رفض العميل الفاتورة — بحاجة لإعادة الإرسال. السبب: %s' % comment)
            # notify the invoice author / accountant
            users = (m.invoice_user_id or m.create_uid)
            if users and 'care.cafm.notification' in env:
                env['care.cafm.notification'].sudo().push(
                    users, 'فاتورة مرفوضة من العميل', '%s — %s' % (m.name, comment), ntype='info')
        except Exception:
            pass
        return _ok({'id': m.id, 'client_approval': 'rejected'})

    # ---- notifications: client broadcasts + delivery log --------------------
    @route(API + '/client/notify/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def notify_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        workers = self._client_workers(env, facs)
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)]) if 'care.cafm.team' in env else []
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        types = sorted(set(env['care.cafm.workorder'].sudo().search([('facility_id', 'in', facs.ids)]).mapped('service_type')))
        return _ok({
            'workers': [{'id': e.id, 'name': e.name, 'job': e.job_title or None} for e in workers],
            'teams': [{'id': t.id, 'name': t.name} for t in teams],
            'services': [{'v': t, 'l': svc_lbl.get(t, t)} for t in types if t],
        })

    def _notify_recipients(self, env, audience, b):
        facs = self._facilities(env)
        WO = env['care.cafm.workorder'].sudo()
        workers = self._client_workers(env, facs)
        if audience == 'worker' and b.get('employee_id'):
            return env['hr.employee'].sudo().browse(int(b['employee_id'])).user_id
        if audience == 'team' and b.get('team_id') and 'care.cafm.team' in env:
            t = env['care.cafm.team'].sudo().browse(int(b['team_id']))
            emps = t.member_line_ids.mapped('employee_id') | t.member_ids
            return (emps.mapped('user_id') | t.supervisor_ids | t.quality_ids)
        if audience == 'service' and b.get('service_type'):
            emps = WO.search([('facility_id', 'in', facs.ids), ('service_type', '=', b['service_type']),
                              ('employee_id', '!=', False)]).mapped('employee_id')
            return emps.mapped('user_id')
        if audience == 'late':
            emps = WO.search([('facility_id', 'in', facs.ids), ('is_overdue', '=', True),
                              ('employee_id', '!=', False)]).mapped('employee_id')
            return emps.mapped('user_id')
        # all workers on the client's sites
        return workers.mapped('user_id')

    @route(API + '/client/notify/send', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def notify_send(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        title = (b.get('title') or '').strip()
        if not title:
            return _err('العنوان مطلوب', 422)
        audience = b.get('audience') or 'all'
        recips = self._notify_recipients(env, audience, b)
        recips = recips.filtered(lambda u: u.active) if recips else recips
        if not recips:
            return _err('لا مستلمين مطابقين', 422)
        batch = uuid.uuid4().hex[:16]
        ntype = b.get('ntype') or 'info'
        # Deferred delivery: snapshot the recipient set now, dispatch by cron.
        sched = (b.get('scheduled_datetime') or '').strip()
        if sched:
            try:
                when = fields.Datetime.to_datetime(sched)
            except Exception:
                when = None
            if when and when > fields.Datetime.now():
                env['care.cafm.notification.scheduled'].sudo().create({
                    'title': title, 'body': b.get('body') or None, 'ntype': ntype,
                    'audience_label': b.get('audience_label') or audience,
                    'user_ids': [(6, 0, recips.ids)], 'scheduled_datetime': when,
                    'author_id': env.user.id, 'batch': batch,
                })
                return _ok({'batch': batch, 'recipients': len(recips), 'scheduled': True,
                            'scheduled_datetime': str(when)})
        env['care.cafm.notification'].sudo().push(
            recips, title, b.get('body') or None, ntype=ntype,
            author=env.user, batch=batch)
        return _ok({'batch': batch, 'recipients': len(recips), 'scheduled': False})

    @route(API + '/client/notify/preview', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def notify_preview(self, **kw):
        """How many recipients the current audience selection resolves to — so the
        sender sees the reach before pressing send."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        recips = self._notify_recipients(env, b.get('audience') or 'all', b)
        recips = recips.filtered(lambda u: u.active) if recips else recips
        return _ok({'count': len(recips) if recips else 0})

    @route(API + '/client/notify/scheduled', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def notify_scheduled(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        S = env['care.cafm.notification.scheduled'].sudo()
        rows = S.search([('author_id', '=', env.user.id), ('state', '=', 'pending')],
                        order='scheduled_datetime asc')
        return _ok([{'id': r.id, 'title': r.title, 'body': r.body, 'ntype': r.ntype,
                     'audience': r.audience_label, 'recipients': r.recipients_count,
                     'scheduled_datetime': str(r.scheduled_datetime)} for r in rows])

    @route(API + '/client/notify/scheduled/cancel', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def notify_scheduled_cancel(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        b = _body()
        rec = env['care.cafm.notification.scheduled'].sudo().search(
            [('id', '=', int(b.get('id') or 0)), ('author_id', '=', env.user.id)])
        if not rec:
            return _err('غير موجود', 404)
        rec.action_cancel()
        return _ok({'ok': True})

    @route(API + '/client/notify/sent', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def notify_sent(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        N = env['care.cafm.notification'].sudo()
        rows = N.search([('author_id', '=', env.user.id), ('batch', '!=', False)], order='create_date desc', limit=400)
        by_batch = {}
        for n in rows:
            g = by_batch.setdefault(n.batch, {'batch': n.batch, 'title': n.title, 'body': n.body,
                                              'ntype': n.ntype, 'date': n.create_date, 'total': 0, 'read': 0})
            g['total'] += 1
            if n.is_read:
                g['read'] += 1
        out = sorted(by_batch.values(), key=lambda g: g['date'] or '', reverse=True)
        return _ok(out)

    @route(API + '/client/notify/batch/<batch>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def notify_batch(self, batch, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        N = env['care.cafm.notification'].sudo()
        rows = N.search([('batch', '=', batch), ('author_id', '=', env.user.id)])
        if not rows:
            return _err('غير موجود', 404)
        return _ok({
            'title': rows[0].title, 'body': rows[0].body,
            'recipients': [{'name': n.user_id.name, 'read': n.is_read,
                            'read_date': n.read_date or None} for n in rows.sorted(lambda x: not x.is_read)],
        })

    # ---- SLA agreements (اتفاقية الخدمة) ------------------------------------
    @route(API + '/client/sla', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def sla(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.sla' not in env:
            return _ok([])
        facs = self._facilities(env)
        recs = env['care.cafm.sla'].sudo().search(
            ['|', ('facility_id', 'in', facs.ids), ('facility_id', '=', False), ('active', '=', True)])
        plbl = {'0': 'عادية', '1': 'متوسطة', '2': 'عالية', '3': 'عاجلة'}
        return _ok([{
            'id': s.id, 'name': s.name,
            'facility': s.facility_id.name or None, 'service': s.service_id.name or None,
            'lines': [{'priority': l.priority, 'priority_label': plbl.get(l.priority, l.priority),
                       'response_hours': l.response_hours, 'resolution_hours': l.resolution_hours}
                      for l in s.line_ids.sorted(lambda x: x.priority, reverse=True)],
        } for s in recs])

    # ---- quality rounds / observations (الجولات والجودة) --------------------
    def _obs_dict(self, o):
        return {'id': o.id, 'name': o.name, 'title': o.title,
                'facility': o.facility_id.name or None, 'location': o.location_id.name or None,
                'service': o.service_id.name or None,
                'severity': o.severity, 'severity_label': dict(o._fields['severity'].selection).get(o.severity),
                'state': o.state, 'state_label': dict(o._fields['state'].selection).get(o.state),
                'raised_by': o.raised_by.name or None, 'assignee': o.assignee_id.name or None,
                'deadline': o.deadline or None, 'is_overdue': o.is_overdue,
                'workorder': o.workorder_id.name or None, 'description': o.description or None}

    @route(API + '/client/observations', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def observations(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.observation' not in env:
            return _ok([])
        state = request.httprequest.args.get('state')
        dom = [('facility_id', 'in', self._facilities(env).ids)]
        if state == 'open':
            dom.append(('state', 'not in', ('closed', 'cancelled')))
        recs = env['care.cafm.observation'].sudo().search(dom, limit=200)
        return _ok([self._obs_dict(o) for o in recs])

    @route(API + '/client/observation/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def observation_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.observation' not in env:
            return _err('غير متاح', 404)
        b = _body()
        if not (b.get('title') or '').strip():
            return _err('عنوان الملاحظة مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        o = env['care.cafm.observation'].sudo().create({
            'title': b['title'].strip(), 'facility_id': fid,
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'service_id': int(b['service_id']) if b.get('service_id') else False,
            'severity': b.get('severity') or 'medium',
            'description': b.get('description') or None,
        })
        # Attach any photos/videos the client captured — stored as attachments on
        # the observation so they show in its chatter and the corrective WO.
        media = b.get('media') or []
        for i, m in enumerate(media):
            data = (m.get('data') or '') if isinstance(m, dict) else str(m)
            if not data:
                continue
            try:
                env['ir.attachment'].sudo().create({
                    'name': (m.get('name') if isinstance(m, dict) else None) or ('media-%d' % (i + 1)),
                    'datas': data, 'res_model': 'care.cafm.observation', 'res_id': o.id,
                    'mimetype': (m.get('mimetype') if isinstance(m, dict) else None) or 'image/jpeg',
                })
            except Exception:
                pass
        if media:
            try:
                o.message_post(body=_('أرفق العميل %d ملف وسائط.') % len(media))
            except Exception:
                pass
        return _ok(self._obs_dict(o))

    @route(API + '/client/observation/<int:oid>/workorder', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def observation_to_wo(self, oid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        o = env['care.cafm.observation'].sudo().browse(oid).exists()
        if not o or o.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        o.action_make_workorder()
        return _ok({'workorder': o.workorder_id.name})

    # ---- preventive maintenance (PPM) ---------------------------------------
    def _ppm_dict(self, p):
        return {'id': p.id, 'name': p.name, 'facility': p.facility_id.name or None,
                'asset': p.asset_id.name or None, 'service': p.service_id.name or None,
                'every': '%s %s' % (p.interval_number, dict(p._fields['interval_unit'].selection).get(p.interval_unit)),
                'interval_number': p.interval_number, 'interval_unit': p.interval_unit,
                'next_date': p.next_date or None, 'last_generated': p.last_generated or None,
                'generated_count': p.generated_count, 'active': p.active}

    @route(API + '/client/ppm', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def ppm(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.ppm' not in env:
            return _ok([])
        recs = env['care.cafm.ppm'].sudo().search([('facility_id', 'in', self._facilities(env).ids)])
        return _ok([self._ppm_dict(p) for p in recs])

    @route(API + '/client/ppm/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def ppm_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        if 'care.cafm.ppm' not in env:
            return _err('غير متاح', 404)
        b = _body()
        fid = int(b['facility_id']) if b.get('facility_id') else None
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        if not b.get('name') or not b.get('service_id'):
            return _err('الاسم والخدمة مطلوبان', 422)
        p = env['care.cafm.ppm'].sudo().create({
            'name': b['name'].strip(), 'facility_id': fid,
            'service_id': int(b['service_id']),
            'asset_id': int(b['asset_id']) if b.get('asset_id') else False,
            'interval_number': int(b.get('interval_number') or 1),
            'interval_unit': b.get('interval_unit') or 'months',
            'expected_minutes': int(b.get('expected_minutes') or 60),
        })
        return _ok(self._ppm_dict(p))

    @route(API + '/client/ppm/<int:pid>/generate', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def ppm_generate(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        p = env['care.cafm.ppm'].sudo().browse(pid).exists()
        if not p or p.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        wo = p._generate_wo()
        return _ok({'workorder': wo.name})

    @route(API + '/client/workorder/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def workorder_options(self, **kw):
        """Everything the 'new work order' form needs: the client's facilities
        (each with its locations), the services they receive, the teams, and the
        workers — so the client can target a service/team or assign directly."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        Loc = env['care.cafm.location'].sudo()
        locs_by_fac = {}
        for l in Loc.search([('facility_id', 'in', facs.ids)]):
            locs_by_fac.setdefault(l.facility_id.id, []).append({
                'id': l.id, 'name': l.name, 'code': l.code or None,
                'building': l.building_id.name if 'building_id' in l._fields and l.building_id else None,
                'floor': l.floor_id.name if 'floor_id' in l._fields and l.floor_id else None,
            })
        services = env['care.cafm.service'].sudo().search([])
        # only services this client actually receives
        _, allowed_types = self._client_service_types(env)
        services = services.filtered(lambda s: not allowed_types or s.service_type in allowed_types)
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)]) if 'care.cafm.team' in env else []
        workers = self._client_workers(env, facs)
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name, 'locations': locs_by_fac.get(f.id, [])} for f in facs],
            'services': [{'id': s.id, 'name': s.name, 'type': s.service_type,
                          'type_label': svc_lbl.get(s.service_type, s.service_type)} for s in services],
            'teams': [{'id': t.id, 'name': t.name, 'facility_id': t.facility_id.id,
                       'service': t.service_id.name or None,
                       'service_id': t.service_id.id or None} for t in teams],
            'workers': [{'id': e.id, 'name': e.name, 'job': e.job_title or None} for e in workers],
            'priorities': [{'v': '0', 'l': 'منخفضة'}, {'v': '1', 'l': 'عادية'},
                           {'v': '2', 'l': 'عالية'}, {'v': '3', 'l': 'عاجلة'}],
        })

    @route(API + '/client/workorder/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def workorder_create(self, **kw):
        """Client raises a work order against a service, optionally targeting a
        team's service line and/or assigning it directly to a worker."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح لك بإنشاء أوامر عمل', 403)
        b = _body()
        title = (b.get('title') or '').strip()
        if not title:
            return _err('عنوان أمر العمل مطلوب', 422)
        fid = int(b['facility_id']) if b.get('facility_id') else (self._facilities(env)[:1].id or None)
        if not fid or fid not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        # service: explicit, or inferred from the chosen team
        sid = int(b['service_id']) if b.get('service_id') else None
        if not sid and b.get('team_id') and 'care.cafm.team' in env:
            t = env['care.cafm.team'].sudo().browse(int(b['team_id'])).exists()
            sid = t.service_id.id if t else None
        if not sid:
            return _err('الخدمة مطلوبة', 422)
        vals = {
            'title': title, 'facility_id': fid, 'service_id': sid,
            'location_id': int(b['location_id']) if b.get('location_id') else False,
            'priority': str(b.get('priority') or '1'),
            'description': b.get('description') or None,
        }
        if b.get('employee_id'):
            emp = env['hr.employee'].sudo().browse(int(b['employee_id'])).exists()
            if emp:
                vals['employee_id'] = emp.id
        # deadline is SLA-computed from request time; honour an explicit request
        # time when the client picks one so urgent jobs get an earlier deadline.
        if b.get('request_datetime'):
            try:
                vals['request_datetime'] = fields.Datetime.to_datetime(b['request_datetime'])
            except Exception:
                pass
        wo = env['care.cafm.workorder'].with_user(SUPERUSER_ID).create(vals)
        # a direct assignment should move it out of the unassigned state
        if wo.employee_id and wo.state == 'new':
            try:
                wo.state = 'assigned'
            except Exception:
                pass
        return _ok(_wo_dict(wo))

    @route(API + '/client/workorders', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def workorders(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        facs = self._facilities(env)
        a = request.httprequest.args
        dom = [('facility_id', 'in', facs.ids)]
        state = a.get('state')
        # 'overdue' and 'urgent' are cuts across states, not states themselves.
        if state in ('open', 'overdue', 'urgent'):
            dom.append(('state', 'not in', ('done', 'verified', 'cancelled')))
        elif state and state not in ('all', 'overdue', 'urgent'):
            dom.append(('state', '=', state))
        for key, field in (('service_type', 'service_type'), ('priority', 'priority')):
            v = a.get(key)
            if v and v != 'all':
                dom.append((field, '=', v))
        for key, field in (('employee_id', 'employee_id'), ('facility_id', 'facility_id')):
            v = a.get(key)
            if v and v != 'all':
                try:
                    dom.append((field, '=', int(v)))
                except ValueError:
                    pass
        q = (a.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('title', 'ilike', q), ('name', 'ilike', q), ('description', 'ilike', q)]
        dstart, dend, period_label = self._range(request.httprequest.args)

        WO = env['care.cafm.workorder'].sudo()
        # Stats must describe the whole filtered set, so they are computed
        # before the display limit is applied — a "300 shown" cap must never
        # silently become "300" in the totals.
        allw = WO.search(dom, order='request_datetime desc')
        if dstart or dend:
            allw = self._in_range(allw, dstart, dend)
        if state == 'overdue':
            allw = allw.filtered('is_overdue')
        elif state == 'urgent':
            allw = allw.filtered(lambda w: w.priority in ('2', '3'))

        now = fields.Datetime.now()

        def _age_days(w):
            """How many days past its deadline an order is (0 if not late)."""
            if not w.deadline or w.state in ('done', 'verified', 'cancelled'):
                return 0
            d = (now - w.deadline).total_seconds() / 86400.0
            return round(d, 1) if d > 0 else 0

        overdue = allw.filtered('is_overdue')
        # Overdue split into buckets, so "late" isn't one undifferentiated pile.
        buckets = {'d1': 0, 'd3': 0, 'w1': 0, 'm1': 0, 'm1p': 0}
        for w in overdue:
            d = _age_days(w)
            if d <= 1: buckets['d1'] += 1
            elif d <= 3: buckets['d3'] += 1
            elif d <= 7: buckets['w1'] += 1
            elif d <= 30: buckets['m1'] += 1
            else: buckets['m1p'] += 1

        open_wos = allw.filtered(lambda w: w.state not in ('done', 'verified', 'cancelled'))
        done_wos = allw.filtered(lambda w: w.state in ('done', 'verified'))
        state_lbl = dict(WO._fields['state'].selection)
        prio_lbl = dict(WO._fields['priority'].selection)
        svc_lbl = dict(env['care.cafm.service']._fields['service_type'].selection)

        # Per-worker and per-role rollups — "who is carrying the late work".
        by_emp, by_job = {}, {}
        for w in allw:
            if w.employee_id:
                e = by_emp.setdefault(w.employee_id.id, {
                    'id': w.employee_id.id, 'name': w.employee_id.name,
                    'job': w.employee_id.job_title or None, 'total': 0, 'open': 0, 'overdue': 0})
                e['total'] += 1
                if w.state not in ('done', 'verified', 'cancelled'): e['open'] += 1
                if w.is_overdue: e['overdue'] += 1
                jb = w.employee_id.job_title or 'بدون دور'
                j = by_job.setdefault(jb, {'name': jb, 'total': 0, 'overdue': 0})
                j['total'] += 1
                if w.is_overdue: j['overdue'] += 1

        recs = []
        for w in allw[:300]:
            d = _wo_dict(w)
            d['overdue_days'] = _age_days(w)
            recs.append(d)

        return _ok({
            'records': recs,
            'count': len(allw),
            'shown': len(recs),
            'period_label': period_label,
            'stats': {
                'total': len(allw),
                'open': len(open_wos),
                'done': len(done_wos),
                'overdue': len(overdue),
                'urgent': len(open_wos.filtered(lambda w: w.priority in ('2', '3'))),
                'unassigned': len(open_wos.filtered(lambda w: not w.employee_id)),
                'completion_rate': round(len(done_wos) * 100.0 / len(allw), 1) if allw else 0.0,
                'sla_rate': round((len(allw) - len(overdue)) * 100.0 / len(allw), 1) if allw else 0.0,
                'overdue_buckets': buckets,
                'by_state': {lbl: len(allw.filtered(lambda w, st=k: w.state == st)) for k, lbl in state_lbl.items()},
                'by_priority': {lbl: len(allw.filtered(lambda w, p=k: w.priority == p)) for k, lbl in prio_lbl.items()},
                'by_service': {svc_lbl.get(t, t): len(allw.filtered(lambda w, tt=t: w.service_type == tt))
                               for t in sorted(set(allw.mapped('service_type')) - {False})},
                'by_employee': sorted(by_emp.values(), key=lambda e: (-e['overdue'], -e['open']))[:20],
                'by_job': sorted(by_job.values(), key=lambda j: -j['total'])[:12],
            },
            # Facet sources, so the app's dropdowns list only what this client
            # actually has rather than every value in the system.
            'facets': {
                'services': [{'value': t, 'label': svc_lbl.get(t, t)}
                             for t in sorted(set(facs and WO.search([('facility_id', 'in', facs.ids)]).mapped('service_type') or []) - {False})],
                'facilities': [{'value': f.id, 'label': f.name} for f in facs],
                'employees': [{'value': e['id'], 'label': e['name']} for e in
                              sorted(by_emp.values(), key=lambda e: e['name'])],
                'states': [{'value': k, 'label': v} for k, v in state_lbl.items()],
                'priorities': [{'value': k, 'label': v} for k, v in prio_lbl.items()],
            },
        })

    # ---- add workers (client self-service, gated per-client or supervisor) ---
    def _can_add_workers(self, env):
        u = env.user
        if (u.has_group('base.group_erp_manager') or u.has_group('base.group_system')
                or u.has_group('security_management.group_security_manager')):
            return True
        # a client user whose company partner is flagged
        p = u.partner_id.commercial_partner_id or u.partner_id
        return bool(p and p.sudo().cafm_can_add_workers)

    @route(API + '/client/worker/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def worker_options(self, **kw):
        """Teams the client can assign a new worker to (for the add-worker form)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح بإضافة عمّال', 403)
        teams = env['care.cafm.team'].sudo().search([('facility_id', 'in', self._facilities(env).ids)])
        return _ok({
            'teams': [{'id': t.id, 'name': t.name, 'facility': t.facility_id.name or None,
                       'service': t.service_id.name or None} for t in teams],
        })

    @route(API + '/client/worker/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def worker_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح لك بإضافة عمّال', 403)
        b = _body()
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اسم العامل مطلوب', 422)
        # The care_attendance guard checks self.env.user.has_group(...); .sudo()
        # only flips su=True and keeps env.user, so it still sees the client. Run
        # the create AS the superuser (with_user), which passes the guard.
        Emp = env['hr.employee'].with_user(SUPERUSER_ID)
        team = env['care.cafm.team'].sudo().browse(int(b['team_id'])).exists() if b.get('team_id') else None
        facility = (team.facility_id if team else False) or self._facilities(env)[:1]
        vals = {
            'name': name,
            'job_title': b.get('job_title') or None,
            'work_phone': b.get('phone') or None,
            'work_email': b.get('email') or None,
        }
        try:
            emp = Emp.create(vals)
        except Exception as e:
            return _err(str(e), 400)
        # attach to the chosen team so the worker shows in the client's roster
        if team:
            team.write({'member_ids': [(4, emp.id)]})
        # optional login so the worker can use the app
        if b.get('create_login') and (b.get('login') or b.get('email')):
            login = (b.get('login') or b.get('email')).strip()
            if not env['res.users'].sudo().search_count([('login', '=', login)]):
                user = env['res.users'].with_user(SUPERUSER_ID).create({
                    'name': name, 'login': login,
                    'password': b.get('password') or None,
                    'email': b.get('email') or None,
                    'groups_id': [(6, 0, [env.ref('base.group_user').id])],
                })
                emp.user_id = user.id
                if team:
                    team.write({'user_member_ids': [(4, user.id)]})
        return _ok({'id': emp.id, 'name': emp.name, 'job': emp.job_title or None,
                    'team': team.name if team else None,
                    'facility': facility.name if facility else None})

    # ---- full client self-management (buildings/floors/locations/teams) ------
    #      gated by the same per-client permission (or supervisor/admin).
    def _fac_ids(self, env):
        return set(self._facilities(env).ids)

    @route(API + '/client/manage/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def manage_options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        facs = self._facilities(env)
        Svc = env['care.cafm.service'].sudo()
        Bld = env['care.cafm.building'].sudo()
        Fl = env['care.cafm.floor'].sudo()
        blds = Bld.search([('facility_id', 'in', facs.ids)])
        Loc = env['care.cafm.location'].sudo()
        return _ok({
            'facilities': [{'id': f.id, 'name': f.name} for f in facs],
            'services': [{'id': s.id, 'name': s.name} for s in Svc.search([])],
            'buildings': [{'id': b.id, 'name': b.name, 'facility_id': b.facility_id.id,
                           'type': b.building_type, 'floors': len(b.floor_ids)} for b in blds],
            'floors': [{'id': f.id, 'name': f.name, 'building_id': f.building_id.id,
                        'building': f.building_id.name} for f in Fl.search([('building_id', 'in', blds.ids)])],
            'teams': [{'id': t.id, 'name': t.name, 'facility_id': t.facility_id.id,
                       'service': t.service_id.name} for t in env['care.cafm.team'].sudo().search([('facility_id', 'in', facs.ids)])],
            'assets': ([{'id': a.id, 'name': a.name, 'code': a.code, 'category': a.category,
                         'facility_id': a.facility_id.id, 'status': a.status}
                        for a in env['care.cafm.asset'].sudo().search([('facility_id', 'in', facs.ids)])]
                       if 'care.cafm.asset' in env else []),
            'asset_categories': ([{'v': v, 'l': l} for v, l in env['care.cafm.asset']._fields['category'].selection]
                                 if 'care.cafm.asset' in env else []),
            'locations_count': Loc.search_count([('facility_id', 'in', facs.ids)]),
            'building_types': [{'v': v, 'l': l} for v, l in (Bld._fields['building_type'].selection or [])],
            'location_types': [{'v': v, 'l': l} for v, l in (Loc._fields['location_type'].selection or [])],
        })

    @route(API + '/client/manage/asset', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_asset(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        if 'care.cafm.asset' not in env:
            return _err('غير متاح', 404)
        b = _body()
        A = env['care.cafm.asset'].sudo()
        fid = int(b['facility_id']) if b.get('facility_id') else None
        if fid and fid not in self._fac_ids(env):
            return _err('لا صلاحية على هذا المرفق', 403)
        vals = {'name': (b.get('name') or '').strip()}
        if fid:
            vals['facility_id'] = fid
        for f in ('category', 'status', 'serial', 'brand', 'model_name'):
            if b.get(f) is not None:
                vals[f] = b.get(f)
        if b.get('location_id'):
            vals['location_id'] = int(b['location_id'])
        if b.get('id'):
            rec = A.browse(int(b['id'])).exists()
            if not rec or rec.facility_id.id not in self._fac_ids(env):
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            if not vals.get('name') or not vals.get('facility_id'):
                return _err('الاسم والمرفق مطلوبان', 422)
            rec = A.create(vals)
        return _ok({'id': rec.id, 'name': rec.name, 'code': rec.code})

    @route(API + '/client/manage/building', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_building(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        b = _body()
        fid = int(b['facility_id']) if b.get('facility_id') else None
        if fid and fid not in self._fac_ids(env):
            return _err('لا صلاحية على هذا المرفق', 403)
        Bld = env['care.cafm.building'].sudo()
        vals = {'name': (b.get('name') or '').strip()}
        if fid:
            vals['facility_id'] = fid
        for f in ('building_type',):
            if b.get(f) is not None:
                vals[f] = b.get(f)
        for f in ('width_m', 'depth_m', 'floor_height_m', 'basement_count'):
            if b.get(f) is not None:
                vals[f] = float(b.get(f))
        if b.get('id'):
            rec = Bld.browse(int(b['id'])).exists()
            if not rec or rec.facility_id.id not in self._fac_ids(env):
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            if not vals.get('name') or not vals.get('facility_id'):
                return _err('الاسم والمرفق مطلوبان', 422)
            rec = Bld.create(vals)
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/client/manage/floor', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_floor(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        b = _body()
        Fl = env['care.cafm.floor'].sudo()
        Bld = env['care.cafm.building'].sudo()
        bid = int(b['building_id']) if b.get('building_id') else None
        if bid:
            bld = Bld.browse(bid).exists()
            if not bld or bld.facility_id.id not in self._fac_ids(env):
                return _err('لا صلاحية على هذا المبنى', 403)
        vals = {'name': (b.get('name') or '').strip()}
        if bid:
            vals['building_id'] = bid
        if b.get('sequence') is not None:
            vals['sequence'] = int(b.get('sequence'))
        if b.get('id'):
            rec = Fl.browse(int(b['id'])).exists()
            if not rec or rec.building_id.facility_id.id not in self._fac_ids(env):
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            if not vals.get('name') or not vals.get('building_id'):
                return _err('الاسم والمبنى مطلوبان', 422)
            rec = Fl.create(vals)
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/client/manage/location', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_location(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        b = _body()
        Loc = env['care.cafm.location'].sudo()
        Fl = env['care.cafm.floor'].sudo()
        flid = int(b['floor_id']) if b.get('floor_id') else None
        fl = Fl.browse(flid).exists() if flid else None
        if fl and fl.building_id.facility_id.id not in self._fac_ids(env):
            return _err('لا صلاحية', 403)
        facility_id = (fl.building_id.facility_id.id if fl else
                       (int(b['facility_id']) if b.get('facility_id') else None))
        if not facility_id or facility_id not in self._fac_ids(env):
            return _err('المرفق مطلوب', 422)
        vals = {'name': (b.get('name') or '').strip(), 'facility_id': facility_id,
                'location_type': b.get('location_type') or 'other'}
        if fl:
            vals['floor_id'] = fl.id
        if b.get('id'):
            rec = Loc.browse(int(b['id'])).exists()
            if not rec or rec.facility_id.id not in self._fac_ids(env):
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            if not vals['name']:
                return _err('الاسم مطلوب', 422)
            rec = Loc.create(vals)
        return _ok({'id': rec.id, 'name': rec.name, 'code': rec.code})

    @route(API + '/client/manage/team', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_team(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        b = _body()
        T = env['care.cafm.team'].sudo()
        fid = int(b['facility_id']) if b.get('facility_id') else None
        if fid and fid not in self._fac_ids(env):
            return _err('لا صلاحية على هذا المرفق', 403)
        vals = {'name': (b.get('name') or '').strip()}
        if fid:
            vals['facility_id'] = fid
        if b.get('service_id'):
            vals['service_id'] = int(b['service_id'])
        if b.get('id'):
            rec = T.browse(int(b['id'])).exists()
            if not rec or rec.facility_id.id not in self._fac_ids(env):
                return _err('غير موجود', 404)
            rec.write(vals)
        else:
            if not vals.get('name') or not vals.get('facility_id') or not vals.get('service_id'):
                return _err('الاسم والمرفق والخدمة مطلوبة', 422)
            rec = T.create(vals)
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/client/manage/<string:kind>/<int:rid>/delete', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def manage_delete(self, kind, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        models = {'building': 'care.cafm.building', 'floor': 'care.cafm.floor',
                  'location': 'care.cafm.location', 'team': 'care.cafm.team',
                  'asset': 'care.cafm.asset'}
        if kind not in models or models[kind] not in env:
            return _err('نوع غير معروف', 404)
        rec = env[models[kind]].sudo().browse(rid).exists()
        if not rec:
            return _err('غير موجود', 404)
        # scope check
        fid = (rec.facility_id.id if kind in ('building', 'team', 'location', 'asset')
               else rec.building_id.facility_id.id)
        if fid not in self._fac_ids(env):
            return _err('لا صلاحية', 403)
        # guard: don't delete structure that has work-order history
        WO = env['care.cafm.workorder'].sudo()
        loc_ids = ({rec.id} if kind == 'location'
                   else set(rec.mapped('floor_ids.location_ids').ids) if kind == 'building'
                   else set(rec.location_ids.ids) if kind == 'floor' else set())
        if loc_ids and WO.search_count([('location_id', 'in', list(loc_ids))]):
            return _err('لا يمكن الحذف — توجد أوامر عمل مرتبطة', 400)
        rec.unlink()
        return _ok({'deleted': rid})

    # ---- translations of names (facility/building/floor/location/asset/team) --
    _TR_MODELS = {'facility': 'care.cafm.facility', 'building': 'care.cafm.building',
                  'floor': 'care.cafm.floor', 'location': 'care.cafm.location',
                  'asset': 'care.cafm.asset', 'team': 'care.cafm.team'}

    @route(API + '/client/i18n/languages', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def i18n_languages(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        langs = env['res.lang'].sudo().search([('active', '=', True)])
        # map to the app's short codes where possible
        short = {'ar_001': 'ar', 'en_US': 'en', 'hi_IN': 'hi', 'ur_PK': 'ur',
                 'bn_IN': 'bn', 'ne_NP': 'ne', 'fil_PH': 'fil', 'fr_FR': 'fr'}
        return _ok([{'code': l.code, 'short': short.get(l.code, l.code), 'name': l.name}
                    for l in langs])

    @route(API + '/client/i18n/get', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def i18n_get(self, **kw):
        """Current per-language values of a record's name, for the editor."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = request.httprequest.args
        kind, rid = a.get('kind'), a.get('id')
        if kind not in self._TR_MODELS or not (rid or '').isdigit():
            return _err('نوع غير معروف', 404)
        rec = env[self._TR_MODELS[kind]].sudo().browse(int(rid)).exists()
        if not rec:
            return _err('غير موجود', 404)
        langs = env['res.lang'].sudo().search([('active', '=', True)])
        out = {}
        for l in langs:
            out[l.code] = rec.with_context(lang=l.code).name or ''
        return _ok({'id': rec.id, 'values': out})

    @route(API + '/client/i18n/set', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def i18n_set(self, **kw):
        """Save a record's name per language. body: {kind, id, values:{lang:val}}."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can_add_workers(env):
            return _err('غير مسموح', 403)
        b = _body()
        kind, rid = b.get('kind'), b.get('id')
        if kind not in self._TR_MODELS or not rid:
            return _err('نوع غير معروف', 404)
        Model = env[self._TR_MODELS[kind]]
        rec = Model.sudo().browse(int(rid)).exists()
        if not rec:
            return _err('غير موجود', 404)
        values = b.get('values') or {}
        # write English source first (the base), then each translation.
        order = sorted(values.keys(), key=lambda c: 0 if c == 'en_US' else 1)
        for code in order:
            val = (values.get(code) or '').strip()
            if not val:
                continue
            try:
                rec.with_context(lang=code).sudo().write({'name': val})
            except Exception:
                pass
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/client/facility/<int:fid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def facility(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        f = env['care.cafm.facility'].sudo().browse(fid).exists()
        if not f or f.id not in self._facilities(env).ids:
            return _err('غير موجود', 404)
        locs = env['care.cafm.location'].sudo().search([('facility_id', '=', f.id)])
        lt = dict(env['care.cafm.location']._fields['location_type'].selection)
        WO = env['care.cafm.workorder'].sudo()
        Asset = env['care.cafm.asset'].sudo() if 'care.cafm.asset' in env else None
        # count fields live on the facility, not the location — count per-location here.
        wo_by_loc = {}
        for grp in WO.read_group([('location_id', 'in', locs.ids)], ['location_id'], ['location_id']):
            if grp.get('location_id'):
                wo_by_loc[grp['location_id'][0]] = grp['location_id_count']
        asset_by_loc = {}
        if Asset is not None:
            for grp in Asset.read_group([('location_id', 'in', locs.ids)], ['location_id'], ['location_id']):
                if grp.get('location_id'):
                    asset_by_loc[grp['location_id'][0]] = grp['location_id_count']
        # per-building floor + location rollup so the tree is clickable at every level
        buildings = []
        for b in f.building_ids:
            floors = [{'id': fl.id, 'name': fl.name,
                       'locations': len(fl.location_ids)} for fl in b.floor_ids]
            buildings.append({'id': b.id, 'name': b.name, 'floors': len(b.floor_ids),
                              'floor_list': floors, 'locations': sum(fl['locations'] for fl in floors)})
        return _ok({
            'id': f.id, 'name': f.name, 'address': f.address or None,
            'stats': {
                'buildings': len(f.building_ids),
                'floors': sum(len(b.floor_ids) for b in f.building_ids),
                'locations': len(locs),
                'checkpoints': len(locs.filtered('is_checkpoint')),
                'workorders': WO.search_count([('facility_id', '=', f.id)]),
                'open_workorders': WO.search_count([('facility_id', '=', f.id),
                                                    ('state', 'not in', ('done', 'verified', 'cancelled'))]),
                'assets': env['care.cafm.asset'].sudo().search_count([('facility_id', '=', f.id)]) if 'care.cafm.asset' in env else 0,
            },
            'buildings': buildings,
            'locations': [{'id': l.id, 'name': l.name, 'code': l.code,
                           'type': l.location_type, 'type_label': lt.get(l.location_type, l.location_type or ''),
                           'building': l.building_id.name or None, 'floor': l.floor_id.name or None,
                           'checkpoint': l.is_checkpoint,
                           'wo_count': wo_by_loc.get(l.id, 0),
                           'asset_count': asset_by_loc.get(l.id, 0)} for l in locs],
        })

    @route(API + '/client/location/<int:lid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def location_detail(self, lid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        l = env['care.cafm.location'].sudo().browse(lid).exists()
        if not l or l.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        lt = dict(env['care.cafm.location']._fields['location_type'].selection)
        WO = env['care.cafm.workorder'].sudo()
        wos = WO.search([('location_id', '=', l.id)], order='request_datetime desc', limit=20)
        wst = dict(WO._fields['state'].selection)
        assets = env['care.cafm.asset'].sudo().search([('location_id', '=', l.id)]) if 'care.cafm.asset' in env else env['care.cafm.location'].browse()
        return _ok({
            'id': l.id, 'name': l.name, 'code': l.code,
            'type': l.location_type, 'type_label': lt.get(l.location_type, l.location_type or ''),
            'facility': l.facility_id.name or None, 'building': l.building_id.name or None,
            'floor': l.floor_id.name or None, 'checkpoint': l.is_checkpoint,
            # a scannable QR image the client can view/save without printing
            'qr_image': _abs('/report/barcode/QR/%s?width=320&height=320' % l.code) if l.code else None,
            'stats': {
                'workorders': WO.search_count([('location_id', '=', l.id)]), 'assets': len(assets),
                'open_workorders': WO.search_count([('location_id', '=', l.id),
                                                    ('state', 'not in', ('done', 'verified', 'cancelled'))]),
                'done_workorders': WO.search_count([('location_id', '=', l.id), ('state', 'in', ('done', 'verified'))]),
            },
            'workorders': [{'id': w.id, 'name': w.name, 'title': w.title,
                            'state': w.state, 'state_label': wst.get(w.state, w.state),
                            'date': str(w.request_datetime)[:16] if w.request_datetime else None} for w in wos],
            'assets': [{'id': a.id, 'name': a.name, 'code': a.code or None,
                        'status': a.status} for a in assets[:20]],
        })

    @route('/cafm/location/<int:lid>/qr', type='http', auth='public', methods=['GET'], csrf=False)
    def location_qr_label(self, lid, **kw):
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        l = env['care.cafm.location'].sudo().browse(lid).exists()
        if not l or l.facility_id.id not in self._fac_ids(env):
            return request.not_found()
        report = env.ref('care_cafm.action_report_location_qr').with_user(SUPERUSER_ID)
        pdf = env['ir.actions.report'].sudo()._render_qweb_pdf(report, res_ids=[l.id])[0]
        fname = 'location-qr-%s.pdf' % (l.code or l.id)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(fname).replace('attachment', 'inline')),
        ])
