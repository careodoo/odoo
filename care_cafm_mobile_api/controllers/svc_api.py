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
                'code': code, 'label': label, 'icon': icon,
                'sections': [{'key': s.key, 'label': s.label, 'icon': s.icon,
                              'can_add': bool((c := p._effective_create(s)))
                                         and p._may(c.perm),
                              'add_label': c.label if c else None}
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
            'service': {'code': code, 'label': reg[0], 'icon': reg[1]},
            'section': {'key': section.key, 'label': section.label,
                        'icon': section.icon, 'empty': section.empty_text or '',
                        'model': section.model},
            'rows': [_row(section, r) for r in recs],
            'page': page, 'pages': max(1, (total + PAGE - 1) // PAGE), 'total': total,
            'can_add': can_add,
            'can_cancel': p._may('record_manage'),
            'add_label': create.label if create else None,
            'fields': fields,
        })

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
