# -*- coding: utf-8 -*-
"""The «My» module — everything about the signed-in user in one place.

A personal self-service hub: who I am, how I'm performing, my requests and their
statuses, and the services I can start. Mirrors Odoo's «My» self-service, native
in the app, for BOTH the management and project-management shells.

All reads are the caller's OWN records (filtered by their employee), so sudo is
safe here — a user can only ever see themselves.
"""
import logging

from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API

_logger = logging.getLogger(__name__)


# Each source = one kind of request the employee can raise. Field names are
# resolved defensively so a model that differs across versions never breaks the
# whole hub.
MY_SOURCES = [
    {'key': 'leaves', 'model': 'hr.leave', 'ar': 'الإجازات', 'en': 'Time off',
     'icon': '🌴', 'draft': ['draft', 'confirm']},
    {'key': 'permissions', 'model': 'permission.request', 'ar': 'الاستئذانات',
     'en': 'Permissions', 'icon': '🕒', 'draft': ['draft', 'submit', 'to_approve']},
    {'key': 'loans', 'model': 'hr.loan', 'ar': 'السلف', 'en': 'Loans',
     'icon': '💵', 'draft': ['draft', 'submit']},
    {'key': 'expenses', 'model': 'hr.expense', 'ar': 'المصروفات',
     'en': 'Expenses', 'icon': '🧾', 'draft': ['draft', 'reported']},
]

# What each request needs to be created — declared once, resolved (options) at
# request time so the app renders a form without knowing the model.
CREATE_SPECS = {
    'leaves': {
        'model': 'hr.leave', 'title': 'طلب إجازة',
        'fields': [
            {'name': 'holiday_status_id', 'label': 'نوع الإجازة', 'type': 'm2o',
             'comodel': 'hr.leave.type', 'required': True},
            {'name': 'request_date_from', 'label': 'من تاريخ', 'type': 'date', 'required': True},
            {'name': 'request_date_to', 'label': 'إلى تاريخ', 'type': 'date', 'required': True},
            {'name': 'name', 'label': 'السبب', 'type': 'text'},
        ],
    },
    'permissions': {
        'model': 'permission.request', 'title': 'طلب استئذان',
        'fields': [
            {'name': 'type', 'label': 'النوع', 'type': 'selection', 'required': True},
            {'name': 'permission_from', 'label': 'من (وقت)', 'type': 'datetime', 'required': True},
            {'name': 'permission_hours', 'label': 'عدد الساعات', 'type': 'integer', 'required': True},
            {'name': 'reason', 'label': 'السبب', 'type': 'text', 'required': True},
        ],
    },
    'loans': {
        'model': 'hr.loan', 'title': 'طلب سلفة',
        'fields': [
            {'name': 'loan_amount', 'label': 'المبلغ', 'type': 'float', 'required': True},
            {'name': 'installment', 'label': 'عدد الأقساط', 'type': 'integer'},
            {'name': 'payment_date', 'label': 'تاريخ أول قسط', 'type': 'date'},
            {'name': 'name', 'label': 'ملاحظة', 'type': 'char'},
        ],
    },
    'expenses': {
        'model': 'hr.expense', 'title': 'مصروف جديد',
        'fields': [
            {'name': 'name', 'label': 'البيان', 'type': 'char', 'required': True},
            {'name': 'product_id', 'label': 'فئة المصروف', 'type': 'm2o',
             'comodel': 'product.product', 'domain': [('can_be_expensed', '=', True)],
             'required': True},
            {'name': 'total_amount', 'label': 'المبلغ', 'type': 'float', 'required': True},
            {'name': 'date', 'label': 'التاريخ', 'type': 'date'},
        ],
    },
}


# Services the user can launch (the app maps each key to its create flow).
MY_SERVICES = [
    {'key': 'profile', 'ar': 'بياناتي', 'en': 'My data', 'icon': '🪪'},
    {'key': 'leave', 'ar': 'طلب إجازة', 'en': 'Request time off', 'icon': '🌴'},
    {'key': 'permission', 'ar': 'استئذان', 'en': 'Permission', 'icon': '🕒'},
    {'key': 'loan', 'ar': 'طلب سلفة', 'en': 'Request a loan', 'icon': '💵'},
    {'key': 'expense', 'ar': 'مصروف', 'en': 'Expense', 'icon': '🧾'},
    {'key': 'timesheet', 'ar': 'ورقة وقت', 'en': 'Timesheet', 'icon': '⏱️'},
    {'key': 'attendance', 'ar': 'الحضور', 'en': 'Attendance', 'icon': '📍'},
]


class MyApi(Controller):

    def _emp(self, env):
        u = env.user
        return u.employee_id if 'employee_id' in u._fields and u.employee_id else None

    def _state_label(self, rec, model):
        if 'state' not in model._fields:
            return None
        f = model._fields['state']
        v = rec.state
        try:
            return dict(f._description_selection(rec.env)).get(v, v)
        except Exception:
            return v

    def _source(self, key):
        return next((s for s in MY_SOURCES if s['key'] == key), None)

    def _my_requests(self, env, emp):
        out = []
        for src in MY_SOURCES:
            model = src['model']
            if model not in env:
                continue
            M = env[model].sudo()
            ef = 'employee_id' if 'employee_id' in M._fields else (
                'employee_ids' if 'employee_ids' in M._fields else None)
            if not ef:
                continue
            try:
                dom = [(ef, 'in', emp.ids)] if ef == 'employee_ids' else [(ef, '=', emp.id)]
                recs = M.search(dom, order='id desc', limit=12)
            except Exception:
                continue
            draft = set(src.get('draft') or ['draft'])
            has_state = 'state' in M._fields
            for r in recs:
                st = r.state if has_state else None
                amount = None
                for af in ('amount', 'total_amount', 'loan_amount', 'number_of_days'):
                    if af in M._fields and r[af]:
                        amount = round(r[af], 2)
                        break
                out.append({
                    'source': src['key'], 'ar': src['ar'], 'en': src['en'], 'icon': src['icon'],
                    'id': r.id,
                    'title': r.display_name,
                    'state': self._state_label(r, M),
                    'raw_state': st,
                    'amount': amount,
                    'date': str(r.create_date)[:10] if 'create_date' in M._fields and r.create_date else None,
                    'can_edit': bool(st in draft) if st is not None else True,
                    'can_delete': bool(st in draft) if st is not None else True,
                })
        return out

    @route(API + '/my/hub', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def my_hub(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        u = env.user
        emp = self._emp(env)

        def _count(model, dom):
            try:
                return env[model].search_count(dom)
            except Exception:
                return None

        # ---- performance-ish personal stats
        stats = []
        tasks = _count('project.task', [('user_ids', 'in', u.id),
                                        ('state', 'not in', ('1_done', '1_canceled'))])
        if tasks is not None:
            stats.append({'key': 'tasks', 'ar': 'مهامي', 'en': 'Tasks',
                          'value': tasks, 'icon': '📋'})
        if emp:
            my_leaves = _count('hr.leave', [('employee_id', '=', emp.id)])
            if my_leaves is not None:
                stats.append({'key': 'leaves', 'ar': 'إجازاتي', 'en': 'Leaves',
                              'value': my_leaves, 'icon': '🌴'})
            perms = _count('permission.request', [('employee_id', '=', emp.id)])
            if perms is not None:
                stats.append({'key': 'permissions', 'ar': 'استئذاناتي', 'en': 'Permits',
                              'value': perms, 'icon': '🕒'})
            import datetime as _dt
            m0 = _dt.date.today().replace(day=1)
            att = _count('hr.attendance', [('employee_id', '=', emp.id), ('check_in', '>=', str(m0) + ' 00:00:00')])
            if att is not None:
                stats.append({'key': 'attendance', 'ar': 'حضوري', 'en': 'Attend.',
                              'value': att, 'icon': '⏱️'})
            loans = _count('care.loan', [('employee_id', '=', emp.id)])
            if loans:
                stats.append({'key': 'loans', 'ar': 'سُلَفي', 'en': 'Loans',
                              'value': loans, 'icon': '💰'})
        pending_mine = 0
        requests = self._my_requests(env, emp) if emp else []
        pending_mine = sum(1 for r in requests if (r['raw_state'] in (None, 'draft', 'confirm', 'submit')))
        stats.append({'key': 'pending', 'ar': 'قيد المعالجة', 'en': 'Pending',
                      'value': pending_mine, 'icon': '⏳'})
        if u.has_group('base.group_erp_manager'):
            awaiting = 0
            for model, dom in (('hr.leave', [('state', 'in', ('confirm', 'validate1'))]),
                               ('hr.expense.sheet', [('state', '=', 'submit')])):
                c = _count(model, dom)
                if c:
                    awaiting += c
            stats.append({'key': 'approvals', 'ar': 'للاعتماد', 'en': 'Approvals',
                          'value': awaiting, 'icon': '✅'})

        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        # base64 avatar — /web/image needs a web session the token app doesn't
        # have, so it rendered blank; inline the small image instead.
        _img = (u.image_256 or u.image_128) if 'image_256' in u._fields else None
        return _ok({
            'profile': {
                'name': u.name,
                'login': u.login,
                'job': (emp.job_title if emp else None) or (u.function if 'function' in u._fields else None),
                'department': emp.department_id.display_name if emp and emp.department_id else None,
                'work_email': (emp.work_email if emp else None) or u.email,
                'work_phone': emp.work_phone if emp else None,
                'avatar_b64': _img.decode() if _img else None,
                'avatar_url': '%s/web/image/res.users/%s/avatar_256' % (base, u.id),
                'employee_id': emp.id if emp else None,
                'is_manager': u.has_group('base.group_erp_manager'),
            },
            'stats': stats,
            'services': MY_SERVICES,
            'requests': sorted(requests, key=lambda r: r['date'] or '', reverse=True)[:30],
        })

    @route(API + '/my/<string:source>/<int:rid>/delete', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def my_delete(self, source, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        src = self._source(source)
        if not src:
            return _err('نوع غير معروف', 404)
        emp = self._emp(env)
        if not emp:
            return _err('لا يوجد ملف موظف', 403)
        M = env[src['model']].sudo()
        ef = 'employee_id' if 'employee_id' in M._fields else None
        rec = M.browse(rid).exists()
        if not rec or (ef and rec[ef].id != emp.id):
            return _err('غير موجود أو ليس سجلّك', 403)
        st = rec.state if 'state' in M._fields else None
        if st is not None and st not in set(src.get('draft') or ['draft']):
            return _err('لا يمكن حذف سجل غير مسودة', 422)
        try:
            rec.unlink()
        except Exception as e:
            return _err(str(e) or 'تعذّر الحذف', 422)
        return _ok({'deleted': rid})

    # ---- self-service create forms ---------------------------------------
    @route(API + '/my/<string:source>/meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def my_meta(self, source, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = CREATE_SPECS.get(source)
        if not spec or spec['model'] not in env:
            return _err('غير متاح', 404)
        M = env[spec['model']]
        fields = []
        for f in spec['fields']:
            if f['name'] not in M._fields:
                continue
            d = dict(f)
            if f['type'] == 'm2o':
                try:
                    # For leave types, annotate each with the caller's remaining
                    # balance so they don't pick a type they can't actually use.
                    if f.get('comodel') == 'hr.leave.type' and source == 'leaves':
                        emp = self._emp(env)
                        opts = []
                        for lt in env['hr.leave.type'].sudo().search(f.get('domain') or [], limit=200):
                            label = lt.display_name
                            if emp:
                                try:
                                    days = lt.with_context(employee_id=emp.id).sudo().virtual_remaining_leaves
                                    req = lt.requires_allocation == 'yes' if 'requires_allocation' in lt._fields else False
                                    if req:
                                        label = '%s (%s يوم متبقٍ)' % (lt.display_name, int(days))
                                except Exception:
                                    pass
                            opts.append({'v': lt.id, 'l': label})
                        d['options'] = opts
                    else:
                        d['options'] = [{'v': r.id, 'l': r.display_name}
                                        for r in env[f['comodel']].sudo().search(
                                            f.get('domain') or [], limit=200)]
                except Exception:
                    d['options'] = []
                d.pop('domain', None)  # server-only; never leak to the client
            elif f['type'] == 'selection':
                try:
                    d['options'] = [{'v': v, 'l': l}
                                    for v, l in M._fields[f['name']]._description_selection(env)]
                except Exception:
                    d['options'] = []
            fields.append(d)
        return _ok({'source': source, 'title': spec['title'], 'fields': fields})

    @route(API + '/my/<string:source>/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def my_create(self, source, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = CREATE_SPECS.get(source)
        if not spec or spec['model'] not in env:
            return _err('غير متاح', 404)
        emp = self._emp(env)
        if not emp:
            return _err('لا يوجد ملف موظف مرتبط بحسابك', 403)
        M = env[spec['model']].sudo()
        b = _body() or {}
        vals = {'employee_id': emp.id}
        if 'department_id' in M._fields and emp.department_id:
            vals['department_id'] = emp.department_id.id
        for f in spec['fields']:
            name = f['name']
            if name not in M._fields or b.get(name) in (None, ''):
                if f.get('required') and name not in vals:
                    return _err('حقل مطلوب: %s' % f['label'], 422)
                continue
            val = b[name]
            t = f['type']
            if t == 'm2o':
                vals[name] = int(val)
            elif t in ('float',):
                vals[name] = float(val)
            elif t == 'integer':
                vals[name] = int(val)
            else:
                vals[name] = val
        # hr.leave also wants the datetime pair; derive from the request dates.
        if source == 'leaves':
            if b.get('request_date_from'):
                vals.setdefault('date_from', '%s 00:00:00' % b['request_date_from'])
            if b.get('request_date_to'):
                vals.setdefault('date_to', '%s 23:59:59' % b['request_date_to'])
        try:
            rec = M.create(vals)
        except Exception as e:
            return _err(self._friendly(str(e)), 422)
        return _ok({'id': rec.id, 'title': rec.display_name,
                    'state': rec.state if 'state' in M._fields else None})

    def _friendly(self, msg):
        """Turn Odoo's raw validation text into a clear Arabic sentence."""
        m = (msg or '').strip()
        low = m.lower()
        if 'no valid allocation' in low or 'allocation to cover' in low:
            return 'لا يوجد رصيد إجازات معتمد لهذا النوع. اختر نوعًا آخر أو راجع الموارد البشرية لاعتماد رصيدك.'
        if 'overlap' in low or 'double-book' in low or 'already booked' in low:
            return 'لديك طلب إجازة يتداخل مع هذه الفترة. اختر تواريخ أخرى.'
        if 'not sufficient' in low or 'remaining' in low and 'not' in low:
            return 'رصيدك من هذا النوع لا يكفي للفترة المطلوبة.'
        if 'start date' in low or 'end date' in low:
            return 'حدّد تاريخ البداية والنهاية بشكل صحيح.'
        return m or 'تعذّر إنشاء الطلب'

    # ---- one request in full detail (clickable card) ---------------------
    @route(API + '/my/<string:source>/<int:rid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def my_detail(self, source, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        src = self._source(source)
        if not src or src['model'] not in env:
            return _err('نوع غير معروف', 404)
        emp = self._emp(env)
        M = env[src['model']].sudo()
        rec = M.browse(int(rid)).exists()
        ef = 'employee_id' if 'employee_id' in M._fields else None
        if not rec or (emp and ef and rec[ef].id != emp.id):
            return _err('غير موجود أو ليس سجلّك', 403)
        # human field list (label → value), tolerant of model differences
        pairs = []

        def _add(label, fname):
            if fname not in M._fields or not rec[fname]:
                return
            f = M._fields[fname]
            v = rec[fname]
            if f.type == 'many2one':
                v = v.display_name
            elif f.type == 'selection':
                try:
                    v = dict(f._description_selection(env)).get(v, v)
                except Exception:
                    pass
            elif f.type in ('date', 'datetime'):
                v = str(v)
            elif f.type == 'boolean':
                v = 'نعم' if v else 'لا'
            pairs.append({'label': label, 'value': str(v)})

        spec = {
            'leaves': [('نوع الإجازة', 'holiday_status_id'), ('من', 'request_date_from'),
                       ('إلى', 'request_date_to'), ('عدد الأيام', 'number_of_days'),
                       ('السبب', 'name'), ('الحالة', 'state')],
            'permissions': [('النوع', 'type'), ('من', 'permission_from'),
                            ('الساعات', 'permission_hours'), ('السبب', 'reason'), ('الحالة', 'state')],
            'loans': [('المبلغ', 'loan_amount'), ('الأقساط', 'installment'),
                      ('المتبقي', 'balance_amount'), ('أول قسط', 'payment_date'),
                      ('ملاحظة', 'name'), ('الحالة', 'state')],
            'expenses': [('البيان', 'name'), ('الفئة', 'product_id'), ('المبلغ', 'total_amount'),
                         ('التاريخ', 'date'), ('الحالة', 'state')],
        }.get(source, [])
        for label, fname in spec:
            _add(label, fname)

        # a printable report where one exists (leaves reuse the HR leave report)
        report_path = None
        if source == 'leaves':
            for cand in ('care_hr.leave_request_report', 'care_hr.leave_request_header_report'):
                if env.ref(cand, raise_if_not_found=False):
                    report_path = '/api/v1/my/leaves/%s/report' % rec.id
                    break
        return _ok({
            'source': source, 'id': rec.id, 'title': rec.display_name,
            'state': self._state_label(rec, M), 'icon': src['icon'],
            'ar': src['ar'], 'en': src['en'],
            'fields': pairs, 'report_path': report_path,
            'can_delete': bool((rec.state if 'state' in M._fields else None)
                               in set(src.get('draft') or ['draft'])),
        })

    @route(API + '/my/leaves/<int:rid>/report', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def my_leave_report(self, rid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        emp = self._emp(env)
        leave = env['hr.leave'].sudo().browse(int(rid)).exists()
        if not leave or (emp and leave.employee_id.id != emp.id):
            return request.make_response('لا صلاحية', status=403)
        rep = None
        for cand in ('care_hr.leave_request_report', 'care_hr.leave_request_header_report'):
            if env.ref(cand, raise_if_not_found=False):
                rep = cand
                break
        if not rep:
            return request.make_response('لا يوجد تقرير', status=404)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(rep, [leave.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="leave-%s.pdf"' % rid)])
