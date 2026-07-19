# -*- coding: utf-8 -*-
"""Every contracted service, with its sub-sections, on the portal.

The app carries a console per service — security has seven tabs, cleaning four,
landscaping four — while the portal had work orders, quality and patrols and
nothing else. Writing fifteen more pages by hand would have meant fifteen more
places to keep in step.

So a service is described once, as data: which sub-sections it has, which model
each reads, how a row renders. One page shape serves all of them, which is also
why they cannot drift apart again.
"""
from markupsafe import Markup

from odoo import fields, http, _
from odoo.http import request

from .main import _shell, esc, _csrf, accent_for, sec, empty, pager

PER_PAGE = 20


def _d(v, n=16):
    return str(v)[:n] if v else '—'


def _sel(rec, field):
    try:
        return dict(rec._fields[field].selection)
    except Exception:
        return {}


class Section:
    """One sub-menu of a service: a model, how to scope it, how to draw a row."""

    def __init__(self, key, label, model, row, scope='facility',
                 order=None, icon='•', empty_text=None):
        self.key = key
        self.label = label
        self.model = model
        self.row = row            # callable(record) -> (title, subtitle, pills)
        self.scope = scope        # 'facility' | 'global' | 'none'
        self.order = order
        self.icon = icon
        self.empty_text = empty_text


# ---------------------------------------------------------------- row renderers
def _r_incident(r):
    sev = _sel(r, 'severity').get(getattr(r, 'severity', ''), '')
    st = _sel(r, 'state').get(getattr(r, 'state', ''), '')
    return (r.display_name, ' · '.join(filter(None, [
        _d(getattr(r, 'incident_date', None) or getattr(r, 'date', None)),
        getattr(r, 'location', '') or '']))
        , [(sev, 'crit'), (st, 'info')])


def _r_generic(title_f, sub_f=None, pills_f=None):
    def render(r):
        title = title_f(r) if callable(title_f) else (getattr(r, title_f, '') or r.display_name)
        sub = ''
        if sub_f:
            sub = sub_f(r) if callable(sub_f) else (getattr(r, sub_f, '') or '')
        pills = pills_f(r) if pills_f else []
        return (title, sub, pills)
    return render


def _state_pill(r, field='state', cls='info'):
    v = getattr(r, field, None)
    if not v:
        return []
    return [(_sel(r, field).get(v, v), cls)]


# ---------------------------------------------------------------- the registry
def REGISTRY():
    """Built lazily so a model missing from this database simply drops out."""
    return {
        'security': ('الأمن', '🛡️', [
            Section('incidents', 'البلاغات', 'security.incident.report', _r_incident, icon='🚨'),
            Section('patrols', 'الجولات', 'security.patrol',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'start_time', None)),
                               lambda r: _state_pill(r)), icon='🚶'),
            Section('gatepasses', 'تصاريح الدخول', 'security.gate.pass',
                    _r_generic(lambda r: r.display_name,
                               lambda r: ' · '.join(filter(None, [
                                   getattr(r, 'visitor_name', '') or '',
                                   getattr(r, 'company', '') or ''])),
                               lambda r: _state_pill(r)), icon='🎫'),
            Section('inspections', 'التفتيش', 'security.inspection',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None)),
                               lambda r: _state_pill(r)), icon='🔎'),
            Section('guards', 'الحرّاس', 'security.guard',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'job_title', '') or ''), icon='👮'),
            Section('keys', 'المفاتيح', 'security.key',
                    _r_generic(lambda r: r.display_name, None,
                               lambda r: _state_pill(r)), icon='🔑'),
        ]),
        'cleaning': ('النظافة', '🧼', [
            Section('audits', 'التدقيقات', 'care.cafm.clean.audit',
                    _r_generic(lambda r: '%s — %s' % (r.name or '', r.location_id.name or ''),
                               lambda r: _d(r.audit_date),
                               lambda r: [('%.0f%%' % (r.score or 0),
                                           'ok' if (r.score or 0) >= 75 else 'warn')]
                               + _state_pill(r)), icon='📋'),
            Section('schedules', 'الجداول', 'care.cafm.clean.schedule',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'location_id', None) and r.location_id.name or ''),
                    icon='🔁'),
            Section('rounds', 'الجولات', 'care.cafm.clean.round',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'scan_in', None)),
                               lambda r: _state_pill(r)), icon='🚶'),
            Section('consumables', 'المستهلكات', 'care.cafm.clean.consumable',
                    _r_generic(lambda r: r.display_name,
                               lambda r: '%s %s' % (getattr(r, 'on_hand', 0),
                                                    getattr(r, 'uom_name', '') or '')), icon='🧴'),
        ]),
        'agriculture': ('الزراعة', '🌳', [
            Section('plants', 'الأشجار والنباتات', 'care.cafm.agri.plant',
                    _r_generic(lambda r: r.display_name,
                               lambda r: ' · '.join(filter(None, [
                                   getattr(r, 'species_id', None) and r.species_id.name or '',
                                   getattr(r, 'zone_id', None) and r.zone_id.name or ''])),
                               lambda r: _state_pill(r, 'health', 'ok')), icon='🌱'),
            Section('operations', 'أعمال الأشجار', 'care.cafm.agri.operation',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None)),
                               lambda r: _state_pill(r)), icon='✂️'),
            Section('zones', 'مناطق الريّ', 'care.cafm.agri.zone',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'location_id', None) and r.location_id.name or '',
                               lambda r: _state_pill(r, 'method', 'info')), icon='💧'),
            Section('species', 'دليل الأنواع', 'care.cafm.agri.species',
                    _r_generic(lambda r: '%s — %s' % (r.name, r.name_en or ''),
                               lambda r: r.scientific_name or '',
                               lambda r: _state_pill(r, 'category', 'info')
                               + _state_pill(r, 'water_need', 'ok')),
                    scope='global', icon='📖'),
        ]),
        'facade': ('الواجهات', '🏙️', [
            Section('permits', 'تصاريح الارتفاع', 'care.cafm.facade.permit',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'zone_id', None) and r.zone_id.name or '',
                               lambda r: _state_pill(r)), icon='🎫'),
            Section('zones', 'الواجهات', 'care.cafm.facade.zone',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _sel(r, 'method').get(getattr(r, 'method', ''), '')),
                    icon='🪟'),
        ]),
        'waste': ('نقل ومعالجة النفايات', '♻️', [
            Section('orders', 'أوامر النقل', 'cafm.waste.order',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'request_datetime', None)),
                               lambda r: _state_pill(r, 'states')
                               or _state_pill(r)), icon='📦'),
            Section('trips', 'الرحلات', 'cafm.waste.trip',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None)),
                               lambda r: _state_pill(r, 'states') or _state_pill(r)), icon='🚛'),
            Section('centers', 'مراكز المعالجة', 'cafm.waste.center',
                    _r_generic(lambda r: r.display_name), scope='global', icon='🏭'),
        ]),
        'maintenance': ('الصيانة', '🛠️', [
            Section('faults', 'الأعطال', 'care.cafm.maint.fault',
                    _r_generic(lambda r: r.title or r.name,
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '', r.department_id.name or ''])),
                               lambda r: _state_pill(r, 'severity', 'crit') + _state_pill(r)),
                    icon='🔧'),
            Section('inspections', 'الفحوص الدورية', 'care.cafm.maint.inspection',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'location_id', None) and r.location_id.name or '',
                               lambda r: _state_pill(r)), icon='🗓️'),
            Section('parts', 'قطع الغيار', 'care.cafm.maint.part',
                    _r_generic(lambda r: r.display_name,
                               lambda r: '%s %s' % (round(getattr(r, 'on_hand', 0), 1),
                                                    getattr(r, 'uom_name', '') or ''),
                               lambda r: [('تحت الحد', 'warn')] if getattr(r, 'low_stock', False) else []),
                    scope='global', icon='📦'),
        ]),
        'inventory': ('المخزون', '📦', [
            Section('stores', 'المخازن', 'care.cafm.store',
                    _r_generic(lambda r: r.display_name), icon='🏬'),
            Section('moves', 'الحركات', 'care.cafm.stock.move',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None)),
                               lambda r: _state_pill(r, 'move_type', 'info')), icon='🔄'),
        ]),
    }


class ServicePages(http.Controller):

    # ---------------- scoping ----------------
    def _facilities(self):
        env = request.env
        Fac = env['care.cafm.facility'].sudo()
        u = env.user
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return Fac.search([])
        pids = set()
        for c in env['care.cafm.client'].sudo().search([('user_ids', 'in', u.id)]):
            pids.add(c.partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', c.partner_id.id)]).ids)
        p = u.partner_id
        pids.add(p.id)
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
        facs = Fac.search([('partner_id', 'in', list(pids))])
        if facs:
            return facs
        emp = u.employee_id
        ids = set()
        if emp:
            ids |= set(env['care.cafm.workorder'].sudo().search(
                [('employee_id', '=', emp.id)]).mapped('facility_id').ids)
        return Fac.browse(list(ids))

    def _records(self, section, page):
        """Fetch one page of a section, scoped to what this user may see."""
        env = request.env
        if section.model not in env:
            return env['res.partner'].browse(), 0
        M = env[section.model].sudo()
        dom = []
        if section.scope == 'facility':
            facs = self._facilities()
            if 'facility_id' in M._fields:
                dom = [('facility_id', 'in', facs.ids)]
            elif 'premise_id' in M._fields and 'security.premise' in env:
                # The security module keys on premises, and the bridge links a
                # premise back to a facility through cafm_facility_id — not the
                # facility_id every other model here uses.
                prem = env['security.premise'].sudo().search(
                    [('cafm_facility_id', 'in', facs.ids)])
                dom = [('premise_id', 'in', prem.ids)] if prem else [('id', '=', 0)]
        total = M.search_count(dom)
        recs = M.search(dom, limit=PER_PAGE, offset=(page - 1) * PER_PAGE,
                        order=section.order or None)
        return recs, total

    # ---------------- pages ----------------
    @http.route('/cafm/m/svc/<string:code>', type='http', auth='user', website=False)
    def service_home(self, code, **kw):
        reg = REGISTRY().get(code)
        if not reg:
            return request.redirect('/cafm/m')
        label, icon, sections = reg
        accent = accent_for(code)
        env = request.env
        body = Markup('')
        # a count per sub-section, so the menu says how much is behind each door
        tiles = Markup('<div class="grid">')
        for s in sections:
            if s.model not in env:
                continue
            _, total = self._records(s, 1)
            tiles += Markup(
                '<a class="tile" href="/cafm/m/svc/%s/%s"><div class="i">%s</div>'
                '<div class="n">%s</div><div class="s">%s سجل</div></a>'
            ) % (code, s.key, s.icon, esc(s.label), total)
        tiles += Markup('</div>')
        body += Markup('<div class="card"><div class="h4">%s %s</div>'
                       '<div class="muted">اختر ما تريد متابعته من هذه الخدمة.</div></div>') % (
            icon, esc(label))
        body += tiles
        body += Markup('<a class="btn g" href="/cafm/m/workorders?state=open">'
                       'أوامر عمل هذه الخدمة</a>')
        return _shell(label, body, accent, crumb=[('CAFM', '/cafm/m'), (label, None)])

    @http.route('/cafm/m/svc/<string:code>/<string:key>', type='http', auth='user', website=False)
    def service_section(self, code, key, page=1, **kw):
        reg = REGISTRY().get(code)
        if not reg:
            return request.redirect('/cafm/m')
        label, icon, sections = reg
        section = next((s for s in sections if s.key == key), None)
        if not section:
            return request.redirect('/cafm/m/svc/%s' % code)
        accent = accent_for(code)
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        recs, total = self._records(section, page)
        pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

        body = Markup('<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px">')
        for s in sections:
            if s.model not in request.env:
                continue
            on = s.key == key
            style = ('background:%s;color:#0b1220' % accent) if on else 'background:#152438;color:#9cb2cd'
            body += Markup('<a class="pill" style="%s;padding:7px 12px" href="/cafm/m/svc/%s/%s">%s %s</a>') % (
                Markup(style), code, s.key, s.icon, esc(s.label))
        body += Markup('</div>')
        body += sec('%s — %s' % (label, section.label))
        body += Markup('<div class="muted" style="margin-bottom:9px">%s سجل · صفحة %s من %s</div>') % (
            total, page, pages)

        if not recs:
            body += empty(section.empty_text or 'لا سجلات في هذا القسم بعد.', section.icon)
        for r in recs:
            try:
                title, sub, pills = section.row(r)
            except Exception:
                title, sub, pills = r.display_name, '', []
            chips = Markup('').join(
                Markup('<span class="pill %s">%s</span> ') % (Markup(cls), esc(txt))
                for txt, cls in (pills or []) if txt)
            body += Markup(
                '<div class="card stripe" style="border-inline-start-color:%s">'
                '<div class="h4">%s</div>%s%s</div>'
            ) % (Markup(accent), esc(title),
                 Markup('<div class="muted" style="margin-top:3px">%s</div>') % esc(sub) if sub else Markup(''),
                 Markup('<div style="margin-top:7px">%s</div>') % chips if chips else Markup(''))
        body += pager(page, pages, '/cafm/m/svc/%s/%s?page={p}' % (code, key))
        return _shell('%s · %s' % (label, section.label), body, accent,
                      back='/cafm/m/svc/%s' % code,
                      crumb=[('CAFM', '/cafm/m'), (label, '/cafm/m/svc/%s' % code),
                             (section.label, None)])
