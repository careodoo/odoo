# -*- coding: utf-8 -*-
"""The service registry as JSON, so the portal and the app show the same thing.

The web portal grew a hand-written branch per service, and every service added
after those branches were written fell through to a bare "work orders +
quality" pair — a client contracted for hospitality or valet saw, functionally,
nothing. Meanwhile the deep records (pool readings, tank cleanings, pest
stations) existed only in the Odoo backend.

care_cafm.controllers.service_pages already declares, once, what each service
is made of: which model, how to scope it, how to draw a row, and what a client
may add. This exposes that same declaration over the API. A service added to
the registry appears in the portal and the app on the same day, with no second
list to keep in step.
"""
from odoo.http import request, Controller, route

from odoo.addons.care_cafm.controllers.service_pages import (
    REGISTRY, ServicePages, _sel,
)

from .api import _auth, _ok, _err          # same auth helpers as the rest of v1

API = '/api/v1'
PAGE = 40


# The registry is written in Arabic. A client reading the portal in English
# must see English section names, and their Odoo account language is not
# the same choice — so both travel and the caller picks.
LABEL_EN = {
    'الأمن': 'Security',
    'النظافة': 'Cleaning',
    'الزراعة': 'Landscaping',
    'الواجهات': 'Facades',
    'نقل ومعالجة النفايات': 'Waste transfer & treatment',
    'الصيانة': 'Maintenance',
    'مكافحة الحشرات': 'Pest control',
    'صيانة المسابح': 'Pool maintenance',
    'تنظيف خزانات المياه': 'Water tank cleaning',
    'التعقيم': 'Disinfection',
    'المخزون': 'Inventory',
    'الضيافة': 'Hospitality',
    'صف السيارات': 'Valet parking',
    'البلاغات': 'Incidents',
    'الجولات': 'Rounds',
    'تصاريح الدخول': 'Gate passes',
    'التفتيش': 'Inspections',
    'الحرّاس': 'Guards',
    'المفاتيح': 'Keys',
    'التدقيقات': 'Audits',
    'الجداول': 'Schedules',
    'المستهلكات': 'Consumables',
    'الأشجار والنباتات': 'Trees & plants',
    'أعمال الأشجار': 'Tree works',
    'مناطق الريّ': 'Irrigation zones',
    'دليل الأنواع': 'Species guide',
    'تصاريح الارتفاع': 'Height permits',
    'أوامر النقل': 'Collection orders',
    'الرحلات': 'Trips',
    'مراكز المعالجة': 'Treatment centres',
    'الأعطال': 'Faults',
    'الفحوص الدورية': 'Periodic inspections',
    'قطع الغيار': 'Spare parts',
    'برامج المكافحة': 'Control programmes',
    'الزيارات': 'Visits',
    'شبكة المحطات': 'Station grid',
    'بلاغات الظهور': 'Sightings',
    'سجل المبيدات المعتمدة': 'Approved pesticides',
    'المسابح': 'Pools',
    'قراءات المياه': 'Water readings',
    'أعمال الصيانة': 'Maintenance work',
    'سجل الخزانات': 'Tank register',
    'عمليات التنظيف': 'Cleaning operations',
    'جولات التعقيم': 'Disinfection rounds',
    'المطهّرات المعتمدة': 'Approved disinfectants',
    'المخازن': 'Stores',
    'الحركات': 'Movements',
    'الأصناف والأرصدة': 'Items & balances',
    'الجرد': 'Stock count',
    'طلبات التعويض': 'Replenishment requests',
    'الطلبات': 'Orders',
    'قائمة الأصناف': 'Menu',
    'الأقسام': 'Categories',
    'حدود الاستهلاك': 'Consumption limits',
    'التذاكر': 'Tickets',
    'المواقف': 'Zones',
    'الورديات': 'Shifts',
    'إضافة سجل': 'Add record',
    'بدء جرد': 'Start a count',
    'طلب تعويض': 'Request replenishment',
    'إضافة خزان': 'Add tank',
    'تسجيل قراءة مياه': 'Log a water reading',
    'تسجيل جولة تعقيم': 'Log a disinfection round',
    'الإبلاغ عن ظهور آفة': 'Report a sighting',
    'طلب ضيافة': 'Place a hospitality order',
    'تسجيل مركبة': 'Register a vehicle',
}


def _en(label):
    return LABEL_EN.get(label, label)

def _pages():
    """The registry's own logic — scoping, capability checks, field inputs —
    reused rather than re-implemented, so the two surfaces cannot drift."""
    return ServicePages()


def _row(section, rec):
    """One record as (title, subtitle, pills) using the section's own renderer."""
    try:
        title, sub, pills = section.row(rec)
    except Exception:
        title, sub, pills = rec.display_name, '', []
    return {
        'id': rec.id,
        'title': title or '',
        'subtitle': sub or '',
        'pills': [{'t': t, 'c': c} for t, c in (pills or []) if t],
    }


_DETAIL_SKIP = {
    'id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date',
    '__last_update', 'access_token', 'access_url', 'access_warning', 'sequence',
    'color', 'facility_id',  # already the section context / title
    # mail.thread / technical plumbing that means nothing to a reader
    'has_message', 'website_message_ids', 'rating_ids', 'rating_last_value',
    'rating_last_feedback', 'rating_count', 'rating_avg', 'rating_percentage_satisfaction',
    'message_is_follower', 'message_bounce', 'active', 'company_id', 'currency_id',
}
_DESC_FIELDS = ('description', 'note', 'notes', 'comment', 'x_description',
                'details', 'remarks', 'observation', 'observations', 'body')


def _fmt_val(rec, name, f, env):
    """A record field rendered as a plain, human string for the detail sheet."""
    val = rec[name]
    t = f.type
    if t == 'many2one':
        return val.display_name if val else None
    if t in ('one2many', 'many2many'):
        return '، '.join(val.mapped('display_name')[:8]) if val else None
    if t == 'boolean':
        return 'نعم' if val else 'لا'
    if t == 'selection':
        try:
            return dict(f._description_selection(env)).get(val, val)
        except Exception:
            return val
    if t in ('date', 'datetime'):
        return str(val) if val else None
    if t in ('float', 'monetary'):
        return None if not val else round(val, 3)
    if t == 'integer':
        return None if not val else val
    if t in ('binary', 'image', 'html'):
        return None
    return val or None


def _record_details(rec, env):
    """(full free-text description, [ {label,value} … ]) for one record — so a
    tap reveals everything the record holds, not just its pills."""
    fg = rec._fields
    desc = ''
    for dn in _DESC_FIELDS:
        if dn in fg and rec[dn]:
            desc = rec[dn]
            break
    rows = []
    for name, f in fg.items():
        if name in _DETAIL_SKIP or name in _DESC_FIELDS:
            continue
        if name.startswith(('message_', 'activity_', 'my_activity_', 'rating_', 'website_')):
            continue
        if f.type in ('binary', 'image', 'html', 'one2many'):
            continue
        try:
            v = _fmt_val(rec, name, f, env)
        except Exception:
            v = None
        if v in (None, '', False):
            continue
        rows.append({'label': f.string or name, 'value': str(v)})
        if len(rows) >= 30:
            break
    return (desc or ''), rows


def _field_spec(f, facs, env):
    """A field described well enough for a web form to render it without
    knowing anything about Odoo."""
    d = {'name': f.name, 'label': f.label, 'kind': f.kind,
         'required': bool(f.required), 'default': f.default, 'help': f.help}
    if f.kind == 'm2o' and f.comodel:
        dom = [('facility_id', 'in', facs.ids)] if f.domain_facility else []
        try:
            recs = env[f.comodel].sudo().search(dom, limit=400)
            d['options'] = [{'v': r.id, 'l': r.display_name} for r in recs]
        except Exception:
            d['options'] = []
    elif f.kind == 'select':
        opts = f.options
        if isinstance(opts, str):
            d['options'] = [{'v': v, 'l': l} for v, l in []]
        elif opts:
            d['options'] = [{'v': v, 'l': l} for v, l in opts]
    return d


class ServiceApi(Controller):

    def _resolve_select(self, section, f, env):
        """A select whose options were declared as a field name reads them off
        the model, so the labels always match what the backend shows."""
        if f.kind != 'select' or not isinstance(f.options, str):
            return None
        try:
            model = env[section.model]
            sel = model._fields[f.options]._description_selection(env)
            return [{'v': v, 'l': l} for v, l in sel]
        except Exception:
            return []

    @route(API + '/client/svc', type='http', auth='public', methods=['GET'],
           csrf=False, cors='*')
    def svc_list(self, **kw):
        """Which services this client actually has, with their sub-sections."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # ServicePages helpers read request.env.user (the web session). The app
        # has no session — only the token — so without this the registry would
        # scope to the PUBLIC user: empty facilities, no permissions. And with
        # a stray admin cookie it would scope to admin. The token must be the
        # only identity either way.
        request.update_env(user=env.user.id)
        p = _pages()
        # No second opinion about which services a client has: /client/services
        # already answers that and the portal already reads it. This describes
        # what each service is *made of*; the caller filters by what it has.
        out = []
        for code, (label, icon, sections) in REGISTRY().items():
            out.append({
                'code': code, 'label': label, 'label_en': _en(label), 'icon': icon,
                'sections': [{'key': s.key, 'label': s.label,
                              'label_en': _en(s.label), 'icon': s.icon,
                              'can_add': bool((c := p._effective_create(s)))
                                         and p._may(c.perm),
                              'add_label': c.label if c else None,
                              'add_label_en': _en(c.label) if c else None}
                             for s in sections],
            })
        return _ok({'services': out})

    @route(API + '/client/svc/<string:code>/<string:key>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def svc_section(self, code, key, page=1, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # ServicePages helpers read request.env.user (the web session). The app
        # has no session — only the token — so without this the registry would
        # scope to the PUBLIC user: empty facilities, no permissions. And with
        # a stray admin cookie it would scope to admin. The token must be the
        # only identity either way.
        request.update_env(user=env.user.id)
        reg = REGISTRY().get(code)
        if not reg:
            return _err('خدمة غير معروفة', 404)
        section = next((s for s in reg[2] if s.key == key), None)
        if not section:
            return _err('قسم غير معروف', 404)
        p = _pages()
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        recs, total = p._records(section, page)
        facs = p._facilities()
        create = p._effective_create(section)
        can_add = bool(create) and p._may(create.perm)
        fields = []
        if can_add:
            for f in create.fields:
                spec = _field_spec(f, facs, env)
                sel = self._resolve_select(section, f, env)
                if sel is not None:
                    spec['options'] = sel
                fields.append(spec)
        return _ok({
            'service': {'code': code, 'label': reg[0], 'label_en': _en(reg[0]),
                        'icon': reg[1]},
            'section': {'key': section.key, 'label': section.label,
                        'label_en': _en(section.label),
                        'icon': section.icon, 'empty': section.empty_text or '',
                        'model': section.model},
            'rows': [_row(section, r) for r in recs],
            'page': page, 'pages': max(1, (total + PAGE - 1) // PAGE), 'total': total,
            'can_add': can_add,
            'can_cancel': p._may('record_manage'),
            'add_label': create.label if create else None,
            'add_label_en': _en(create.label) if create else None,
            'fields': fields,
        })

    @route(API + '/client/svc/<string:code>/<string:key>/<int:rid>', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def svc_record(self, code, key, rid, **kw):
        """One record in full — its free-text description and every readable
        field — so a tap opens the record, not a report."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        request.update_env(user=env.user.id)
        reg = REGISTRY().get(code)
        if not reg:
            return _err('خدمة غير معروفة', 404)
        section = next((s for s in reg[2] if s.key == key), None)
        if not section:
            return _err('قسم غير معروف', 404)
        rec = env[section.model].sudo().browse(int(rid)).exists()
        if not rec:
            return _err('السجل غير موجود', 404)
        # A client only ever reads records within their own facilities.
        facs = _pages()._facilities()
        if 'facility_id' in rec._fields and facs and rec.facility_id.id not in facs.ids:
            return _err('غير مصرّح', 403)
        out = _row(section, rec)
        desc, details = _record_details(rec, env)
        out['description'] = desc
        out['details'] = details
        return _ok(out)

    @route(API + '/client/svc/<string:code>/<string:key>/add', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def svc_add(self, code, key, **post):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # ServicePages helpers read request.env.user (the web session). The app
        # has no session — only the token — so without this the registry would
        # scope to the PUBLIC user: empty facilities, no permissions. And with
        # a stray admin cookie it would scope to admin. The token must be the
        # only identity either way.
        request.update_env(user=env.user.id)
        reg = REGISTRY().get(code)
        if not reg:
            return _err('خدمة غير معروفة', 404)
        section = next((s for s in reg[2] if s.key == key), None)
        p = _pages()
        create = p._effective_create(section) if section else None
        if not create:
            return _err('لا يمكن الإضافة في هذا القسم', 404)
        # The capability check is here, not only in the UI — a form that is
        # hidden is not a form that cannot be posted to.
        if not p._may(create.perm):
            return _err('لا تملك صلاحية الإضافة هنا', 403)
        try:
            rec = p._create_record(section, post)
        except Exception as e:
            return _err(str(e) or 'تعذّر الحفظ', 422)
        return _ok({'id': rec.id, 'name': rec.display_name})

    @route(API + '/client/svc/<string:code>/<string:key>/<int:rid>/cancel',
           type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def svc_cancel(self, code, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # ServicePages helpers read request.env.user (the web session). The app
        # has no session — only the token — so without this the registry would
        # scope to the PUBLIC user: empty facilities, no permissions. And with
        # a stray admin cookie it would scope to admin. The token must be the
        # only identity either way.
        request.update_env(user=env.user.id)
        reg = REGISTRY().get(code)
        section = next((s for s in reg[2] if s.key == key), None) if reg else None
        if not section:
            return _err('قسم غير معروف', 404)
        p = _pages()
        if not p._may('record_manage'):
            return _err('إلغاء السجلات يتطلب صلاحية «إدارة السجلات»', 403)
        try:
            how = p._cancel_record(section, rid)
        except Exception as e:
            return _err(str(e) or 'تعذّر الإلغاء', 422)
        return _ok({'result': how})
