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
def _r_hosp_order(r):
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r, 'room_label', '') or '',
        getattr(r.facility_id, 'name', '') or '',
        _d(getattr(r, 'placed_at', None) or getattr(r, 'create_date', None))]))
    pills = list(_state_pill(r, 'state', 'info'))
    if getattr(r, 'is_late', False):
        pills.append((_t('متأخر', 'Late'), 'danger'))
    if getattr(r, 'is_vip', False):
        pills.append(('VIP', 'warn'))
    if getattr(r, 'item_count', 0):
        pills.append((_t('%d صنف', '%d items') % r.item_count, 'muted'))
    return (r.display_name, sub, pills)


def _r_hosp_item(r):
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r.category_id, 'name', '') or '',
        '%d دقيقة' % r.prep_minutes if getattr(r, 'prep_minutes', 0) else '']))
    pills = [('%.3f د.ك' % (r.cost or 0.0), 'muted')]
    if not getattr(r, 'active', True):
        pills.append(('موقوف', 'danger'))
    return (r.display_name, sub, pills)


def _r_valet_ticket(r):
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r, 'plate', '') or '',
        getattr(r, 'guest_name', '') or '',
        _d(getattr(r, 'received_at', None))]))
    pills = list(_state_pill(r, 'state', 'info'))
    if getattr(r, 'key_tag', ''):
        pills.append((_t('مفتاح %s', 'Key %s') % r.key_tag, 'muted'))
    return (r.display_name, sub, pills)


# A pill written as a bare Arabic string is Arabic for everyone, whatever
# language the reader chose — which is how an English portal ended up showing
# "مفتاح K-814" beside "Delivered". These render in the caller's language.
def _t(ar, en):
    """Arabic or English, per the active language."""
    return en if (request.env.context.get('lang') or '').startswith('en') else ar


def _r_key_hub(r):
    """A hub is read for: how many keys, who holds it, and where it is."""
    keys = getattr(r, 'key_ids', None)
    pills = [('%d %s' % (len(keys) if keys else 0, _t('مفتاح', 'keys')), 'info')]
    resp = getattr(r, 'responsible_id', None)
    if resp and resp.name:
        pills.append((resp.name, 'muted'))
    return (r.display_name,
            ' \u00b7 '.join(filter(None, [getattr(r, 'code', '') or '',
                                          getattr(r, 'location', '') or ''])),
            pills)


def _r_key(r):
    """A key is read for: which door, and is it out."""
    st = getattr(r, 'state', '') or ''
    out = st in ('issued', 'out', 'borrowed')
    pills = list(_state_pill(r, 'state', 'warn' if out else 'ok'))
    if getattr(r, 'nfc_uid', False):
        pills.append((_t('بشريحة NFC', 'NFC tagged'), 'muted'))
    return (r.display_name,
            ' \u00b7 '.join(filter(None, [
                '%s %s' % (_t('باب', 'door'), getattr(r, 'door_number', '') or ''),
                '%s %s' % (_t('رقم', 'no.'), getattr(r, 'key_number', '') or '')])),
            pills)


def _r_cashier(r):
    """A cashier report is read for: what was collected, and does it balance."""
    total = getattr(r, 'total_amount', 0) or getattr(r, 'amount_total', 0) or 0
    pills = [('%.3f' % total, 'ok' if total else 'muted')]
    pills += list(_state_pill(r, 'state', 'info'))
    return (r.display_name, _d(getattr(r, 'date', None)), pills)


def _r_facade_permit(r):
    """A permit is read for one thing: may the crew go up or not."""
    safe = getattr(r, 'is_safe', False)
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r.zone_id, 'name', '') or '', _d(getattr(r, 'date', None)),
        '%s %s' % (_t('رياح', 'wind'), getattr(r, 'wind_speed', 0) or 0)]))
    pills = [((_t('مصرّح', 'Approved') if safe else _t('غير مصرّح', 'Not approved')),
              'ok' if safe else 'danger')]
    if not getattr(r, 'risk_assessed', False):
        pills.append((_t('بلا تقييم مخاطر', 'No risk assessment'), 'warn'))
    return (r.display_name, sub, pills)


def _r_facade_zone(r):
    """The history a facade carries: when it was last done and when it is due."""
    sub = ' \u00b7 '.join(filter(None, [
        _sel(r, 'method').get(getattr(r, 'method', ''), ''),
        '%s م²' % r.area_sqm if getattr(r, 'area_sqm', 0) else '',
        '%s %s' % (getattr(r, 'floors', 0), _t('دور', 'floors')) if getattr(r, 'floors', 0) else '']))
    pills = []
    last = getattr(r, 'last_cleaned', None)
    if last:
        pills.append(('%s %s' % (_t('آخر تنظيف', 'last'), _d(last)), 'muted'))
    due = getattr(r, 'next_due', None)
    if due:
        import datetime as _dt
        late = due < _dt.date.today() if isinstance(due, _dt.date) else False
        pills.append(((_t('متأخر', 'Overdue') if late else '%s %s' % (_t('يستحق', 'due'), _d(due))),
                      'danger' if late else 'info'))
    return (r.display_name, sub, pills)


def _r_clean_consumable(r):
    """Balance first, and say when it runs short — a consumables list that
    only shows names is a list nobody opens twice."""
    on = getattr(r, 'on_hand', 0) or 0
    mn = getattr(r, 'min_qty', 0) or 0
    low = mn and on <= mn
    pills = [('%s %s' % (on, getattr(r, 'uom_name', '') or ''), 'danger' if low else 'ok')]
    if low:
        pills.append((_t('تحت الحد الأدنى', 'Below minimum'), 'warn'))
    return (r.display_name, getattr(r.location_id, 'name', '') or '', pills)


def _r_stock_item(r):
    """Balance first, because that is the only number anyone opens this for."""
    low = getattr(r, 'low_stock', False)
    bal = '%.0f %s' % (r.on_hand or 0.0, getattr(r, 'uom_name', '') or '')
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r.store_id, 'name', '') or '',
        _t('الحد الأدنى %.0f', 'min %.0f') % r.min_qty if r.min_qty else '']))
    pills = [(bal, 'danger' if low else 'ok')]
    if low and getattr(r, 'to_reorder', 0):
        pills.append((_t('يُطلب %.0f', 'reorder %.0f') % r.to_reorder, 'warn'))
    return (r.display_name, sub, pills)


def _r_stock_count(r):
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r.store_id, 'name', '') or '', _d(getattr(r, 'count_date', None))]))
    pills = list(_state_pill(r, 'state', 'info'))
    if r.state == 'done':
        pills.append((_t('دقة %.0f%%', 'accuracy %.0f%%') % (r.accuracy or 0),
                      'ok' if (r.accuracy or 0) >= 95 else 'warn'))
    if r.variance_lines:
        pills.append((_t('%d فرق', '%d variances') % r.variance_lines, 'warn'))
    return (r.display_name, sub, pills)


def _r_stock_request(r):
    sub = ' \u00b7 '.join(filter(None, [
        getattr(r.store_id, 'name', '') or '',
        _t('%d صنف', '%d items') % len(r.line_ids) if r.line_ids else '',
        _d(getattr(r, 'needed_by', None))]))
    pills = list(_state_pill(r, 'state', 'info'))
    if getattr(r, 'urgency', '') in ('high', 'critical'):
        pills.append((_sel(r, 'urgency').get(r.urgency, ''),
                      'danger' if r.urgency == 'critical' else 'warn'))
    return (r.display_name, sub, pills)


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
            # These two systems existed in full inside security_management and
            # were simply never shown to the client — building them again
            # would have been the expensive way to answer the request.
            Section('keyhubs', 'أقفال المفاتيح', 'security.key.hub',
                    _r_key_hub, icon='🗄️', scope='none',
                    empty_text='لا توجد أقفال مفاتيح مسجّلة.'),
            Section('keys', 'المفاتيح', 'security.key',
                    _r_key, icon='🔑', scope='none',
                    empty_text='لا مفاتيح مسجّلة.'),
            Section('cashier', 'كاشير المواقف', 'security.cashier.report',
                    _r_cashier, icon='💵', scope='none',
                    empty_text='لا تقارير كاشير.'),
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
                               + _state_pill(r)), icon='📋',
                    empty_text='لا توجد تدقيقات بعد.',
                    # The client inspects their own building every day and had
                    # no way to record it — the audit trail only ever held
                    # CARE's own view of CARE's own work.
                    create=Create('تسجيل تدقيق', 'observation_create', [
                        Field('location_id', 'الموقع', 'm2o', required=True,
                              comodel='care.cafm.location', domain_facility=True),
                        Field('template_id', 'قالب الفحص', 'm2o',
                              comodel='care.cafm.clean.audit.template'),
                        Field('audit_date', 'التاريخ والوقت', 'datetime'),
                        Field('note', 'الملاحظات', 'text'),
                    ])),
            Section('schedules', 'الجداول', 'care.cafm.clean.schedule',
                    _r_generic(lambda r: r.display_name,
                               lambda r: getattr(r, 'location_id', None) and r.location_id.name or ''),
                    icon='🔁'),
            Section('rounds', 'الجولات', 'care.cafm.clean.round',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'scan_in', None)),
                               lambda r: _state_pill(r)), icon='🚶',
                    empty_text='لا جولات مسجّلة.'),
            Section('consumables', 'المستهلكات', 'care.cafm.clean.consumable',
                    _r_clean_consumable, icon='🧴',
                    empty_text='لا مستهلكات مسجّلة.',
                    create=Create('تسجيل مستهلك', 'inventory_policy', [
                        Field('name', 'الاسم', 'char', required=True),
                        Field('uom_name', 'الوحدة', 'char'),
                        Field('on_hand', 'الرصيد', 'float'),
                        Field('min_qty', 'حد إعادة الطلب', 'float'),
                    ])),
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
                    _r_facade_permit, icon='🎫',
                    empty_text='لا تصاريح مسجّلة.',
                    create=Create('طلب تصريح ارتفاع', 'observation_create', [
                        Field('zone_id', 'الواجهة', 'm2o', required=True,
                              comodel='care.cafm.facade.zone', domain_facility=True),
                        Field('date', 'التاريخ', 'date', required=True),
                        Field('valid_hours', 'صلاحية (ساعات)', 'float', default=6),
                        Field('wind_speed', 'سرعة الرياح (كم/س)', 'float'),
                        Field('risk_assessed', 'تقييم مخاطر مرفق', 'bool'),
                        Field('equipment_checked', 'فحص المعدّات والحبال', 'bool'),
                    ])),
            Section('zones', 'الواجهات', 'care.cafm.facade.zone',
                    _r_facade_zone, icon='🪟',
                    empty_text='لم تُسجَّل واجهات بعد.',
                    create=Create('إضافة واجهة', 'structure_manage', [
                        Field('name', 'اسم الواجهة', 'char', required=True),
                        Field('method', 'طريقة الوصول', 'select', options='method'),
                        Field('area_sqm', 'المساحة (م²)', 'float'),
                        Field('floors', 'عدد الأدوار', 'int'),
                        Field('clean_cycle_days', 'دورة التنظيف (يوم)', 'int'),
                    ])),
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
                               lambda r: [(_t('ضمن النطاق', 'In range'), 'ok')] if r.is_safe
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
                               lambda r: ([(_t('مخبريًا: مطابقة', 'Lab: pass'), 'ok')] if r.lab_result == 'pass'
                                          else [(_t('مخبريًا: غير مطابقة', 'Lab: fail'), 'crit')] if r.lab_result
                                          else []) + _state_pill(r)), icon='🧾'),
        ]),
        'disinfection': ('التعقيم', '🧴', [
            Section('rounds', 'جولات التعقيم', 'care.disinfect.round',
                    _r_generic(lambda r: '%s — %s' % (r.name, _d(r.done_at)),
                               lambda r: ' · '.join(filter(None, [
                                   r.location_id.name or '',
                                   r.product_id.name or '',
                                   _t('تلامس %s د (المطلوب %s)', 'contact %s min (needs %s)') % (r.contact_minutes,
                                                                 r.required_minutes)])),
                               lambda r: ([('التلامس مُحترَم', 'ok')] if r.contact_ok
                                          else [(_t('تلامس أقل من المطلوب', 'Contact below requirement'), 'crit')])
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
        'hospitality': ('الضيافة', '\u2615', [
            Section('orders', 'الطلبات', 'care.hosp.order', _r_hosp_order, icon='\U0001f9fe',
                    empty_text='لا توجد طلبات ضيافة بعد.',
                    create=Create('طلب ضيافة', 'hospitality_order', [
                        Field('room_label', 'المكتب/القاعة', 'char', required=True),
                        Field('order_type', 'نوع الطلب', 'select', required=True,
                              options='order_type', default='personal'),
                        Field('guest_count', 'عدد الحضور', 'int', default=1),
                        Field('location_id', 'الموقع', 'm2o',
                              comodel='care.cafm.location', domain_facility=True),
                        Field('note', 'ملاحظة', 'text'),
                    ])),
            Section('menu', 'قائمة الأصناف', 'care.hosp.item', _r_hosp_item, icon='\u2615',
                    scope='global',
                    empty_text='لم تُضَف أصناف للقائمة بعد.'),
            Section('categories', 'الأقسام', 'care.hosp.category',
                    _r_generic(lambda r: r.display_name), icon='\U0001f5c2', scope='global'),
            Section('limits', 'حدود الاستهلاك', 'care.hosp.limit',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _sel(r, 'period').get(getattr(r, 'period', ''), '')),
                    icon='\U0001f6d1', scope='global',
                    empty_text='لا توجد سياسات حدود — الاستهلاك مفتوح.'),
        ]),
        'valet': ('صف السيارات', '\U0001f697', [
            Section('tickets', 'التذاكر', 'care.valet.ticket', _r_valet_ticket, icon='\U0001f39f',
                    empty_text='لا توجد تذاكر بعد.',
                    create=Create('تسجيل مركبة', 'record_manage', [
                        Field('plate', 'رقم اللوحة', 'char', required=True),
                        Field('guest_name', 'اسم الضيف', 'char'),
                        Field('guest_phone', 'هاتف الضيف', 'char'),
                        Field('car_make', 'الماركة', 'char'),
                        Field('car_color', 'اللون', 'char'),
                        Field('key_tag', 'رقم المفتاح', 'char'),
                    ])),
            Section('zones', 'المواقف', 'care.valet.zone',
                    _r_generic(lambda r: r.display_name), icon='\U0001f17f'),
            Section('shifts', 'الورديات', 'care.valet.shift',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None))), icon='\U0001f552'),
        ]),
        'inventory': ('المخزون', '📦', [
            Section('stores', 'المخازن', 'care.cafm.store',
                    _r_generic(lambda r: r.display_name), icon='🏬'),
            Section('moves', 'الحركات', 'care.cafm.stock.move',
                    _r_generic(lambda r: r.display_name,
                               lambda r: _d(getattr(r, 'date', None)),
                               lambda r: _state_pill(r, 'move_type', 'info')), icon='🔄'),
            Section('items', 'الأصناف والأرصدة', 'care.cafm.stock.item',
                    _r_stock_item, icon='📋',
                    empty_text='لا توجد أصناف مسجّلة في مخازن هذا المرفق.'),
            Section('counts', 'الجرد', 'care.cafm.stock.count',
                    _r_stock_count, icon='🧮',
                    empty_text='لم يُجرَ جرد بعد — ابدأ جردًا لمطابقة الرصيد الدفتري بالواقع.',
                    create=Create('بدء جرد', 'inventory_policy', [
                        Field('store_id', 'المخزن', 'm2o', required=True,
                              comodel='care.cafm.store', domain_facility=True),
                        Field('count_type', 'نوع الجرد', 'select', required=True,
                              options='count_type', default='cycle'),
                        Field('count_date', 'تاريخ الجرد', 'date'),
                        Field('note', 'ملاحظة', 'text'),
                    ])),
            Section('requests', 'طلبات التعويض', 'care.cafm.stock.request',
                    _r_stock_request, icon='📥',
                    empty_text='لا توجد طلبات تعويض — تُنشأ تلقائيًا عند نزول صنف تحت حدّه الأدنى.',
                    create=Create('طلب تعويض', 'inventory_issue', [
                        Field('store_id', 'المخزن الطالب', 'm2o', required=True,
                              comodel='care.cafm.store', domain_facility=True),
                        Field('urgency', 'الأولوية', 'select', required=True,
                              options='urgency', default='normal'),
                        Field('needed_by', 'مطلوب بحلول', 'date'),
                        Field('reason', 'المبرّر', 'text', required=True),
                    ])),
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

    # ---- full record control -------------------------------------------
    # 33 of the 39 sections shipped read-only. Rather than hand-writing 33
    # forms (and 33 more chances to drift), a section with no declared Create
    # builds one from the model's own field definitions — required fields
    # first, then the common describing fields — gated on the record_manage
    # capability. Declared specs still win: curation beats generation.
    AUTO_SKIP = {
        'company_id', 'active', 'color', 'sequence', 'name',
        'create_uid', 'write_uid', 'message_ids', 'activity_ids',
    }
    AUTO_KINDS = {'char': 'char', 'text': 'text', 'integer': 'int',
                  'float': 'float', 'date': 'date', 'datetime': 'datetime',
                  'boolean': 'bool', 'selection': 'select', 'many2one': 'm2o'}

    def _effective_create(self, section):
        """The section's declared Create, or one generated from the model."""
        if section.create:
            return section.create
        env = request.env
        if section.model not in env:
            return None
        Model = env[section.model]
        fac_field = 'facility_id' if 'facility_id' in Model._fields else None
        picked = []
        for fname, f in Model._fields.items():
            if fname in self.AUTO_SKIP or fname == fac_field:
                continue
            kind = self.AUTO_KINDS.get(f.type)
            if not kind or f.compute or getattr(f, 'related', None) or f.readonly:
                continue
            if kind == 'm2o' and not f.comodel_name:
                continue
            picked.append((not f.required, fname, f, kind))
        picked.sort(key=lambda t: t[0])          # required fields first
        fields = []
        for _opt, fname, f, kind in picked[:10]:
            fields.append(Field(
                fname, f.string or fname, kind, required=bool(f.required),
                comodel=f.comodel_name if kind == 'm2o' else None,
                domain_facility=bool(
                    kind == 'm2o' and f.comodel_name and
                    'facility_id' in env[f.comodel_name]._fields),
                options=fname if kind == 'select' else None))
        if not fields:
            return None
        return Create('إضافة سجل', 'record_manage', fields,
                      facility_field=fac_field)

    def _cancel_record(self, section, rid):
        """Cancel/remove one record, the least destructive way that sticks:
        a cancel state if the model has one, else archive, else unlink —
        so 'إلغاء' never silently destroys a paper trail that had one."""
        env = request.env
        rec = env[section.model].sudo().browse(int(rid)).exists()
        if not rec:
            raise ValueError('السجل غير موجود')
        facs = self._facilities()
        rec_fac = getattr(rec, 'facility_id', None)
        if rec_fac and rec_fac.id not in facs.ids:
            raise ValueError('السجل خارج نطاق مرافقك')
        st = rec._fields.get('state')
        if st and st.type == 'selection':
            keys = [k for k, _l in (st.selection or []) if isinstance(st.selection, list)]
            if 'cancelled' in keys:
                rec.write({'state': 'cancelled'}); return 'cancelled'
            if 'cancel' in keys:
                rec.write({'state': 'cancel'}); return 'cancelled'
        if 'active' in rec._fields:
            rec.write({'active': False}); return 'archived'
        rec.unlink()
        return 'deleted'

    def _create_record(self, section, post):
        """Build values from a posted form and create the record.

        Shared by the HTML form and the JSON API so the two cannot disagree
        about what a field means or which facility a record lands in.
        """
        env = request.env
        c = self._effective_create(section)
        facs = self._facilities()
        vals = {}
        fid = int(post.get('__facility') or 0) or (facs[:1].id or 0)
        if c.facility_field and fid in facs.ids:
            vals[c.facility_field] = fid
        for f in c.fields:
            raw = post.get(f.name)
            if f.kind == 'bool':
                vals[f.name] = raw in (True, 'true', 'on', '1', 1)
                continue
            if raw in (None, ''):
                continue
            if f.kind in ('int', 'm2o'):
                try:
                    vals[f.name] = int(raw)
                except (TypeError, ValueError):
                    continue
            elif f.kind == 'float':
                try:
                    vals[f.name] = float(raw)
                except (TypeError, ValueError):
                    continue
            elif f.kind == 'datetime':
                vals[f.name] = str(raw).replace('T', ' ') + (':00' if len(str(raw)) == 16 else '')
            else:
                vals[f.name] = raw
        return env[section.model].sudo().create(vals)

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
        c = self._effective_create(section)
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
        c = self._effective_create(section) if section else None
        if not c:
            return request.redirect('/cafm/m/svc/%s' % code)
        if not self._may(c.perm):
            return _shell('غير مصرّح', Markup(
                '<div class="card"><div class="h4">⛔ غير مصرّح</div>'
                '<div class="muted">حسابك لا يملك صلاحية «%s». اطلبها من صفحة الصلاحيات.</div>'
                '<a class="btn g" href="/cafm/m/permissions">صلاحياتي</a></div>') % esc(c.label),
                accent=accent_for(code), back='/cafm/m/svc/%s/%s' % (code, key))

        try:
            self._create_record(section, post)
        except Exception as e:
            msg = str(getattr(e, 'args', [e])[0] if getattr(e, 'args', None) else e)
            return _shell('تعذّر الحفظ', Markup(
                '<div class="card"><div class="h4">⛔ لم يُحفظ السجل</div>'
                '<div class="muted" style="margin-top:6px">%s</div>'
                '<a class="btn g" href="/cafm/m/svc/%s/%s">رجوع</a></div>') % (
                    esc(msg), code, key),
                accent=accent_for(code), back='/cafm/m/svc/%s/%s' % (code, key))
        return request.redirect('/cafm/m/svc/%s/%s' % (code, key))

    @http.route('/cafm/m/svc/<string:code>/<string:key>/<int:rid>/cancel',
                type='http', auth='user', methods=['POST'], website=False, csrf=True)
    def section_cancel(self, code, key, rid, **post):
        reg = REGISTRY().get(code)
        section = next((s for s in reg[2] if s.key == key), None) if reg else None
        if not section:
            return request.redirect('/cafm/m')
        if not self._may('record_manage'):
            return _shell('غير مصرّح', Markup(
                '<div class="card"><div class="h4">⛔ غير مصرّح</div>'
                '<div class="muted">إلغاء السجلات يتطلب صلاحية «إدارة السجلات».</div></div>'),
                accent=accent_for(code), back='/cafm/m/svc/%s/%s' % (code, key))
        try:
            self._cancel_record(section, rid)
        except Exception:
            pass
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
