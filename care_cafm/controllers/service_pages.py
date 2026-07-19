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


class Field:
    """One input on a section's add form. Declared, not hand-written, so every
    service gets the same form behaviour without twenty near-identical pages."""

    def __init__(self, name, label, kind='char', required=False, comodel=None,
                 domain_facility=False, options=None, default=None, help=None):
        self.name = name
        self.label = label
        self.kind = kind          # char | text | int | float | date | datetime
                                  # | select | m2o | bool
        self.required = required
        self.comodel = comodel    # for m2o
        self.domain_facility = domain_facility   # scope the m2o to the facility
        self.options = options    # for select: [(value, label)] or a field name
        self.default = default
        self.help = help


class Create:
    """What it takes for a client to add one of these."""

    def __init__(self, label, perm, fields, facility_field='facility_id'):
        self.label = label
        self.perm = perm          # capability code from the client matrix
        self.fields = fields
        self.facility_field = facility_field


class Section:
    """One sub-menu of a service: a model, how to scope it, how to draw a row."""

    def __init__(self, key, label, model, row, scope='facility',
                 order=None, icon='•', empty_text=None, create=None):
        self.key = key
        self.label = label
        self.model = model
        self.row = row            # callable(record) -> (title, subtitle, pills)
        self.scope = scope        # 'facility' | 'global' | 'none'
        self.order = order
        self.icon = icon
        self.empty_text = empty_text
        self.create = create      # a Create spec, or None if read-only


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
        'pest': ('مكافحة الحشرات', '🐜', [
            Section('programs', 'برامج المكافحة', 'care.pest.program',
                    _r_generic(lambda r: r.name,
                               lambda r: 'آخر زيارة %s · القادمة %s' % (
                                   _d(r.last_visit, 10), _d(r.next_due, 10)),
                               lambda r: ([('متأخر', 'crit')] if r.is_overdue else [])
                               + _state_pill(r, 'frequency', 'info')), icon='🗓️'),
            Section('visits', 'الزيارات', 'care.pest.visit',
                    _r_generic(lambda r: '%s — %s' % (r.name, _d(r.visit_date, 10)),
                               lambda r: '%s محطة مفحوصة · %s ملتقط' % (
                                   r.stations_checked, r.total_catch),
                               lambda r: _state_pill(r, 'activity_level', 'warn')
                               + _state_pill(r)), icon='🔎'),
            Section('stations', 'شبكة المحطات', 'care.pest.station',
                    _r_generic(lambda r: r.name,
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '',
                                   'آخر فحص %s' % _d(r.last_check, 10) if r.last_check else ''])),
                               lambda r: _state_pill(r, 'target', 'info') + _state_pill(r)),
                    icon='📍'),
            Section('sightings', 'بلاغات الظهور', 'care.pest.sighting',
                    _r_generic(lambda r: dict(r._fields['pest_type'].selection).get(
                                   r.pest_type, ''),
                               lambda r: r.description or '',
                               lambda r: _state_pill(r, 'severity', 'crit') + _state_pill(r)),
                    icon='⚠️',
                    create=Create('الإبلاغ عن ظهور آفة', 'observation_create', [
                        Field('pest_type', 'نوع الآفة', 'select', required=True, options=[
                            ('cockroach', 'صراصير'), ('rodent', 'قوارض'), ('ant', 'نمل'),
                            ('fly', 'ذباب'), ('mosquito', 'بعوض'), ('bedbug', 'بق الفراش'),
                            ('termite', 'نمل أبيض'), ('bird', 'طيور'), ('other', 'أخرى')]),
                        Field('severity', 'مدى الانتشار', 'select', required=True, default='one',
                              options=[('one', 'مشاهدة فردية'), ('few', 'عدة مشاهدات'),
                                       ('infestation', 'انتشار واضح')]),
                        Field('location_id', 'الموقع', 'm2o', comodel='care.cafm.location',
                              domain_facility=True),
                        Field('description', 'الوصف', 'text',
                              help='أين ومتى شوهدت — يساعد الفني على تحديد نقطة الدخول.'),
                    ])),
            Section('chemicals', 'سجل المبيدات المعتمدة', 'care.pest.chemical',
                    _r_generic(lambda r: '%s — %s' % (r.name, r.name_en or ''),
                               lambda r: '%s · تسجيل %s' % (
                                   r.active_ingredient or '', r.moh_registration or '—'),
                               lambda r: ([('آمن في مناطق الأغذية', 'ok')] if r.food_area_safe else [])
                               + ([('منع دخول %sس' % r.reentry_hours, 'warn')] if r.reentry_hours else [])),
                    scope='global', icon='🧪'),
        ]),
        'pool': ('صيانة المسابح', '🏊', [
            Section('pools', 'المسابح', 'care.pool.pool',
                    _r_generic(lambda r: '%s — %s' % (r.name, r.name_en or ''),
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '',
                                   '%s م³' % int(r.volume_m3) if r.volume_m3 else '',
                                   'آخر قراءة %s' % _d(r.last_reading, 16) if r.last_reading else 'لا قراءة'])),
                               lambda r: _state_pill(r)
                               + ([('بانتظار قراءة اليوم', 'warn')] if r.needs_reading else [])
                               + ([] if r.last_safe else [('آخر قراءة خارج النطاق', 'crit')])),
                    icon='🏊'),
            Section('readings', 'قراءات المياه', 'care.pool.reading',
                    _r_generic(lambda r: '%s — %s' % (r.pool_id.name or '', _d(r.taken_at)),
                               lambda r: 'pH %.1f · كلور %.1f · حرارة %.1f · عكارة %.2f' % (
                                   r.ph or 0, r.free_chlorine or 0,
                                   r.temperature or 0, r.turbidity or 0),
                               lambda r: [('ضمن النطاق', 'ok')] if r.is_safe
                               else [(r.breaches or 'خارج النطاق', 'crit')]), icon='🧪',
                    create=Create('تسجيل قراءة مياه', 'workorder_verify', [
                        Field('pool_id', 'المسبح', 'm2o', comodel='care.pool.pool',
                              domain_facility=True, required=True),
                        Field('ph', 'الأس الهيدروجيني pH', 'float'),
                        Field('free_chlorine', 'الكلور الحر (ppm)', 'float'),
                        Field('combined_chlorine', 'الكلور المرتبط (ppm)', 'float'),
                        Field('temperature', 'الحرارة (°م)', 'float'),
                        Field('turbidity', 'العكارة (NTU)', 'float'),
                        Field('note', 'ملاحظة', 'char'),
                    ], facility_field=None)),
            Section('tasks', 'أعمال الصيانة', 'care.pool.task',
                    _r_generic(lambda r: dict(r._fields['task_type'].selection).get(
                                   r.task_type, ''),
                               lambda r: ' · '.join(filter(None, [
                                   r.pool_id.name or '', _d(r.done_at),
                                   '%s %s' % (r.quantity, r.uom_name or '') if r.quantity else '',
                                   'ضغط الفلتر %.2f' % r.filter_pressure if r.filter_pressure else ''])),
                               ), icon='🧹'),
        ]),
        'watertank': ('تنظيف خزانات المياه', '🚰', [
            Section('tanks', 'سجل الخزانات', 'care.tank.tank',
                    _r_generic(lambda r: r.name,
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '',
                                   'آخر تنظيف %s' % _d(r.last_cleaned, 10) if r.last_cleaned
                                   else 'لم يُنظَّف بعد',
                                   'القادم %s' % _d(r.next_due, 10) if r.next_due else ''])),
                               lambda r: _state_pill(r, 'status',
                                                     'crit' if r.status in ('overdue', 'never')
                                                     else 'warn' if r.status == 'due_soon' else 'ok')
                               + _state_pill(r, 'use', 'info')), icon='🛢️',
                    create=Create('إضافة خزان', 'asset_manage', [
                        Field('code', 'رقم الخزان', 'char', required=True),
                        Field('position', 'الموقع', 'select', default='roof', options=[
                            ('roof', 'علوي'), ('ground', 'أرضي'), ('underground', 'تحت الأرض')]),
                        Field('material', 'الخامة', 'select', default='grp', options=[
                            ('grp', 'فايبر جلاس'), ('polyethylene', 'بولي إيثيلين'),
                            ('concrete', 'خرساني'), ('steel', 'حديد مجلفن')]),
                        Field('capacity_gal', 'السعة (جالون)', 'float'),
                        Field('use', 'الاستخدام', 'select', default='domestic', options=[
                            ('potable', 'مياه شرب'), ('domestic', 'استخدام عام'),
                            ('fire', 'مكافحة حريق'), ('irrigation', 'ري')]),
                        Field('cycle_months', 'دورة التنظيف (شهر)', 'int', default=6),
                        Field('location_id', 'الموقع', 'm2o', comodel='care.cafm.location',
                              domain_facility=True),
                    ])),
            Section('cleanings', 'عمليات التنظيف', 'care.tank.cleaning',
                    _r_generic(lambda r: '%s — %s' % (r.tank_id.name or '', _d(r.clean_date, 10)),
                               lambda r: ' · '.join(filter(None, [
                                   'اكتمال %s%%' % r.completeness,
                                   'شهادة %s' % r.certificate_no if r.certificate_no else '',
                                   'تقرير %s' % r.lab_reference if r.lab_reference else ''])),
                               lambda r: ([('مخبريًا: مطابقة', 'ok')] if r.lab_result == 'pass'
                                          else [('مخبريًا: غير مطابقة', 'crit')] if r.lab_result
                                          else []) + _state_pill(r)), icon='🧾'),
        ]),
        'disinfection': ('التعقيم', '🧴', [
            Section('rounds', 'جولات التعقيم', 'care.disinfect.round',
                    _r_generic(lambda r: '%s — %s' % (r.name, _d(r.done_at)),
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '',
                                   r.product_id.name or '',
                                   'تلامس %s د (المطلوب %s)' % (r.contact_minutes,
                                                                 r.required_minutes)])),
                               lambda r: ([('التلامس مُحترَم', 'ok')] if r.contact_ok
                                          else [('تلامس أقل من المطلوب', 'crit')])
                               + ([('ATP %s' % r.atp_reading,
                                    'ok' if r.atp_pass else 'warn')] if r.atp_tested else [])
                               + _state_pill(r)), icon='🧽',
                    create=Create('تسجيل جولة تعقيم', 'observation_create', [
                        Field('product_id', 'المطهّر', 'm2o',
                              comodel='care.disinfect.product', required=True),
                        Field('location_id', 'الموقع', 'm2o', comodel='care.cafm.location',
                              domain_facility=True),
                        Field('round_type', 'نوع الجولة', 'select', default='routine', options=[
                            ('routine', 'دوري'), ('terminal', 'نهائي بعد خروج مريض'),
                            ('outbreak', 'استجابة لعدوى'), ('preventive', 'وقائي')]),
                        Field('method', 'الطريقة', 'select', default='wipe', options=[
                            ('wipe', 'مسح'), ('spray', 'رشّ'), ('fog', 'تضبيب'),
                            ('electrostatic', 'رشّ كهروستاتيكي')]),
                        Field('contact_minutes', 'زمن التلامس (دقيقة)', 'int', required=True,
                              help='المدة التي بقي فيها المطهّر رطبًا — هي الفارق بين التعقيم والمسح.'),
                        Field('note', 'ملاحظات', 'text'),
                    ])),
            Section('products', 'المطهّرات المعتمدة', 'care.disinfect.product',
                    _r_generic(lambda r: '%s — %s' % (r.name, r.name_en or ''),
                               lambda r: '%s · تخفيف %s · تلامس %s دقيقة' % (
                                   r.active_ingredient or '', r.dilution or '—',
                                   r.contact_minutes),
                               lambda r: ([('آمن في مناطق الأغذية', 'ok')] if r.food_safe else [])),
                    scope='global', icon='🧪'),
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

    # ---------------- adding records ----------------
    def _may(self, code):
        """Does this caller hold the capability the section asks for?"""
        env = request.env
        u = env.user
        if u.has_group('base.group_system') or u.has_group('base.group_erp_manager'):
            return True
        C = env['care.cafm.client'].sudo()
        client = C.search([('user_ids', 'in', u.id)], limit=1)
        if not client:
            par = u.partner_id.commercial_partner_id or u.partner_id
            client = C.search([('partner_id', '=', par.id)], limit=1) if par else None
        if client:
            return client.can(code)
        # an employee acting on site keeps the operational capabilities
        return bool(u.employee_id)

    def _field_input(self, f, facs):
        env = request.env
        if f.kind == 'm2o':
            recs = env[f.comodel].sudo().search(
                [('facility_id', 'in', facs.ids)] if f.domain_facility else [], limit=400)
            opts = Markup('' if f.required else '<option value="">— بدون —</option>')
            opts += Markup('').join(
                Markup('<option value="%s">%s</option>') % (r.id, esc(r.display_name))
                for r in recs)
            return Markup('<select name="%s"%s>%s</select>') % (
                f.name, Markup(' required' if f.required else ''), opts)
        if f.kind == 'select':
            opts = f.options
            if isinstance(opts, str):
                opts = env[f.model_hint]._fields[opts].selection if False else []
            body = Markup('').join(
                Markup('<option value="%s"%s>%s</option>') % (
                    v, Markup(' selected' if v == f.default else ''), esc(l))
                for v, l in (opts or []))
            return Markup('<select name="%s"%s>%s</select>') % (
                f.name, Markup(' required' if f.required else ''), body)
        if f.kind == 'bool':
            return Markup('<label style="display:flex;gap:8px;align-items:center;margin-top:6px">'
                          '<input type="checkbox" name="%s" value="1"%s '
                          'style="width:auto;margin:0"/> %s</label>') % (
                f.name, Markup(' checked' if f.default else ''), esc(f.label))
        if f.kind == 'text':
            return Markup('<textarea name="%s" rows="3"%s></textarea>') % (
                f.name, Markup(' required' if f.required else ''))
        html_type = {'int': 'number', 'float': 'number', 'date': 'date',
                     'datetime': 'datetime-local'}.get(f.kind, 'text')
        step = ' step="any"' if f.kind == 'float' else ''
        return Markup('<input type="%s" name="%s"%s%s%s/>') % (
            Markup(html_type), f.name, Markup(step),
            Markup(' required' if f.required else ''),
            Markup(' value="%s"' % f.default) if f.default is not None else Markup(''))

    def _create_form(self, code, section, facs):
        c = section.create
        if not c or not self._may(c.perm):
            return Markup('')
        rows = Markup('')
        for f in c.fields:
            if f.kind == 'bool':
                rows += self._field_input(f, facs)
                continue
            rows += Markup('<label>%s%s</label>%s') % (
                esc(f.label), Markup(' *' if f.required else ''), self._field_input(f, facs))
            if f.help:
                rows += Markup('<div class="muted" style="margin-top:3px">%s</div>') % esc(f.help)
        fopts = Markup('').join(
            Markup('<option value="%s">%s</option>') % (f.id, esc(f.name)) for f in facs)
        fac_row = (Markup('<label>المرفق</label><select name="__facility">%s</select>') % fopts) \
            if len(facs) > 1 else Markup('<input type="hidden" name="__facility" value="%s"/>') % (
                facs[:1].id or 0)
        return Markup(
            '<details class="card"><summary style="font-weight:900;cursor:pointer">➕ %s</summary>'
            '<form method="post" action="/cafm/m/svc/%s/%s/add" style="margin-top:10px">%s'
            '%s%s<button class="btn">حفظ</button></form></details>'
        ) % (esc(c.label), code, section.key, _csrf(), fac_row, rows)

    @http.route('/cafm/m/svc/<string:code>/<string:key>/add', type='http', auth='user',
                methods=['POST'], website=False, csrf=True)
    def section_add(self, code, key, **post):
        reg = REGISTRY().get(code)
        if not reg:
            return request.redirect('/cafm/m')
        _label, _icon, sections = reg
        section = next((s for s in sections if s.key == key), None)
        if not section or not section.create:
            return request.redirect('/cafm/m/svc/%s' % code)
        c = section.create
        if not self._may(c.perm):
            return _shell('غير مصرّح', Markup(
                '<div class="card"><div class="h4">⛔ غير مصرّح</div>'
                '<div class="muted">حسابك لا يملك صلاحية «%s». اطلبها من صفحة الصلاحيات.</div>'
                '<a class="btn g" href="/cafm/m/permissions">صلاحياتي</a></div>') % esc(c.label),
                accent=accent_for(code), back='/cafm/m/svc/%s/%s' % (code, key))

        env = request.env
        facs = self._facilities()
        vals = {}
        fid = int(post.get('__facility') or 0) or (facs[:1].id or 0)
        if c.facility_field and fid in facs.ids:
            vals[c.facility_field] = fid
        for f in c.fields:
            raw = post.get(f.name)
            if f.kind == 'bool':
                vals[f.name] = bool(raw)
                continue
            if raw in (None, ''):
                continue
            if f.kind in ('int', 'm2o'):
                try:
                    vals[f.name] = int(raw)
                except ValueError:
                    continue
            elif f.kind == 'float':
                try:
                    vals[f.name] = float(raw)
                except ValueError:
                    continue
            elif f.kind == 'datetime':
                vals[f.name] = raw.replace('T', ' ') + (':00' if len(raw) == 16 else '')
            else:
                vals[f.name] = raw
        try:
            env[section.model].sudo().create(vals)
        except Exception as e:
            msg = str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e)
            return _shell('تعذّر الحفظ', Markup(
                '<div class="card"><div class="h4">⛔ لم يُحفظ السجل</div>'
                '<div class="muted" style="margin-top:6px">%s</div>'
                '<a class="btn g" href="/cafm/m/svc/%s/%s">رجوع</a></div>') % (
                    esc(msg), code, key),
                accent=accent_for(code), back='/cafm/m/svc/%s/%s' % (code, key))
        return request.redirect('/cafm/m/svc/%s/%s' % (code, key))

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
            style = ('background:%s;color:#ffffff' % accent) if on else 'background:#ffffff;color:#71809a'
            body += Markup('<a class="pill" style="%s;padding:7px 12px" href="/cafm/m/svc/%s/%s">%s %s</a>') % (
                Markup(style), code, s.key, s.icon, esc(s.label))
        body += Markup('</div>')
        body += self._create_form(code, section, self._facilities())
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
