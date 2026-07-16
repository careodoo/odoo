# -*- coding: utf-8 -*-
"""Native MANAGEMENT API — the company's back-office systems in the app.

The management interface used to be a launcher of /web links, i.e. web pages
inside a WebView. These endpoints expose the same systems as real data so the
app can render them natively.

Security model: every read runs with the CALLER's env — never sudo — so Odoo's
own record rules and ACLs decide what each user may see. A system that raises
AccessError is simply reported as unavailable to that user.
"""
import re

from odoo.exceptions import AccessError
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, API


# Never surface these, whatever Odoo would technically allow the caller to read.
SENSITIVE_RE = re.compile(
    r'salary|wage|bank|acc_number|iban|ssnid|sinid|passport|identification|'
    r'private|pin$|barcode|birthday|children|marital|gender|emergency|'
    r'km_home|permit|visa|study_|certificate|country_of_birth|place_of_birth|'
    r'password|token|secret', re.I)


def _d(v):
    return v and str(v) or None


# key -> spec. `fields` are what the list shows; `search` drives the query.
# Only whitelisted models are reachable — never a model name from the client.
REGISTRY = {
    'purchases': {
        'model': 'purchase.order', 'icon': '🛒', 'ar': 'المشتريات', 'en': 'Purchases',
        'order': 'date_order desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'date_order', 'state': 'state',
    },
    'sales': {
        'model': 'sale.order', 'icon': '💰', 'ar': 'المبيعات', 'en': 'Sales',
        'order': 'date_order desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'date_order', 'state': 'state',
    },
    'tenders': {
        'model': 'purchase.tender', 'icon': '📑', 'ar': 'المناقصات', 'en': 'Tenders',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': 'state',
    },
    'proposals': {
        'model': 'proposal.proposal', 'icon': '📊', 'ar': 'عروض الأسعار', 'en': 'Proposals',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': 'state',
    },
    'employees': {
        'model': 'hr.employee', 'icon': '👥', 'ar': 'الموظفون', 'en': 'Employees',
        'order': 'name', 'search': ['name', 'work_email', 'job_title'],
        'title': 'name', 'subtitle': 'job_title', 'amount': None,
        'date': None, 'state': None, 'image': 'avatar_128',
        # WORK data only. Never the private HR block (identification_id/civil ID,
        # birthday, marital, gender, permits, bank) — a directory in a phone app
        # has no business carrying it, even for users Odoo would let read it.
        'fields': ['name', 'job_title', 'department_id', 'parent_id', 'coach_id',
                   'work_phone', 'mobile_phone', 'work_email', 'work_location_id',
                   'company_id', 'resource_calendar_id', 'employee_type'],
    },
    'documents': {
        'model': 'care.dms.document', 'icon': '📁', 'ar': 'المستندات', 'en': 'Documents',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': None, 'amount': None,
        'date': 'create_date', 'state': 'state',
    },
    'experience': {
        'model': 'care.experience', 'icon': '🏆', 'ar': 'الخبرات', 'en': 'Experience',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': 'state',
    },
    'fleet': {
        'model': 'fleet.vehicle', 'icon': '🚗', 'ar': 'الأسطول', 'en': 'Fleet',
        'order': 'id desc', 'search': ['name', 'license_plate'],
        'title': 'name', 'subtitle': 'license_plate', 'amount': None,
        'date': None, 'state': 'state_id',
    },
    'crm': {
        'model': 'crm.lead', 'icon': '🎯', 'ar': 'الفرص', 'en': 'CRM',
        'order': 'id desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'expected_revenue',
        'date': 'create_date', 'state': 'stage_id',
    },
    'invoices': {
        'model': 'account.move', 'icon': '🧾', 'ar': 'الفواتير', 'en': 'Invoices',
        'order': 'invoice_date desc, id desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'invoice_date', 'state': 'state',
        'domain': [('move_type', 'in', ('out_invoice', 'in_invoice'))],
    },
    'projects': {
        'model': 'project.project', 'icon': '🏗️', 'ar': 'المشاريع', 'en': 'Projects',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': None,
    },
}


# Whitelisted workflow actions per system. A client sends an action KEY, never a
# method name, and the method must appear here — arbitrary calls are impossible.
# `states` gates when the button shows; empty = always. Execution uses the
# caller's env, so Odoo still refuses if they lack write access.
ACTIONS = {
    'purchases': [
        {'key': 'confirm', 'method': 'button_confirm', 'ar': 'تأكيد الطلب', 'en': 'Confirm order',
         'states': ['draft', 'sent', 'to approve'], 'style': 'primary'},
        {'key': 'approve', 'method': 'button_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['to approve'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'button_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'sent', 'to approve', 'purchase'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel'], 'style': 'plain'},
    ],
    'sales': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'تأكيد', 'en': 'Confirm',
         'states': ['draft', 'sent'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'action_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'sent', 'sale'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel'], 'style': 'plain'},
    ],
    'invoices': [
        {'key': 'post', 'method': 'action_post', 'ar': 'ترحيل القيد', 'en': 'Post',
         'states': ['draft'], 'style': 'primary', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['posted', 'cancel'], 'style': 'plain'},
    ],
    'crm': [
        {'key': 'won', 'method': 'action_set_won_rainbowman', 'ar': 'كسبت', 'en': 'Mark won',
         'states': [], 'style': 'primary'},
        {'key': 'lost', 'method': 'action_set_lost', 'ar': 'خسرت', 'en': 'Mark lost',
         'states': [], 'style': 'danger', 'confirm': True},
    ],
    'proposals': [
        {'key': 'submit', 'method': 'button_submit', 'ar': 'تقديم', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'button_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['submit', 'waiting'], 'style': 'primary'},
        {'key': 'reject', 'method': 'button_reject', 'ar': 'رفض', 'en': 'Reject',
         'states': ['submit', 'waiting'], 'style': 'danger', 'confirm': True},
        {'key': 'won', 'method': 'button_won', 'ar': '🏆 فزنا', 'en': 'Won',
         'states': ['approve', 'submit'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'button_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'submit', 'waiting', 'approve'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel', 'reject'], 'style': 'plain'},
    ],
    'tenders': [
        {'key': 'under_study', 'method': 'action_set_under_study', 'ar': 'قيد الدراسة', 'en': 'Under study',
         'states': ['new'], 'style': 'primary'},
        {'key': 'interested', 'method': 'action_set_interested', 'ar': 'مهتمون', 'en': 'Interested',
         'states': ['new', 'under_study', 'docs_purchased'], 'style': 'primary'},
        {'key': 'preparing', 'method': 'action_set_preparing', 'ar': 'جارٍ التحضير', 'en': 'Preparing',
         'states': ['interested', 'docs_purchased', 'under_study'], 'style': 'primary'},
        {'key': 'participated', 'method': 'action_set_participated', 'ar': 'تم التقديم', 'en': 'Submitted',
         'states': ['preparing'], 'style': 'primary'},
        {'key': 'winner', 'method': 'action_set_winner', 'ar': '🏆 فزنا', 'en': 'Won',
         'states': ['participated'], 'style': 'primary'},
        {'key': 'lost', 'method': 'action_set_lost', 'ar': 'خسرنا', 'en': 'Lost',
         'states': ['participated'], 'style': 'danger', 'confirm': True},
        {'key': 'cancelled', 'method': 'action_set_cancelled', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': [], 'style': 'danger', 'confirm': True},
    ],
}


class ManagementApi(Controller):

    def _spec(self, key):
        return REGISTRY.get(key)

    def _raw_state(self, rec, spec):
        """The stored state value (not its label), for gating actions."""
        f = spec.get('state')
        if not f or f not in rec._fields:
            return None
        v = rec[f]
        return v.id if rec._fields[f].type == 'many2one' else v

    def _actions_for(self, env, rec, key, spec):
        """Actions available on THIS record for THIS user."""
        out = []
        defs = ACTIONS.get(key) or []
        if not defs:
            return out
        # no write access → offer nothing rather than fail on tap
        try:
            env[spec['model']].check_access_rights('write', raise_exception=True)
        except Exception:
            return out
        st = self._raw_state(rec, spec)
        for a in defs:
            if not hasattr(rec, a['method']):
                continue
            if a['states'] and st not in a['states']:
                continue
            out.append({'key': a['key'], 'ar': a['ar'], 'en': a['en'],
                        'style': a.get('style', 'plain'), 'confirm': bool(a.get('confirm'))})
        return out

    def _val(self, rec, fname):
        """Read a field for display, tolerating missing fields across versions."""
        if not fname or fname not in rec._fields:
            return None
        v = rec[fname]
        f = rec._fields[fname]
        if f.type == 'many2one':
            return v.display_name if v else None
        if f.type == 'selection':
            try:
                return dict(f._description_selection(rec.env)).get(v, v)
            except Exception:
                return v
        if f.type in ('date', 'datetime'):
            return _d(v)
        if f.type in ('float', 'monetary'):
            return round(v or 0, 2)
        return v if v not in (False, None) else None

    def _can(self, env, spec):
        """Whether this user may read the model at all (Odoo decides)."""
        model = spec['model']
        if model not in env:
            return False
        try:
            env[model].check_access_rights('read', raise_exception=True)
            return True
        except (AccessError, Exception):
            return False

    # ---- which systems does THIS user actually have? ----------------------
    @route(API + '/management/apps', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_apps(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        out = []
        for key, spec in REGISTRY.items():
            if not self._can(env, spec):
                continue
            try:
                count = env[spec['model']].search_count(spec.get('domain') or [])
            except Exception:
                continue
            out.append({'key': key, 'icon': spec['icon'], 'ar': spec['ar'], 'en': spec['en'],
                        'count': count})
        return _ok(out)

    # ---- list ------------------------------------------------------------
    @route(API + '/management/<string:key>/list', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_list(self, key, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على هذا النظام', 403)
        Model = env[spec['model']]  # no sudo → record rules apply
        dom = list(spec.get('domain') or [])
        q = (kw.get('q') or '').strip()
        if q and spec.get('search'):
            sub = []
            for f in spec['search']:
                root = f.split('.')[0]
                if root in Model._fields:
                    sub.append((f, 'ilike', q))
            if sub:
                dom += ['|'] * (len(sub) - 1) + sub
        try:
            limit = min(int(kw.get('limit') or 60), 200)
        except Exception:
            limit = 60
        try:
            recs = Model.search(dom, order=spec.get('order') or 'id desc', limit=limit)
        except Exception:
            recs = Model.search(dom, limit=limit)
        rows = []
        for r in recs:
            rows.append({
                'id': r.id,
                'title': self._val(r, spec['title']) or r.display_name,
                'subtitle': self._val(r, spec.get('subtitle')),
                'amount': self._val(r, spec.get('amount')),
                'date': self._val(r, spec.get('date')),
                'state': self._val(r, spec.get('state')),
                'image': ('/web/image/%s/%s/%s' % (spec['model'], r.id, spec['image']))
                         if spec.get('image') and spec['image'] in r._fields and r[spec['image']] else None,
            })
        return _ok({'key': key, 'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'],
                    'count': Model.search_count(dom), 'rows': rows})

    # ---- detail ----------------------------------------------------------
    @route(API + '/management/<string:key>/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_detail(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على هذا النظام', 403)
        try:
            rec = env[spec['model']].browse(rid)
            rec.check_access_rule('read')  # record rules on this exact record
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        # Only the fields this system declares. Dumping every readable field
        # leaked private HR data (civil ID, birthday, marital status) and would
        # also blow up on group-restricted fields.
        skip_types = ('binary', 'image', 'one2many', 'many2many', 'html')
        allowed = spec.get('fields')
        if allowed:
            names = [f for f in allowed if f in rec._fields]
        else:
            names = [fname for fname, f in rec._fields.items()
                     if f.type not in skip_types
                     and not fname.startswith(('message_', 'activity_', 'website_'))
                     and fname not in ('id', 'display_name', '__last_update',
                                       'create_uid', 'write_uid', 'write_date')
                     and not SENSITIVE_RE.search(fname)]
        fields = []
        for fname in names:
            f = rec._fields[fname]
            if f.type in skip_types:
                continue
            try:
                v = self._val(rec, fname)   # a group-restricted field raises here
            except Exception:
                continue
            if v in (None, '', False):
                continue
            fields.append({'name': fname, 'label': f.string, 'value': v})
        return _ok({
            'id': rec.id, 'title': self._val(rec, spec['title']) or rec.display_name,
            'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'],
            'state': self._val(rec, spec.get('state')),
            'fields': fields[:40],
            'actions': self._actions_for(env, rec, key, spec),
        })

    # ---- run a whitelisted workflow action --------------------------------
    @route(API + '/management/<string:key>/<int:rid>/action', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_action(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        from .api import _body
        akey = (_body() or {}).get('action')
        adef = next((a for a in (ACTIONS.get(key) or []) if a['key'] == akey), None)
        if not adef:
            return _err('إجراء غير معروف', 422)
        try:
            rec = env[spec['model']].browse(rid)  # caller's env → Odoo enforces
            rec.check_access_rule('write')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        st = self._raw_state(rec, spec)
        if adef['states'] and st not in adef['states']:
            return _err('لا يمكن تنفيذ هذا الإجراء في الحالة الحالية', 422)
        if not hasattr(rec, adef['method']):
            return _err('الإجراء غير متاح', 422)
        try:
            getattr(rec, adef['method'])()  # may return an ir.actions dict — ignored
        except AccessError:
            return _err('لا تملك صلاحية تنفيذ هذا الإجراء', 403)
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        rec.invalidate_recordset()
        return _ok({'id': rec.id, 'state': self._val(rec, spec.get('state')),
                    'actions': self._actions_for(env, rec, key, spec)})
