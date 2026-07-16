# -*- coding: utf-8 -*-
"""Native MANAGEMENT API — the company's back-office systems in the app.

The management interface used to be a launcher of /web links, i.e. web pages
inside a WebView. These endpoints expose the same systems as real data so the
app can render them natively.

Security model: every read runs with the CALLER's env — never sudo — so Odoo's
own record rules and ACLs decide what each user may see. A system that raises
AccessError is simply reported as unavailable to that user.
"""
from odoo.exceptions import AccessError
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, API


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


class ManagementApi(Controller):

    def _spec(self, key):
        return REGISTRY.get(key)

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
        # a readable, human field set — skip technical/binary noise
        skip_types = ('binary', 'image', 'one2many', 'many2many', 'html')
        fields = []
        for fname, f in rec._fields.items():
            if f.type in skip_types or fname.startswith(('message_', 'activity_', 'website_')):
                continue
            if fname in ('id', 'display_name', '__last_update', 'create_uid', 'write_uid', 'write_date'):
                continue
            v = self._val(rec, fname)
            if v in (None, '', False):
                continue
            fields.append({'name': fname, 'label': f.string, 'value': v})
        return _ok({
            'id': rec.id, 'title': self._val(rec, spec['title']) or rec.display_name,
            'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'],
            'state': self._val(rec, spec.get('state')),
            'fields': fields[:40],
        })
