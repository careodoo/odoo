# -*- coding: utf-8 -*-
# نقاط نهاية الشكاوى التأديبية للتطبيق:
#  - ملف الموظف: العامل يرى شكاواه (surface ملف الموظف بالتطبيق).
#  - مدير المشروع: قائمة شكاواه + تقديم شكوى (مرآة لبوابة /my/pm/p/<id>/discipline).
# الموديل اختياري: إن لم يكن care_discipline مُثبّتًا تُرجِع النقاط 404 بسلاسة.
from odoo import http
from odoo.http import route
from .api import _auth, _ok, _err, _body, API


def _complaint_row(env, r):
    sel = lambda f: dict(r._fields[f]._description_selection(env)).get(r[f], '')
    return {
        'id': r.id, 'name': r.name,
        'employee': r.employee_id.name,
        'category': r.category_id.name or '',
        'severity': sel('severity'), 'severity_key': r.severity,
        'incident_date': str(r.incident_date or ''),
        'state': r.state, 'state_label': sel('state'),
        'penalty': sel('penalty_type') if r.penalty_type else '',
        'law_article': r.law_article_id.display_name or '',
        'description': r.description or '',
        'rejected': r.state == 'rejected',
    }


def _emp_of(env):
    return env['hr.employee'].sudo().search([('user_id', '=', env.user.id)], limit=1)


def _pm_project(env, pid):
    return env['project.project'].sudo().search([
        ('id', '=', int(pid)),
        '|', ('project_manager_id', '=', env.user.id),
        ('portal_user_ids', 'in', env.user.ids)], limit=1) or None


class DisciplineMobileAPI(http.Controller):

    # ----- ملف الموظف: شكاوى العامل نفسه -----
    @route(API + '/discipline/my', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def disc_my(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.complaint' not in env:
            return _err('غير متاح', 404)
        emp = _emp_of(env)
        if not emp:
            return _ok({'count': 0, 'rows': []})
        recs = env['care.complaint'].sudo().search(
            [('employee_id', '=', emp.id)], order='create_date desc', limit=200)
        return _ok({'count': len(recs), 'rows': [_complaint_row(env, r) for r in recs]})

    # ----- مدير المشروع: قائمة شكاواه + بيانات النموذج -----
    @route(API + '/pms/discipline/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def disc_pm_list(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.complaint' not in env:
            return _err('غير متاح', 404)
        proj = _pm_project(env, pid)
        if not proj:
            return _err('لا صلاحية على هذا المشروع', 403)
        dept = proj.pms_department_id
        dom = [('complainant_id', '=', env.user.id)]
        if dept:
            dom += [('employee_id.department_id', 'child_of', dept.id)]
        recs = env['care.complaint'].sudo().search(dom, order='create_date desc', limit=200)
        workers = env['hr.employee'].sudo().search(
            [('department_id', 'child_of', dept.id)], order='name') if dept else env['hr.employee'].browse()
        cats = env['care.complaint.category'].sudo().search([('active', '=', True)])
        return _ok({
            'project': {'id': proj.id, 'name': proj.name},
            'rows': [_complaint_row(env, r) for r in recs],
            'workers': [{'id': w.id, 'name': w.name, 'badge': w.barcode or ''} for w in workers],
            'categories': [{'id': c.id, 'name': c.name} for c in cats],
            'severities': [{'key': 'low', 'label': 'بسيطة'},
                           {'key': 'medium', 'label': 'متوسّطة'},
                           {'key': 'high', 'label': 'جسيمة'}],
        })

    # ----- مدير المشروع: تقديم شكوى -----
    @route(API + '/pms/discipline/<int:pid>/file', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def disc_pm_file(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.complaint' not in env:
            return _err('غير متاح', 404)
        proj = _pm_project(env, pid)
        if not proj:
            return _err('لا صلاحية على هذا المشروع', 403)
        body = _body() or {}
        try:
            emp = int(body.get('employee_id') or 0)
            cat = int(body.get('category_id') or 0)
            desc = (body.get('description') or '').strip()
            if not (emp and cat and desc):
                return _err('أكمل العامل والنوع والوصف', 400)
            dept = proj.pms_department_id
            scope_ok = dept and env['hr.employee'].sudo().search_count(
                [('id', '=', emp), ('department_id', 'child_of', dept.id)])
            if not scope_ok:
                return _err('العامل خارج نطاق مشروعك', 403)
            vals = {'employee_id': emp, 'category_id': cat, 'description': desc,
                    'severity': body.get('severity') or 'medium',
                    'complainant_ack': bool(body.get('ack'))}
            if body.get('incident_date'):
                vals['incident_date'] = body['incident_date']
            if body.get('witnesses'):
                vals['witnesses'] = body['witnesses']
            # يُنشأ باسم المستخدم (المدير) ليكون مُقدّم الشكوى، ثم يُقدَّم
            c = env['care.complaint'].create(vals)
            c.action_submit()
            return _ok({'id': c.id, 'name': c.name, 'state': c.state})
        except Exception as e:
            return _err(str(e), 400)
