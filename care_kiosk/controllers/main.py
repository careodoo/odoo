# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request


class CareKioskController(http.Controller):

    # ---------- helpers ----------
    def _kiosk(self, kiosk_id):
        return request.env['care.kiosk'].sudo().browse(kiosk_id).exists()

    def _skey(self, kiosk_id):
        return 'care_kiosk_%s' % kiosk_id

    def _session_employee(self, kiosk):
        """Return the employee bound to the current kiosk session if still
        within the inactivity timeout, else False (and clears it)."""
        data = request.session.get(self._skey(kiosk.id))
        if not data:
            return False
        emp_id, ts = data.get('emp'), data.get('ts')
        try:
            last = datetime.fromisoformat(ts)
        except Exception:
            return False
        if (fields.Datetime.now() - last).total_seconds() > max(kiosk.timeout_seconds, 30):
            request.session.pop(self._skey(kiosk.id), None)
            return False
        emp = request.env['hr.employee'].sudo().browse(emp_id).exists()
        if emp:
            # refresh activity timestamp
            request.session[self._skey(kiosk.id)] = {
                'emp': emp.id, 'ts': fields.Datetime.now().isoformat()}
        return emp

    # ---------- page ----------
    @http.route('/care/kiosk/<int:kiosk_id>', type='http', auth='public',
                website=True, sitemap=False)
    def kiosk_page(self, kiosk_id, **kw):
        kiosk = self._kiosk(kiosk_id)
        if not kiosk or not kiosk.active:
            return request.not_found()
        return request.render('care_kiosk.kiosk_page', {'kiosk': kiosk})

    # ---------- identify (poll after fingerprint scan) ----------
    @http.route('/care/kiosk/<int:kiosk_id>/identify', type='json', auth='public')
    def kiosk_identify(self, kiosk_id, **kw):
        kiosk = self._kiosk(kiosk_id)
        if not kiosk or not kiosk.active:
            return {'found': False}
        emp = self._session_employee(kiosk)
        if not emp:
            emp = kiosk._find_scanned_employee()
            if not emp:
                return {'found': False}
            request.session[self._skey(kiosk.id)] = {
                'emp': emp.id, 'ts': fields.Datetime.now().isoformat()}
        return {
            'found': True,
            'name': emp.name,
            'job': emp.job_id.name or '',
            'department': emp.department_id.name or '',
            'image': '/web/image/hr.employee/%s/image_128' % emp.id,
        }

    # ---------- panels (read-only, scoped to the scanned worker) ----------
    @http.route('/care/kiosk/<int:kiosk_id>/panel', type='json', auth='public')
    def kiosk_panel(self, kiosk_id, panel=None, **kw):
        kiosk = self._kiosk(kiosk_id)
        emp = kiosk and self._session_employee(kiosk)
        if not emp:
            return {'ok': False, 'reason': 'no_session'}
        env = request.env
        if panel == 'payslips' and 'hr.payslip' in env:
            slips = env['hr.payslip'].sudo().search(
                [('employee_id', '=', emp.id), ('state', 'in', ('done', 'paid'))],
                order='date_to desc', limit=12)
            return {'ok': True, 'items': [
                {'name': s.number or s.name, 'period': str(s.date_to or ''),
                 'net': round(s.net_wage, 3) if 'net_wage' in s._fields else 0.0}
                for s in slips]}
        if panel == 'docs' and 'care.dms.document' in env:
            docs = env['care.dms.document'].sudo().search(
                [('employee_id', '=', emp.id), ('disposed', '=', False), ('is_current', '=', True)],
                order='issue_date desc', limit=20)
            return {'ok': True, 'items': [
                {'name': d.name, 'category': d.category_id.name or '',
                 'date': str(d.issue_date or '')} for d in docs]}
        if panel == 'announcements' and 'care.announcement' in env:
            anns = env['care.announcement'].sudo().search([], order='id desc', limit=10)
            return {'ok': True, 'items': [
                {'name': a.name, 'body': (a.body or a.name) if 'body' in a._fields else a.name}
                for a in anns]}
        return {'ok': True, 'items': []}

    # ---------- requests (create as the scanned worker) ----------
    @http.route('/care/kiosk/<int:kiosk_id>/request', type='json', auth='public')
    def kiosk_request(self, kiosk_id, kind=None, note=None, **kw):
        kiosk = self._kiosk(kiosk_id)
        emp = kiosk and self._session_employee(kiosk)
        if not emp:
            return {'ok': False, 'reason': 'no_session'}
        env = request.env
        note = (note or '').strip()[:2000]
        if kind == 'grievance' and 'care.grievance' in env:
            rec = env['care.grievance'].sudo().create({
                'employee_id': emp.id,
                'description': note or _('طلب عبر الكشك'),
            })
            return {'ok': True, 'ref': rec.display_name}
        if kind == 'leave':
            # lightweight leave request as a grievance-style note if no leave
            # type resolution here; recorded on the employee for HR follow-up
            lt = env['hr.leave.type'].sudo().search([], limit=1)
            if lt:
                today = fields.Date.today()
                leave = env['hr.leave'].sudo().create({
                    'employee_id': emp.id,
                    'holiday_status_id': lt.id,
                    'request_date_from': today,
                    'request_date_to': today,
                    'name': note or _('طلب إجازة عبر الكشك'),
                })
                return {'ok': True, 'ref': leave.display_name}
        return {'ok': False, 'reason': 'unsupported'}

    @http.route('/care/kiosk/<int:kiosk_id>/logout', type='json', auth='public')
    def kiosk_logout(self, kiosk_id, **kw):
        request.session.pop(self._skey(kiosk_id), None)
        return {'ok': True}
