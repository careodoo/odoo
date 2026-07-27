# -*- coding: utf-8 -*-
"""واجهة تطبيق موديول التدريب (training_management) — كاملة: طلبات التدريب
(training.application) وسطورها (الدورات/المواضيع/المراكز/القاعات) + المراحل
+ المهام المرتبطة، بإحصائيات للهيدر وفلاتر ونماذج إضافة مطابقة للباك ايند."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _d(v):
    return str(v)[:10] if v else None


class TrainingApi(Controller):

    def _has(self, env):
        # صلاحية حقيقية: التدريب للمدير/الأدمن فقط
        return ('training.application' in env) and (
            env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'))

    def _cids(self, env):
        return env.companies.ids or [env.company.id]

    def _app_dict(self, a, full=False):
        st = a.stage_id
        d = {
            'id': a.id, 'name': a.name,
            'application_name': a.application_name,
            'training_name': a.training_name,
            'employee_id': a.employee_id.id if a.employee_id else None,
            'employee': a.employee_id.name if a.employee_id else None,
            'responsible_id': a.responsible_id.id if a.responsible_id else None,
            'responsible': a.responsible_id.name if a.responsible_id else None,
            'project_id': a.project_id.id if a.project_id else None,
            'project': a.project_id.name if a.project_id else None,
            'date': _d(a.date), 'date_start': _d(a.date_start), 'date_end': _d(a.date_end),
            'description': a.description or None,
            'stage_id': st.id if st else None, 'stage': st.name if st else None,
            'is_approved': a.is_approved, 'is_completed': a.is_completed,
            'lines_count': len(a.line_ids), 'task_count': a.task_count,
            'has_sign': bool(a.sign),
        }
        if full:
            d['lines'] = [self._line_dict(l) for l in a.line_ids]
            d['tasks'] = [{
                'id': t.id, 'name': t.name,
                'stage': t.stage_id.name if t.stage_id else None,
                'deadline': _d(t.date_deadline),
                'assignees': t.user_ids.mapped('name'),
            } for t in a.task_ids]
        return d

    def _line_dict(self, l):
        return {
            'id': l.id,
            'course_id': l.course_id.id if l.course_id else None,
            'course': l.course_id.name if l.course_id else None,
            'content': l.content_ids.mapped('name'),
            'content_ids': l.content_ids.ids,
            'description': l.description or None,
            'center_id': l.training_center_id.id if l.training_center_id else None,
            'center': l.training_center_id.name if l.training_center_id else None,
            'room_id': l.training_room_id.id if l.training_room_id else None,
            'room': l.training_room_id.name if l.training_room_id else None,
            'date_start': _d(l.date_start), 'date_end': _d(l.date_end),
        }

    # ---- نظرة عامة + إحصائيات --------------------------------------------
    @route(API + '/training/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'available': False})
        cids = self._cids(env)
        A = env['training.application'].sudo()
        dom = [('company_id', 'in', cids)]
        apps = A.search(dom)
        stages = env['application.stage'].sudo().search([])
        by_stage = [{'id': s.id, 'name': s.name,
                     'count': A.search_count(dom + [('stage_id', '=', s.id)])} for s in stages]
        stats = {
            'applications': len(apps),
            'approved': len(apps.filtered('is_approved')),
            'completed': len(apps.filtered('is_completed')),
            'in_progress': len(apps.filtered(lambda x: not x.is_completed and not x.is_approved)),
            'tasks': sum(apps.mapped('task_count')),
            'centers': env['training.center'].sudo().search_count([]) if 'training.center' in env else 0,
            'rooms': env['training.room'].sudo().search_count([]) if 'training.room' in env else 0,
        }
        return _ok({'available': True, 'stats': stats, 'by_stage': by_stage})

    @route(API + '/training/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def options(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({})
        Emp = env['hr.employee'].sudo().search([], limit=2000)
        return _ok({
            'employees': [{'id': e.id, 'name': e.name} for e in Emp],
            'projects': [{'id': p.id, 'name': p.name} for p in env['project.project'].sudo().search([], limit=1000)],
            'courses': [{'id': c.id, 'name': c.name} for c in env['slide.channel'].sudo().search([], limit=1000)] if 'slide.channel' in env else [],
            'centers': [{'id': c.id, 'name': c.name, 'code': c.code} for c in env['training.center'].sudo().search([])] if 'training.center' in env else [],
            'rooms': [{'id': r.id, 'name': r.name, 'center_id': r.center_id.id} for r in env['training.room'].sudo().search([])] if 'training.room' in env else [],
            'stages': [{'id': s.id, 'name': s.name} for s in env['application.stage'].sudo().search([])],
        })

    @route(API + '/training/course/<int:cid>/contents', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def course_contents(self, cid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'slide.slide' not in env:
            return _ok({'items': []})
        recs = env['slide.slide'].sudo().search([('channel_id', '=', cid)])
        return _ok({'items': [{'id': s.id, 'name': s.name} for s in recs]})

    # ---- قوائم + فلاتر ----------------------------------------------------
    @route(API + '/training/applications', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def applications(self, stage=None, employee=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _ok({'items': []})
        dom = [('company_id', 'in', self._cids(env))]
        if stage:
            dom.append(('stage_id', '=', int(stage)))
        if employee:
            dom.append(('employee_id', '=', int(employee)))
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('training_name', 'ilike', q), ('application_name', 'ilike', q)]
        recs = env['training.application'].sudo().search(dom, order='id desc', limit=300)
        return _ok({'items': [self._app_dict(a) for a in recs]})

    @route(API + '/training/application/<int:aid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def application_detail(self, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        a = env['training.application'].sudo().browse(aid).exists()
        if not a or a.company_id.id not in self._cids(env):
            return _err('غير موجود', 404)
        return _ok(self._app_dict(a, full=True))

    @route(API + '/training/config/<string:kind>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def config_list(self, kind, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        model = {'centers': 'training.center', 'rooms': 'training.room', 'stages': 'application.stage'}.get(kind)
        if not model or model not in env:
            return _ok({'items': []})
        recs = env[model].sudo().search([])
        out = []
        for r in recs:
            row = {'id': r.id, 'name': r.name}
            if 'code' in r._fields:
                row['code'] = r.code
            if model == 'training.room':
                row['center'] = r.center_id.name if r.center_id else None
            if model == 'application.stage':
                row.update({'is_default': r.is_default, 'is_approved': r.is_approved, 'is_completed': r.is_completed})
            out.append(row)
        return _ok({'items': out})

    # ---- إنشاء (حقول مطابقة للباك ايند) -----------------------------------
    @route(API + '/training/application/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def application_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._has(env):
            return _err('غير متاح', 404)
        b = _body() or {}
        req = ('application_name', 'training_name', 'employee_id', 'responsible_id', 'project_id', 'date_start', 'date_end')
        for f in req:
            if not b.get(f):
                return _err('الحقل %s مطلوب' % f, 400)
        vals = {
            'application_name': b['application_name'], 'training_name': b['training_name'],
            'employee_id': int(b['employee_id']), 'responsible_id': int(b['responsible_id']),
            'project_id': int(b['project_id']),
            'date_start': b['date_start'], 'date_end': b['date_end'],
            'description': b.get('description') or False,
        }
        if b.get('date'):
            vals['date'] = b['date']
        if b.get('stage_id'):
            vals['stage_id'] = int(b['stage_id'])
        # السطور (الدورات) — اختياري عند الإنشاء
        lines = b.get('lines') or []
        if lines:
            vals['line_ids'] = [(0, 0, {
                'course_id': int(l['course_id']),
                'content_ids': [(6, 0, [int(x) for x in (l.get('content_ids') or [])])],
                'description': l.get('description') or False,
                'training_center_id': int(l['center_id']) if l.get('center_id') else False,
                'training_room_id': int(l['room_id']) if l.get('room_id') else False,
                'date_start': l.get('date_start') or b['date_start'],
                'date_end': l.get('date_end') or b['date_end'],
            }) for l in lines]
        try:
            rec = env['training.application'].sudo().create(vals)
        except Exception as e:
            return _err('تعذّر إنشاء الطلب: %s' % e, 400)
        return _ok(self._app_dict(rec, full=True))

    @route('/cafm/training/export', type='http', auth='public', methods=['GET'], csrf=False)
    def training_export(self, **kw):
        """تصدير طلبات التدريب إلى Excel."""
        from odoo import _
        from .client_api import _xlsx_response, _report_env
        env = _report_env()
        if not env:
            return request.redirect('/web/login')
        if not self._has(env):
            return request.not_found()
        recs = env['training.application'].sudo().search([('company_id', 'in', self._cids(env))], order='id desc', limit=10000)
        columns = [_('الرقم'), _('اسم التدريب'), _('الموظف'), _('المسؤول'), _('المشروع'),
                   _('المرحلة'), _('من'), _('إلى'), _('الدورات'), _('المهام')]
        rows = [[a.name, a.training_name or '', a.employee_id.name or '', a.responsible_id.name or '',
                 a.project_id.name or '', a.stage_id.name or '', str(a.date_start or ''), str(a.date_end or ''),
                 len(a.line_ids), a.task_count] for a in recs]
        return _xlsx_response(_('طلبات التدريب'), columns, rows, 'training.xlsx', [(_('العدد'), len(recs))])

    @route(API + '/training/application/<int:aid>/create_tasks', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create_tasks(self, aid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = env['training.application'].sudo().browse(aid).exists()
        if not a:
            return _err('غير موجود', 404)
        try:
            a.button_create_tasks()
        except Exception as e:
            return _err('تعذّر إنشاء المهام: %s' % e, 400)
        return _ok(self._app_dict(a, full=True))
