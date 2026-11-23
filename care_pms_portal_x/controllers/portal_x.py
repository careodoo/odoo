# -*- coding: utf-8 -*-
# الشكل الجديد لبورتال إدارة المشاريع على رابط مستقلّ (/my/pm/x).
# يقدّم ملف الموكاب (static/src/pm_x_app.html) لكن **ببيانات حقيقية** مُحقَنة عبر window.PMX
# (مشاريع المستخدم، مؤشّرات المشروع، وبيانات كل قسم من موديله الحقيقي بأشكال محرّك الـSPA).
import os
import json
import logging
from odoo import http, fields
from odoo.exceptions import UserError, ValidationError, AccessError, AccessDenied, MissingError
from odoo.http import request
from odoo.addons.care_pms.controllers.pm_portal import PMManagerPortal

_logger = logging.getLogger(__name__)


def _x_safe_error(e):
    """رسالة خطأ آمنة وموجَّهة للمستخدم: أخطاء التحقّق/القواعد (ValidationError/UserError) تُعرض
    نصّها العربي كما هو، وأخطاء الصلاحية/السجل المفقود تُلخَّص برسالة عامّة (لأن نصّها يكشف اسم
    النموذج/السجل)، وأيّ خطأ تقنيّ آخر يُسجَّل ويُعرض بدله رسالة عامّة بلا تفاصيل داخلية.
    ملاحظة مهمّة: AccessError/AccessDenied/MissingError جميعها فروع من UserError في أودو، لذا
    يجب فحصها قبل فرع (ValidationError, UserError) وإلّا تسرّب نصّها التقنيّ."""
    if isinstance(e, (AccessError, AccessDenied)):
        return 'لا تملك صلاحية لتنفيذ هذا الإجراء.'
    if isinstance(e, MissingError):
        return 'السجلّ غير موجود أو حُذِف.'
    if isinstance(e, (ValidationError, UserError)):
        try:
            return str(e.args[0])[:240]
        except Exception:
            return str(e)[:240]
    _logger.exception('PM-X portal create/update failed')
    return 'تعذّر الحفظ — تحقّق من صحّة البيانات المدخلة وحاول مجددًا.'

_APP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'src', 'pm_x_app.html')

# خريطة حالة العامل → (pill class, نص)
_WS = {
    'active': ('ok', 'نشط'), 'new': ('info', 'جديد'), 'on_leave': ('mut', 'في إجازة'),
    'suspended': ('crit', 'موقوف'), 'absence': ('warn', 'غياب'), 'absconding': ('crit', 'هروب'),
    'arrested': ('crit', 'محتجز'), 'resignation': ('mut', 'استقالة'), 'eos': ('mut', 'نهاية خدمة'),
}


# حالات «منتهية» لا تمنع طلباً جديداً ولا تُلغى (الطلب أُنجز/اعتُمد/رُفض/أُلغي)
_X_DONE_STATES = {
    'done', 'validate', 'validate1', 'validated', 'approve', 'approved', 'approved1',
    'refuse', 'refused', 'reject', 'rejected', 'cancel', 'cancelled', 'canceled',
    'posted', 'paid', 'issued', 'closed', 'close', 'completed', 'complete', 'settled',
    'expired', 'returned', 'active', 'running', 'lifted', 'eos', 'exit',
    '1_done', '1_canceled', '2_done', '3_approved',
}
# حالات «مسوّدة» تُلغى/تُعدَّل من البوابة
_X_DRAFT_STATES = {'draft', 'new', '', False, None, '/', 'to_submit', '0_draft'}
# #11: حقول مالية حسّاسة لا تُعرض لمدير المشروع (أرقام حسابات/دفاتر/قواعد رواتب/تحليلي/بطاقات بنكية)
_X_SENSITIVE = ('account_id', 'journal', 'salary_rule', 'analytic', 'bank_account', 'acc_number', 'iban')

# موديلات عامّة مشتركة تُعرَض للقراءة/الطباعة فقط — يُمنع أي تعديل/حذف/إجراء عليها من البوابة
_X_READONLY_MODELS = ('petrol.tank', 'care.cafm.catalog.item')


def _dname(rec):
    """اسم العرض مراعيًا العربية: الموظفون display_name لديهم = الاسم الإنجليزي،
    فنستخدم name (العربي). لغير الموظفين display_name كالمعتاد."""
    try:
        if not rec:
            return ''
        if rec._name in ('hr.employee', 'hr.department', 'project.project'):
            # نُفضّل الاسم المباشر (غالبًا العربي) على display_name الذي قد يكون الاسم الإنجليزي
            # (الموظفون) أو سلسلة الأقسام الأب (complete_name) بالإنجليزية.
            return rec.name or rec.display_name or ''
        return rec.display_name or ''
    except Exception:
        return ''


def _sel_label_rec(rec, field='state'):
    """تسمية حقل اختيار (مترجَمة) بدل الكود الخام — عامّة على أي سجلّ (تُستعمل في شارات القوائم)."""
    try:
        v = getattr(rec, field, None)
        if v and field in rec._fields and rec._fields[field].type == 'selection':
            return dict(rec._fields[field]._description_selection(rec.env)).get(v, v) or ''
        return v or ''
    except Exception:
        return getattr(rec, field, '') or ''


def _wstag(emp):
    """وسم حالة العامل (صنف، نص، معرّف العامل للصورة) لإلحاقه بخلية اسم العامل في كل الأقسام.
    العنصر الثالث = emp.id لعرض صورة العامل القابلة للنقر. قائمة فارغة إن لم يتوفّر الموظف."""
    try:
        if not emp:
            return []
        st = getattr(emp, 'worker_status', None) or 'active'
        cls, txt = _WS.get(st, ('ok', 'نشط'))
        return [cls, txt, emp.id]
    except Exception:
        return []


def _f(v):
    """رقم آمن للعرض (بفواصل آلاف بلا كسور للأعداد الكبيرة)."""
    try:
        v = float(v or 0)
        return '{:,.0f}'.format(v) if abs(v) >= 1000 else ('{:,.3f}'.format(v) if v and v != int(v) else str(int(v)))
    except Exception:
        return str(v or 0)


def _stat(label, value, icon, accent='var(--navy-600)', trend='flat', delta='—', spark=None):
    return [label, value, 'si:' + icon, 'accent:' + accent, trend, delta, 'spark:' + json.dumps(spark or [value or 0])]


# خريطة كود القسم → الموديل الحقيقي (للطباعة/الفتح/الإجراءات على السجل)
CODE_MODEL = {
    'allowances': 'care.allowance', 'contracts': 'care.experience', 'invoices': 'request.invoice',
    'petty': 'care.pms.petty.cash', 'permits': 'care.permit.request', 'overtime': 'overtime.request',
    'penalties': 'care.penalty', 'bonuses': 'care.bonus', 'timesheet': 'care.timesheet',
    'discipline': 'care.complaint',
    'deliveries': 'care.pms.delivery.note', 'supplies': 'care.pms.supply', 'manpower': 'manpower.requisition',
    'grn': 'care.pms.supply.receipt',
    'workshops': 'c2c.workshop', 'extrawork': 'care.extra.work', 'tasks': 'project.task',
    'requests': 'care.document.request', 'materials': 'care.pms.material',
    'suspension': 'care.suspension.request.line', 'resume': 'care.resume.request.line',
    'attendance': 'hr.attendance', 'vehicles': 'fleet.vehicle', 'security': 'care.cafm.shift',
    'items': 'care.cafm.request', 'store': 'care.cafm.catalog.item', 'storeorder': 'care.pms.store.order',
    'fuel': 'care.fuel.entry', 'fuelcard': 'care.fuel.card', 'letters': 'care.letter', 'additional': 'employee.shift.request',
    'assets': 'care.custody', 'passets': 'account.asset', 'assetdeliv': 'care.asset.delivery', 'petrol': 'petrol.tank',
    'leaves': 'hr.leave', 'passports': 'care.passport.request', 'loans': 'care.loan',
    'resignations': 'hr.employee.resignation', 'eos': 'care.eos', 'xts': 'care.extra.timesheet',
    # ---- إجراءات العامل (إنشاء من ملف 360°) ----
    'permission': 'permission.request', 'absence': 'hr.action.absence',
    'leavereturn': 'hr.action.leave.return', 'joining': 'hr.action.joining',
    'clearance': 'hr.action.clearance', 'salarycert': 'care.salary.certificate',
    'expcert': 'care.experience.certificate', 'perfeval': 'care.performance.log',
    'exitint': 'exit.interview', 'govtx': 'care.gov.transaction',
    'uniform': 'uniform.delivery', 'bankcard': 'care.bank.card.request',
    'expense': 'care.expense.claim',
    'transport': 'care.transport.request',
    'substitution': 'care.worker.substitution',
    'handover': 'care.vehicle.handover',
}


class PMPortalX(PMManagerPortal):

    def _pm_projects(self):
        """مشاريع المدير: مدير المشروع المخصّص + مستخدمو البوابة. ولمن **لا إسناد رسمي له**
        (قائمة الأساس فارغة) نعرض مشاريعه كمسؤول/مالك (user_id) حتى لا يظهر البورتال فارغًا —
        دون منح المستوردين/المنشئين الذين لهم إسناد رسمي مشاريعَ زائدة."""
        base = super()._pm_projects()
        if base:
            return base
        # مفوَّض (#19): أرجع مشاريع تفويضاته ليعمل البورتال في وضع التفويض
        try:
            restr = self._x_delegate_restriction()
            if restr and restr.get('project_ids'):
                return request.env['project.project'].sudo().browse(restr['project_ids']).exists()
        except Exception:
            pass
        try:
            return request.env['project.project'].sudo().search(
                [('user_id', '=', request.env.user.id)])
        except Exception:
            return base

    # ============ KPIs ============
    def _x_kpis(self, p):
        g = lambda f: getattr(p, f, 0) or 0
        return [
            ['team', 'العمّال', g('worker_count'), 'teal', '—', 'flat', 'team'],
            ['grid3', 'المهام المفتوحة', g('pms_task_open'), 'sky', '—', 'flat', 'tasks'],
            ['alert', 'مهام متأخّرة', g('pms_task_overdue'), 'rose', '—', 'flat', 'tasks'],
            ['shield', 'إقامات تنتهي', g('compliance_count'), 'amber', '—', 'flat', 'compliance'],
            ['asset', 'أصول المشروع', g('asset_count'), 'violet', '—', 'flat', 'passets'],
            ['truck', 'المركبات', g('vehicle_count'), 'indigo', '—', 'flat', 'vehicles'],
            ['bank', 'الإيراد الشهري', _f(g('pms_revenue')), 'emerald', '—', 'flat', 'finance'],
            ['cash', 'تكلفة العمالة', _f(g('pms_labor_cost')), 'teal', '—', 'flat', 'finance'],
            ['truck', 'تكلفة الأسطول', _f(g('pms_fleet_cost')), 'sky', '—', 'flat', 'vehicles'],
            ['cash', 'المصروف النقدي', _f(g('pms_petty_spent')), 'amber', '—', 'flat', 'petty'],
            ['chart', 'هامش الربح', str(int(g('pms_margin_pct'))) + '%', 'emerald', '—', 'flat', 'finance'],
            ['chart', 'نسبة الالتزام', str(int(g('sla_compliance_pct'))) + '%', 'blue', '—', 'flat', 'performance'],
            ['doc', 'العقود', g('experience_count'), 'plum', '—', 'flat', 'contracts'],
            ['ship', 'التوريدات', g('supply_count'), 'sky', '—', 'flat', 'supplies'],
            ['cash', 'العُهد النقدية', g('pettycash_count') or g('custody_count'), 'violet', '—', 'flat', 'petty'],
            ['fuel', 'عمليات الوقود', g('fuel_count'), 'rose', '—', 'flat', 'fuel'],
            ['box', 'المواد', g('material_count'), 'teal', '—', 'flat', 'materials'],
            ['group3', 'طلبات النقل', g('shift_request_count'), 'indigo', '—', 'flat', 'additional'],
            ['truck', 'المواصلات', g('transport_request_count'), 'sky', '—', 'flat', 'transport'],
            ['group3', 'الإحلال (البديل)', g('substitution_count'), 'violet', '—', 'flat', 'substitution'],
        ]

    # ============ Sections (real data) ============
    def _x_sections(self, p):
        env = request.env
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        dept_id = dept.id if dept else 0
        # معرّفات عمّال المشروع (قسمه وفروعه) — متاحة لكل البناة
        emp_ids = env['hr.employee'].sudo().search(self._x_emp_dom(dept_id)).ids if dept_id else []
        S = {}

        # هل لموديل القسم تقرير PDF قابل للطباعة؟ (يشمل تقرير سجلّ الأصل عبر الحقول الشائعة)
        # يُستخدم لإخفاء زر الطباعة في القوائم على الموديولات بلا تقرير (كان يؤدي لصفحة «لا يوجد تقرير») — M1
        _rep_cache = {}

        def _model_has_report(mdl):
            if not mdl:
                return False
            if mdl in _rep_cache:
                return _rep_cache[mdl]
            Rep = env['ir.actions.report'].sudo()
            ok = bool(Rep.search_count([('model', '=', mdl), ('report_type', '=', 'qweb-pdf')]))
            if not ok and mdl in env:
                flds = env[mdl]._fields
                for pf in ('request_id', 'parent_id', 'move_id', 'order_id', 'batch_id'):
                    f = flds.get(pf)
                    cm = getattr(f, 'comodel_name', None) if f else None
                    if cm and Rep.search_count([('model', '=', cm), ('report_type', '=', 'qweb-pdf')]):
                        ok = True
                        break
            _rep_cache[mdl] = ok
            return ok

        def safe(code, fn):
            try:
                res = fn()
                if isinstance(res, dict) and 'can_print' not in res:
                    res['can_print'] = _model_has_report(CODE_MODEL.get(code))
                S[code] = res
            except Exception:
                pass

        # ---- الفريق والعمّال ----
        def _team():
            Emp = env['hr.employee'].sudo()
            edom = self._x_emp_dom(dept_id) if dept_id else [('id', '=', 0)]
            # الإجماليات والتفصيل بالحالة عبر read_group/search_count (لا تحميل آلاف السجلّات)
            total = Emp.search_count(edom) if dept_id else 0
            by = {}
            if dept_id and 'worker_status' in Emp._fields:
                for g in Emp.read_group(edom, ['worker_status'], ['worker_status'], lazy=False):
                    by[g.get('worker_status') or 'active'] = g.get('__count', 0)
            rows, ids = [], []
            for e in (Emp.search(edom, order='name', limit=100000) if dept_id else Emp.browse()):
                st = getattr(e, 'worker_status', 'active') or 'active'
                cls, txt = _WS.get(st, ('ok', 'نشط'))
                rows.append([['f', e.name, '#' + (e.barcode or str(e.id)), '', '', e.id],
                             'pill:%s:%s' % (cls, txt),
                             (e.job_title or e.job_id.name or '—'),
                             (e.department_id.name or '—')])
                ids.append(e.id)
            return {'cols': ['العامل', 'الحالة', 'المهنة', 'الإدارة', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('العمّال', total, 'team'),
                              _stat('نشطون', by.get('active', 0), 'check', 'var(--ok)', 'up'),
                              _stat('في إجازة', by.get('on_leave', 0), 'clock', 'var(--warn)'),
                              _stat('موقوفون', by.get('suspended', 0), 'pause', 'var(--crit)')]}
        safe('team', _team)

        # ---- التاسكات (كانبان) ----
        def _tasks():
            Task = env['project.task'].sudo()
            tasks = Task.search([('project_id', '=', p.id)], limit=100000)
            stages = {}
            colr = {0: 'info', 1: 'warn', 2: 'violet', 3: 'ok'}
            flat_rows, flat_ids = [], []  # قائمة مسطّحة لفتح تفاصيل المهمة الحقيقية
            for idx, t in enumerate(tasks):
                sg = t.stage_id.name or 'عام'
                stages.setdefault(sg, [])
                # العنصر الأخير = الفهرس المسطّح (ليفتح الكانبان السجلّ الصحيح)
                stages[sg].append([t.name or '—', 'مهمة',
                                   (t.user_ids[:1].name if t.user_ids else '—'),
                                   str(t.date_deadline or ''), idx])
                flat_rows.append([['TASK', t.name or '—', ''],
                                  'pill:info:%s' % (t.stage_id.name or ''),
                                  str(t.date_deadline or '')])
                flat_ids.append(t.id)
            out = [[sg, colr.get(i, 'info'), rows] for i, (sg, rows) in enumerate(list(stages.items())[:6])]
            done = len(tasks.filtered(lambda t: t.stage_id.fold)) if tasks else 0
            return {'stages': out, 'rows': flat_rows, 'ids': flat_ids,
                    'stats': [_stat('مهام مفتوحة', getattr(p, 'pms_task_open', 0) or 0, 'grid3'),
                              _stat('متأخّرة', getattr(p, 'pms_task_overdue', 0) or 0, 'alert', 'var(--crit)'),
                              _stat('الإجمالي', len(tasks), 'grid3', 'var(--navy-600)'),
                              _stat('منجزة', done, 'check', 'var(--ok)', 'up')]}
        safe('tasks', _tasks)

        # ---- المواد ----
        def _materials():
            mats = env['care.pms.material'].sudo().search([('project_id', '=', p.id)])
            cards, ids, low = [], [], 0
            for m in mats:
                islow = bool(getattr(m, 'is_low', False))
                low += 1 if islow else 0
                # بطاقة بصورة المنتج: [اسم, وحدة, متاح, مستلَم, مصروف, منخفض؟, product_id(للصورة)]
                cards.append([m.name or (m.product_id.display_name or '—'),
                              m.uom_name or 'وحدة',
                              _f(getattr(m, 'available_qty', 0)),
                              _f(getattr(m, 'received_qty', 0)),
                              _f(getattr(m, 'issued_qty', 0)),
                              islow, (m.product_id.id or 0)])
                ids.append(m.id)
            return {'cards': cards, 'ids': ids,
                    'stats': [_stat('أصناف', len(mats), 'box'),
                              _stat('متوفّرة', len(mats) - low, 'check', 'var(--ok)'),
                              _stat('منخفضة', low, 'alert', 'var(--warn)', 'down')]}
        safe('materials', _materials)

        # ---- التوريدات ----
        def _supplies():
            sup = env['care.pms.supply'].sudo().search([('project_id', '=', p.id)], limit=100000)
            st = dict(env['care.pms.supply']._fields['state']._description_selection(env)) if 'state' in env['care.pms.supply']._fields else {}
            rows = [[['SUP', s.name or '—', ''], 'pill:info:%s' % (st.get(s.state, s.state or '')),
                     str(s.date or ''), (s.receiver_name or '—'), (s.delivery_note_name or '—')] for s in sup]
            rec = len(sup.filtered(lambda s: s.state in ('received', 'done'))) if sup else 0
            return {'cols': ['التوريد', 'الحالة', 'التاريخ', 'المستلِم', 'سند', ''], 'rows': rows, 'ids': [s.id for s in sup],
                    'stats': [_stat('توريدات', len(sup), 'truck'),
                              _stat('مستلَمة', rec, 'check', 'var(--ok)', 'up'),
                              _stat('قيد الاستلام', len(sup) - rec, 'clock', 'var(--warn)')]}
        safe('supplies', _supplies)

        # ---- المواصلات (للقراءة: طلبات + رحلات المشروع) ----
        def _transport():
            TR = env.get('care.transport.request')
            if TR is None:
                return {'cols': ['الطلب', '', '', '', ''], 'rows': [], 'ids': [],
                        'stats': [_stat('طلبات', 0, 'truck')]}
            reqs = TR.sudo().search([('project_id', '=', p.id)], order='id desc', limit=100000)
            kinds = dict(TR._fields['transport_kind']._description_selection(env))
            sts = dict(TR._fields['state']._description_selection(env))
            _cls = {'draft': 'mut', 'submitted': 'info', 'approved': 'ok',
                    'converted': 'ok', 'rejected': 'crit'}
            rows = []
            for r in reqs:
                route = '%s ← %s' % (r.destination_location_id.name or '—',
                                     r.origin_location_id.name or '—')
                rows.append([['TRQ', r.name or '—', ''],
                             'pill:%s:%s' % (_cls.get(r.state, 'info'), sts.get(r.state, r.state or '')),
                             kinds.get(r.transport_kind, '—'),
                             route,
                             str(r.needed_date or '')])
            pend = len(reqs.filtered(lambda x: x.state == 'submitted'))
            conv = len(reqs.filtered(lambda x: x.state == 'converted'))
            return {'cols': ['الطلب', 'الحالة', 'الوسيلة', 'المسار', 'التاريخ'],
                    'rows': rows, 'ids': reqs.ids, 'can_print': False,
                    'stats': [_stat('طلبات النقل', len(reqs), 'truck'),
                              _stat('بانتظار الاعتماد', pend, 'clock', 'var(--warn)'),
                              _stat('محوّلة لرحلات', conv, 'check', 'var(--ok)', 'up')]}
        safe('transport', _transport)

        # ---- محاضر استلام السيارات (fleet) — عرض + طباعة لمحاضر المشروع ----
        def _handover():
            HO = env.get('care.vehicle.handover')
            if HO is None:
                return {'cols': ['الرقم', '', '', '', ''], 'rows': [], 'ids': [],
                        'stats': [_stat('المحاضر', 0, 'truck')]}
            recs = HO.sudo().search(
                ['|', ('project_id', '=', p.id), ('pm_id', '=', env.user.id)],
                order='id desc', limit=100000)
            sts = dict(HO._fields['state']._description_selection(env))
            _cls = {'draft': 'mut', 'submitted': 'info', 'approved': 'ok', 'rejected': 'crit'}
            rows = []
            for r in recs:
                rows.append([['VHR', r.name or '—', ''],
                             'pill:%s:%s' % (_cls.get(r.state, 'info'), sts.get(r.state, r.state or '')),
                             r.vehicle_id.license_plate or r.vehicle_id.name or '—',
                             r.to_driver_name or '—',
                             str(r.handover_date or '')])
            pend = len(recs.filtered(lambda x: x.state == 'submitted'))
            appr = len(recs.filtered(lambda x: x.state == 'approved'))
            return {'cols': ['الرقم', 'الحالة', 'المركبة', 'المستلم', 'التاريخ'],
                    'rows': rows, 'ids': recs.ids, 'can_print': True,
                    'stats': [_stat('محاضر الاستلام', len(recs), 'truck'),
                              _stat('بانتظار مدير الفليت', pend, 'clock', 'var(--warn)'),
                              _stat('معتمدة', appr, 'check', 'var(--ok)', 'up')]}
        safe('handover', _handover)

        # ---- الإحلال (البديل عن الغائب) ----
        def _substitution():
            SB = env.get('care.worker.substitution')
            if SB is None:
                return {'cols': ['الطلب', '', '', '', ''], 'rows': [], 'ids': [],
                        'stats': [_stat('طلبات', 0, 'group3')]}
            reqs = SB.sudo().search([('project_id', '=', p.id)], order='id desc', limit=100000)
            sts = dict(SB._fields['state']._description_selection(env))
            rules = dict(SB._fields['price_rule']._description_selection(env))
            _cls = {'draft': 'mut', 'submitted': 'info', 'approved': 'ok',
                    'applied': 'ok', 'rejected': 'crit'}
            rows = []
            total_cost = 0.0
            total_days = 0
            for r in reqs:
                total_cost += r.total_cost or 0.0
                total_days += r.day_count or 0
                rows.append([['SUB', r.name or '—', ''],
                             (r.month_key or '—'),
                             'pill:%s:%s' % (_cls.get(r.state, 'info'), sts.get(r.state, r.state or '')),
                             '%s ← %s' % (r.substitute_employee_id.name or '—', r.absent_employee_id.name or '—'),
                             (r.timesheet_id.name or '—'),
                             str(r.day_count or 0),
                             rules.get(r.price_rule, '—'),
                             _f(r.total_cost or 0.0)])
            pend = len(reqs.filtered(lambda x: x.state == 'submitted'))
            applied = len(reqs.filtered(lambda x: x.state == 'applied'))
            return {'cols': ['الطلب', 'الشهر', 'الحالة', 'البديل ← الغائب', 'الكشف', 'الأيام', 'التسعير', 'التكلفة'],
                    'rows': rows, 'ids': reqs.ids,
                    'stats': [_stat('طلبات الإحلال', len(reqs), 'group3'),
                              _stat('بانتظار الاعتماد', pend, 'clock', 'var(--warn)'),
                              _stat('مطبَّقة', applied, 'check', 'var(--ok)', 'up'),
                              _stat('إجمالي الأيام', total_days, 'calendar', 'var(--navy-600)'),
                              _stat('إجمالي التكلفة', _f(total_cost), 'cash', 'var(--navy-600)')]}
        safe('substitution', _substitution)

        # ---- سندات التسليم ----
        def _deliveries():
            dn = env['care.pms.delivery.note'].sudo().search([('project_id', '=', p.id)], limit=100000)
            rows = [[['DN', d.name or '—', ''], 'pill:ok:%s' % (_sel_label_rec(d) or 'مسلّم'),
                     str(d.date or ''), (d.receiver_name or '—')] for d in dn]
            return {'cols': ['السند', 'الحالة', 'التاريخ', 'المستلِم', ''], 'rows': rows, 'ids': [d.id for d in dn],
                    'stats': [_stat('سندات', len(dn), 'ship'), _stat('هذا الشهر', len(dn), 'check', 'var(--ok)')]}
        safe('deliveries', _deliveries)

        # ---- العهدة النقدية ----
        def _petty():
            cash = env['care.pms.petty.cash'].sudo().search([('project_id', '=', p.id)], limit=100000)
            bal = sum(cash.mapped(lambda c: getattr(c, 'remaining', 0) or 0))
            spent = sum(cash.mapped(lambda c: getattr(c, 'spent', 0) or 0))
            rows = [[['CASH', c.name or '—', ''], 'pill:info:%s' % _sel_label_rec(c),
                     str(c.date or c.request_date or ''), _f(c.amount), _f(getattr(c, 'remaining', 0))] for c in cash]
            return {'cols': ['العهدة', 'الحالة', 'التاريخ', 'المبلغ', 'المتبقّي', ''], 'rows': rows, 'ids': [c.id for c in cash],
                    'stats': [_stat('الرصيد', _f(bal), 'cash', 'var(--ok)'),
                              _stat('المصروف', _f(spent), 'chart', 'var(--warn)'),
                              _stat('عُهد', len(cash), 'invoice', 'var(--navy-600)')]}
        safe('petty', _petty)

        # ---- العقود ----
        def _contracts():
            exp = env['care.experience'].sudo()
            dom = [('project_id', '=', p.id)]
            cons = exp.search(dom, limit=100000) if dom else exp.browse()
            rows = [[['DOC', c.name or '—', (c.partner_id.name or '')], 'pill:%s:%s' % (
                'ok' if (c.state or '') not in ('expired',) else 'crit', c.expiry_state or c.state or ''),
                str(c.start_date or ''), str(c.expire_date or ''), _f(getattr(c, 'contract_amount', 0))] for c in cons]
            return {'cols': ['العقد', 'الحالة', 'البدء', 'الانتهاء', 'القيمة', ''], 'rows': rows, 'ids': [c.id for c in cons],
                    'stats': [_stat('عقود', len(cons), 'doc'),
                              _stat('سارية', len(cons.filtered(lambda c: (c.expiry_state or '') not in ('expired', 'expiring'))), 'check', 'var(--ok)')]}
        safe('contracts', _contracts)

        # ---- فواتير/طلبات الفواتير ----
        def _invoices():
            RI = env['request.invoice'].sudo()
            dom = [('project_id', '=', p.id)]
            invs = RI.search(dom, limit=100000) if dom else RI.browse()
            total = sum(invs.mapped(lambda i: getattr(i, 'amount_total', 0) or 0))
            rows = [[['INV', i.name or '—', (i.partner_id.name or '')], 'pill:info:%s' % _sel_label_rec(i),
                     str(i.invoice_date or ''), _f(getattr(i, 'amount_total', 0))] for i in invs]
            return {'cols': ['الفاتورة', 'الحالة', 'التاريخ', 'المبلغ', ''], 'rows': rows, 'ids': [i.id for i in invs],
                    'stats': [_stat('الإجمالي', _f(total), 'invoice'), _stat('عدد', len(invs), 'doc', 'var(--navy-600)')]}
        safe('invoices', _invoices)

        # ---- الامتثال والإقامات ----
        def _compliance():
            import datetime as _dt
            Emp = env['hr.employee'].sudo()
            today = _dt.date.today()
            docs = [('residency_end_date', 'الإقامة'), ('work_permit_expiration_date', 'تصريح العمل'),
                    ('affairs_permit_end_date', 'تصريح الشؤون'), ('visa_expire', 'التأشيرة')]
            docs = [(f, lab) for f, lab in docs if f in Emp._fields]
            if not dept_id or not docs:
                return {'cols': ['العامل', 'نوع المستند', 'تاريخ الانتهاء', 'المتبقّي', ''], 'rows': [], 'ids': [],
                        'stats': [_stat('عمّال', 0, 'team', 'var(--navy-600)')]}
            base = self._x_emp_dom(dept_id)

            def _cnt(lo, hi):
                tot = 0
                for f, _ in docs:
                    dom = base + [(f, '!=', False)]
                    if lo is not None:
                        dom += [(f, '>=', str(today + _dt.timedelta(days=lo)))]
                    if hi is not None:
                        dom += [(f, '<=', str(today + _dt.timedelta(days=hi)))]
                    tot += Emp.search_count(dom)
                return tot
            exp_c, c30, c60 = _cnt(None, -1), _cnt(0, 30), _cnt(31, 60)
            # صفوف: كل (عامل × مستند) ينتهي خلال 90 يومًا أو منتهٍ — مرتّبة بالأقرب انتهاءً، ملوّنة
            rows, ids = [], []
            horizon = str(today + _dt.timedelta(days=90))
            for f, lab in docs:
                for e in Emp.search(base + [(f, '!=', False), (f, '<=', horizon)], order=f, limit=100000):
                    d = getattr(e, f, False)
                    dl = (d - today).days if d else 0
                    cls = 'crit' if dl <= 30 else ('warn' if dl <= 60 else 'ok')
                    txt = ('منتهٍ منذ %d يوم' % (-dl)) if dl < 0 else ('%d يوم' % dl)
                    rows.append([['f', e.name, '#' + (e.barcode or str(e.id))] + _wstag(e),
                                 lab, str(d or '—'), 'pill:%s:%s' % (cls, txt)])
                    ids.append(e.id)
            return {'cols': ['العامل', 'نوع المستند', 'تاريخ الانتهاء', 'المتبقّي', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('منتهية', exp_c, 'alert', 'var(--crit)'),
                              _stat('خلال 30 يومًا', c30, 'shield', 'var(--crit)'),
                              _stat('خلال 60 يومًا', c60, 'clock', 'var(--warn)'),
                              _stat('عمّال', Emp.search_count(base), 'team', 'var(--navy-600)')]}
        safe('compliance', _compliance)

        # ---- طلبات المستندات ----
        def _requests():
            dr = env['care.document.request'].sudo()
            dom = self._x_emp_dom(dept_id, 'employee_id.department_id') if dept_id else []
            reqs = dr.search(dom, limit=100000) if dom else dr.browse()
            rows = [[['f', (r.employee_id.name or r.worker_name_en or '—'), r.name or ''] + _wstag(r.employee_id),
                     (r.type_id.name if getattr(r, 'type_id', False) else '—'),
                     'pill:%s:%s' % (('crit' if r.priority == '1' else 'info'), _sel_label_rec(r)),
                     str(getattr(r, 'deadline', '') or '—')] for r in reqs]
            return {'cols': ['العامل', 'نوع المستند', 'الحالة', 'الموعد', ''], 'rows': rows, 'ids': [r.id for r in reqs],
                    'stats': [_stat('طلبات', len(reqs), 'doc'),
                              _stat('عاجلة', dr.search_count(dom + [('priority', '=', '1')]) if dom else 0, 'alert', 'var(--crit)')]}
        safe('requests', _requests)

        # ---- الأصول والعُهد ----
        def _assets():
            cust = env['care.custody'].sudo().search(self._x_emp_dom(dept_id)) if (dept_id and 'care.custody' in env) else (env['care.custody'].sudo().browse() if 'care.custody' in env else [])
            cust_l = list(cust)
            rows = [[[getattr(c, 'name', '') or '—', (c.employee_id.name if getattr(c, 'employee_id', False) else '')],
                     'pill:ok:مُسلّمة', str(getattr(c, 'issue_date', '') or getattr(c, 'date', '') or getattr(c, 'custody_date', '') or getattr(c, 'create_date', '') or '')[:10]] for c in cust_l]
            return {'cols': ['العهدة', 'الحالة', 'التاريخ', ''], 'rows': rows,
                    'ids': [c.id for c in cust_l],
                    'stats': [_stat('عُهد', len(list(cust)), 'asset')]}
        safe('assets', _assets)

        # ---- أصول المشروع (account.asset) بالباركود والصور والحالة ----
        def _passets():
            A = env['account.asset'].sudo() if 'account.asset' in env else None
            if A is None:
                return {'cards': [], 'ids': [], 'stats': []}
            dom = ['|', ('project_id', '=', p.id)]
            dom += [('department_id', '=', dept_id)] if dept_id else [('project_id', '=', p.id)]
            assets = A.search(dom, limit=100000)
            cmap = {'new': ('جديد', 'ok'), 'good': ('جيّد', 'ok'), 'fair': ('مقبول', 'info'),
                    'damaged': ('تالف', 'crit'), 'lost': ('مفقود', 'crit'), 'maintenance': ('صيانة', 'warn')}
            has_cond = 'condition' in A._fields
            cards, ids, dmg = [], [], 0
            for a in assets:
                cond = getattr(a, 'condition', 'good') if has_cond else 'good'
                cl = cmap.get(cond, ('—', 'mut'))
                if cond in ('damaged', 'lost'):
                    dmg += 1
                # [اسم, فئة·باركود, قيمة, condition_class, condition_label, asset_id]
                cards.append([a.name or '—',
                              ((a.category_id.name + ' · ') if getattr(a, 'category_id', False) else '') + (getattr(a, 'barcode', '') or ''),
                              _f(getattr(a, 'original_value', 0) or 0), cl[1], cl[0], a.id,
                              (a.custodian_id.name if getattr(a, 'custodian_id', False) else '')])
                ids.append(a.id)
            return {'cards': cards, 'ids': ids,
                    'stats': [_stat('أصول', len(assets), 'asset'),
                              _stat('تالفة/مفقودة', dmg, 'alert', 'var(--crit)', 'down'),
                              _stat('القيمة', _f(sum(assets.mapped('original_value')) if assets else 0), 'bank', 'var(--gold)')]}
        safe('passets', _passets)

        # ---- تسليمات الأصول للمشروع (care.asset.delivery) ----
        def _assetdeliv():
            D = env['care.asset.delivery'].sudo() if 'care.asset.delivery' in env else None
            if D is None:
                return {'cols': ['الدفعة', 'الحالة', 'التاريخ', 'البنود', 'أصول', ''], 'rows': [], 'ids': [], 'stats': []}
            recs = D.search([('project_id', '=', p.id), ('state', 'in', ('delivered', 'converted', 'purchased'))],
                            order='id desc', limit=100000)
            try:
                sel = dict(D._fields['state']._description_selection(request.env))
            except Exception:
                sel = {}
            stcls = {'purchased': 'info', 'delivered': 'warn', 'converted': 'ok'}
            rows = [[['AD', d.name or '—', ''], 'pill:%s:%s' % (stcls.get(d.state, 'mut'), sel.get(d.state, d.state)),
                     str(d.date or ''), str(d.line_count or 0), str(d.asset_count or 0)] for d in recs]
            return {'cols': ['الدفعة', 'الحالة', 'التاريخ', 'البنود', 'أصول', ''],
                    'rows': rows, 'ids': [d.id for d in recs],
                    'stats': [_stat('دفعات', len(recs), 'box'),
                              _stat('مُحوّلة لأصول', len(recs.filtered(lambda x: x.state == 'converted')), 'check', 'var(--ok)')]}
        safe('assetdeliv', _assetdeliv)

        # ---- الأداء ----
        def _performance():
            emps = env['hr.employee'].sudo().search(self._x_emp_dom(dept_id), order='name') if dept_id else env['hr.employee'].sudo().browse()
            rows, ids = [], []
            for e in emps:
                pts = getattr(e, 'performance_points', 0) or getattr(e, 'total_points', 0) or 0
                rows.append([['f', e.name, '#' + (e.barcode or str(e.id))] + _wstag(e), 'pill:info:تقييم', str(pts)])
                ids.append(e.id)
            return {'cols': ['العامل', 'الحالة', 'النقاط', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('العمّال', len(emps), 'team')]}
        safe('performance', _performance)

        # ---- المتجر (كتالوج) ----
        def _store():
            items = env['care.cafm.catalog.item'].sudo().search([], limit=100000) if 'care.cafm.catalog.item' in env else []
            cards = [[getattr(it, 'name', '') or '—', (it.category_id.name if getattr(it, 'category_id', False) else (getattr(it, 'category', '') or '')),
                      _f(getattr(it, 'price', 0) or getattr(it, 'list_price', 0)), 'box'] for it in list(items)]
            return {'cards': cards, 'stats': [_stat('أصناف', len(list(items)), 'store')]}
        # 'store' يُحمّل كسولًا عبر renderStore→/store/data (بناؤه المسبق كان هدرًا على كل تحميل)
        # safe('store', _store)

        # ---- طلبات الأصناف ----
        def _items():
            R = env['care.cafm.request'].sudo() if 'care.cafm.request' in env else None
            reqs = R.search([('project_id', '=', p.id)], limit=100000) if R is not None else []
            rows = [[['RQ', getattr(r, 'name', '') or '—', ''], 'pill:info:%s' % _sel_label_rec(r),
                     str(getattr(r, 'create_date', '') or '')[:10]] for r in list(reqs)]
            return {'cols': ['الطلب', 'الحالة', 'التاريخ', ''], 'rows': rows, 'ids': [r.id for r in list(reqs)],
                    'stats': [_stat('طلبات', len(list(reqs)), 'cart')]}
        safe('items', _items)

        # ---- طلبات المتجر (care.pms.store.order) — لتظهر طلبات المتجر المُرسلة ----
        def _storeorder():
            O = env['care.pms.store.order'].sudo() if 'care.pms.store.order' in env else None
            if O is None:
                return {'cols': ['الطلب', 'الحالة', 'التاريخ', 'النوع', 'المبلغ', ''], 'rows': [], 'ids': [], 'stats': []}
            recs = O.search([('project_id', '=', p.id)], order='id desc', limit=100000)
            try:
                sel = dict(O._fields['state']._description_selection(env))
            except Exception:
                sel = {}
            stcls = {'draft': 'mut', 'submitted': 'info', 'approved': 'ok', 'sent': 'ok',
                     'done': 'ok', 'cancel': 'crit', 'rejected': 'crit'}
            rows, ids = [], []
            for o in recs:
                stt = getattr(o, 'state', '') or ''
                rows.append([['SO', o.name or '—', (o.order_type_id.name if getattr(o, 'order_type_id', False) else '')],
                             'pill:%s:%s' % (stcls.get(stt, 'mut'), sel.get(stt, stt)),
                             str(getattr(o, 'date', '') or getattr(o, 'create_date', '') or '')[:10],
                             (o.order_type_id.name if getattr(o, 'order_type_id', False) else '—'),
                             _f(getattr(o, 'amount_total', 0) or 0)])
                ids.append(o.id)
            nsub = len(recs.filtered(lambda x: (getattr(x, 'state', '') or '') in ('submitted', 'sent', 'approved', 'done')))
            return {'cols': ['الطلب', 'الحالة', 'التاريخ', 'النوع', 'المبلغ', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('طلبات', len(recs), 'cart'),
                              _stat('مُرسلة', nsub, 'check', 'var(--ok)')]}
        safe('storeorder', _storeorder)

        # ---- الإيقاف عن العمل ----
        def _suspension():
            SL = env['care.suspension.request.line'].sudo() if 'care.suspension.request.line' in env else None
            lines = SL.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (SL is not None and dept_id) else []
            rows = [[['f', l.employee_id.name, '#' + (l.employee_id.barcode or '')] + _wstag(l.employee_id),
                     'pill:%s:%s' % ('crit' if not getattr(l, 'lifted', False) else 'mut', 'موقوف' if not getattr(l, 'lifted', False) else 'رُفع'),
                     str(getattr(l, 'effective_date', '') or ''), (getattr(l, 'reason_display', '') or '')] for l in list(lines)]
            return {'cols': ['العامل', 'الحالة', 'تاريخ الإيقاف', 'السبب', ''], 'rows': rows, 'ids': [l.id for l in list(lines)],
                    'stats': [_stat('سجلات', len(list(lines)), 'pause', 'var(--crit)')]}
        safe('suspension', _suspension)

        # ---- مباشرة العمل ----
        def _resume():
            RL = env['care.resume.request.line'].sudo() if 'care.resume.request.line' in env else None
            lines = RL.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (RL is not None and dept_id) else []
            rows = [[['f', l.employee_id.name, '#' + (l.badge or '')] + _wstag(l.employee_id),
                     'pill:ok:%s' % (getattr(l, 'status_display', '') or 'عودة'),
                     str(getattr(l, 'return_date', '') or ''), (l.return_department_id.name if getattr(l, 'return_department_id', False) else '')] for l in list(lines)]
            return {'cols': ['العامل', 'الحالة', 'تاريخ العودة', 'الإدارة', ''], 'rows': rows, 'ids': [l.id for l in list(lines)],
                    'stats': [_stat('سجلات', len(list(lines)), 'play', 'var(--ok)')]}
        safe('resume', _resume)

        # ---- تكليف إضافي / الواردة ----
        def _additional():
            SR = env['employee.shift.request'].sudo() if 'employee.shift.request' in env else None
            reqs = SR.search(self._x_emp_dom(dept_id, 'new_department'), limit=100000) if (SR is not None and dept_id) else []
            rows = [[['f', r.employee_id.name, ''] + _wstag(r.employee_id), 'pill:info:%s' % _sel_label_rec(r),
                     (r.current_department.name if getattr(r, 'current_department', False) else '—'),
                     (r.new_department.name if getattr(r, 'new_department', False) else '—')] for r in list(reqs)]
            return {'cols': ['العامل', 'الحالة', 'من', 'إلى', ''], 'rows': rows,
                    'ids': [r.id for r in list(reqs)],
                    'stats': [_stat('طلبات', len(list(reqs)), 'group3')]}
        safe('additional', _additional)

        def _inbox():
            """مركز إجراءات موحّد: كل ما ينتظر قرار المدير (اعتمادات ضمن نطاقه) + المهام
            المسنَدة إليه. كل صفّ يحمل هدفه الحقيقي في tgt=[code,rid] ليفتح موديله الصحيح."""
            # (model, code, state-domain, scope) — scope يحدّد كيف يُقصر على نطاق المدير
            # 'emp_dept'=قسم العامل | 'benef'=مشروع مستفيد | 'proj'=مشروع | 'proj_or_dept'=مشروع أو قسم
            specs = [
                ('hr.leave', 'leaves', [('state', 'in', ('confirm',))], 'emp_dept', 'طلب إجازة'),
                ('overtime.request', 'overtime', [('state', 'in', ('submit', 'submitted', 'to_approve'))], 'proj_or_dept', 'عمل إضافي'),
                ('care.extra.work', 'extrawork', [('state', 'in', ('submit', 'submitted', 'to_approve'))], 'benef', 'تكليف إضافي'),
                ('care.cafm.request', 'items', [('state', '=', 'submitted')], 'proj', 'طلب أصناف'),
            ]
            rows, ids, tgt = [], [], []
            npend = 0
            for model, code, sdom, scope, label in specs:
                try:
                    if model not in env:
                        continue
                    M = env[model].sudo()
                    ff = M._fields
                    if scope == 'emp_dept':
                        if not dept_id or 'employee_id' not in ff:
                            continue
                        dom = self._x_emp_dom(dept_id, 'employee_id.department_id') + sdom
                    elif scope == 'benef':
                        if 'benef_project_id' not in ff:
                            continue
                        dom = [('benef_project_id', '=', p.id)] + sdom
                    elif scope == 'proj':
                        if 'project_id' not in ff:
                            continue
                        dom = [('project_id', '=', p.id)] + sdom
                    elif scope == 'proj_or_dept':
                        if 'project_id' not in ff:
                            continue
                        if dept_id and 'department_id' in ff:
                            dom = ['|', ('project_id', '=', p.id), ('department_id', '=', dept_id)] + sdom
                        else:
                            dom = [('project_id', '=', p.id)] + sdom
                    else:
                        continue
                    recs = M.search(dom, order='create_date desc', limit=100000)
                    for r in recs:
                        emp = getattr(r, 'employee_id', False)
                        if emp:
                            ref = ['f', emp.name, label] + _wstag(emp)
                            party = emp.name
                        else:
                            # اسم نظيف: name حقيقي وإلا المشروع وإلا «النوع #المعرّف»
                            nm = ''
                            if 'name' in ff and r.name and not str(r.name).startswith(model):
                                nm = r.name
                            proj = getattr(r, 'project_id', False)
                            pnm = _dname(proj) if proj else ''
                            main = nm or pnm or ('%s #%d' % (label, r.id))
                            ref = ['', main, label]
                            party = pnm or main
                        dt = str(getattr(r, 'create_date', '') or '')[:10]
                        rows.append([ref, 'pill:info:%s' % label, party, dt, 'pill:warn:بانتظار اعتمادك'])
                        ids.append(r.id)
                        tgt.append([code, r.id])
                        npend += 1
                except Exception:
                    pass
            # المهام المسنَدة إليّ في هذا المشروع
            tcount = 0
            try:
                Task = env['project.task'].sudo()
                tdom = [('project_id', '=', p.id), ('user_ids', 'in', env.user.ids)]
                # استبعاد المراحل المطويّة (منجَز/ملغى) — الوارد = ما يحتاج إجراءً فعلاً
                if 'fold' in env['project.task.type']._fields:
                    tdom.append(('stage_id.fold', '=', False))
                tasks = Task.search(tdom, order='date_deadline', limit=100000)
                # حارس إضافي: استبعاد المراحل المغلقة بالاسم (الإعداد لا يضبط fold دائمًا)
                _closed = ('done', 'archiv', 'cancel', 'closed', 'complete',
                           'منجز', 'مؤرشف', 'أرشيف', 'ملغ', 'مغلق', 'مكتمل', 'منتهٍ', 'منتهي')
                tasks = tasks.filtered(lambda t: not any(
                    k in ((t.stage_id.name or '').strip().lower()) for k in _closed))
                for t in tasks:
                    rows.append([['', t.name or '—', 'مهمة'], 'pill:mut:مهمة مسنَدة',
                                 (t.stage_id.name or '—'), str(t.date_deadline or '—'),
                                 'pill:info:%s' % (t.stage_id.name or '—')])
                    ids.append(t.id)
                    tgt.append(['tasks', t.id])
                    tcount += 1
            except Exception:
                pass
            return {'cols': ['العنصر', 'النوع', 'الطرف', 'التاريخ', 'الحالة', ''],
                    'rows': rows, 'ids': ids, 'tgt': tgt,
                    'stats': [_stat('بانتظار اعتمادك', npend, 'check'),
                              _stat('مهامّي', tcount, 'mail'),
                              _stat('الإجمالي', len(rows), 'grid')]}
        safe('inbox', _inbox)

        # ---- البدلات (مع معرّفات السجلّات لزر الإيقاف/الطباعة) ----
        def _allowances():
            AL = env['care.allowance'].sudo() if 'care.allowance' in env else None
            recs = AL.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (AL is not None and dept_id) else []
            stmap = {'running': ('ok', 'سارٍ'), 'stop_requested': ('warn', 'طلب إيقاف'),
                     'stopped': ('crit', 'موقوف'), 'resume_requested': ('info', 'طلب استئناف')}
            rows, ids = [], []
            for r in list(recs):
                scls, stxt = stmap.get(getattr(r, 'stop_state', '') or 'running', ('ok', ''))
                rows.append([['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id),
                             'pill:info:%s' % _sel_label_rec(r),
                             (r.allowance_type_id.name if r.allowance_type_id else '—'),
                             _f(getattr(r, 'amount', 0)),
                             'pill:%s:%s' % (scls, stxt)])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'البدل', 'المبلغ', 'الإيقاف', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('بدلات', len(list(recs)), 'cash'),
                              _stat('موقوفة', len([r for r in recs if getattr(r, 'stop_state', '') == 'stopped']), 'pause', 'var(--crit)')]}
        safe('allowances', _allowances)

        # ---- المالية (إحصائيات) ----
        def _finance():
            g = lambda f: getattr(p, f, 0) or 0
            return {'cols': ['البند', 'القيمة', ''], 'rows': [
                        ['الميزانية', _f(g('pms_budget') or g('budget')), ''],
                        ['المصروف', _f(g('pms_total_cost')), ''],
                        ['الهامش %', str(int(g('pms_margin_pct'))) + '%', '']],
                    'stats': [_stat('الميزانية', _f(g('pms_budget') or g('budget')), 'bank'),
                              _stat('الهامش %', int(g('pms_margin_pct')), 'chart', 'var(--ok)')]}
        safe('finance', _finance)

        # ---- المركبات والوقود ----
        def _fuel():
            ent = env['care.fuel.entry'].sudo().search([('project_id', '=', p.id)], limit=100000) if 'care.fuel.entry' in env else []
            rows = [[['FUEL', getattr(e, 'name', '') or '—', ''], 'pill:ok:مصروف',
                     str(getattr(e, 'date', '') or ''), _f(getattr(e, 'amount', 0) or getattr(e, 'liters', 0))] for e in list(ent)]
            return {'cols': ['العملية', 'الحالة', 'التاريخ', 'القيمة', ''], 'rows': rows, 'ids': [e.id for e in list(ent)],
                    'stats': [_stat('عمليات', len(list(ent)), 'fuel')]}
        safe('fuel', _fuel)

        # ---- بطاقات الوقود مسبقة الدفع ----
        def _fuelcard():
            C = env['care.fuel.card'].sudo() if 'care.fuel.card' in env else None
            cards = C.search([('project_id', '=', p.id)], limit=100000) if C is not None else []
            rows = []
            for c in list(cards):
                rows.append([['cash', c.name or '—', (c.provider or '')],
                             'pill:%s:%s' % (('ok' if c.state == 'active' else 'mut'), _sel_label_rec(c)),
                             _f(getattr(c, 'balance', 0)), _f(getattr(c, 'topup_total', 0)),
                             (c.vehicle_id.name if c.vehicle_id else '—')])
            return {'cols': ['البطاقة', 'الحالة', 'الرصيد', 'إجمالي الشحن', 'المركبة', ''], 'rows': rows,
                    'ids': [c.id for c in list(cards)],
                    'stats': [_stat('بطاقات', len(list(cards)), 'cash'),
                              _stat('إجمالي الرصيد', _f(sum((c.balance or 0) for c in cards)), 'cash', 'var(--ok)')]}
        safe('fuelcard', _fuelcard)

        # ---- العمل الإضافي (طلبات) ----
        def _overtime():
            OT = env['overtime.request'].sudo() if 'overtime.request' in env else None
            reqs = OT.search(['|', ('project_id', '=', p.id), ('department_id', '=', dept_id)], limit=100000) if OT is not None else []
            rows = [[['OT', getattr(r, 'name', '') or r.display_name or '—', ''],
                     ('pill:warn:⏸ طلب إيقاف' if getattr(r, 'care_stop_requested', False) else 'pill:info:%s' % _sel_label_rec(r)),
                     str(getattr(r, 'request_date', '') or ''), _f(getattr(r, 'total_hours', 0)), _f(getattr(r, 'total_amount', 0))] for r in list(reqs)]
            return {'cols': ['الطلب', 'الحالة', 'التاريخ', 'الساعات', 'المبلغ', ''], 'rows': rows, 'ids': [r.id for r in list(reqs)],
                    'stats': [_stat('طلبات', len(list(reqs)), 'bolt'),
                              _stat('إجمالي المبلغ', _f(sum(r.total_amount or 0 for r in reqs)) if reqs else 0, 'cash', 'var(--gold)')]}
        safe('overtime', _overtime)

        # ---- العمل الإضافي الوارد ----
        def _extrawork():
            EW = env['care.extra.work'].sudo() if 'care.extra.work' in env else None
            recs = EW.search([('benef_project_id', '=', p.id)], limit=100000) if EW is not None else []
            rows = [[['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id), 'pill:info:%s' % _sel_label_rec(r),
                     str(getattr(r, 'date_from', '') or ''), str(getattr(r, 'date_to', '') or ''), _f(getattr(r, 'fixed_amount', 0))] for r in list(recs)]
            return {'cols': ['العامل', 'الحالة', 'من', 'إلى', 'المبلغ', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('سجلات', len(list(recs)), 'group3')]}
        safe('extrawork', _extrawork)

        # ---- التصاريح ----
        def _permits():
            PR = env['care.permit.request'].sudo() if 'care.permit.request' in env else None
            reqs = PR.search(self._x_emp_dom(dept_id), limit=100000) if (PR is not None and dept_id) else []
            rows = []
            for r in list(reqs):
                _st, _lbl, _cls, _ = self._x_state_info(r)
                rows.append([['PRM', getattr(r, 'name', '') or '—', (r.default_type_id.name if getattr(r, 'default_type_id', False) else '')],
                             'pill:%s:%s' % (_cls, _lbl),
                             str(getattr(r, 'request_date', '') or ''), str(getattr(r, 'line_count', 0)), _f(getattr(r, 'amount_total', 0))])
            return {'cols': ['الطلب', 'الحالة', 'التاريخ', 'عمّال', 'المبلغ', ''], 'rows': rows, 'ids': [r.id for r in list(reqs)],
                    'stats': [_stat('طلبات', len(list(reqs)), 'permit')]}
        safe('permits', _permits)

        # ---- الجزاءات ----
        def _penalties():
            PN = env['care.penalty'].sudo() if 'care.penalty' in env else None
            recs = PN.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (PN is not None and dept_id) else []
            rows = [[['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id), 'pill:crit:%s' % _sel_label_rec(r),
                     str(getattr(r, 'date', '') or ''), _f(getattr(r, 'amount', 0)), (getattr(r, 'reason', '') or '')] for r in list(recs)]
            return {'cols': ['العامل', 'الحالة', 'التاريخ', 'المبلغ', 'السبب', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('جزاءات', len(list(recs)), 'alert', 'var(--crit)'),
                              _stat('الإجمالي', _f(sum(r.amount or 0 for r in recs)) if recs else 0, 'cash', 'var(--warn)')]}
        safe('penalties', _penalties)

        # ---- الشكاوى التأديبية ----
        def _complaints():
            CP = env['care.complaint'].sudo() if 'care.complaint' in env else None
            recs = CP.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (CP is not None and dept_id) else []
            recs = list(recs)
            pend = ('submitted', 'manager_approved', 'hr_review', 'legal_review', 'penalty_decided')
            rows = [[['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id),
                     'pill:crit:%s' % _sel_label_rec(r),
                     str(getattr(r, 'incident_date', '') or ''),
                     (r.category_label() if hasattr(r, 'category_label') else (r.category_id.name or '—')),
                     (dict(r._fields['severity']._description_selection(env)).get(r.severity, '') if getattr(r, 'severity', False) else '')]
                    for r in recs]
            return {'cols': ['العامل', 'الحالة', 'تاريخ الواقعة', 'نوع المخالفة', 'الخطورة', ''],
                    'rows': rows, 'ids': [r.id for r in recs],
                    'stats': [_stat('الشكاوى', len(recs), 'alert', 'var(--crit)'),
                              _stat('قيد المعالجة', sum(1 for r in recs if r.state in pend), 'clock', 'var(--warn)'),
                              _stat('مطبّقة', sum(1 for r in recs if r.state == 'applied'), 'check', 'var(--ok)')]}
        safe('discipline', _complaints)

        # ---- المكافآت ----
        def _bonuses():
            BN = env['care.bonus'].sudo() if 'care.bonus' in env else None
            recs = BN.search(self._x_emp_dom(dept_id, 'employee_id.department_id'), limit=100000) if (BN is not None and dept_id) else []
            rows = [[['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id), 'pill:ok:%s' % _sel_label_rec(r),
                     str(getattr(r, 'date', '') or ''), _f(getattr(r, 'amount', 0)), (getattr(r, 'reason', '') or '')] for r in list(recs)]
            return {'cols': ['العامل', 'الحالة', 'التاريخ', 'المبلغ', 'السبب', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('مكافآت', len(list(recs)), 'star', 'var(--gold)'),
                              _stat('الإجمالي', _f(sum(r.amount or 0 for r in recs)) if recs else 0, 'cash', 'var(--ok)')]}
        safe('bonuses', _bonuses)

        # ---- المراسلات ----
        def _letters():
            LT = env['care.letter'].sudo() if 'care.letter' in env else None
            recs = LT.search([('employee_id', 'in', emp_ids)], limit=100000) if (LT is not None and emp_ids) else []
            rows = [[['LTR', getattr(r, 'name', '') or r.display_name or '—', ''], 'pill:info:%s' % _sel_label_rec(r),
                     str(getattr(r, 'date', '') or '')] for r in list(recs)]
            return {'cols': ['الكتاب', 'الحالة', 'التاريخ', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('مراسلات', len(list(recs)), 'mail')]}
        safe('letters', _letters)

        # ---- التايم شيت ----
        def _timesheet():
            TS = env['care.timesheet'].sudo() if 'care.timesheet' in env else None
            recs = list(TS.search([('project_id', '=', p.id)], order='date_from desc', limit=100000)) if TS is not None else []
            _pill = {'approved': 'ok', 'submit': 'info', 'draft': 'mut'}
            rows = [[['TS', getattr(r, 'name', '') or '—', ''],
                     (getattr(r, 'period_label', '') or '—'),
                     'pill:%s:%s' % (_pill.get(getattr(r, 'state', ''), 'info'), _sel_label_rec(r)),
                     str(getattr(r, 'date_from', '') or ''), str(getattr(r, 'date_to', '') or ''),
                     _f(getattr(r, 'total_salary_days', 0))] for r in recs]
            import datetime as _dt
            _t = _dt.date.today()
            _appr = sum(1 for r in recs if getattr(r, 'state', '') == 'approved')
            _draft = sum(1 for r in recs if getattr(r, 'state', '') == 'draft')
            _sub = sum(1 for r in recs if getattr(r, 'state', '') == 'submit')
            _days = sum((getattr(r, 'total_salary_days', 0) or 0) for r in recs)
            _tm = sum(1 for r in recs if getattr(r, 'date_from', None) and r.date_from.month == _t.month and r.date_from.year == _t.year)
            return {'cols': ['الكشف', 'الشهر', 'الحالة', 'من', 'إلى', 'أيام', ''], 'rows': rows, 'ids': [r.id for r in recs],
                    'stats': [_stat('كشوف', len(recs), 'timer'),
                              _stat('معتمدة', _appr, 'check'),
                              _stat('مسوّدة', _draft, 'edit'),
                              _stat('بانتظار الاعتماد', _sub, 'clock'),
                              _stat('هذا الشهر', _tm, 'calendar'),
                              _stat('إجمالي أيام العمل', _f(_days), 'timer')]}
        safe('timesheet', _timesheet)

        # ---- طلب قوى عاملة ----
        def _manpower():
            MR = env['manpower.requisition'].sudo() if 'manpower.requisition' in env else None
            recs = MR.search([('project_id', '=', p.id)], limit=100000) if MR is not None else []
            rows = [[['MP', getattr(r, 'name', '') or '—', ''], 'pill:info:%s' % _sel_label_rec(r),
                     str(getattr(r, 'request_date', '') or ''), str(getattr(r, 'actual_headcount', 0))] for r in list(recs)]
            return {'cols': ['الطلب', 'الحالة', 'التاريخ', 'العدد', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('طلبات', len(list(recs)), 'group3')]}
        safe('manpower', _manpower)

        # ---- الورش (c2c.workshop) ----
        # الورش التي يراها/ينشئها مدير المشروع في بورتال الورش القديم /my/pm/workshops هي c2c.workshop
        # (ليست service.order). نطبّق النطاق نفسه (_ws_domain): رؤية كاملة للمخوّلين، وإلا ورش المستخدم.
        def _workshops():
            WS = env['c2c.workshop'].sudo() if 'c2c.workshop' in env else None
            if WS is None:
                return {'cols': ['الورشة', 'الحالة', '', ''], 'rows': [], 'ids': [], 'stats': []}
            recs = self._x_ws_scope(WS)
            rows = [[['WS', getattr(r, 'title', '') or r.display_name or '—', r.name or ''],
                     'pill:info:%s' % _sel_label_rec(r, 'state'), ''] for r in list(recs)]
            return {'cols': ['الورشة', 'الحالة', '', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('ورش', len(list(recs)), 'tool')]}
        safe('workshops', _workshops)

        # ---- بترول استيشن ----
        def _petrol():
            PT = env['petrol.tank'].sudo() if 'petrol.tank' in env else None
            recs = PT.search([], limit=100000) if PT is not None else []
            rows = [[[getattr(r, 'name', '') or '—', ''], 'pill:ok:خزان', _f(getattr(r, 'balance', 0)), _f(getattr(r, 'capacity', 0))] for r in list(recs)]
            return {'cols': ['الخزان', 'الحالة', 'الرصيد', 'السعة', ''], 'rows': rows, 'ids': [r.id for r in list(recs)],
                    'stats': [_stat('خزانات', len(list(recs)), 'fuel')]}
        safe('petrol', _petrol)

        # ---- التايم شيت الإضافي (care.extra.timesheet للمشروع المستفيد) ----
        def _xts():
            XT = env['care.extra.timesheet'].sudo() if 'care.extra.timesheet' in env else None
            recs = XT.search([('project_id', '=', p.id)], order='id desc', limit=100000) if XT is not None else []
            scls = {'draft': 'mut', 'submitted': 'warn', 'approved': 'ok', 'cancelled': 'crit'}
            sel = dict(XT._fields['state']._description_selection(env)) if XT is not None else {}
            rows = [[['XTS', getattr(r, 'name', '') or '—', getattr(r, 'period_label', '') or ''],
                     'pill:%s:%s' % (scls.get(r.state, 'info'), sel.get(r.state, r.state or '')),
                     str(getattr(r, 'period_from', '') or ''), str(getattr(r, 'worker_count', 0) or 0),
                     _f(getattr(r, 'total_amount', 0))] for r in list(recs)]
            return {'cols': ['الكشف', 'الحالة', 'من', 'العمّال', 'المستحق', ''], 'rows': rows,
                    'ids': [r.id for r in list(recs)],
                    'stats': [_stat('كشوف', len(list(recs)), 'timer'),
                              _stat('إجمالي المستحق', _f(sum(getattr(r, 'total_amount', 0) or 0 for r in recs)) if recs else 0, 'cash', 'var(--gold)')]}
        safe('xts', _xts)

        # ---- الحضور والانصراف (hr.attendance لعمّال قسم المشروع) ----
        def _attendance():
            emps = env['hr.employee'].sudo().search(self._x_emp_dom(dept_id)).ids if dept_id else []
            recs = env['hr.attendance'].sudo().search([('employee_id', 'in', emps)], order='check_in desc', limit=100000) if emps else []
            rows, ids = [], []
            present = 0
            for a in list(recs):
                out = a.check_out
                present += 0 if out else 1
                rows.append([['f', a.employee_id.name, '#' + (a.employee_id.barcode or '')] + _wstag(a.employee_id),
                             'pill:%s:%s' % ('ok', 'بالداخل') if not out else 'pill:mut:انصرف',
                             str(a.check_in or '')[:16], str(out or '—')[:16],
                             _f(getattr(a, 'worked_hours', 0))])
                ids.append(a.id)
            return {'cols': ['العامل', 'الحالة', 'الدخول', 'الخروج', 'ساعات', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('سجلات', len(list(recs)), 'clock'),
                              _stat('بالداخل الآن', present, 'check', 'var(--ok)', 'up')]}
        # 'attendance' يُحمّل كسولًا عبر renderAttendance→/attendance/query (كان أثقل استعلام:
        # ORDER BY check_in DESC فوق IN(آلاف العمّال) على كل تحميل صفحة) — أُزيل من المسار الساخن
        # safe('attendance', _attendance)

        # ---- صيانة المركبات (fleet.vehicle بقسم المشروع) ----
        def _vehicles():
            import datetime as _dt
            today = _dt.date.today()
            veh = env['fleet.vehicle'].sudo().search(self._x_emp_dom(dept_id), limit=100000) if (dept_id and 'fleet.vehicle' in env) else []
            rows, ids = [], []

            def _expcell(d):
                if not d:
                    return '—'
                dl = (d - today).days
                cls = 'crit' if dl < 0 else ('warn' if dl <= 30 else 'ok')
                return 'pill:%s:%s' % (cls, str(d))
            for v in list(veh):
                ins = min([c.expiration_date for c in v.log_contracts if getattr(c, 'expiration_date', False)], default=False) if 'log_contracts' in v._fields else False
                nsv = min([s.next_service_date for s in v.log_services if getattr(s, 'next_service_date', False)], default=False) if 'log_services' in v._fields else False
                rows.append([['truck', v.name or (v.license_plate or '—'), (v.license_plate or '')],
                             (v.driver_id.name if v.driver_id else '—'),
                             _f(getattr(v, 'odometer', 0)),
                             _expcell(ins), _expcell(nsv)])
                ids.append(v.id)
            return {'cols': ['المركبة', 'السائق', 'العدّاد', 'انتهاء التأمين', 'الخدمة القادمة', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('مركبات', len(list(veh)), 'truck'),
                              _stat('تكلفة الأسطول', _f(getattr(p, 'pms_fleet_cost', 0)), 'cash', 'var(--warn)')]}
        safe('vehicles', _vehicles)

        # ---- إدارة الأمن (care.cafm.shift لعمّال قسم المشروع) ----
        def _security():
            SH = env['care.cafm.shift'].sudo() if 'care.cafm.shift' in env else None
            emps = env['hr.employee'].sudo().search(self._x_emp_dom(dept_id)).ids if dept_id else []
            recs = SH.search([('employee_id', 'in', emps)], order='id desc', limit=100000) if (SH is not None and emps) else []
            st = dict(SH._fields['state']._description_selection(env)) if (SH is not None and 'state' in SH._fields) else {}
            rows, ids = [], []
            for s in list(recs):
                rows.append([['f', s.employee_id.name, s.name or ''] + _wstag(s.employee_id),
                             'pill:info:%s' % (st.get(s.state, s.state or '') if 'state' in s._fields else ''),
                             str(getattr(s, 'check_in', '') or '')[:16], str(getattr(s, 'check_out', '') or '—')[:16]])
                ids.append(s.id)
            return {'cols': ['الحارس', 'الحالة', 'بداية الوردية', 'نهايتها', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('ورديات', len(list(recs)), 'shield', 'var(--navy-600)')]}
        safe('security', _security)

        # ====== طلبات وسجلّات العمّال (إجازات/جوازات/سلف/استقالات/نهاية خدمة) ======
        def _sel(model, field, val):
            try:
                return dict(env[model]._fields[field]._description_selection(env)).get(val, val)
            except Exception:
                return val

        # ---- الإجازات (hr.leave لعمّال المشروع) ----
        def _leaves():
            L = env['hr.leave'].sudo() if 'hr.leave' in env else None
            recs = L.search([('employee_id', 'in', emp_ids)], order='id desc', limit=100000) if (L is not None and emp_ids) else []
            scls = {'validate': 'ok', 'confirm': 'warn', 'validate1': 'info', 'refuse': 'crit', 'draft': 'mut'}
            rows, ids = [], []
            for r in list(recs):
                rows.append([['f', r.employee_id.name, '#' + (r.employee_id.barcode or '')] + _wstag(r.employee_id),
                             'pill:%s:%s' % (scls.get(r.state, 'info'), _sel('hr.leave', 'state', r.state)),
                             (r.holiday_status_id.name or '—'),
                             str(getattr(r, 'request_date_from', '') or '')[:10],
                             _f(getattr(r, 'number_of_days', 0))])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'النوع', 'من', 'أيام', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('إجازات', len(list(recs)), 'clock'),
                              _stat('معتمدة', len([r for r in recs if r.state == 'validate']), 'check', 'var(--ok)')]}
        safe('leaves', _leaves)

        # ---- سحب الجوازات (care.passport.request) ----
        def _passports():
            PP = env['care.passport.request'].sudo() if 'care.passport.request' in env else None
            recs = PP.search([('employee_id', 'in', emp_ids)], order='id desc', limit=100000) if (PP is not None and emp_ids) else []
            rows, ids = [], []
            for r in list(recs):
                _bc = r.employee_id.barcode or ''
                _sub = (r.name or '') + ((' · بادج ' + _bc) if _bc else '')
                rows.append([['f', r.employee_id.name, _sub] + _wstag(r.employee_id),
                             'pill:info:%s' % _sel('care.passport.request', 'state', getattr(r, 'state', '')),
                             str(getattr(r, 'request_date', '') or getattr(r, 'date', '') or '')[:10],
                             (getattr(r, 'reason', '') or getattr(r, 'purpose', '') or '')])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'التاريخ', 'الغرض', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('طلبات سحب', len(list(recs)), 'doc')]}
        safe('passports', _passports)

        # ---- السلف والقروض (care.loan) ----
        def _loans():
            LN = env['care.loan'].sudo() if 'care.loan' in env else None
            recs = LN.search([('employee_id', 'in', emp_ids)], order='id desc', limit=100000) if (LN is not None and emp_ids) else []
            rows, ids = [], []
            for r in list(recs):
                rows.append([['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id),
                             'pill:info:%s' % _sel('care.loan', 'state', getattr(r, 'state', '')),
                             str(getattr(r, 'date', '') or '')[:10],
                             _f(getattr(r, 'amount', 0) or getattr(r, 'loan_amount', 0)),
                             _f(getattr(r, 'balance', 0) or getattr(r, 'balance_amount', 0))])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'التاريخ', 'المبلغ', 'المتبقّي', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('سلف', len(list(recs)), 'cash'),
                              _stat('الإجمالي', _f(sum(getattr(r, 'amount', 0) or 0 for r in recs)) if recs else 0, 'bank', 'var(--warn)')]}
        safe('loans', _loans)

        # ---- الاستقالات (hr.employee.resignation) ----
        def _resignations():
            RS = env['hr.employee.resignation'].sudo() if 'hr.employee.resignation' in env else None
            recs = RS.search([('employee_id', 'in', emp_ids)], order='id desc', limit=100000) if (RS is not None and emp_ids) else []
            rows, ids = [], []
            for r in list(recs):
                rows.append([['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id),
                             'pill:warn:%s' % _sel('hr.employee.resignation', 'state', getattr(r, 'state', '')),
                             str(getattr(r, 'request_date', '') or '')[:10],
                             str(getattr(r, 'leave_date', '') or '—')[:10]])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'تاريخ الطلب', 'آخر يوم عمل', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('استقالات', len(list(recs)), 'group3', 'var(--warn)')]}
        safe('resignations', _resignations)

        # ---- نهاية الخدمة (care.eos) ----
        def _eos():
            EO = env['care.eos'].sudo() if 'care.eos' in env else None
            recs = EO.search([('employee_id', 'in', emp_ids)], order='id desc', limit=100000) if (EO is not None and emp_ids) else []
            rows, ids = [], []
            for r in list(recs):
                rows.append([['f', r.employee_id.name, r.name or ''] + _wstag(r.employee_id),
                             'pill:info:%s' % _sel('care.eos', 'state', getattr(r, 'state', '')),
                             str(getattr(r, 'last_working_day', '') or '')[:10],
                             _f(getattr(r, 'net_amount', 0))])
                ids.append(r.id)
            return {'cols': ['العامل', 'الحالة', 'آخر يوم عمل', 'الصافي', ''], 'rows': rows, 'ids': ids,
                    'stats': [_stat('مستحقات نهاية خدمة', len(list(recs)), 'invoice'),
                              _stat('الإجمالي', _f(sum(getattr(r, 'net_amount', 0) or 0 for r in recs)) if recs else 0, 'cash', 'var(--crit)')]}
        safe('eos', _eos)

        return S

    # ============ Projects list (plist) ============
    def _x_projects_plist(self):
        rows = []
        Task = request.env['project.task'].sudo()
        for p in self._pm_projects():
            prog = int(getattr(p, 'pms_progress_pct', 0) or getattr(p, 'progress', 0) or 0)
            if not prog:  # احسب من المهام (المنجزة ÷ الإجمالي) — اتّساقاً مع اللوحة
                try:
                    tot = Task.search_count([('project_id', '=', p.id)])
                    done = Task.search_count([('project_id', '=', p.id), ('state', 'in', ('1_done',))]) if tot else 0
                    prog = int(round(100.0 * done / tot)) if tot else 0
                except Exception:
                    prog = 0
            rows.append([p.name,
                         (p.pms_department_id.name if 'pms_department_id' in p._fields and p.pms_department_id else '—'),
                         'نشط', prog,
                         getattr(p, 'worker_count', 0) or 0,
                         p.id])  # [5] = معرّف المشروع (لتبديل المشروع النشط)
        return rows

    # ============ Portfolio overview (كل المشاريع) ============
    def _x_overview(self):
        """إجماليات عبر كل مشاريع المدير — تظهر في الصفحة الرئيسية."""
        projs = self._pm_projects()
        rows = []
        tot_w = tot_open = tot_assets = tot_comp = 0
        for p in projs:
            w = int(getattr(p, 'worker_count', 0) or 0)
            ot = int(getattr(p, 'pms_task_open', 0) or 0)
            ac = int(getattr(p, 'asset_count', 0) or 0)
            cc = int(getattr(p, 'compliance_count', 0) or 0)
            tot_w += w
            tot_open += ot
            tot_assets += ac
            tot_comp += cc
            dept = (p.pms_department_id.name if 'pms_department_id' in p._fields and p.pms_department_id else '—')
            rows.append([p.name, dept, w, ot, p.id])
        rows.sort(key=lambda r: r[2], reverse=True)  # الأكثر عمالة أولاً
        return {
            'projects_count': len(projs),
            'workers': tot_w, 'open_tasks': tot_open,
            'assets': tot_assets, 'compliance': tot_comp,
            'rows': rows,
        }

    # ============ Dashboard extras (real) ============
    def _x_attend_trend(self, p):
        """اتجاه الحضور آخر 14 يومًا (عدد الحاضرين يوميًّا) — من كشوف الدوام المعتمدة إن توفّرت،
        وإلا من البصمات (بصمة واحدة لكل عامل/يوم، لا عدّ السجلّات الخام)."""
        env = request.env
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        if not dept:
            return []
        try:
            import datetime as _dt
            emp_ids = env['hr.employee'].sudo().search(self._x_emp_dom(dept.id)).ids
            if not emp_ids:
                return []
            today = _dt.date.today()
            start = today - _dt.timedelta(days=13)
            cnt = {}
            used_ts = False
            # المصدر الموثوق: care.timesheet.day (حاضر = P/T/E؛ صفّ واحد لكل عامل/يوم ⇒ عدد مميّز)
            tsd = env['care.timesheet.day'].sudo() if 'care.timesheet.day' in env else None
            if tsd is not None:
                g = tsd.read_group(
                    [('employee_id', 'in', emp_ids), ('status', 'in', ['P', 'T', 'E']),
                     ('date', '>=', str(start)), ('date', '<=', str(today))],
                    ['date'], ['date:day'], lazy=False)
                if g and sum(x.get('__count', 0) for x in g):
                    used_ts = True
                    for gr in g:
                        rng = (gr.get('__range') or {}).get('date:day') or {}
                        frm = rng.get('from')
                        if frm:
                            cnt[str(frm)[:10]] = gr.get('__count', 0)
            # احتياطي: البصمات — عدد (عامل، يوم) المميّز لا السجلّات الخام
            if not used_ts and 'hr.attendance' in env:
                g = env['hr.attendance'].sudo().read_group(
                    [('employee_id', 'in', emp_ids), ('check_in', '>=', str(start)),
                     ('check_in', '<', str(today + _dt.timedelta(days=1)))],
                    ['__count'], ['check_in:day', 'employee_id'], lazy=False)
                for gr in g:
                    rng = (gr.get('__range') or {}).get('check_in:day') or {}
                    frm = rng.get('from')
                    if frm:
                        k = str(frm)[:10]
                        cnt[k] = cnt.get(k, 0) + 1
            out = []
            for i in range(14):
                d = start + _dt.timedelta(days=i)
                out.append([d.strftime('%m-%d'), cnt.get(str(d), 0)])
            return out
        except Exception:
            return []

    def _x_workforce(self, p):
        """تحليلات القوى العاملة لعمّال قسم المشروع: التوزيع حسب الجنسية + حسب الحالة — لرسوم دائرية."""
        env = request.env
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        out = {'by_nat': [], 'by_status': [], 'total': 0}
        if not dept or 'hr.employee' not in env:
            return out
        try:
            Emp = env['hr.employee'].sudo()
            dom = self._x_emp_dom(dept.id)
            out['total'] = Emp.search_count(dom)
            # الجنسية (أعلى 6 + أخرى)
            gn = Emp.read_group(dom, ['country_id'], ['country_id'], lazy=False)
            nats = sorted([[(gr.get('country_id') or [0, '—'])[1] or '—', gr.get('__count', 0)] for gr in gn],
                          key=lambda x: x[1], reverse=True)
            top = nats[:6]
            rest = sum(x[1] for x in nats[6:])
            if rest:
                top.append(['أخرى', rest])
            out['by_nat'] = top
            # الحالة
            _lbl = {'active': 'نشط', 'on_leave': 'في إجازة', 'suspended': 'موقوف',
                    'absconded': 'هارب', 'terminated': 'منتهٍ', 'resigned': 'مستقيل',
                    'absence': 'غائب', 'absent': 'غائب', 'vacation': 'في إجازة'}
            if 'worker_status' in Emp._fields:
                gs = Emp.read_group(dom, ['worker_status'], ['worker_status'], lazy=False)
                out['by_status'] = sorted(
                    [[_lbl.get((gr.get('worker_status') or 'active'), (gr.get('worker_status') or 'نشط')),
                      gr.get('__count', 0)] for gr in gs],
                    key=lambda x: x[1], reverse=True)
        except Exception:
            pass
        return out

    def _x_attention(self, p):
        """مركز «يحتاج انتباهك» — أولويات قابلة للتنفيذ للمشروع الحالي، مرتّبة بالخطورة.
        كل عنصر: [severity(crit/warn/info), icon, count, title, code] للانتقال للقسم."""
        env = request.env
        import datetime as _dt
        today = _dt.date.today()
        items = []
        try:
            dept = p.pms_department_id if 'pms_department_id' in p._fields else False
            dept_id = dept.id if dept else 0
            Task = env['project.task'].sudo()
            # إحالات بانتظار قبولك
            fwd = Task.search_count([('project_id', '=', p.id), ('forward_state', '=', 'pending'),
                                     ('forward_to_id', '=', env.user.id)])
            if fwd:
                items.append(['warn', 'group3', fwd, 'مهام محالة بانتظار قبولك', 'tasks'])
            # مهام متأخّرة
            over = 0
            try:
                over = Task.search_count([('project_id', '=', p.id), ('is_overdue', '=', True)])
            except Exception:
                over = Task.search_count([('project_id', '=', p.id), ('date_deadline', '<', str(today)),
                                          ('state', 'not in', ('1_done', '1_canceled'))])
            if over:
                items.append(['crit' if over >= 5 else 'warn', 'alert', over, 'مهام متأخّرة عن موعدها', 'tasks'])
            # إقامات: حرجة ≤30 و تحذير 31–60
            if dept_id:
                Emp = env['hr.employee'].sudo()
                rf = 'residency_expiry_date' if 'residency_expiry_date' in Emp._fields else (
                    'visa_expire' if 'visa_expire' in Emp._fields else None)
                if rf:
                    d30 = str(today + _dt.timedelta(days=30))
                    d60 = str(today + _dt.timedelta(days=60))
                    crit = Emp.search_count(self._x_emp_dom(dept_id) + [(rf, '!=', False),
                                             (rf, '<=', d30)])
                    warn = Emp.search_count(self._x_emp_dom(dept_id) + [(rf, '!=', False),
                                             (rf, '>', d30), (rf, '<=', d60)])
                    if crit:
                        items.append(['crit', 'shield', crit, 'إقامات تنتهي خلال 30 يومًا', 'compliance'])
                    if warn:
                        items.append(['warn', 'shield', warn, 'إقامات تنتهي خلال 60 يومًا', 'compliance'])
            # اعتمادات معلّقة بانتظارك (طلبات في حالة تقديم/تأكيد ضمن النطاق)
            # نفس نطاقات الوارد «inbox» لضمان تطابق العدّاد مع صفوف الوارد
            pend_specs = [('hr.leave', [('state', 'in', ('confirm',))], 'emp_dept'),
                          ('overtime.request', [('state', 'in', ('submit', 'submitted', 'to_approve'))], 'proj_or_dept'),
                          ('care.extra.work', [('state', 'in', ('submit', 'submitted', 'to_approve'))], 'benef'),
                          ('care.cafm.request', [('state', '=', 'submitted')], 'proj')]
            tot_pend = 0
            for model, sdom, scope in pend_specs:
                try:
                    if model not in env:
                        continue
                    M = env[model].sudo()
                    ff = M._fields
                    if scope == 'emp_dept':
                        if not dept_id or 'employee_id' not in ff:
                            continue
                        dom = self._x_emp_dom(dept_id, 'employee_id.department_id') + sdom
                    elif scope == 'benef':
                        if 'benef_project_id' not in ff:
                            continue
                        dom = [('benef_project_id', '=', p.id)] + sdom
                    elif scope == 'proj':
                        if 'project_id' not in ff:
                            continue
                        dom = [('project_id', '=', p.id)] + sdom
                    elif scope == 'proj_or_dept':
                        if 'project_id' not in ff:
                            continue
                        if dept_id and 'department_id' in ff:
                            dom = ['|', ('project_id', '=', p.id), ('department_id', '=', dept_id)] + sdom
                        else:
                            dom = [('project_id', '=', p.id)] + sdom
                    else:
                        continue
                    tot_pend += M.search_count(dom)
                except Exception:
                    pass
            if tot_pend:
                items.append(['info', 'check', tot_pend, 'طلبات بانتظار اعتمادك', 'inbox'])
            # طلبات جرد أصول بانتظار مدير المشروع
            try:
                if 'care.asset.inventory' in env:
                    ninv = env['care.asset.inventory'].sudo().search_count(
                        [('project_id', '=', p.id), ('state', 'in', ('requested', 'in_progress'))])
                    if ninv:
                        items.append(['warn', 'check', ninv, 'طلبات جرد أصول بانتظارك', 'inventory'])
            except Exception:
                pass
            # أصول تالفة/مفقودة في المشروع
            try:
                if 'account.asset' in env and 'condition' in env['account.asset']._fields:
                    adom = ['|', ('project_id', '=', p.id)]
                    adom += [('department_id', '=', dept_id)] if dept_id else [('project_id', '=', p.id)]
                    ndmg = env['account.asset'].sudo().search_count(adom + [('condition', 'in', ('damaged', 'lost'))])
                    if ndmg:
                        items.append(['warn', 'alert', ndmg, 'أصول تالفة/مفقودة', 'passets'])
            except Exception:
                pass
        except Exception:
            pass
        rank = {'crit': 0, 'warn': 1, 'info': 2}
        items.sort(key=lambda x: (rank.get(x[0], 3), -x[2]))
        return items

    def _x_dash_extra(self, p):
        env = request.env
        stages_bars, activity = [], []
        try:
            Task = env['project.task'].sudo()
            # أعمدة المراحل عبر read_group بدل تحميل كل مهام المشروع وعدّها بايثون
            grp = Task.read_group([('project_id', '=', p.id)], ['stage_id'], ['stage_id'], lazy=False)
            bars = sorted(([(g['stage_id'][1] if g.get('stage_id') else 'عام'), g.get('__count', 0)] for g in grp),
                          key=lambda x: x[1], reverse=True)
            stages_bars = bars[:6]
            for t in Task.search([('project_id', '=', p.id)], order='write_date desc', limit=5):
                activity.append(['grid3', t.name or '—', (t.stage_id.name or '')])
        except Exception:
            pass
        return stages_bars, activity

    # ============ Notifications (real: user's pending activities) ============
    def _x_notifs(self):
        """تنبيهات مدير المشروع: أنشطته + إشارات تشغيلية عالية القيمة (إحالات بانتظاره،
        إقامات تنتهي، مهام متأخّرة، اعتمادات معلّقة). كل عنصر: [أيقونة,لون,عنوان,وصف,جديد؟,code]."""
        env = request.env
        out = []
        model_code = {v: k for k, v in CODE_MODEL.items()}
        # 1) أنشطتي (mail.activity)
        try:
            acts = env['mail.activity'].sudo().search(
                [('user_id', '=', env.user.id)], order='date_deadline', limit=12)
            ic_map = {'overdue': ('alert', 'rose'), 'today': ('clock', 'amber'), 'planned': ('mail', 'teal')}
            for a in acts:
                state = a.state or 'planned'
                icn, col = ic_map.get(state, ('mail', 'sky'))
                title = a.summary or (a.activity_type_id.name if a.activity_type_id else 'مهمة')
                meta = ' · '.join([x for x in [(a.res_name or ''), str(a.date_deadline or '')] if x])
                out.append([icn, col, title, meta, state in ('overdue', 'today'),
                            model_code.get(a.res_model or '', 'inbox')])
        except Exception:
            pass
        # 2) إشارات تشغيلية عبر مشاريع المدير
        try:
            projs = self._pm_projects()
            dept_ids = projs.mapped('pms_department_id').ids
            proj_ids = projs.ids
            Task = env['project.task'].sudo()
            # مهام بانتظار قبولي (إحالات)
            fwd = Task.search_count([('project_id', 'in', proj_ids), ('forward_state', '=', 'pending'),
                                     ('forward_to_id', '=', env.user.id)]) if proj_ids else 0
            if fwd:
                out.insert(0, ['group3', 'violet', 'مهام بانتظار قبولك',
                               '%s مهمة محالة إليك' % fwd, True, 'tasks'])
            # مهام متأخّرة
            over = Task.search_count([('project_id', 'in', proj_ids), ('is_overdue', '=', True)]) if proj_ids else 0
            if over:
                out.append(['alert', 'rose', 'مهام متأخّرة', '%s مهمة تجاوزت موعدها' % over, True, 'tasks'])
            # إقامات تنتهي قريبًا (≤60 يومًا)
            try:
                import datetime as _dt
                soon = str(_dt.date.today() + _dt.timedelta(days=60))
                Emp = env['hr.employee'].sudo()
                if dept_ids and 'residency_expiry_date' in Emp._fields:
                    _ex = self._x_exclude_dept_ids()
                    _rdom = [('department_id', 'child_of', dept_ids),
                             ('residency_expiry_date', '!=', False),
                             ('residency_expiry_date', '<=', soon)]
                    if _ex:
                        _rdom += ['!', ('department_id', 'child_of', _ex)]
                    rc = Emp.search_count(_rdom)
                    if rc:
                        out.append(['shield', 'amber', 'إقامات تنتهي قريبًا',
                                    '%s عامل خلال 60 يومًا' % rc, True, 'compliance'])
            except Exception:
                pass
        except Exception:
            pass
        return out[:18]

    # ============ Full payload ============
    def _x_payload(self, p):
        dept = (p.pms_department_id.name if 'pms_department_id' in p._fields and p.pms_department_id else '')
        pm = (p.project_manager_id.name if 'project_manager_id' in p._fields and p.project_manager_id else '')
        g = lambda f: getattr(p, f, 0) or 0
        stages_bars, activity = self._x_dash_extra(p)
        # نسبة التقدّم الحقيقية من المهام (المنجزة ÷ الإجمالي) عند غياب حقل جاهز
        progress = int(getattr(p, 'pms_progress_pct', 0) or getattr(p, 'progress', 0) or 0)
        if not progress:
            try:
                Task = request.env['project.task'].sudo()
                tot = Task.search_count([('project_id', '=', p.id)])
                done = Task.search_count([('project_id', '=', p.id), ('state', 'in', ('1_done',))]) if tot else 0
                progress = int(round(100.0 * done / tot)) if tot else 0
            except Exception:
                progress = 0
        payload = {
            'project': {'id': p.id, 'name': p.name, 'dept': dept, 'pm': pm,
                        'loc': dept or '—', 'status': 'نشط'},
            'dash': {
                'workers': g('worker_count'), 'open_tasks': g('pms_task_open'),
                'budget': _f(g('pms_budget') or g('budget')), 'margin': int(g('pms_margin_pct')),
                'progress': progress,
                'kpis': self._x_kpis(p),
                'info': [['الإدارة', dept or '—'], ['مدير المشروع', pm or '—'],
                         ['الحالة', 'pill:ok:نشط'], ['العمّال', g('worker_count')],
                         ['المهام المفتوحة', g('pms_task_open')], ['الأصول', g('asset_count')]],
                'stages_bars': stages_bars,
                'activity': activity,
                'trend': self._x_attend_trend(p),
                'workforce': self._x_workforce(p),
                'attention': self._x_attention(p),
            },
            'projects': self._x_projects_plist(),
            'overview': self._x_overview(),
            'sections': self._x_sections(p),
            'notifs': self._x_notifs(),
            'me': {'name': request.env.user.name or '',
                   'initials': ''.join([w[0] for w in (request.env.user.name or 'PM').split()[:2]]) or 'PM',
                   'login': request.env.user.login or ''},
        }
        # عدّادات القائمة الجانبية (تُحدِّث الأرقام بجانب أسماء الأقسام)
        payload['counts'] = {
            'team': g('worker_count'), 'tasks': g('pms_task_open'),
            'compliance': g('compliance_count'),
        }
        payload['creatable'] = sorted(self.pm_x_create_models())
        # أيقونة «التحوّل لإدارة المرافق»: تظهر فقط إن كان لدى المدير مشروع مُعلَّم CAFM.
        # getattr آمن إن لم يكن care_cafm مثبّتًا (لا يوجد الحقل).
        try:
            payload['has_cafm'] = bool(self._pm_projects().filtered(
                lambda p: getattr(p, 'is_cafm_project', False)))
        except Exception:
            payload['has_cafm'] = False
        return payload

    def _x_current_project(self, project_id=None):
        projs = self._pm_projects()
        if not projs:
            return False
        if project_id:
            cur = projs.filtered(lambda x: x.id == project_id)
            if cur:
                return cur[0]
        # الافتراضي: فضّل مشروعاً له قسم مرتبط وعمّال (وإلا يبدو البورتال فارغاً/موكاب).
        # 1) مشروع به قسم وعمّال، 2) مشروع به قسم، 3) الأوّل.
        with_workers = projs.filtered(
            lambda x: ('pms_department_id' in x._fields and x.pms_department_id
                       and (getattr(x, 'worker_count', 0) or 0) > 0))
        if with_workers:
            return with_workers[0]
        with_dept = projs.filtered(
            lambda x: 'pms_department_id' in x._fields and x.pms_department_id)
        if with_dept:
            return with_dept[0]
        return projs[0]

    def _x_render_app(self, project_id=None, ts_open=None, readonly=False):
        with open(_APP_FILE, 'r', encoding='utf-8') as f:
            body = f.read()
        p = self._x_current_project(project_id)
        pmx = self._x_payload(p) if p else {'project': {}, 'dash': {}, 'sections': {}, 'projects': [], 'overview': {}, 'counts': {}}
        # وضع التفويض (#19): مستخدم مفوَّض (ليس مدير المشروع الأصلي) يرى القوائم المفوَّضة فقط
        try:
            if not self._x_is_native_pm():
                restr = self._x_delegate_restriction()
                if restr:
                    pmx['delegate'] = restr
        except Exception:
            pass
        inject = '<script>window.PMX = %s;</script>\n' % json.dumps(pmx, ensure_ascii=False, default=str)
        if ts_open:
            inject += '<script>window.PMX_TS_OPEN = %d;</script>\n' % int(ts_open)
        if readonly:
            inject += '<script>window.PMX_TS_RO = 1;</script>\n'
        html = (
            '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8"/>\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>\n'
            '</head>\n<body>\n' + inject + body + '\n</body>\n</html>'
        )
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    # ============ تفويض مدير المشروع (#19): يفوّض مستخدمًا على قائمة بصلاحيات محدّدة ============
    def _x_is_native_pm(self):
        try:
            return bool(super(PMPortalX, self)._pm_projects())
        except Exception:
            return False

    def _x_delegate_restriction(self):
        """قيد المفوَّض الحالي: الأقسام المسموحة + صلاحياتها + مشاريعها. None لغير المفوَّض."""
        env = request.env
        if 'care.pms.delegation' not in env:
            return None
        D = env['care.pms.delegation'].sudo()
        recs = D.search([('delegate_id', '=', env.user.id), ('active', '=', True)])
        today = fields.Date.today()
        recs = recs.filtered(lambda r: (not r.date_until or r.date_until >= today)
                             and (r.state or 'accepted') != 'rejected')
        if not recs:
            return None
        sections, projs = {}, []
        for r in recs:
            sections[r.section_code] = {
                'label': r.section_label or r.section_code,
                'perms': r.perms_dict() if hasattr(r, 'perms_dict') else {'read': True},
                'project_id': r.project_id.id, 'project': r.project_id.display_name}
            if r.project_id.id not in projs:
                projs.append(r.project_id.id)
        return {'sections': sections, 'project_ids': projs}

    def _x_deleg_check(self, code, action='read'):
        """حارس خادمي للمفوَّض: يمنع غير قسمه المفوَّض، ويتحقّق من الصلاحية المطلوبة.
        يرجع None إذا مسموح (أو إن لم يكن المستخدم مفوَّضًا أصلًا)، أو dict خطأ إن مُنع.
        المدير الأصلي (native PM) غير مقيَّد إطلاقًا."""
        try:
            if self._x_is_native_pm():
                return None
            restr = self._x_delegate_restriction()
            if not restr:
                return None
            sec = (restr.get('sections') or {}).get(code)
            if not sec:
                return {'ok': False, 'error': 'غير مُصرّح لك بهذه القائمة'}
            if action and action != 'read' and not (sec.get('perms') or {}).get(action):
                _lbl = {'write': 'تعديل', 'cancel': 'إلغاء', 'submit': 'إرسال للاعتماد',
                        'print': 'طباعة'}.get(action, action)
                return {'ok': False, 'error': 'ليست لديك صلاحية «%s» على هذه القائمة' % _lbl}
            return None
        except Exception:
            return None

    @http.route(['/my/pm/x/deleg/users'], type='json', auth='user', website=False)
    def pm_x_deleg_users(self, q=None, **kw):
        """بحث مستخدمين بالاسم أو الإيميل أو رقم البادج."""
        env = request.env
        q = (q or '').strip()
        if len(q) < 2:
            return {'ok': True, 'users': []}
        Users = env['res.users'].sudo()
        users = Users.search(['|', '|', ('name', 'ilike', q), ('login', 'ilike', q),
                              ('partner_id.email', 'ilike', q)], limit=25)
        uids = set(users.ids)
        emps = env['hr.employee'].sudo().search([('barcode', 'ilike', q), ('user_id', '!=', False)], limit=25)
        for e in emps:
            uids.add(e.user_id.id)
        out = []
        for u in Users.browse(list(uids)):
            e0 = env['hr.employee'].sudo().search([('user_id', '=', u.id)], limit=1)
            out.append({'id': u.id, 'name': u.name, 'login': u.login,
                        'email': (u.partner_id.email or u.login or ''), 'badge': (e0.barcode or '')})
        out.sort(key=lambda x: x['name'] or '')
        return {'ok': True, 'users': out[:25]}

    @http.route(['/my/pm/x/deleg/list'], type='json', auth='user', website=False)
    def pm_x_deleg_list(self, **kw):
        env = request.env
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        if 'care.pms.delegation' not in env:
            return {'ok': True, 'project': p.display_name, 'items': []}
        recs = env['care.pms.delegation'].sudo().search([('project_id', '=', p.id)])
        out = []
        for r in recs:
            e0 = env['hr.employee'].sudo().search([('user_id', '=', r.delegate_id.id)], limit=1)
            out.append({'id': r.id, 'uid': r.delegate_id.id, 'user': r.delegate_id.name,
                        'email': (r.delegate_id.partner_id.email or r.delegate_id.login or ''),
                        'badge': (e0.barcode or ''), 'section': r.section_code,
                        'label': r.section_label or r.section_code,
                        'perms': r.perms_dict() if hasattr(r, 'perms_dict') else {'read': True},
                        'active': bool(r.active), 'until': str(r.date_until or '')})
        return {'ok': True, 'project': p.display_name, 'items': out}

    @http.route(['/my/pm/x/deleg/save'], type='json', auth='user', website=False)
    def pm_x_deleg_save(self, delegate_id=None, section_code=None, section_label=None,
                        perms=None, date_until=None, rid=None, **kw):
        env = request.env
        # إدارة التفويضات حصرًا للمدير الأصلي — يمنع مفوَّضًا من منح نفسه قوائم/صلاحيات
        if not self._x_is_native_pm():
            return {'ok': False, 'error': 'غير مُصرّح — إدارة التفويضات للمدير فقط'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        if not (delegate_id and section_code):
            return {'ok': False, 'error': 'حدّد المستخدم والقائمة'}
        if 'care.pms.delegation' not in env:
            return {'ok': False, 'error': 'التفويض غير مُفعّل'}
        perms = perms or {}
        vals = {'project_id': p.id, 'delegate_id': int(delegate_id),
                'section_code': section_code, 'section_label': section_label or section_code,
                'granted_by': env.user.id, 'state': 'accepted', 'active': True,
                'perm_read': bool(perms.get('read', True)), 'perm_write': bool(perms.get('write')),
                'perm_cancel': bool(perms.get('cancel')), 'perm_submit': bool(perms.get('submit')),
                'perm_print': bool(perms.get('print'))}
        if date_until:
            vals['date_until'] = date_until
        D = env['care.pms.delegation'].sudo()
        try:
            if rid:
                rec = D.browse(int(rid)).exists()
                if rec and rec.project_id.id not in self._pm_projects().ids:
                    return {'ok': False, 'error': 'غير مُصرّح'}
                if rec:
                    rec.write(vals)
                    return {'ok': True, 'id': rec.id, 'msg': 'حُدِّث التفويض'}
            exist = D.search([('project_id', '=', p.id), ('delegate_id', '=', int(delegate_id)),
                              ('section_code', '=', section_code)], limit=1)
            if exist:
                exist.write(vals)
                return {'ok': True, 'id': exist.id, 'msg': 'حُدِّث التفويض'}
            rec = D.create(vals)
            return {'ok': True, 'id': rec.id, 'msg': 'تم إنشاء التفويض'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/deleg/delete'], type='json', auth='user', website=False)
    def pm_x_deleg_delete(self, rid=None, **kw):
        env = request.env
        if not self._x_is_native_pm():
            return {'ok': False, 'error': 'غير مُصرّح — إدارة التفويضات للمدير فقط'}
        p = self._x_current_project(None)
        if 'care.pms.delegation' not in env:
            return {'ok': False, 'error': 'غير مُفعّل'}
        rec = env['care.pms.delegation'].sudo().browse(int(rid or 0)).exists()
        if rec and rec.project_id.id in self._pm_projects().ids and (not p or rec.project_id.id == p.id):
            rec.unlink()
            return {'ok': True, 'msg': 'حُذف التفويض'}
        return {'ok': False, 'error': 'غير موجود'}

    @http.route(['/my/pm/x', '/my/pm/x/p/<int:project_id>'], type='http', auth='user', website=False)
    def pm_x_home(self, project_id=None, **kw):
        return self._x_render_app(project_id=project_id)

    @http.route(['/my/pm/x/ts-full/<int:tid>'], type='http', auth='user', website=False)
    def pm_x_ts_full(self, tid=None, ro=None, **kw):
        """الشبكة التفاعلية بوضع مستقل (ملء الشاشة بلا شريط جانبي) — تُستدعى من زرّ
        الباك-إند على نموذج care.timesheet. نفس كود البورتال تمامًا، والتعديلات تُكتب
        على نفس الموديلات فتتزامن في المكانين.
        ro=1: وضع «اطّلاع فقط» — متاح لأي مستخدم داخلي (HR/إدارة) يملك صلاحية قراءة
        الكشف حتى لو لم يكن مدير المشروع؛ تُعطَّل كل أدوات التعديل وتبقى الطباعة/البحث/الشاشة."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not ts:
            return request.not_found()
        readonly = bool(ro)
        allowed = self._x_rec_allowed(ts)
        if (not allowed) and readonly and env.user.has_group('base.group_user'):
            # مستخدم داخلي: اطّلاع فقط إن كان يملك صلاحية قراءة الكشف (ACL غير sudo)
            try:
                env['care.timesheet'].browse(ts.id).check_access_rule('read')
                allowed = True
            except Exception:
                allowed = False
        if not allowed:
            return request.not_found()
        pid = ts.project_id.id if ('project_id' in ts._fields and ts.project_id) else None
        return self._x_render_app(project_id=pid, ts_open=ts.id, readonly=readonly)

    @http.route(['/my/pm/x/xw-stop/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_xw_stop(self, code=None, rid=None, reason=None, **kw):
        """طلب إيقاف العمل الإضافي من قائمتَي البوابة (overtime.request / care.extra.work الوارد)."""
        env = request.env
        model = CODE_MODEL.get(code)
        if code not in ('overtime', 'extrawork') or not model or model not in env:
            return {'ok': False, 'error': 'غير متاح لهذا النوع'}
        rec = env[model].sudo().browse(int(rid or 0)).exists()
        if not rec:
            return {'ok': False, 'error': 'السجلّ غير موجود'}
        try:
            my_projs = set(self._pm_projects().ids)
        except Exception:
            my_projs = set()
        is_hr = env.user.has_group('hr.group_hr_user') or env.user.has_group('base.group_system')
        proj = (rec.benef_project_id or rec.project_id) if code == 'extrawork' else getattr(rec, 'project_id', False)
        if not (is_hr or (proj and proj.id in my_projs)):
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            if code == 'extrawork':
                if rec.state not in ('active', 'paused'):
                    return {'ok': False, 'error': 'لا يمكن طلب إيقاف تكليف غير ساري'}
                rec._open_stop_request('end', reason or '')
                return {'ok': True, 'msg': 'تم إرسال طلب إيقاف الإضافي — بانتظار الموارد البشرية'}
            rec.action_care_request_stop(reason or '')
            return {'ok': True, 'msg': 'تم إرسال طلب إيقاف العمل الإضافي'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ الإحلال: /my/pm القديم يقدّم البورتال الجديد (SPA) ============
    # نُبقي البورتال القديم كاملاً في مكانه (لا حذف) ونتجاوز نقطتي الدخول فقط —
    # قابل للعودة فورًا عبر «?classic=1». التطبيق لا يتأثّر (يستخدم /api/v1 لا هذه الصفحات).
    @http.route(['/my/pm'], type='http', auth='user', website=True)
    def pm_home(self, **kw):
        if kw.get('classic'):
            return super(PMPortalX, self).pm_home(**kw)
        return self._x_render_app(project_id=None)

    @http.route(['/my/pm/p/<int:project_id>'], type='http', auth='user', website=True)
    def pm_overview(self, project_id=None, **kw):
        if kw.get('classic'):
            return super(PMPortalX, self).pm_overview(project_id=project_id, **kw)
        return self._x_render_app(project_id=project_id)

    # ============ بيانات العامل الحقيقية (ملف 360°) ============
    def _x_worker_data(self, e):
        g = lambda f, d='—': (getattr(e, f, None) or d)
        gd = lambda f: (str(getattr(e, f, '') or '') or '—')
        env = request.env

        def _lbl_sel(rec, field='state'):
            """تسمية حقل اختيار بدل الكود الخام (draft→مسودة…) — يصلح «اكواد» ملف العامل."""
            try:
                v = getattr(rec, field, None)
                if v and field in rec._fields and rec._fields[field].type == 'selection':
                    return dict(rec._fields[field]._description_selection(env)).get(v, v) or ''
                return v or ''
            except Exception:
                return getattr(rec, field, '') or ''
        nat = e.country_id.name if e.country_id else '—'
        resid = gd('residency_expiry_date') if 'residency_expiry_date' in e._fields else (gd('visa_expire') if 'visa_expire' in e._fields else '—')
        wage = ''
        try:
            wage = '%.3f' % (e.contract_id.wage or 0) if (e.contract_id and e.contract_id.wage) else ''
        except Exception:
            wage = ''
        wage = wage or (str(g('wage', '')) if 'wage' in e._fields else '')
        fields = [['الاسم الكامل', e.name], ['الرقم الوظيفي', g('barcode')],
                  ['المهنة', g('job_title') or (e.job_id.name if e.job_id else '—')],
                  ['الجنسية', nat], ['تاريخ الميلاد', gd('birthday')],
                  ['الرقم المدني', g('identification_id') or g('civil_code')],
                  ['انتهاء الإقامة', resid], ['القسم / المشروع', e.department_id.name or '—'],
                  ['تاريخ الالتحاق', gd('joining_date') if 'joining_date' in e._fields else (gd('first_contract_date'))],
                  ['الراتب', wage or '—'], ['الجوال', g('mobile_phone') or g('work_phone')]]

        def cnt(model, dom):
            try:
                return env[model].sudo().search_count(dom) if model in env else 0
            except Exception:
                return 0
        loans_n = cnt('care.loan', [('employee_id', '=', e.id)])
        docs_n = cnt('care.worker.document', [('employee_id', '=', e.id)]) or cnt('care.document.request', [('employee_id', '=', e.id)])
        cust_n = cnt('care.custody', [('employee_id', '=', e.id)])
        att_n = cnt('hr.attendance', [('employee_id', '=', e.id)])
        smart = [['clock', 'الحضور', att_n, 'teal'], ['play', 'الإجازات', cnt('hr.leave', [('employee_id', '=', e.id)]), 'emerald'],
                 ['cash', 'السلف', loans_n, 'amber'], ['star', 'التقييم', str(round(getattr(e, 'pulse_avg', 0) or 0, 1)), 'blue'],
                 ['doc', 'المستندات', docs_n, 'sky'], ['asset', 'العُهد', cust_n, 'violet']]

        def rows_of(model, dom, mapper, limit=100000):
            try:
                if model not in env:
                    return []
                recs = env[model].sudo().search(dom, limit=limit, order='id desc')
                return [mapper(r) for r in recs]
            except Exception:
                return []
        loans = rows_of('care.loan', [('employee_id', '=', e.id)],
                        lambda r: [getattr(r, 'name', '') or '—', _f(getattr(r, 'amount', 0)), _f(getattr(r, 'remaining', 0) or getattr(r, 'balance', 0)), 'pill:info:%s' % _lbl_sel(r, 'state')])
        pens = rows_of('care.penalty', [('employee_id', '=', e.id)],
                       lambda r: [getattr(r, 'name', '') or '—', _f(getattr(r, 'amount', 0)), str(getattr(r, 'date', '') or ''), 'pill:crit:%s' % _lbl_sel(r, 'state')])
        bons = rows_of('care.bonus', [('employee_id', '=', e.id)],
                       lambda r: [getattr(r, 'name', '') or '—', _f(getattr(r, 'amount', 0)), str(getattr(r, 'date', '') or ''), 'pill:ok:%s' % _lbl_sel(r, 'state')])
        leaves = rows_of('hr.leave', [('employee_id', '=', e.id)],
                         lambda r: [(r.holiday_status_id.name if r.holiday_status_id else '—'), str(getattr(r, 'request_date_from', '') or getattr(r, 'date_from', '') or ''), str(getattr(r, 'request_date_to', '') or getattr(r, 'date_to', '') or ''), _f(getattr(r, 'number_of_days', 0)), 'pill:info:%s' % _lbl_sel(r, 'state')])
        docs = rows_of('care.worker.document', [('employee_id', '=', e.id)],
                       lambda r: [(r.type_id.name if getattr(r, 'type_id', False) else (getattr(r, 'name', '') or '—')), 'pill:info:%s' % (_lbl_sel(r, 'state') or _lbl_sel(r, 'status') or 'سارٍ')])
        reqs = rows_of('care.document.request', [('employee_id', '=', e.id)],
                       lambda r: [getattr(r, 'name', '') or '—', 'pill:info:%s' % _lbl_sel(r, 'state'), str(getattr(r, 'create_date', '') or '')[:10]])
        transfers = rows_of('employee.shift.request', [('employee_id', '=', e.id)],
                            lambda r: [(r.current_department.name if getattr(r, 'current_department', False) else '—'),
                                       (r.new_department.name if getattr(r, 'new_department', False) else '—'),
                                       (_lbl_sel(r, 'shift_type') or '—'),
                                       str(getattr(r, 'transfer_date', '') or ''), 'pill:info:%s' % _lbl_sel(r, 'state')])
        # المقاسات من حقول الموظف (care_uniform_delivery)
        sizes = []
        for fld, lab in (('uniform_top_size', 'مقاس العلوي'), ('uniform_bottom_size', 'مقاس السفلي'),
                         ('shoe_size', 'مقاس الحذاء'), ('cap_size', 'مقاس القبعة')):
            if fld in e._fields and getattr(e, fld, False):
                v = getattr(e, fld)
                try:
                    v = dict(e._fields[fld]._description_selection(env)).get(v, v)
                except Exception:
                    pass
                sizes.append([lab, v])
        if 'uniform_size_note' in e._fields and getattr(e, 'uniform_size_note', False):
            sizes.append(['ملاحظة المقاسات', e.uniform_size_note])
        # بطاقات «السجلات» (عدّادات)
        records = [['الإجازات', '🏖️', cnt('hr.leave', [('employee_id', '=', e.id)])],
                   ['السلف', '💵', loans_n],
                   ['الجزاءات', '⚠️', cnt('care.penalty', [('employee_id', '=', e.id)])],
                   ['المكافآت', '🎖️', cnt('care.bonus', [('employee_id', '=', e.id)])],
                   ['العُهد', '📦', cust_n], ['الحضور', '🕐', att_n],
                   ['المستندات', '📄', docs_n],
                   ['طلبات المستندات', '📝', cnt('care.document.request', [('employee_id', '=', e.id)])],
                   ['الإضافي', '⚡', cnt('overtime.request', [('employee_id', '=', e.id)])],
                   ['التكليفات', '🔁', cnt('employee.shift.request', [('employee_id', '=', e.id)])]]
        att = rows_of('hr.attendance', [('employee_id', '=', e.id)],
                      lambda r: [str(r.check_in.date()) if r.check_in else '—', str(r.check_in.strftime('%H:%M')) if r.check_in else '—', str(r.check_out.strftime('%H:%M')) if r.check_out else '—', _f(getattr(r, 'worked_hours', 0))], limit=15)
        cls, txt = _WS.get(getattr(e, 'worker_status', 'active') or 'active', ('ok', 'نشط'))
        # ===== نبض صحّي: شريط حضور 14 يومًا + مؤشّرات امتثال =====
        import datetime as _dt
        today_d = _dt.date.today()
        att14 = []
        try:
            Att = env['hr.attendance'].sudo()
            start = today_d - _dt.timedelta(days=13)
            for i in range(14):
                d = start + _dt.timedelta(days=i)
                pres = Att.search_count([('employee_id', '=', e.id), ('check_in', '>=', str(d)),
                                         ('check_in', '<', str(d + _dt.timedelta(days=1)))])
                att14.append([d.strftime('%d'), 1 if pres else 0])
        except Exception:
            att14 = []
        present14 = sum(x[1] for x in att14)
        compliance = []

        def _chk(label, dval):
            if not dval:
                return [label, 'mut', '—']
            try:
                dd = dval if hasattr(dval, 'year') else _dt.date.fromisoformat(str(dval)[:10])
                days = (dd - today_d).days
                st = 'crit' if days < 0 else ('warn' if days <= 60 else 'ok')
                return [label, st, str(dd) + ((' · %s يوم' % days) if days >= 0 else ' · منتهية')]
            except Exception:
                return [label, 'mut', str(dval)[:10]]
        try:
            rv = getattr(e, 'residency_expiry_date', None) or getattr(e, 'visa_expire', None)
            compliance.append(_chk('الإقامة', rv))
            if 'work_permit_expiration_date' in e._fields:
                compliance.append(_chk('تصريح العمل', getattr(e, 'work_permit_expiration_date', None)))
            compliance.append(['المستندات', 'ok' if docs_n else 'warn', '%s مستند' % docs_n])
            compliance.append(['السلف المفتوحة', 'warn' if loans_n else 'ok', '%s سلفة' % loans_n])
        except Exception:
            pass
        health = {'attend_rate': int(round(present14 / 14.0 * 100)) if att14 else 0,
                  'present14': present14, 'att14': att14, 'compliance': compliance,
                  'loans_n': loans_n, 'docs_n': docs_n}
        # ===== مخطّط زمني تفاعلي: دمج أحداث العامل الأخيرة زمنيًّا =====
        timeline = []

        def _evt(model, dom, icon, color, code, titlefn, metafn, datefn, limit=8):
            try:
                if model not in env:
                    return
                for r in env[model].sudo().search(dom, limit=limit, order='id desc'):
                    dv = datefn(r)
                    if not dv:
                        continue
                    ds = str(dv)[:10]
                    timeline.append([ds, icon, color, titlefn(r) or '—', metafn(r) or '', code, r.id])
            except Exception:
                pass
        _evt('hr.leave', [('employee_id', '=', e.id)], 'play', 'emerald', 'leaves',
             lambda r: (r.holiday_status_id.name if r.holiday_status_id else 'إجازة'),
             lambda r: '%s يوم · %s' % (_f(getattr(r, 'number_of_days', 0)), (r.state or '')),
             lambda r: getattr(r, 'request_date_from', '') or getattr(r, 'create_date', ''))
        _evt('care.loan', [('employee_id', '=', e.id)], 'cash', 'amber', 'loans',
             lambda r: getattr(r, 'name', '') or 'سلفة',
             lambda r: '%s · %s' % (_f(getattr(r, 'amount', 0)), _lbl_sel(r, 'state')),
             lambda r: getattr(r, 'create_date', ''))
        _evt('care.penalty', [('employee_id', '=', e.id)], 'alert', 'red', 'penalties',
             lambda r: getattr(r, 'name', '') or 'جزاء',
             lambda r: _f(getattr(r, 'amount', 0)), lambda r: getattr(r, 'date', '') or getattr(r, 'create_date', ''))
        _evt('care.bonus', [('employee_id', '=', e.id)], 'star', 'blue', 'bonuses',
             lambda r: getattr(r, 'name', '') or 'مكافأة',
             lambda r: _f(getattr(r, 'amount', 0)), lambda r: getattr(r, 'date', '') or getattr(r, 'create_date', ''))
        _evt('care.document.request', [('employee_id', '=', e.id)], 'doc', 'sky', 'requests',
             lambda r: getattr(r, 'name', '') or 'طلب مستند',
             lambda r: _lbl_sel(r, 'state'), lambda r: getattr(r, 'create_date', ''))
        _evt('employee.shift.request', [('employee_id', '=', e.id)], 'group3', 'violet', 'additional',
             lambda r: 'تكليف: %s' % (r.new_department.name if getattr(r, 'new_department', False) else '—'),
             lambda r: _lbl_sel(r, 'state'),
             lambda r: getattr(r, 'transfer_date', '') or getattr(r, 'create_date', ''))
        _evt('overtime.request', [('employee_id', '=', e.id)], 'clock', 'teal', 'overtime',
             lambda r: 'عمل إضافي',
             lambda r: _lbl_sel(r, 'state'), lambda r: getattr(r, 'create_date', ''))
        timeline.sort(key=lambda x: x[0], reverse=True)
        timeline = timeline[:20]
        # تصاريح العامل (الحالة + التواريخ + صورة التصريح عبر مسار sudo)
        permits = []
        if 'care.permit.line' in env:
            try:
                for r in env['care.permit.line'].sudo().search([('employee_id', '=', e.id)], order='id desc', limit=100000):
                    permits.append({
                        'type': (r.type_id.name if r.type_id else '—'),
                        'ref': r.reference or '',
                        'state': (_sel_label_rec(r.request_id) if r.request_id else (_sel_label_rec(r) if 'state' in r._fields else '')),
                        'expiry': (_sel_label_rec(r, 'expiry_state') if 'expiry_state' in r._fields else ''),
                        'date_from': str(r.date_from or ''), 'date_to': str(r.date_to or ''),
                        'issued': bool(getattr(r, 'issued', False)),
                        'days_left': getattr(r, 'days_left', 0) or 0,
                        'img': ('/my/pm/x/permit/img/%s' % r.id) if r.attachment else '',
                    })
            except Exception:
                permits = []

        # بطاقات نظرة عامة غنيّة (كل الحقول المهمّة، محروسة بوجود الحقل)
        def _ef(f):  # قيمة حقل محروسة بوجوده (تاريخ/نص)
            return gd(f) if f in e._fields else None

        def _es(f):  # تسمية حقل اختيار
            return _lbl_sel(e, f) if (f in e._fields and getattr(e, f, None)) else None

        def _card(title, items):
            items = [it for it in items if it and it[1] not in (None, '', '—', False)]
            return [title, items] if items else None
        _bank = ''
        try:
            if 'bank_account_id' in e._fields and e.bank_account_id:
                _bank = e.bank_account_id.acc_number or e.bank_account_id.bank_id.name or ''
        except Exception:
            _bank = ''
        _house = ''
        for hf in ('housing_room_id', 'room_id', 'housing_bed_id', 'bed_id', 'hostel_id', 'housing_hostel_id'):
            if hf in e._fields and getattr(e, hf, False):
                try:
                    _house = (_house + ' / ' if _house else '') + (getattr(e, hf).display_name or '')
                except Exception:
                    pass
        _lv_bal = ''
        if 'leave_remaining_total' in e._fields:
            try:
                _lv_bal = '%g' % (e.leave_remaining_total or 0)
            except Exception:
                _lv_bal = str(getattr(e, 'leave_remaining_total', '') or '')
        _ocards = [c for c in [
            _card('👤 البيانات الشخصية', [
                ['الاسم بالإنجليزية', _ef('english_name')], ['الجنسية', nat],
                ['تاريخ الميلاد', gd('birthday')], ['الجنس', _es('gender')],
                ['الحالة الاجتماعية', _es('marital')],
                ['الرقم المدني', g('identification_id') or g('civil_code')],
                ['الرقم الآلي (MOI)', _ef('moi_number')]]),
            _card('🛂 الإقامة والتأشيرة', [
                ['نوع الإقامة', _es('residency_type')],
                ['بداية الإقامة', _ef('residency_start_date')], ['انتهاء الإقامة', resid],
                ['رقم التأشيرة', _ef('visa_no')], ['انتهاء التأشيرة', _ef('visa_expire')],
                ['تاريخ الدخول', _ef('enter_date')],
                ['رقم الجواز', _ef('passport_no')]]),
            _card('🏛️ الشؤون وتصريح العمل', [
                ['مسمّى الشؤون', _ef('social_affairs_title')],
                ['انتهاء تصريح الشؤون', _ef('affairs_permit_end_date')],
                ['انتهاء تصريح العمل', _ef('work_permit_expiration_date')],
                ['رقم العقد الاجتماعي', _ef('social_contract_no')],
                ['تاريخ أوّل عقد', _ef('first_contract_date')]]),
            _card('💼 العمل والراتب', [
                ['المهنة', g('job_title') or (e.job_id.name if e.job_id else '—')],
                ['القسم / المشروع', e.department_id.name or '—'], ['الراتب', wage or '—'],
                ['راتب الشؤون', _ef('affairs_salary')], ['الحساب البنكي', _bank or None],
                ['رصيد الإجازات', _lv_bal or None]]),
            _card('🏠 السكن والطوارئ', [
                ['السكن', _house or None],
                ['جهة الطوارئ', _ef('emergency_contact')], ['هاتف الطوارئ', _ef('emergency_phone')]]),
            _card('📞 التواصل', [
                ['الجوال', g('mobile_phone') or g('work_phone')], ['البريد', g('work_email')]]),
        ] if c]
        return {
            'name': e.name, 'no': g('barcode'), 'job': g('job_title') or (e.job_id.name if e.job_id else '—'),
            'dept': e.department_id.name or '—', 'status': [cls, txt], 'residency': resid, 'wage': wage or '—',
            'fields': fields, 'smart': smart,
            'ocards': _ocards,
            'loans': loans, 'penalties': pens, 'bonuses': bons, 'leaves': leaves, 'docs': docs, 'attendance': att,
            'requests': reqs, 'transfers': transfers, 'sizes': sizes, 'records': records,
            'health': health, 'timeline': timeline, 'permits': permits,
        }

    @http.route(['/my/pm/x/worker/<int:eid>'], type='http', auth='user', website=False)
    def pm_x_worker(self, eid=None, **kw):
        env = request.env
        e = env['hr.employee'].sudo().browse(int(eid or 0)).exists()
        # تحقّق أن العامل ضمن مشاريع المدير
        dept_ids = self._pm_projects().mapped('pms_department_id').ids
        ok = self._x_emp_allowed(e, dept_ids)
        if not ok:
            return request.make_response(json.dumps({'ok': False}), headers=[('Content-Type', 'application/json')])
        data = self._x_worker_data(e)
        return request.make_response(json.dumps({'ok': True, 'data': data}, ensure_ascii=False, default=str),
                                     headers=[('Content-Type', 'application/json; charset=utf-8')])

    @http.route(['/my/pm/x/worker/<int:eid>/file'], type='http', auth='user', website=True)
    def pm_x_worker_file(self, eid=None, **kw):
        """ملف العامل الشامل (صفحة A4 ثنائية اللغة بهوية CARE، جاهزة للطباعة من المتصفّح)."""
        env = request.env
        e = env['hr.employee'].sudo().browse(int(eid or 0)).exists()
        dept_ids = self._pm_projects().mapped('pms_department_id').ids
        ok = self._x_emp_allowed(e, dept_ids)
        if not ok:
            return request.not_found()
        d = self._x_worker_data(e)
        h = d.get('health', {})
        comp = h.get('compliance', [])
        tl = d.get('timeline', [])
        company = (self._pm_projects()[:1].company_id or env.company)
        from markupsafe import escape as _esc

        # تسميات ثنائية اللغة في الملف المطبوع (مستند رسمي) — عربي · English
        _LBLEN = {
            'الاسم الكامل': 'Full Name', 'الرقم الوظيفي': 'Staff No.', 'الجنسية': 'Nationality',
            'تاريخ الميلاد': 'Date of Birth', 'الرقم المدني': 'Civil ID', 'الجوال': 'Mobile',
            'المهنة': 'Job Title', 'القسم / المشروع': 'Department / Project',
            'انتهاء الإقامة': 'Residency Expiry', 'تاريخ الالتحاق': 'Joining Date', 'الراتب': 'Salary',
            'الإقامة': 'Residency', 'تصريح العمل': 'Work Permit', 'المستندات': 'Documents', 'السلف': 'Loans',
        }

        def _lbl(a):
            en = _LBLEN.get(a)
            return (_esc(a) + ' · ' + _esc(en)) if en else _esc(a)

        def _rowspairs(pairs):
            return ''.join(
                '<tr><td class="k">%s</td><td class="v">%s</td></tr>' % (_lbl(a), _esc(b))
                for a, b in pairs)
        _stc = {'ok': '#1f9a55', 'warn': '#c58a22', 'crit': '#cc4668', 'mut': '#9aa3b2'}
        comp_html = ''.join(
            '<tr><td class="k">%s</td><td class="v"><span class="dot" style="background:%s"></span>%s</td></tr>'
            % (_lbl(c[0]), _stc.get(c[1], '#9aa3b2'), _esc(c[2])) for c in comp) or '<tr><td colspan="2">—</td></tr>'
        bars = ''.join(
            '<span class="bar" style="height:%spx;background:%s" title="%s"></span>'
            % ((18 if x[1] else 5), ('#1f9a55' if x[1] else '#d7dce3'), _esc(x[0])) for x in h.get('att14', []))
        tl_html = ''.join(
            '<tr><td class="td">%s</td><td class="tt">%s</td><td class="tm">%s</td></tr>'
            % (_esc(t[0]), _esc(t[3]), _esc(t[4] or '')) for t in tl[:14]) or '<tr><td colspan="3">—</td></tr>'
        rec_html = ''.join(
            '<div class="rc"><div class="rn">%s</div><div class="rl">%s</div></div>'
            % (r[2], _esc(r[0])) for r in d.get('records', []))
        logo = '/web/image/res.company/%s/logo' % company.id
        photo = '/web/image/hr.employee/%s/image_256' % e.id
        html = u"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ملف العامل · %(name)s</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap"/>
<style>
@page{size:A4;margin:12mm}
*{box-sizing:border-box;font-family:'Tajawal','Segoe UI',Tahoma,sans-serif}
body{margin:0;background:#eef1f5;color:#17202e;font-size:12px}
.sheet{max-width:800px;margin:16px auto;background:#fff;padding:0;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.08);overflow:hidden}
.hd{background:linear-gradient(135deg,#0a1f44,#12306e);color:#fff;padding:18px 22px;display:flex;align-items:center;gap:16px}
.hd img.logo{height:44px;background:#fff;border-radius:6px;padding:4px}
.hd .ttl{flex:1}
.hd h1{margin:0;font-size:18px;font-weight:800}
.hd .sub{opacity:.85;font-size:11px;margin-top:2px}
.hd img.photo{width:72px;height:72px;border-radius:10px;object-fit:cover;border:2px solid rgba(255,255,255,.35)}
.body{padding:18px 22px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{border:1px solid #e3e8ef;border-radius:9px;overflow:hidden;margin-bottom:14px}
.ch{background:#f5f7fa;padding:8px 12px;font-weight:800;font-size:12px;color:#0a1f44;border-bottom:1px solid #e3e8ef}
table{width:100%%;border-collapse:collapse}
td{padding:6px 12px;border-bottom:1px solid #eef1f5;vertical-align:top}
td.k{color:#657086;width:42%%;font-size:11px}
td.v{font-weight:700;font-size:11.5px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%%;margin-inline-end:6px;vertical-align:middle}
.bars{display:flex;align-items:flex-end;gap:2px;height:22px;padding:10px 12px}
.bar{flex:1;border-radius:2px}
.rate{font-size:22px;font-weight:800;color:#1f9a55}
.recs{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;padding:12px}
.rc{text-align:center;background:#f7f9fb;border:1px solid #eef1f5;border-radius:8px;padding:8px 4px}
.rc .rn{font-size:17px;font-weight:800;color:#0a1f44}
.rc .rl{font-size:10px;color:#657086;margin-top:2px}
td.td{font-size:10.5px;color:#657086;width:22%%;white-space:nowrap}
td.tt{font-weight:700;font-size:11px}
td.tm{font-size:10.5px;color:#657086;text-align:left}
.ft{display:flex;justify-content:space-between;padding:26px 22px 14px;color:#657086;font-size:11px}
.sig{text-align:center}.sig .ln{border-top:1px solid #9aa3b2;width:150px;margin:28px auto 4px}
.toolbar{max-width:800px;margin:14px auto 0;text-align:center}
.toolbar button{background:#0a1f44;color:#fff;border:0;border-radius:8px;padding:9px 20px;font-weight:700;cursor:pointer;font-family:inherit}
@media print{.toolbar{display:none}body{background:#fff}.sheet{box-shadow:none;margin:0;border-radius:0;max-width:none}}
</style></head><body>
<div class="toolbar"><button onclick="window.print()">🖨️ طباعة الملف / Print</button></div>
<div class="sheet">
  <div class="hd">
    <img class="logo" src="%(logo)s" onerror="this.style.display='none'"/>
    <div class="ttl"><h1>%(name)s</h1><div class="sub">ملف العامل الشامل · Worker File &nbsp;|&nbsp; %(no)s · %(job)s</div></div>
    <img class="photo" src="%(photo)s" onerror="this.style.display='none'"/>
  </div>
  <div class="body">
    <div class="grid">
      <div class="card"><div class="ch">البيانات الأساسية · Personal</div><table>%(personal)s</table></div>
      <div class="card"><div class="ch">الإقامة والعمل · Residency &amp; Work</div><table>%(work)s</table></div>
    </div>
    <div class="grid">
      <div class="card"><div class="ch">الحضور (14 يومًا) · Attendance</div>
        <div style="padding:10px 12px 0"><span class="rate">%(rate)s%%</span> <span style="color:#657086;font-size:11px">· %(present)s/14</span></div>
        <div class="bars">%(bars)s</div></div>
      <div class="card"><div class="ch">الامتثال والمستحقّات · Compliance</div><table>%(comp)s</table></div>
    </div>
    <div class="card"><div class="ch">ملخّص السجلّات · Records summary</div><div class="recs">%(recs)s</div></div>
    <div class="card"><div class="ch">المخطّط الزمني للنشاط · Activity timeline</div><table>%(tl)s</table></div>
    <div class="ft">
      <div class="sig"><div class="ln"></div>مدير المشروع · Project Manager</div>
      <div class="sig"><div class="ln"></div>الموارد البشرية · HR</div>
      <div style="align-self:flex-end;text-align:left">تاريخ الطباعة · Printed: %(today)s<br/>%(company)s</div>
    </div>
  </div>
</div>
</body></html>""" % {
            'name': _esc(d.get('name', '')), 'no': _esc(d.get('no', '')), 'job': _esc(d.get('job', '')),
            'logo': logo, 'photo': photo,
            'personal': _rowspairs([(f[0], f[1]) for f in d.get('fields', []) if f[0] in (
                'الاسم الكامل', 'الرقم الوظيفي', 'الجنسية', 'تاريخ الميلاد', 'الرقم المدني', 'الجوال')]),
            'work': _rowspairs([(f[0], f[1]) for f in d.get('fields', []) if f[0] in (
                'المهنة', 'القسم / المشروع', 'انتهاء الإقامة', 'تاريخ الالتحاق', 'الراتب')]),
            'rate': h.get('attend_rate', 0), 'present': h.get('present14', 0),
            'bars': bars, 'comp': comp_html, 'recs': rec_html, 'tl': tl_html,
            'today': str(request.env.cr and __import__('datetime').date.today()),
            'company': _esc(company.name or 'CARE'),
        }
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route(['/my/pm/x/project/<int:pid>/file'], type='http', auth='user', website=True)
    def pm_x_project_file(self, pid=None, **kw):
        """ملخّص المشروع الشامل (صفحة A4 ثنائية اللغة بهوية CARE، جاهزة للطباعة)."""
        env = request.env
        p = env['project.project'].sudo().browse(int(pid or 0)).exists()
        if not p or p.id not in self._pm_projects().ids:
            return request.not_found()
        from markupsafe import escape as _esc
        import datetime as _dt
        g = lambda f: getattr(p, f, 0) or 0
        dept = (p.pms_department_id.name if 'pms_department_id' in p._fields and p.pms_department_id else '—')
        pm = (p.project_manager_id.name if 'project_manager_id' in p._fields and p.project_manager_id else '—')
        wf = self._x_workforce(p)
        attn = self._x_attention(p)
        trend = self._x_attend_trend(p)
        kpis = self._x_kpis(p)
        company = (self._pm_projects()[:1].company_id or env.company)
        progress = 0
        try:
            Task = env['project.task'].sudo()
            tot = Task.search_count([('project_id', '=', p.id)])
            done = Task.search_count([('project_id', '=', p.id), ('state', 'in', ('1_done',))]) if tot else 0
            progress = int(round(100.0 * done / tot)) if tot else 0
        except Exception:
            progress = 0
        # KPI cards
        kpi_html = ''.join(
            '<div class="kpi"><div class="kn">%s</div><div class="kl">%s</div></div>'
            % (_esc(str(k[2])), _esc(k[1])) for k in (kpis or [])[:6]) or ''
        # workforce tables
        def _wf_rows(data):
            tot = sum(x[1] for x in data) or 1
            return ''.join('<tr><td class="k">%s</td><td class="v">%s</td><td class="p">%s%%</td></tr>'
                           % (_esc(x[0]), x[1], int(round(x[1] * 100.0 / tot))) for x in data) or '<tr><td colspan="3">—</td></tr>'
        _stc = {'crit': '#cc4668', 'warn': '#c58a22', 'info': '#1f86c7'}
        attn_html = ''.join(
            '<tr><td class="v"><span class="dot" style="background:%s"></span>%s</td><td class="n">%s</td></tr>'
            % (_stc.get(a[0], '#1f86c7'), _esc(a[3]), a[2]) for a in attn) or '<tr><td colspan="2">لا بنود · None</td></tr>'
        tvals = [x[1] for x in trend] or [0]
        tavg = int(round(sum(tvals) / len(tvals))) if tvals else 0
        tpeak = max(tvals) if tvals else 0
        bars = ''.join('<span class="bar" style="height:%spx" title="%s"></span>'
                       % (max(3, int(v * 26.0 / (tpeak or 1))), _esc(str(d))) for d, v in (trend or []))
        logo = '/web/image/res.company/%s/logo' % company.id
        html = u"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ملخّص المشروع · %(name)s</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap"/>
<style>
@page{size:A4;margin:12mm}
*{box-sizing:border-box;font-family:'Tajawal','Segoe UI',Tahoma,sans-serif}
body{margin:0;background:#eef1f5;color:#17202e;font-size:12px}
.sheet{max-width:800px;margin:16px auto;background:#fff;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.08);overflow:hidden}
.hd{background:linear-gradient(135deg,#0a1f44,#12306e);color:#fff;padding:18px 22px;display:flex;align-items:center;gap:16px}
.hd img.logo{height:46px;background:#fff;border-radius:6px;padding:4px}
.hd .ttl{flex:1}.hd h1{margin:0;font-size:18px;font-weight:800}.hd .sub{opacity:.85;font-size:11px;margin-top:3px}
.body{padding:18px 22px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
.kpi{background:#f7f9fb;border:1px solid #eef1f5;border-radius:9px;padding:12px;text-align:center}
.kpi .kn{font-size:20px;font-weight:800;color:#0a1f44}.kpi .kl{font-size:10.5px;color:#657086;margin-top:3px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{border:1px solid #e3e8ef;border-radius:9px;overflow:hidden;margin-bottom:14px}
.ch{background:#f5f7fa;padding:8px 12px;font-weight:800;font-size:12px;color:#0a1f44;border-bottom:1px solid #e3e8ef}
table{width:100%%;border-collapse:collapse}
td{padding:6px 12px;border-bottom:1px solid #eef1f5}
td.k{color:#657086;font-size:11px}td.v{font-weight:700;font-size:11.5px}td.p,td.n{text-align:left;font-weight:700;color:#0a1f44;width:60px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%%;margin-inline-end:6px;vertical-align:middle}
.prog{height:9px;background:#eef1f5;border-radius:6px;overflow:hidden;margin:6px 0}
.prog i{display:block;height:100%%;background:linear-gradient(90deg,#1f9a55,#45c57e)}
.bars{display:flex;align-items:flex-end;gap:2px;height:30px;padding:10px 12px}
.bar{flex:1;background:#1f9a55;border-radius:2px;min-height:3px}
.ft{display:flex;justify-content:space-between;padding:26px 22px 14px;color:#657086;font-size:11px}
.sig{text-align:center}.sig .ln{border-top:1px solid #9aa3b2;width:150px;margin:28px auto 4px}
.toolbar{max-width:800px;margin:14px auto 0;text-align:center}
.toolbar button{background:#0a1f44;color:#fff;border:0;border-radius:8px;padding:9px 20px;font-weight:700;cursor:pointer;font-family:inherit}
@media print{.toolbar{display:none}body{background:#fff}.sheet{box-shadow:none;margin:0;border-radius:0;max-width:none}}
</style></head><body>
<div class="toolbar"><button onclick="window.print()">🖨️ طباعة الملخّص / Print</button></div>
<div class="sheet">
  <div class="hd"><img class="logo" src="%(logo)s" onerror="this.style.display='none'"/>
    <div class="ttl"><h1>%(name)s</h1><div class="sub">ملخّص المشروع · Project Summary &nbsp;|&nbsp; %(dept)s · %(pm)s</div></div></div>
  <div class="body">
    <div class="kpis">%(kpis)s</div>
    <div class="card"><div class="ch">نسبة الإنجاز · Completion</div><div style="padding:10px 12px"><div class="prog"><i style="width:%(progress)s%%"></i></div><div style="text-align:center;font-weight:800;color:#0a1f44">%(progress)s%%</div></div></div>
    <div class="grid">
      <div class="card"><div class="ch">القوى العاملة حسب الجنسية · By nationality</div><table>%(nat)s</table></div>
      <div class="card"><div class="ch">القوى العاملة حسب الحالة · By status</div><table>%(status)s</table></div>
    </div>
    <div class="card"><div class="ch">يحتاج انتباهك · Needs attention</div><table>%(attn)s</table></div>
    <div class="card"><div class="ch">اتجاه الحضور (14 يومًا) · Attendance trend &nbsp;—&nbsp; المتوسّط %(tavg)s · الذروة %(tpeak)s</div><div class="bars">%(bars)s</div></div>
    <div class="ft">
      <div class="sig"><div class="ln"></div>مدير المشروع · Project Manager</div>
      <div class="sig"><div class="ln"></div>الإدارة · Management</div>
      <div style="align-self:flex-end;text-align:left">تاريخ الطباعة · Printed: %(today)s<br/>%(company)s</div>
    </div>
  </div>
</div>
</body></html>""" % {
            'name': _esc(p.name or ''), 'dept': _esc(dept), 'pm': _esc(pm), 'logo': logo,
            'kpis': kpi_html, 'progress': progress,
            'nat': _wf_rows(wf.get('by_nat', [])), 'status': _wf_rows(wf.get('by_status', [])),
            'attn': attn_html, 'bars': bars, 'tavg': tavg, 'tpeak': tpeak,
            'today': str(_dt.date.today()), 'company': _esc(company.name or 'CARE'),
        }
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ============ تضييق النطاق: طرح شجر أقسام المشاريع الأخرى (أمان) ============
    def _x_exclude_dept_ids(self):
        """أقسام مشاريعَ لا يديرها المستخدم (مطروحةً منها أقسامه) — تُستبعَد من شجرة
        child_of حتى لا يرث مديرٌ قسمُ مشروعه عقدةٌ أب (مثل «الإدارة») عمّالَ مشاريع أخرى."""
        c = getattr(self, '_x_excl_cache', None)
        if c is not None:
            return c
        env = request.env
        mine = self._pm_projects()
        my_dept_ids = set(mine.mapped('pms_department_id').ids)
        res = []
        if my_dept_ids:
            others = env['project.project'].sudo().search(
                [('id', 'not in', mine.ids), ('pms_department_id', '!=', False)])
            cand = list(set(others.mapped('pms_department_id').ids) - my_dept_ids)
            if cand:
                # نُبقي فقط أقسام المشاريع الأخرى التي هي **أحفاد** داخل شجرة أقسام المستخدم
                # (لا الأسلاف) — وإلا لو كان قسم مشروع المستخدم متفرّعًا تحت قسم مشروع آخر،
                # لأفرغنا نطاقه بالكامل خطأً.
                res = env['hr.department'].sudo().search(
                    [('id', 'in', cand), ('id', 'child_of', list(my_dept_ids))]).ids
        self._x_excl_cache = res
        return res

    def _x_emp_dom(self, dept_scope, field='department_id'):
        """نطاق مضيّق: child_of على قسم المشروع **ناقصاً** شجر أقسام المشاريع الأخرى.
        يُستعمل في بناة القوائم والعدّادات فلا تظهر صفوف/أعداد عمّالِ مشاريعَ أخرى حين
        يكون قسم المشروع عقدةً أب. `field` قد يكون department_id أو employee_id.department_id."""
        dom = [(field, 'child_of', dept_scope)]
        ex = self._x_exclude_dept_ids()
        if ex:
            dom += ['!', (field, 'child_of', ex)]
        return dom

    def _x_emp_allowed(self, emp, base_dept_ids):
        """عامل ضمن شجرة أقسام المستخدم بعد طرح شجر المشاريع الأخرى."""
        if not (emp and base_dept_ids):
            return False
        Emp = request.env['hr.employee'].sudo()
        if not Emp.search_count([('id', '=', emp.id), ('department_id', 'child_of', base_dept_ids)]):
            return False
        excl = self._x_exclude_dept_ids()
        if excl and Emp.search_count([('id', '=', emp.id), ('department_id', 'child_of', excl)]):
            return False
        return True

    def _x_dept_allowed(self, dept, base_dept_ids, exact=False):
        """قسم ضمن شجرة أقسام المستخدم بعد طرح شجر المشاريع الأخرى (أو مطابقة دقيقة للأصول)."""
        if not (dept and base_dept_ids):
            return False
        if exact:
            return dept.id in base_dept_ids
        Dept = request.env['hr.department'].sudo()
        if not Dept.search_count([('id', '=', dept.id), ('id', 'child_of', base_dept_ids)]):
            return False
        excl = self._x_exclude_dept_ids()
        if excl and Dept.search_count([('id', '=', dept.id), ('id', 'child_of', excl)]):
            return False
        return True

    # ============ نطاق الورش (c2c.workshop) — مطابق لبورتال الورش القديم ============
    def _x_ws_full_access(self):
        u = request.env.user
        if u.has_group('care2care_workshop.group_workshop_manager') or u.has_group('base.group_system'):
            return True
        try:
            return u in request.env['c2c.workshop.approval.config'].sudo()._get()._authorized_user_ids()
        except Exception:
            return False

    def _x_ws_authorized(self):
        u = request.env.user
        if self._x_ws_full_access():
            return True
        try:
            if u in request.env['c2c.workshop.approval.config'].sudo()._get().pm_user_ids:
                return True
        except Exception:
            pass
        try:
            return u.has_group('care2care_workshop.group_workshop_user')
        except Exception:
            return False

    def _x_ws_scope(self, WS):
        """نفس _ws_domain: غير مخوّل=لا شيء، رؤية كاملة=الكل، وإلا ورش المستخدم (مديرها أو منشئها)."""
        if not self._x_ws_authorized():
            return WS.browse()
        if self._x_ws_full_access():
            return WS.search([], order='id desc', limit=100000)
        uid = request.env.uid
        return WS.search(['|', ('project_manager_id.user_id', '=', uid), ('create_uid', '=', uid)],
                         order='id desc', limit=100000)

    def _x_ws_can_see(self, ws):
        if self._x_ws_full_access():
            return True
        if not self._x_ws_authorized():
            return False
        uid = request.env.uid
        return (ws.project_manager_id.user_id.id == uid) or (ws.create_uid.id == uid)

    # ============ طباعة أي سجلّ (التقرير الافتراضي للموديل) ============
    def _x_rec_allowed(self, rec):
        """تحقّق عام: السجلّ ضمن نطاق مدير المشروع إذا طابق **أيّ** حقل نطاق — مشروعه الأصلي
        أو المستفيد (العمل الوارد)، أو قسمه المباشر أو قسم الوجهة (التكليف الوارد)، أو عامله.
        منطق OR لا «أوّل فرع يربح»، وإلا رُفض العمل/التكليف الوارد لأنّ عامله من قسم آخر."""
        try:
            dept_ids = self._pm_projects().mapped('pms_department_id').ids
            proj_ids = self._pm_projects().ids
            if not rec:
                return False
            f = rec._fields

            # للأصول: مطابقة قسم دقيقة (child_of يسرّب أصول الأقسام الفرعية لمشروع قسمُه أب)؛
            # لبقية السجلّات child_of **مع طرح شجر المشاريع الأخرى** (منع تسرّب عقدة الأب).
            _exact_dept = (rec._name == 'account.asset')

            # مشروع أصلي أو مستفيد ضمن مشاريع المدير
            for pf in ('project_id', 'benef_project_id'):
                if pf in f and rec[pf] and rec[pf].id in proj_ids:
                    return True
            # قسم مباشر أو قسم وجهة التكليف ضمن أقسام المدير (منطقة مضيّقة)
            for df in ('department_id', 'new_department'):
                if df in f and self._x_dept_allowed(rec[df], dept_ids, exact=_exact_dept):
                    return True
            # عامل ضمن أقسام المدير (منطقة مضيّقة)
            if 'employee_id' in f and self._x_emp_allowed(rec.employee_id, dept_ids):
                return True
            # الورش: c2c.workshop بنطاق بورتال الورش (مخوّل + مديرها/منشئها، أو رؤية كاملة)
            if rec._name == 'c2c.workshop':
                return self._x_ws_can_see(rec)
            # (مهجور) أوامر الخدمة service.order: جسر عبر عميل المشروع — لم يعد «workshops» يشير إليه
            if rec._name == 'service.order':
                try:
                    client = rec.project_id.contact_id if rec.project_id else False
                    if client and client.id in self._pm_projects().mapped('pms_client_id').ids:
                        return True
                except Exception:
                    pass
            # محاضر استلام السيارات: يراها منشئها (مدير المشروع) حتى بلا مشروع محدَّد
            if rec._name == 'care.vehicle.handover' and rec.pm_id and rec.pm_id.id == request.env.user.id:
                return True
            # موديلات عامّة مشتركة (كتالوج المتجر/خزانات البترول) تُعرض للجميع عمدًا (قراءة فقط)
            if rec._name in _X_READONLY_MODELS:
                return True
            # افتراض آمن: الرفض (كل الوصول عبر sudo، فهذه البوّابة الوحيدة)
            return False
        except Exception:
            return False

    @http.route(['/my/pm/x/print/<string:code>/<int:rid>'], type='http', auth='user', website=False)
    def pm_x_print(self, code=None, rid=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env:
            return request.not_found()
        if self._x_deleg_check(code, 'print'):
            return request.make_response('غير مُصرّح بالطباعة', status=403)
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return request.not_found()
        Rep = request.env['ir.actions.report'].sudo()

        def _find_report(mdl):
            return (Rep.search([('model', '=', mdl), ('report_type', '=', 'qweb-pdf'), ('binding_model_id', '!=', False)], limit=1)
                    or Rep.search([('model', '=', mdl), ('report_type', '=', 'qweb-pdf')], limit=1))

        report = _find_report(model)
        # عند غياب تقرير للسطر → استخدم تقرير سجلّ الأصل (طلب الإيقاف/المباشرة... إلخ)
        if not report:
            for pf in ('request_id', 'parent_id', 'move_id', 'order_id', 'batch_id'):
                if pf in rec._fields and getattr(rec, pf, False):
                    parent = getattr(rec, pf)
                    prep = _find_report(parent._name)
                    if prep:
                        report, rec = prep, parent
                        break
        if not report:
            return request.make_response('لا يوجد تقرير قابل للطباعة لهذا السجل.',
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        try:
            pdf, _ct = report._render_qweb_pdf(report.report_name, [rec.id])
        except Exception as e:
            return request.make_response('تعذّرت الطباعة: %s' % (str(e)),
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename=%s_%s.pdf' % (code, rid))])

    # ============ إجراء سير عمل عام (اعتماد/رفض/تقديم) على أي سجلّ ضمن نطاق PM ============
    # قوائم بيضاء لأسماء الدوال المسموح استدعاؤها لكل إجراء (تُجرَّب بالترتيب، أول موجودة تُنفَّذ)
    _X_ACTION_METHODS = {
        'approve': ['action_approve', 'action_confirm', 'action_validate', 'action_dept_approve',
                    'button_approve', 'action_done', 'action_pm_approve',
                    'action_issue', 'action_start', 'approve'],
                    # أُزيلت action_make_wo/action_to_schedule (خاصّتان بـservice.order): «الورش» صارت
                    # c2c.workshop؛ لا نريد إنشاء/تحريك service.order من البوابة (كان يرسل إيميلات «أمر خدمة جديد»).
                    # أُزيلت action_hr_approve/action_senior_approve/action_manager_approve: كان مدير
                    # المشروع يستدعي اعتماد HR/الإدارة (مثلاً اعتماد الفاتورة→المالية أو استقالة→HR) تصعيدًا للصلاحية
        'reject': ['action_refuse', 'action_reject', 'button_refuse', 'action_cancel',
                   'action_return', 'action_resignation_refuse', 'button_reject_res_approval',
                   'button_reject', 'button_cancel', 'refuse', 'reject'],
        'submit': ['action_submit', 'action_confirm', 'button_submit', 'submit'],
    }

    # موديلات يُمنع فيها إجراء معيّن من بوابة PM (مثلاً: اعتماد النقل حصراً لـHR)
    _X_ACTION_EXCLUDE = {'employee.shift.request': ('approve',),
                         'manpower.requisition': ('approve',)}

    @http.route(['/my/pm/x/action/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_action(self, code=None, rid=None, action=None, reason=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env:
            return {'ok': False, 'error': 'نموذج غير معروف'}
        _g = self._x_deleg_check(code, {'submit': 'submit', 'approve': 'submit', 'send': 'submit',
                                        'reject': 'cancel', 'cancel': 'cancel'}.get((action or '').lower(), 'write'))
        if _g:
            return _g
        if model in _X_READONLY_MODELS:
            return {'ok': False, 'error': 'هذا السجل للعرض فقط'}
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح لهذا السجل'}
        if action in self._X_ACTION_EXCLUDE.get(model, ()):
            return {'ok': False, 'error': 'هذا الإجراء من صلاحية الموارد البشرية'}
        methods = self._X_ACTION_METHODS.get(action or '')
        if not methods:
            return {'ok': False, 'error': 'إجراء غير مدعوم'}
        # سجّل سبب الرفض في المحادثة إن وُجد
        try:
            if reason and action == 'reject' and hasattr(rec, 'message_post'):
                rec.message_post(body='سبب الرفض (من بوابة المشاريع): %s' % reason)
        except Exception:
            pass
        # الأهداف: السجلّ نفسه، ثم الطلب الأب (لنماذج البنود كالإيقاف/المباشرة التي
        # تحمل دوال سير العمل على الطلب لا على البند)
        targets = [rec]
        par = getattr(rec, 'request_id', False)
        if par and par not in targets:
            targets.append(par)
        for tgt in targets:
            for m in methods:
                fn = getattr(tgt, m, None)
                if callable(fn):
                    try:
                        fn()
                        label = {'approve': 'الاعتماد', 'reject': 'الرفض', 'submit': 'الإرسال'}.get(action, 'الإجراء')
                        return {'ok': True, 'msg': label, 'method': m,
                                'state': getattr(rec, 'state', '') or getattr(rec, 'stop_state', '') or ''}
                    except Exception as e:
                        return {'ok': False, 'error': _x_safe_error(e)}
        return {'ok': False, 'error': 'لا توجد دالة سير عمل مناسبة لهذا السجل'}

    # ============ تفاصيل سجلّ حقيقية (بنود + سجلّ زمني + مرفقات + مناقشة) ============
    @http.route(['/my/pm/x/detail/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_detail(self, code=None, rid=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env:
            return {'ok': False, 'error': 'نموذج غير معروف'}
        _g = self._x_deleg_check(code, 'read')
        if _g:
            return _g
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        f = rec._fields

        # --- حقول إضافية مفيدة (تواريخ/مبالغ/مسؤولون) غير المعروضة في القائمة ---
        extra = []
        pref = ['request_date', 'date_from', 'date_to', 'start_date', 'end_date', 'expire_date',
                'amount', 'amount_total', 'total_amount', 'fixed_amount', 'est_cost',
                'reason', 'note', 'notes', 'description', 'project_id', 'department_id',
                'requested_by', 'pm_approved_by', 'hr_approved_by', 'state']
        seen = set()
        for fn in pref:
            if fn in f and fn not in seen:
                try:
                    val = rec[fn]
                    if not val:
                        continue
                    if f[fn].type == 'many2one':
                        val = _dname(val)
                    elif f[fn].type in ('date', 'datetime'):
                        val = str(val)
                    elif f[fn].type == 'selection':
                        val = dict(f[fn]._description_selection(request.env)).get(val, val)
                    extra.append([f[fn].string or fn, str(val)])
                    seen.add(fn)
                except Exception:
                    pass

        # --- تعبئة تكميلية: إن كانت الحقول المفضّلة قليلة، أظهر بقية الحقول غير الفارغة
        #     حتى لا تظهر تفاصيل الطلب فارغة (كثير من الموديلات حقولها خارج قائمة pref) ---
        if len(extra) < 12:
            _skip_pref = ('message_', 'activity_', 'access_', 'website_', 'rating_', 'x_studio_', 'image', '__')
            _skip = {'id', 'display_name', 'name', 'create_uid', 'write_uid', 'create_date', 'write_date',
                     'company_id', 'currency_id', 'color', 'active', 'sequence', 'barcode'}
            for fn, fld in f.items():
                if len(extra) >= 16:
                    break
                if fn in seen or fn in _skip or fn.startswith(_skip_pref):
                    continue
                # #11: لا نكشف حقولًا مالية حسّاسة (أرقام حسابات/دفاتر/قواعد رواتب) لمدير المشروع
                if any(s in fn for s in _X_SENSITIVE):
                    continue
                if fld.type not in ('char', 'text', 'date', 'datetime', 'selection', 'many2one', 'monetary', 'float', 'integer', 'boolean'):
                    continue
                if not getattr(fld, 'store', True):
                    continue
                try:
                    val = rec[fn]
                    if val is False or val is None or val == '' or (fld.type in ('monetary', 'float', 'integer') and not val):
                        continue
                    if fld.type == 'many2one':
                        val = _dname(val)
                    elif fld.type in ('date', 'datetime'):
                        val = str(val)
                    elif fld.type == 'selection':
                        val = dict(fld._description_selection(request.env)).get(val, val)
                    elif fld.type == 'boolean':
                        val = 'نعم'
                    sval = str(val)
                    if not sval or sval in ('—', 'False'):
                        continue
                    extra.append([fld.string or fn, sval])
                    seen.add(fn)
                except Exception:
                    pass

        # --- البنود (أوّل one2many منطقي) ---
        lines = {'cols': [], 'rows': []}
        o2m = None
        # تفضيل one2many الأنسب لبعض الموديلات (مثل سجلّ صيانة المركبة لا سجلّ السائقين)
        _pref = {'fleet.vehicle': 'log_services', 'project.task': 'child_ids'}.get(model)
        if _pref and _pref in f and f[_pref].type == 'one2many':
            o2m = _pref
        for cand in () if o2m else ('line_ids', 'order_line', 'input_line_ids', 'invoice_line_ids',
                     'calc_line_ids', 'item_ids', 'detail_ids', 'worker_line_ids', 'move_line_ids'):
            if cand in f and f[cand].type == 'one2many':
                o2m = cand
                break
        if not o2m:
            _skip_names = ('message_', 'activity_', 'website_', 'rating_', 'access_', 'x_studio_')
            _skip_comodels = ('mail.', 'rating.', 'bus.', 'ir.attachment', 'mail.followers')
            for fn, fo in f.items():
                if fo.type != 'one2many' or fn.startswith(_skip_names):
                    continue
                co = fo.comodel_name or ''
                if co.startswith(_skip_comodels) or co in ('rating.rating', 'mail.message', 'mail.activity'):
                    continue
                o2m = fn
                break
        if o2m:
            try:
                children = rec[o2m]
                if children:
                    cf = children._fields
                    num = [n for n in ('quantity', 'qty', 'product_qty', 'days', 'amount',
                                       'price_unit', 'price_subtotal', 'daily_rate', 'number_of_days')
                           if n in cf][:3]
                    lines['cols'] = ['البند'] + [cf[n].string or n for n in num]

                    def _disp_line(ch):
                        # اسم بند مقروء بدل fallback «model,id» (مثل care.loan.line,31)
                        cff = ch._fields
                        for nf in ('name', 'display_name'):
                            if nf in cff:
                                v = ch[nf]
                                if v and v != '%s,%s' % (ch._name, ch.id):
                                    return v
                        for rf in ('employee_id', 'product_id', 'worker_id', 'partner_id',
                                   'asset_id', 'item_id', 'vehicle_id', 'type_id'):
                            if rf in cff and ch[rf]:
                                return _disp(ch[rf])
                        for fn2, fo2 in cff.items():
                            if fo2.type == 'char' and not fn2.startswith(('message_', 'activity_')) and ch[fn2]:
                                return ch[fn2]
                        return '#%s' % ch.id

                    for ch in children:
                        row = [_disp_line(ch)]
                        for n in num:
                            v = ch[n]
                            row.append(('{:,.3f}'.format(v).rstrip('0').rstrip('.')) if isinstance(v, float) else str(v or ''))
                        lines['rows'].append(row)
            except Exception:
                pass

        # --- المرفقات ---
        files = []
        try:
            atts = request.env['ir.attachment'].sudo().search(
                [('res_model', '=', model), ('res_id', '=', rec.id)], limit=20, order='id desc')
            for a in atts:
                kb = int((a.file_size or 0) / 1024)
                files.append([a.name or '—', ('%d KB' % kb) if kb else (a.mimetype or ''), a.id])
        except Exception:
            pass

        # --- المناقشة + السجلّ الزمني (من mail.message) ---
        chatter, timeline = [], []
        try:
            msgs = rec.message_ids.sorted(lambda m: m.id, reverse=True)[:14] if 'message_ids' in f else []
            from markupsafe import Markup
            import re as _re
            for m in msgs:
                body = _re.sub('<[^>]+>', ' ', str(m.body or '')).strip()
                body = ' '.join(body.split())
                auth = m.author_id.name or (m.create_uid.name if m.create_uid else '') or 'النظام'
                dt = str(m.date or '')[:16]
                if m.message_type == 'comment' and body:
                    chatter.append([auth, dt, body])
                if m.tracking_value_ids or (m.subtype_id and m.subtype_id.name) or body:
                    label = body or (m.subtype_id.name if m.subtype_id else 'تحديث')
                    timeline.append(['clock', label, auth, dt])
        except Exception:
            pass

        # --- سجلّات ذات صلة (نفس العامل/المشروع في نفس الموديل) ---
        related = []
        try:
            dom, link = None, None
            if 'employee_id' in f and rec.employee_id:
                dom = [('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id)]
            elif 'project_id' in f and rec.project_id:
                dom = [('project_id', '=', rec.project_id.id), ('id', '!=', rec.id)]
            if dom:
                sib = request.env[model].sudo().search(dom, limit=6, order='id desc')
                for s in sib:
                    st = ''
                    if 'state' in s._fields and s.state:
                        try:
                            st = dict(s._fields['state']._description_selection(request.env)).get(s.state, s.state)
                        except Exception:
                            st = s.state
                    dt = ''
                    for df in ('date', 'request_date', 'create_date'):
                        if df in s._fields and s[df]:
                            dt = str(s[df])[:10]
                            break
                    related.append([s.display_name or '—', (st or dt or '')])
        except Exception:
            pass

        # إجراءات سير العمل المتاحة فعلاً على هذا السجلّ (لإظهار الأزرار المدعومة فقط)
        _excl = self._X_ACTION_EXCLUDE.get(model, ())
        _act_tgts = [rec]
        _par = getattr(rec, 'request_id', False)
        if _par and _par not in _act_tgts:
            _act_tgts.append(_par)
        _has = lambda key: any(callable(getattr(t, m, None)) for t in _act_tgts for m in self._X_ACTION_METHODS.get(key, []))
        # لا نُظهر زرّ «اعتماد» لسجلّ بلغ حالة نهائية/معتمدة بالفعل (زرّ ميت يرمي خطأً عند الضغط).
        # نستعمل نفس تعريف _X_DONE_STATES المستخدَم في is_open/مركز الطلبات حفاظًا على الاتّساق.
        _st = ''
        for _t in _act_tgts:
            if 'state' in _t._fields and _t.state:
                _st = str(_t.state)
                break
        _finalized = _st in _X_DONE_STATES
        # #15: السجلّ المنتهي/المعتمد يُظهر الحالة فقط — لا أزرار إرسال/اعتماد/رفض
        can_approve = (not _finalized) and ('approve' not in _excl) and _has('approve')
        can_reject = (not _finalized) and ('reject' not in _excl) and _has('reject')
        can_submit = (not _finalized) and _has('submit') and self._x_editable(rec)
        can_edit = self._x_editable(rec) and (CODE_MODEL.get(code) == model) and (code in self.pm_x_create_models())
        # الإلغاء/السحب أوسع من التعديل: يشمل السجلّات التي لها دالة إلغاء صريحة وما زالت مفتوحة
        # (كالشكوى التأديبية تُسحب حتى بعد اعتماد المدير وقبل التطبيق)
        can_cancel = self._x_cancellable(rec)
        # هل يوجد تقرير قابل للطباعة (للموديل أو لسجل الأصل)؟
        Rep = request.env['ir.actions.report'].sudo()
        has_report = bool(Rep.search_count([('model', '=', model), ('report_type', '=', 'qweb-pdf')]))
        if not has_report:
            for pf in ('request_id', 'parent_id', 'move_id', 'order_id', 'batch_id'):
                if pf in f and rec[pf]:
                    has_report = bool(Rep.search_count([('model', '=', rec[pf]._name), ('report_type', '=', 'qweb-pdf')]))
                    if has_report:
                        break

        task_info = None
        if model == 'project.task':
            task_info = {
                'id': rec.id,
                'forward_state': getattr(rec, 'forward_state', 'none') or 'none',
                'forward_to': rec.forward_to_id.name if getattr(rec, 'forward_to_id', False) else '',
                'forward_reason': getattr(rec, 'forward_reason', '') or '',
                'is_recipient': bool(getattr(rec, 'is_forward_recipient', False)),
            }
        contract_info = None
        if model == 'care.experience':
            def _sl(rr, st):
                try:
                    return dict(rr._fields['state']._description_selection(request.env)).get(st, st or '—')
                except Exception:
                    return st or '—'
            _gcls = {'active': 'ok', 'expiring': 'warn', 'expired': 'crit', 'released': 'mut', 'returned': 'mut', 'draft': 'mut'}
            _rcls = {'signed': 'ok', 'approved': 'info', 'guarantee': 'info', 'cancelled': 'crit', 'draft': 'mut'}
            gtypes = {}
            try:
                if getattr(rec, 'guarantee_ids', False):
                    gtypes = dict(rec.guarantee_ids._fields['guarantee_type']._description_selection(request.env))
            except Exception:
                gtypes = {}
            guarantees = [{
                'ref': g.name or g.guarantee_number or '—', 'number': g.guarantee_number or '',
                'bank': g.bank_name or '—', 'type': gtypes.get(getattr(g, 'guarantee_type', ''), getattr(g, 'guarantee_type', '') or ''),
                'amount': g.amount or 0, 'issue': str(g.issue_date or '')[:10], 'expiry': str(g.expiry_date or '')[:10],
                'days': getattr(g, 'days_to_expiry', 0) or 0, 'label': _sl(g, g.state), 'cls': _gcls.get(g.state, 'mut'),
            } for g in (rec.guarantee_ids if getattr(rec, 'guarantee_ids', False) else [])]
            renewals = [{
                'ref': r.name or '—', 'title': getattr(r, 'title', '') or (r.name or '—'),
                'label': _sl(r, r.state), 'cls': _rcls.get(r.state, 'warn'),
                'request_date': str(getattr(r, 'request_date', '') or '')[:10],
                'deadline': str(getattr(r, 'respond_deadline', '') or '')[:10],
            } for r in (rec.renewal_ids if getattr(rec, 'renewal_ids', False) else [])]
            contract_info = {
                'guarantees': guarantees, 'renewals': renewals,
                'currency': (rec.currency_id.name if getattr(rec, 'currency_id', False) else 'KWD'),
                'insurance': getattr(rec, 'insurance_amount', 0) or 0,
            }
        vehicle_info = None
        if model == 'fleet.vehicle':
            svcs = []
            try:
                Svc = request.env['fleet.vehicle.log.services'].sudo()
                tsel = dict(Svc._fields['type']._description_selection(request.env)) if 'type' in Svc._fields else {}
                ssel = dict(Svc._fields['state']._description_selection(request.env)) if 'state' in Svc._fields else {}
                for s in Svc.search([('vehicle_id', '=', rec.id)], order='id desc', limit=12):
                    svcs.append({'id': s.id, 'type': tsel.get(getattr(s, 'type', ''), getattr(s, 'type', '') or '—'),
                                 'date': str(getattr(s, 'date', '') or '')[:10],
                                 'amount': getattr(s, 'amount', 0) or getattr(s, 'total_cost', 0) or 0,
                                 'desc': getattr(s, 'description', '') or '—',
                                 'state': ssel.get(getattr(s, 'state', ''), getattr(s, 'state', '') or '')})
            except Exception:
                svcs = []
            _ins = _reg = _nextsvc = ''
            try:
                if 'log_contracts' in rec._fields:
                    cons = rec.log_contracts.filtered(lambda c: getattr(c, 'expiration_date', False))
                    if cons:
                        _ins = str(min(cons.mapped('expiration_date')))
            except Exception:
                pass
            try:
                if 'log_services' in rec._fields:
                    fut = [s.next_service_date for s in rec.log_services if getattr(s, 'next_service_date', False)]
                    if fut:
                        _nextsvc = str(min(fut))
            except Exception:
                pass
            vehicle_info = {'id': rec.id, 'name': rec.name or (rec.license_plate or '—'),
                            'plate': getattr(rec, 'license_plate', '') or '', 'services': svcs,
                            'driver': (rec.driver_id.name if getattr(rec, 'driver_id', False) else ''),
                            'driver_id': (rec.driver_id.id if getattr(rec, 'driver_id', False) else 0),
                            'odometer': round(getattr(rec, 'odometer', 0) or 0, 1),
                            'model': (rec.model_id.display_name if getattr(rec, 'model_id', False) else ''),
                            'fuel': (dict(rec._fields['fuel_type']._description_selection(request.env)).get(rec.fuel_type, rec.fuel_type) if getattr(rec, 'fuel_type', False) else ''),
                            'insurance_expiry': _ins, 'next_service': _nextsvc}
        petrol_info = None
        if model == 'petrol.tank':
            petrol_info = {'id': rec.id, 'name': rec.name or '—',
                           'balance': round(getattr(rec, 'balance', 0) or 0, 1),
                           'capacity': round(getattr(rec, 'capacity', 0) or 0, 1)}
        fuelcard_info = None
        if model == 'care.fuel.card':
            tops = [{'date': str(getattr(t, 'date', '') or ''), 'amount': getattr(t, 'amount', 0) or 0,
                     'ref': getattr(t, 'reference', '') or ''} for t in rec.topup_ids[:20]]
            fuelcard_info = {'id': rec.id, 'name': rec.name or '—', 'provider': rec.provider or '',
                             'balance': round(getattr(rec, 'balance', 0) or 0, 3),
                             'topup_total': round(getattr(rec, 'topup_total', 0) or 0, 3),
                             'consumed': round(getattr(rec, 'consumed', 0) or 0, 3),
                             'state': rec.state, 'auto': bool(getattr(rec, 'auto_recharge', False)),
                             'recharge_amount': getattr(rec, 'recharge_amount', 0) or 0,
                             'recharge_day': getattr(rec, 'recharge_day', 1) or 1,
                             'topups': tops}
        supply_info = None
        if model == 'care.pms.supply':
            lines_s = []
            for l in (rec.line_ids if getattr(rec, 'line_ids', False) else []):
                _rcv = getattr(l, 'received_qty', 0) or 0
                _rem = getattr(l, 'remaining_qty', None)
                if _rem is None:
                    _rem = max((l.qty or 0) - _rcv, 0)
                lines_s.append({'lid': l.id, 'name': l.name or '—', 'qty': l.qty or 0,
                                'received': _rcv, 'remaining': round(_rem, 3),
                                'uom': getattr(l, 'uom_name', '') or '',
                                'line_state': getattr(l, 'line_state', '') or ''})
            # سندات الاستلام السابقة (الدفعات) — تُعرض في التفاصيل مع زر طباعة لكلٍّ
            receipts = []
            for g in getattr(rec, 'receipt_ids', []):
                receipts.append({'id': g.id, 'name': g.name or '—',
                                 'date': str(g.date or ''), 'receiver': g.receiver_name or '',
                                 'qty': round(g.qty_total or 0, 3), 'state': g.state,
                                 'delivery_ref': g.delivery_ref or ''})
            supply_info = {'id': rec.id, 'state': rec.state, 'receiver': getattr(rec, 'receiver_name', '') or '',
                           'lines': lines_s, 'receipts': receipts}
        petty_info = None
        if model == 'care.pms.petty.cash':
            cat_tot = {}
            exps = []
            for e in rec.expense_ids:
                cn = (e.category_id.name if getattr(e, 'category_id', False) else '—')
                cat_tot[cn] = cat_tot.get(cn, 0) + (e.amount or 0)
                exps.append({'id': e.id, 'name': e.name or '—', 'amount': e.amount or 0,
                             'date': str(e.date or ''), 'category': (e.category_id.name if getattr(e, 'category_id', False) else ''),
                             'invoice': getattr(e, 'invoice_number', '') or '',
                             'partner': (e.partner_id.name if getattr(e, 'partner_id', False) else ''),
                             'note': getattr(e, 'note', '') or '', 'has_file': bool(getattr(e, 'attachment', False))})
            setls = [{'id': s.id, 'name': s.name or '—', 'state': s.state,
                      'date': str(getattr(s, 'date', '') or ''), 'total': getattr(s, 'amount_total', 0) or 0,
                      'count': len(s.expense_ids)} for s in getattr(rec, 'settlement_ids', [])]
            try:
                bt = dict(rec._fields['beneficiary_type']._description_selection(request.env)).get(getattr(rec, 'beneficiary_type', False), '')
            except Exception:
                bt = ''
            petty_info = {
                'id': rec.id, 'state': rec.state,
                'amount': getattr(rec, 'amount', 0) or 0,
                'spent': getattr(rec, 'spent', 0) or 0,
                'remaining': getattr(rec, 'remaining', 0) or 0,
                'currency': (rec.currency_id.name if getattr(rec, 'currency_id', False) else 'KWD'),
                'custodian': (rec.manager_id.name if getattr(rec, 'manager_id', False) else ''),
                'reason': getattr(rec, 'reason', '') or '',
                'request_date': str(getattr(rec, 'request_date', '') or ''),
                'disbursed_date': str(getattr(rec, 'disbursed_date', '') or ''),
                'return_date': str(getattr(rec, 'return_date', '') or ''),
                'returned_amount': getattr(rec, 'returned_amount', 0) or 0,
                'beneficiary': bt,
                'expenses': exps,
                'settlements': setls,
                'by_category': [[k, round(v, 3)] for k, v in cat_tot.items()],
            }
        # --- بنود طلب المتجر: عرض غنيّ (صورة المنتج + الكمية + السعر + الإجمالي) ---
        store_lines = []
        store_total = 0.0
        if model == 'care.pms.store.order':
            try:
                for l in rec.line_ids:
                    pr = l.product_id
                    qty = l.qty if 'qty' in l._fields else 0.0
                    price = l.price_unit if 'price_unit' in l._fields else 0.0
                    sub = l.subtotal if 'subtotal' in l._fields else ((qty or 0.0) * (price or 0.0))
                    store_total += sub or 0.0
                    store_lines.append({
                        'pid': pr.id if pr else 0,
                        'name': (pr.display_name if pr else (getattr(l, 'name', '') or '—')),
                        'code': (pr.default_code or '') if pr else '',
                        'qty': qty or 0.0,
                        'uom': (getattr(l, 'uom_name', '') or (pr.uom_id.name if (pr and pr.uom_id) else '')) or '',
                        'size': getattr(l, 'size_label', '') or '',
                        'price': round(price or 0.0, 3),
                        'subtotal': round(sub or 0.0, 3),
                    })
            except Exception:
                store_lines = []
        # العمل الإضافي: إجراءات الإيقاف/الإنهاء (طلب يُعتمد من الموارد البشرية) + حالة المدة
        xwork_info = None
        if model == 'care.extra.work':
            _xs = str(rec.state or '')
            xwork_info = {
                'state': _xs,
                'duration_type': rec.duration_type or '',
                'date_from': str(rec.date_from or ''),
                'date_to': str(rec.date_to or ''),
                'can_req_pause': _xs == 'active',
                'can_req_end': _xs in ('active', 'paused'),
                'stop_type': rec.stop_request_type or '',
                'stop_reason': rec.stop_reason or '',
            }
        # طلب مستند: بيانات فورم الرفع (أمام/خلف/PDF + رقم/تواريخ) ثم الإرسال للاعتماد
        docreq_info = None
        if model == 'care.document.request':
            _ds = str(rec.state or '')
            docreq_info = {
                'state': _ds, 'locked': bool(rec.locked),
                'need_front': bool(rec.need_front), 'need_back': bool(rec.need_back),
                'type': rec.type_id.name or '',
                'number': rec.new_number or '',
                'issue_date': str(rec.new_issue_date or ''),
                'expiry_date': str(rec.new_expiry_date or ''),
                'has_front': bool(rec.up_front), 'has_back': bool(rec.up_back),
                'has_pdf': bool(rec.up_pdf),
                'can_upload': (not rec.locked) and _ds in ('draft', 'pending', 'viewed'),
            }
        return {'ok': True, 'fields': extra, 'lines': lines, 'files': files,
                'store_lines': store_lines, 'store_total': round(store_total, 3),
                'chatter': chatter, 'timeline': timeline[:12], 'related': related,
                'can_approve': can_approve, 'can_reject': can_reject, 'can_print': has_report,
                'can_submit': can_submit, 'can_edit': can_edit, 'can_cancel': can_cancel,
                'task': task_info, 'petty': petty_info, 'contract': contract_info,
                'supply': supply_info, 'petrol': petrol_info, 'vehicle': vehicle_info,
                'fuelcard': fuelcard_info, 'xwork': xwork_info, 'docreq': docreq_info}

    @http.route(['/my/pm/x/docreq/upload'], type='json', auth='user', website=False)
    def pm_x_docreq_upload(self, rid=None, number=None, issue_date=None, expiry_date=None,
                           front=None, back=None, pdf=None, submit=None, **kw):
        env = request.env
        rec = env['care.document.request'].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if rec.locked:
            return {'ok': False, 'error': 'الطلب مقفل (مرفوع/معتمد) — لا يمكن التعديل.'}

        def _b64(x):
            if not x:
                return False
            if isinstance(x, str) and x.startswith('data:') and ',' in x:
                return x.split(',', 1)[1] or False
            return x or False
        vals = {}
        f, b, pf = _b64(front), _b64(back), _b64(pdf)
        if f:
            vals['up_front'] = f
            vals['up_front_filename'] = 'front.jpg'
        if b:
            vals['up_back'] = b
            vals['up_back_filename'] = 'back.jpg'
        if pf:
            vals['up_pdf'] = pf
            vals['up_pdf_filename'] = 'document.pdf'
        if number is not None:
            vals['new_number'] = number
        if issue_date:
            vals['new_issue_date'] = issue_date
        if expiry_date:
            vals['new_expiry_date'] = expiry_date
        if vals:
            rec.write(vals)
        if submit:
            try:
                rec.action_upload()
                return {'ok': True, 'submitted': True,
                        'msg': 'تم رفع المستند «%s» وإرساله لاعتماد الموارد البشرية.' % (rec.type_id.name or '')}
            except Exception as e:
                return {'ok': False, 'error': _x_safe_error(e)}
        return {'ok': True, 'submitted': False, 'msg': 'تم حفظ البيانات (لم تُرسَل بعد).'}

    @http.route(['/my/pm/x/requests/cards'], type='http', auth='user', website=False)
    def pm_x_requests_cards(self, ids=None, **kw):
        """يطبع كروت «تحديث مستند» (2×6/صفحة) لعدّة طلبات محدَّدة — ضمن نطاق المدير فقط."""
        env = request.env
        try:
            want = [int(x) for x in (ids or '').split(',') if x.strip()]
        except Exception:
            want = []
        if not want:
            return request.make_response('حدِّد طلبات أولًا',
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        recs = env['care.document.request'].sudo().browse(want).exists()
        allowed = recs.filtered(lambda r: self._x_rec_allowed(r))
        if not allowed:
            return request.make_response('لا توجد طلبات مصرّح بها',
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        rep = env['ir.actions.report'].sudo().search(
            [('report_name', '=', 'care_worker_docs.report_request_cards')], limit=1)
        if not rep:
            return request.make_response('تقرير الكروت غير متاح',
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        try:
            pdf, _ct = rep._render_qweb_pdf(rep.report_name, allowed.ids)
        except Exception as e:
            return request.make_response('تعذّرت الطباعة: %s' % str(e),
                                         headers=[('Content-Type', 'text/plain; charset=utf-8')])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="document_cards.pdf"')])

    @http.route(['/my/pm/x/extrawork/<int:rid>/stop'], type='json', auth='user', website=False)
    def pm_x_extrawork_stop(self, rid=None, kind=None, reason=None, **kw):
        """طلب إيقاف/إنهاء تكليف العمل الإضافي من بوابة المدير — يُعتمد من الموارد البشرية."""
        env = request.env
        if 'care.extra.work' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        rec = env['care.extra.work'].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('extrawork', 'cancel')
        if _g:
            return _g
        try:
            rec._open_stop_request('end' if kind == 'end' else 'pause', reason=(reason or '').strip())
            return {'ok': True, 'msg': 'تم إرسال الطلب لاعتماد الموارد البشرية'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/message/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_message(self, code=None, rid=None, body=None, **kw):
        """نشر تعليق على سجلّ من بوابة المشاريع (المناقشة التفاعلية)."""
        model = CODE_MODEL.get(code)
        if not model or model not in request.env:
            return {'ok': False, 'error': 'نموذج غير معروف'}
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check(code, 'write')
        if _g:
            return _g
        body = (body or '').strip()
        if not body:
            return {'ok': False, 'error': 'الرسالة فارغة'}
        if not hasattr(rec, 'message_post'):
            return {'ok': False, 'error': 'لا تدعم هذه السجلات المناقشة'}
        try:
            rec.message_post(body=body, author_id=request.env.user.partner_id.id,
                             message_type='comment')
            return {'ok': True, 'author': request.env.user.name,
                    'date': fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ إنشاء سجلّ جديد: مواصفات الحقول + الإنشاء (نطاق PM) ============
    _X_FORM_TYPES = ('char', 'text', 'float', 'integer', 'monetary', 'date', 'datetime', 'boolean', 'selection', 'many2one')
    _X_FORM_SKIP = {
        'id', 'display_name', 'create_uid', 'write_uid', 'create_date', 'write_date', '__last_update',
        'state', 'stop_state', 'company_id', 'currency_id', 'color', 'active', 'sequence', 'name',
        # payslip_state (حالة إيصال الدفع): تخصّ الموارد البشرية — تُخفى عن مدير المشروع؛ لها default
        # ('normal') فلا يفشل الإنشاء بدونها، ويحدّدها HR من الواجهة الخلفية.
        'payslip_state',
        # request_id: الأصل يُنشأ تلقائيًّا في _X_CREATE_PARENT (إيقاف/عودة) — لا يُعرض في النموذج.
        'request_id',
    }
    _X_FORM_SKIP_PREFIX = ('message_', 'activity_', 'access_', 'website_', 'rating_', 'x_studio_')

    def pm_x_create_models(self):
        """الأقسام المسموح إنشاؤها من البوابة (طلبات يبدأها مدير المشروع)."""
        # ملاحظة: «items» (care.cafm.request) يتطلّب facility_id (مفهوم عميل CAFM) + بنود أصناف،
        # فلا يُنشأ من بوابة مدير المشروع (يبقى للعرض فقط). «permits» له شاشة إنشاء مجمّعة مخصّصة.
        return {'penalties', 'bonuses', 'overtime', 'extrawork', 'manpower',
                'requests', 'permits', 'allowances', 'petty', 'tasks',
                'leaves', 'passports', 'loans', 'fuel', 'additional',
                'suspension', 'resume', 'resignations', 'eos',
                'permission', 'absence', 'leavereturn', 'joining', 'clearance',
                'salarycert', 'expcert', 'perfeval', 'exitint', 'govtx',
                'bankcard', 'expense', 'transport', 'discipline'}
        # ملاحظة: «uniform» (uniform.delivery) يتطلّب توقيعًا (signature required) غير متاح في
        # النموذج العام ⇒ الإنشاء يفشل دائمًا، فأُزيل من الإنشاء حتى تُضاف لوحة توقيع.

    # نماذج إنشاء مخصّصة: قائمة حقول منتقاة بدل fields_get الكامل (لموديلات معقّدة)
    # #1 إظهار/إخفاء حقل حسب قيمة حقل آخر (cascading): {model:{field:{ctrl_field:[allowed_values]}}}
    _X_FIELD_SHOW = {
        'care.fuel.entry': {'card_id': {'method': ['card']}, 'petty_cash_id': {'method': ['cash']}},
        'care.bank.card.request': {'reason_other': {'reason': ['other']}},
        'care.salary.certificate': {'purpose_other': {'purpose': ['other']}},
        'care.experience.certificate': {'purpose_other': {'purpose': ['other']}},
        'care.passport.request': {'reason_other': {'reason': ['other']}},
        'employee.shift.request': {
            'additional_project_id': {'shift_type': ['additional']},
            'additional_start_date': {'shift_type': ['additional']},
            'additional_end_date': {'shift_type': ['additional']},
            'additional_days': {'shift_type': ['additional']},
            'additional_daily_rate': {'shift_type': ['additional']},
            'additional_wage': {'shift_type': ['additional']},
            'additional_allowance': {'shift_type': ['additional']},
        },
        'care.extra.work': {
            'est_hours': {'comp_type': ['hourly', 'hours_fixed']},
            'hourly_rate': {'comp_type': ['hourly']},
            'multiplier': {'comp_type': ['hourly']},
            'fixed_amount': {'comp_type': ['fixed', 'hours_fixed']},
            'fixed_period': {'comp_type': ['fixed', 'hours_fixed']},
            # «تاريخ الانتهاء» يظهر فقط حين تكون المدة محددة
            'date_to': {'duration_type': ['fixed']},
        },
    }
    _X_FORM_FIELDS = {
        'hr.leave': ['employee_id', 'holiday_status_id', 'request_date_from', 'request_date_to'],
        'care.passport.request': ['employee_id', 'reason', 'request_date', 'expected_return', 'recipient_name', 'note'],
        'care.fuel.entry': ['date', 'method', 'amount', 'card_id', 'petty_cash_id', 'vehicle_id', 'driver_id', 'liters', 'station', 'odometer', 'note'],
        'employee.shift.request': ['employee_id', 'new_department', 'shift_type', 'transfer_date', 'working_hours',
                                   'additional_project_id', 'additional_start_date', 'additional_end_date',
                                   'additional_days', 'additional_daily_rate', 'additional_wage', 'additional_allowance'],
        'care.loan': ['employee_id', 'loan_type', 'date', 'amount', 'installments', 'start_date', 'reason'],
        'care.suspension.request.line': ['employee_id', 'effective_date', 'line_reason', 'note'],
        'care.resume.request.line': ['employee_id', 'return_date', 'return_department_id'],
        'project.task': ['name', 'date_deadline', 'stage_id', 'description'],
        'care.document.request': ['employee_id', 'type_id', 'need_front', 'need_back', 'deadline', 'priority', 'note'],
        'hr.employee.resignation': ['employee_id', 'request_date', 'leave_date', 'resignation_type', 'reason'],
        'care.eos': ['employee_id', 'last_working_day', 'reason'],
        'care.complaint': ['employee_id', 'category_id', 'category_other', 'severity', 'incident_date', 'witnesses', 'description'],
        'permission.request': ['employee_id', 'type', 'permission_from', 'permission_hours', 'reason'],
        'hr.action.absence': ['employee_id', 'case_type', 'absence_date', 'absence_reason', 'absence_hours'],
        'hr.action.leave.return': ['employee_id', 'start_work_date', 'return_to_country_date', 'notes'],
        'hr.action.joining': ['employee_id', 'join_date', 'salary_date'],
        'hr.action.clearance': ['employee_id'],
        'care.salary.certificate': ['employee_id', 'request_source', 'request_date', 'purpose', 'purpose_other', 'include_salary', 'addressed_to', 'bank_name'],
        'care.experience.certificate': ['employee_id', 'request_source', 'request_date', 'purpose', 'purpose_other', 'last_working_day'],
        'care.performance.log': ['employee_id', 'date', 'name'],
        'exit.interview': ['employee_id', 'date', 'supervisor_id', 'resignation_date', 'last_working_day', 'contact_number'],
        'care.gov.transaction': ['transaction_type', 'employee_id', 'submit_date', 'deadline', 'note'],
        'uniform.delivery': ['name', 'employee_id', 'uniform_type_id', 'date'],
        'care.bank.card.request': ['employee_id', 'request_type', 'reason', 'reason_other', 'request_date', 'card_bank', 'account_number', 'note'],
        'care.expense.claim': ['employee_id', 'expense_type', 'expense_date', 'amount', 'note'],
        'care.extra.work': ['employee_id', 'comp_type', 'duration_type', 'date_from', 'date_to', 'est_hours', 'hourly_rate', 'multiplier', 'fixed_amount', 'fixed_period', 'note'],
        'care.transport.request': ['transport_kind', 'trip_scope', 'origin_location_id', 'destination_location_id',
                                   'origin_text', 'destination_text', 'needed_date', 'needed_time', 'passenger_count', 'purpose'],
    }
    # حقول تُفرَض مطلوبة في النموذج وإن لم تكن required في fields_get (قيد موديل مشروط)
    # date_from (تاريخ البدء) مطلوب دائمًا؛ date_to مطلوب فقط حين «المدة محددة» (show_when يتخطّى المطلوب للمخفيّ)
    _X_FORM_REQUIRED = {
        'care.extra.work': ('date_from', 'date_to'),
    }
    # تسميات مخصّصة للحقول في نموذج البوابة
    _X_FORM_LABEL = {
        'care.extra.work': {'date_from': 'تاريخ بدء الإضافي', 'date_to': 'تاريخ الانتهاء', 'duration_type': 'نوع المدة'},
        'care.suspension.request.line': {'employee_id': 'العامل', 'effective_date': 'تاريخ الإيقاف',
                                         'line_reason': 'سبب الإيقاف', 'note': 'تفاصيل / ملاحظات'},
    }
    # إنشاء مخصّص: كود → (موديل الأصل، حقول السطر) — يُنشئ طلب أصل بسطر واحد للعامل
    _X_CREATE_PARENT = {
        'suspension': ('care.suspension.request', ('employee_id', 'effective_date', 'line_reason', 'note')),
        'resume': ('care.resume.request', ('employee_id', 'return_date', 'return_department_id')),
    }
    # قيم تُحقن تلقائياً عند الإنشاء (لا يراها المستخدم)
    _X_CREATE_INJECT = {
        'hr.leave': {'holiday_type': 'employee'},
        # الشكوى التأديبية: مدير المشروع يُقرّ بصحّة البيانات عند الرفع (حماية من الكيدية)
        'care.complaint': {'complainant_ack': True},
    }
    # أكواد تُقدَّم تلقائياً بعد الإنشاء (action_submit) — يُشعر المسؤول فورًا كما في التطبيق
    _X_CREATE_AUTOSUBMIT = {'transport', 'discipline'}

    def _x_editable(self, rec):
        """هل يُسمح بتعديل السجلّ من البوابة؟ مسوّدة/قبل الاعتماد؛ مع مراعاة حالات خاصّة."""
        st = getattr(rec, 'state', 'draft')
        if rec._name == 'project.task':
            return st not in ('1_done', '1_canceled')
        if rec._name == 'hr.leave':
            return st in ('draft', 'confirm', False, None)
        return st in ('draft', 'submitted', False, None)

    def _x_cancellable(self, rec):
        """هل يُسمح بإلغاء/سحب السجلّ من البوابة؟ مسوّدة/قبل الاعتماد، أو أي سجلّ
        له دالة إلغاء صريحة (كالشكوى التأديبية: تُسحب حتى قبل التطبيق) وما زال مفتوحًا.
        النموذج نفسه يحرس حالاته المنتهية وصلاحية المُلغِي، فالتوسيع هنا آمن."""
        if self._x_editable(rec):
            return True
        if callable(getattr(rec, 'action_cancel', None)):
            _, _, _, is_open = self._x_state_info(rec)
            return bool(is_open)
        return False

    # أكواد «طلب واحد مفتوح في المرّة» (سياسة: لا طلب جديد وثمّة غير منجَز) —
    # للطلبات الفردية ذاتيّة البدء فقط (لا الجزاءات/المكافآت/البدلات التي تتعدّد)
    _X_SINGLE_OPEN = {'leaves', 'permission', 'loans', 'resignations', 'eos', 'bankcard',
                      'salarycert', 'expcert', 'passports', 'leavereturn', 'joining', 'clearance'}

    def _x_state_info(self, rec):
        """(state, label, cls, is_open) لسجلّ طلب."""
        st = getattr(rec, 'state', None)
        if st is None:
            st = getattr(rec, 'stop_state', None)
        label = st or '—'
        try:
            if 'state' in rec._fields and rec._fields['state'].type == 'selection':
                label = dict(rec._fields['state']._description_selection(request.env)).get(st, st or '—')
        except Exception:
            pass
        is_open = bool(st) and (str(st) not in _X_DONE_STATES)
        if (st in _X_DRAFT_STATES):
            cls = 'mut'
        elif str(st) in ('refuse', 'refused', 'reject', 'rejected', 'cancel', 'cancelled', 'canceled'):
            cls = 'crit'
        elif is_open:
            cls = 'warn'
        else:
            cls = 'ok'
        return st, label, cls, is_open

    def _x_emp_field(self, M):
        for f in ('employee_id', 'emp_id', 'worker_id'):
            if f in M._fields:
                return f
        return None

    def _x_open_blocker(self, model, eid):
        """أوّل طلب مفتوح (غير منجَز) لنفس العامل من نفس النوع، أو False."""
        M = request.env[model].sudo()
        ef = self._x_emp_field(M)
        if not ef or not eid:
            return False
        try:
            recs = M.search([(ef, '=', int(eid))], order='id desc', limit=100000)
        except Exception:
            return False
        for r in recs:
            _, _, _, is_open = self._x_state_info(r)
            if is_open:
                return r
        return False

    @http.route(['/my/pm/x/wreq/<string:code>/<int:eid>'], type='json', auth='user', website=False)
    def pm_x_worker_reqs(self, code=None, eid=None, **kw):
        """مركز طلبات العامل لنوع واحد: السجلّات الحالية + حالاتها + هل يُسمح بطلب جديد."""
        model = CODE_MODEL.get(code)
        if not model or model not in request.env or code not in self.pm_x_create_models():
            return {'ok': False, 'error': 'غير متاح لهذا النوع'}
        projs = self._pm_projects()
        dept_ids = projs.mapped('pms_department_id').ids
        emp = request.env['hr.employee'].sudo().browse(int(eid or 0)).exists()
        if not self._x_emp_allowed(emp, dept_ids):
            return {'ok': False, 'error': 'العامل خارج نطاقك'}
        M = request.env[model].sudo()
        ef = self._x_emp_field(M)
        recs = M.search([(ef, '=', emp.id)], order='id desc', limit=100000) if ef else M.browse()
        Rep = request.env['ir.actions.report'].sudo()
        has_report = bool(Rep.search_count([('model', '=', model), ('report_type', '=', 'qweb-pdf')]))
        rows, open_cnt, blocker = [], 0, ''
        for r in recs:
            st, label, cls, is_open = self._x_state_info(r)
            if is_open:
                open_cnt += 1
                blocker = blocker or (r.display_name or ('#%s' % r.id))
            editable = self._x_editable(r)
            # تاريخ تمثيلي
            dt = ''
            for df in ('request_date', 'date', 'create_date', 'date_from', 'effective_date', 'start_date'):
                if df in r._fields and r[df]:
                    dt = str(r[df])[:10]
                    break
            # هل يمكن الإرسال للاعتماد؟ (دالة submit متاحة وما زال مسوّدة)
            tgts = [r] + ([r.request_id] if getattr(r, 'request_id', False) else [])
            can_submit = editable and any(callable(getattr(t, m, None)) for t in tgts for m in self._X_ACTION_METHODS.get('submit', []))
            rows.append({
                'id': r.id, 'ref': r.display_name or ('#%s' % r.id), 'date': dt,
                'state': st or '', 'label': label, 'cls': cls, 'open': is_open,
                'can_cancel': bool(editable), 'can_submit': bool(can_submit), 'can_print': has_report,
            })
        single = code in self._X_SINGLE_OPEN
        can_create = (open_cnt == 0) if single else True
        return {'ok': True, 'code': code, 'worker': emp.name,
                'records': rows, 'can_create': can_create, 'single': single,
                'blocking': blocker if not can_create else ''}

    @http.route(['/my/pm/x/cancel/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_cancel(self, code=None, rid=None, **kw):
        """إلغاء طلب في حالة مسوّدة (action_cancel، وإلا حذف المسوّدة)."""
        model = CODE_MODEL.get(code)
        # الإلغاء مقصور على أنواع الطلبات القابلة للإنشاء من البوابة فقط —
        # يمنع المساس بالموديلات المشتركة للعرض فقط (كتالوج المتجر/البترول) أو أي موديل آخر.
        if not model or model not in request.env or code not in self.pm_x_create_models() or model in _X_READONLY_MODELS:
            return {'ok': False, 'error': 'الإلغاء غير متاح لهذا النوع'}
        _g = self._x_deleg_check(code, 'cancel')
        if _g:
            return _g
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if not self._x_cancellable(rec):
            return {'ok': False, 'error': 'لا يمكن إلغاء هذا السجلّ في حالته الحالية'}
        st = getattr(rec, 'state', None)
        # مسوّدة خالصة → حذفها هو الإلغاء الأنظف (تختفي ويُسمح بطلب جديد)
        if st in _X_DRAFT_STATES:
            try:
                rec.unlink()
                return {'ok': True, 'msg': 'أُلغيت المسوّدة', 'method': 'unlink'}
            except Exception:
                pass
        # غير مسوّدة (مثلاً مُقدَّمة قبل الاعتماد) → دالة إلغاء/رفض تنقلها لحالة منتهية.
        # نجرّب الدوال بالتسلسل ونحتفظ بآخر خطأ؛ لا نُرجعه إلا بعد فشل الجميع.
        last_err = ''
        for m in ('action_cancel', 'button_cancel', 'action_draft_cancel', 'action_refuse', 'action_reject'):
            fn = getattr(rec, m, None)
            if callable(fn):
                try:
                    fn()
                    _, _, _, still_open = self._x_state_info(rec.exists())
                    if not rec.exists() or not still_open:
                        return {'ok': True, 'msg': 'أُلغي الطلب', 'method': m}
                except Exception as e:
                    last_err = _x_safe_error(e)
        # محاولة أخيرة: حذف — للمسوّدات فقط، كي لا يُحذف سجلّ تقدّم في مساره
        if st in _X_DRAFT_STATES:
            try:
                rec.unlink()
                return {'ok': True, 'msg': 'أُلغيت المسوّدة', 'method': 'unlink'}
            except Exception as e:
                return {'ok': False, 'error': _x_safe_error(e)}
        return {'ok': False, 'error': last_err or 'تعذّر إلغاء السجلّ في حالته الحالية'}

    # ============ الإجراءات الجماعية على القوائم ============
    @http.route(['/my/pm/x/bulk/<string:code>/<string:action>'], type='json', auth='user', website=False)
    def pm_x_bulk(self, code=None, action=None, rids=None, reason=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env or model in _X_READONLY_MODELS:
            return {'ok': False, 'error': 'غير متاح لهذا النوع'}
        _g = self._x_deleg_check(code, {'approve': 'submit', 'submit': 'submit',
                                        'reject': 'cancel'}.get((action or '').lower(), 'write'))
        if _g:
            return _g
        excl = self._X_ACTION_EXCLUDE.get(model, ())
        methods = self._X_ACTION_METHODS.get(action or '')
        done = failed = skipped = 0
        for rid in (rids or []):
            rec = request.env[model].sudo().browse(int(rid)).exists()
            if not (rec and self._x_rec_allowed(rec)):
                failed += 1
                continue
            # إلغاء جماعي
            if action == 'cancel':
                if code not in self.pm_x_create_models() or not self._x_editable(rec):
                    skipped += 1
                    continue
                ok = False
                try:
                    st = getattr(rec, 'state', None)
                    if st in _X_DRAFT_STATES:
                        rec.unlink()
                        ok = True
                    else:
                        for m in ('action_cancel', 'button_cancel', 'action_refuse', 'action_reject'):
                            fn = getattr(rec, m, None)
                            if callable(fn):
                                fn()
                                if (not rec.exists()) or (not self._x_state_info(rec)[3]):
                                    ok = True
                                break
                        if not ok and rec.exists():
                            rec.unlink()
                            ok = True
                except Exception:
                    ok = False
                done += 1 if ok else 0
                failed += 0 if ok else 1
                continue
            # اعتماد/رفض/إرسال جماعي
            if action in excl:
                skipped += 1
                continue
            if not methods:
                failed += 1
                continue
            if reason and action == 'reject' and hasattr(rec, 'message_post'):
                try:
                    rec.message_post(body='سبب الرفض (جماعي، من بوابة المشاريع): %s' % reason)
                except Exception:
                    pass
            targets = [rec] + ([rec.request_id] if getattr(rec, 'request_id', False) else [])
            applied = False
            for tgt in targets:
                for m in methods:
                    fn = getattr(tgt, m, None)
                    if callable(fn):
                        try:
                            fn()
                            applied = True
                        except Exception:
                            pass
                        break
                if applied:
                    break
            if applied:
                done += 1
            else:
                skipped += 1
        return {'ok': True, 'done': done, 'failed': failed, 'skipped': skipped}

    # ============ متجر المشروع: سلّة حقيقية (reuse care.pms.store.order + الميزانيات) ============
    def _x_store_cart(self, project, create=False):
        Order = request.env['care.pms.store.order'].sudo()
        o = Order.search([('project_id', '=', project.id), ('user_id', '=', request.env.user.id),
                          ('state', '=', 'draft')], limit=1)
        if not o and create:
            import datetime as _dt
            today = _dt.date.today()
            vals = {'project_id': project.id, 'user_id': request.env.user.id}
            if 'order_month' in Order._fields:
                vals['order_month'] = str(today.month)
            if 'order_year' in Order._fields:
                vals['order_year'] = str(today.year)
            o = Order.create(vals)
        return o

    def _x_store_cc(self, project):
        dept = project.pms_department_id if 'pms_department_id' in project._fields else False
        CC = request.env['cost.center'].sudo() if 'cost.center' in request.env else None
        if not dept or CC is None:
            return CC.browse() if CC is not None else None
        return CC.search([('department_id', '=', dept.id)], limit=1)

    @http.route(['/my/pm/x/store/data'], type='json', auth='user', website=False)
    def pm_x_store_data(self, type_id=None, q=None, **kw):
        env = request.env
        if 'care.pms.store.order' not in env or 'product.product' not in env:
            return {'ok': False, 'error': 'المتجر غير مُفعّل'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        Prod = env['product.product'].sudo()
        Type = env['care.pms.order.type'].sudo()
        Budget = env['care.pms.cost.budget'].sudo()
        cart = self._x_store_cart(p)
        # مركز التكلفة والميزانية حسب فترة الطلب (الشهر/السنة) — من السلّة إن وُجدت
        cc = (cart.cost_center_id if (cart and getattr(cart, 'cost_center_id', False)) else self._x_store_cc(p))
        _when = cart.period_date if (cart and getattr(cart, 'period_date', False)) else None
        active_tid = int(type_id) if type_id else (cart.order_type_id.id if (cart and cart.order_type_id) else 0)
        # مركز التكلفة المعروض يتبع النوع المختار/المعروض لا نوع السلّة العالق
        disp_cc = cc
        if active_tid:
            try:
                _at = Type.browse(active_tid)
                _b = Budget.budget_for(self._x_store_cc(p), _at, project=p, when=_when)
                if _b and _b.cost_center_id:
                    disp_cc = _b.cost_center_id
            except Exception:
                pass
        types = []
        for t in Type.search([]):
            try:
                b = Budget.budget_for(cc, t, project=p, when=_when) if cc else Budget.browse()
            except Exception:
                b = Budget.browse()
            cnt = Prod.search_count([('product_tmpl_id.pms_store_available', '=', True),
                                     ('product_tmpl_id.pms_order_type_id', '=', t.id)])
            # لقطة الميزانية للشهر المختار (period_date) لا الشهر الحالي دائمًا
            snap = b._usage_for(_when) if b else None
            types.append({'id': t.id, 'name': t.name, 'icon': t.icon or '📦', 'count': cnt,
                          'limit': snap['limit'] if snap else 0, 'used': snap['used'] if snap else 0,
                          'remaining': snap['remaining'] if snap else 0,
                          'pct': int(snap['pct']) if snap else 0,
                          'cc': (b.cost_center_id.display_name if (b and b.cost_center_id) else '')})
        wished = set()
        if 'care.pms.store.wishlist' in env:
            wished = set(env['care.pms.store.wishlist'].sudo().search(
                [('user_id', '=', env.user.id)]).mapped('product_id').ids)
        prods = []
        _wish_on = bool(kw.get('wish'))
        # البحث/المفضّلة يشملان كل الأنواع (قائمة حقيقية)؛ غيرهما يعرض أصناف النوع المختار
        if active_tid or q or _wish_on:
            dom = [('product_tmpl_id.pms_store_available', '=', True)]
            if _wish_on:
                dom.append(('id', 'in', list(wished) or [0]))
            elif q:
                dom += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
            elif active_tid:
                dom.append(('product_tmpl_id.pms_order_type_id', '=', active_tid))
            Uom = env['uom.uom'].sudo()
            recs = Prod.search(dom, limit=100000)
            # الاسم بالعربي والإنجليزي صراحةً (مع تهيئة تبادلية حتى لا يظهر اسم فارغ لصنفٍ ترجمته خاوية)
            nm_en = {r.id: (r.name or '') for r in recs.with_context(lang='en_US')}
            nm_ar = {r.id: (r.name or '') for r in recs.with_context(lang='ar_001')}
            for pr in recs:
                base = pr.list_price or pr.standard_price or 0
                uoms = Uom.search([('category_id', '=', pr.uom_id.category_id.id)]) if pr.uom_id else Uom.browse()
                uom_opts = [{'id': u.id, 'name': u.name,
                             'price': round(pr.uom_id._compute_price(base, u) if u != pr.uom_id else base, 3)}
                            for u in uoms]
                en = nm_en.get(pr.id) or nm_ar.get(pr.id) or pr.display_name
                ar = nm_ar.get(pr.id) or nm_en.get(pr.id) or pr.display_name
                prods.append({'id': pr.id, 'name': pr.display_name, 'name_en': en, 'name_ar': ar,
                              'code': pr.default_code or '', 'price': base,
                              'uom': pr.uom_id.name or '', 'uom_id': pr.uom_id.id, 'uoms': uom_opts,
                              'img': '/web/image/product.product/%s/image_256' % pr.id,
                              'wish': pr.id in wished})
        lines = []
        for l in (cart.line_ids if cart else []):
            _pr = l.product_id
            _en = (_pr.with_context(lang='en_US').name or '') or _pr.display_name
            _ar = (_pr.with_context(lang='ar_001').name or '') or _en
            lines.append({'lid': l.id, 'name': _pr.display_name, 'name_en': _en, 'name_ar': _ar,
                          'code': _pr.default_code or '', 'qty': l.qty,
                          'price': l.price_unit, 'sub': l.subtotal, 'uom': l.uom_name or ''})
        return {'ok': True, 'types': types, 'active': active_tid, 'products': prods,
                'currency': (p.company_id.currency_id.name or 'KWD'),
                'cart': {'id': cart.id if cart else 0, 'lines': lines,
                         'total': round(cart.amount_total, 3) if cart else 0,
                         'type': (cart.order_type_id.name if (cart and cart.order_type_id) else ''),
                         'max_amount': round(cart.max_amount, 3) if cart else 0,
                         'remaining': round((cart.max_amount or 0) - (cart.amount_total or 0), 3) if cart else 0,
                         'over_budget': cart.over_budget if cart else False, 'count': len(lines),
                         'note': (cart.note or '') if cart else ''},
                'period': {'month': (cart.order_month if cart else ''), 'year': (cart.order_year if cart else ''),
                           'cc': (disp_cc.display_name if disp_cc else ''),
                           'months': [[k, v] for k, v in (env['care.pms.store.order']._fields['order_month'].selection if 'order_month' in env['care.pms.store.order']._fields else [])],
                           'years': [[k, v] for k, v in (env['care.pms.store.order'].sudo().fields_get(['order_year'])['order_year'].get('selection') or [])]}}

    @http.route(['/my/pm/x/store/period'], type='json', auth='user', website=False)
    def pm_x_store_period(self, month=None, year=None, **kw):
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        cart = self._x_store_cart(p, create=True)
        vals = {}
        if month:
            vals['order_month'] = str(int(month))
        if year:
            vals['order_year'] = str(int(year))
        if vals:
            cart.sudo().write(vals)
        return {'ok': True, 'cc': (cart.cost_center_id.name if cart.cost_center_id else '')}

    @http.route(['/my/pm/x/store/wish/<int:pid>'], type='json', auth='user', website=False)
    def pm_x_store_wish(self, pid=None, **kw):
        env = request.env
        if 'care.pms.store.wishlist' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        W = env['care.pms.store.wishlist'].sudo()
        exist = W.search([('user_id', '=', env.user.id), ('product_id', '=', int(pid or 0))], limit=1)
        if exist:
            exist.unlink()
            return {'ok': True, 'wished': False}
        W.create({'user_id': env.user.id, 'product_id': int(pid or 0)})
        return {'ok': True, 'wished': True}

    @http.route(['/my/pm/x/store/reorder/<int:oid>'], type='json', auth='user', website=False)
    def pm_x_store_reorder(self, oid=None, **kw):
        env = request.env
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        src = env['care.pms.store.order'].sudo().browse(int(oid or 0)).exists()
        if not (src and self._x_rec_allowed(src)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        cart = self._x_store_cart(p, create=True)
        try:
            if not cart.line_ids and src.order_type_id:
                cart.order_type_id = src.order_type_id.id
            Line = env['care.pms.store.order.line'].sudo()
            n = 0
            for l in src.line_ids:
                Line.create({'order_id': cart.id, 'product_id': l.product_id.id, 'qty': l.qty or 1,
                             'employee_id': l.employee_id.id if l.employee_id else False})
                n += 1
            return {'ok': True, 'msg': 'أُضيف %d صنفًا من الطلب %s إلى السلّة' % (n, src.name or '')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/store/add'], type='json', auth='user', website=False)
    def pm_x_store_add(self, product_id=None, qty=None, **kw):
        env = request.env
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        pr = env['product.product'].sudo().browse(int(product_id or 0)).exists()
        if not pr:
            return {'ok': False, 'error': 'صنف غير معروف'}
        cart = self._x_store_cart(p, create=True)
        otype = pr.product_tmpl_id.pms_order_type_id
        # إصلاح: السلّة الفارغة لا تُقفَل على نوع عالق — نُحرّر القفل ونأخذ نوع المنتج
        if not cart.line_ids and cart.order_type_id.id != (otype.id if otype else 0):
            cart.order_type_id = otype.id if otype else False
        if cart.order_type_id and otype and cart.order_type_id.id != otype.id:
            return {'ok': False, 'error': 'السلّة تحوي نوع طلب مختلف — أرسلها أو أفرغها أولاً.'}
        if not cart.order_type_id and otype:
            cart.order_type_id = otype.id
        qv = float(qty or 1) or 1
        # الوحدة المختارة: تغيير الوحدة يغيّر السعر (تحويل السعر بمعامل القياس)
        L = env['care.pms.store.order.line'].sudo()
        uom = env['uom.uom'].sudo().browse(int(kw.get('uom_id') or 0))
        if not (uom and uom.exists() and uom.category_id == pr.uom_id.category_id):
            uom = pr.uom_id
        base = pr.list_price or pr.standard_price or 0.0
        price = pr.uom_id._compute_price(base, uom) if (uom and uom != pr.uom_id) else base
        has_uom = 'uom_id' in L._fields
        line = cart.line_ids.filtered(
            lambda l: l.product_id.id == pr.id and ((l.uom_id.id if has_uom else 0) or pr.uom_id.id) == uom.id)[:1]
        if line:
            line.qty += qv
        else:
            vals = {'order_id': cart.id, 'product_id': pr.id, 'qty': qv, 'price_unit': price}
            if has_uom:
                vals['uom_id'] = uom.id
            L.create(vals)
        return {'ok': True, 'msg': 'أُضيف للسلّة'}

    @http.route(['/my/pm/x/store/qty'], type='json', auth='user', website=False)
    def pm_x_store_qty(self, lid=None, qty=None, **kw):
        line = request.env['care.pms.store.order.line'].sudo().browse(int(lid or 0)).exists()
        if not (line and line.order_id.user_id.id == request.env.user.id and line.order_id.state == 'draft'):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        order = line.order_id
        qv = float(qty or 0)
        if qv <= 0:
            line.unlink()
        else:
            line.qty = qv
        if not order.line_ids and order.order_type_id:
            order.order_type_id = False  # إفراغ السلّة يُحرّر قفل النوع ومركز التكلفة
        return {'ok': True}

    @http.route(['/my/pm/x/store/remove'], type='json', auth='user', website=False)
    def pm_x_store_remove(self, lid=None, **kw):
        line = request.env['care.pms.store.order.line'].sudo().browse(int(lid or 0)).exists()
        if not (line and line.order_id.user_id.id == request.env.user.id and line.order_id.state == 'draft'):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        order = line.order_id
        line.unlink()
        if not order.line_ids and order.order_type_id:
            order.order_type_id = False
        return {'ok': True}

    @http.route(['/my/pm/x/store/clear'], type='json', auth='user', website=False)
    def pm_x_store_clear(self, **kw):
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        p = self._x_current_project(None)
        cart = self._x_store_cart(p) if p else None
        if cart and cart.user_id.id == request.env.user.id:
            cart.line_ids.unlink()
            cart.order_type_id = False
        return {'ok': True}

    @http.route(['/my/pm/x/store/submit'], type='json', auth='user', website=False)
    def pm_x_store_submit(self, note=None, **kw):
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        _g = self._x_deleg_check('store', 'submit')
        if _g:
            return _g
        cart = self._x_store_cart(p)
        if not cart or not cart.line_ids:
            return {'ok': False, 'error': 'السلّة فارغة'}
        if note:
            cart.note = note
        if cart.over_budget:
            return {'ok': False, 'error': 'الطلب يتجاوز ميزانية مركز التكلفة لهذا النوع.'}
        try:
            cart.action_submit()
            return {'ok': True, 'msg': 'تم إرسال الطلب %s' % (cart.name or ''), 'name': cart.name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ تدفّق التاسكات: تحويل/قبول/رفض (reuse project.task forward) ============
    def _x_task_scope(self, rid):
        t = request.env['project.task'].sudo().browse(int(rid or 0)).exists()
        if not (t and self._x_rec_allowed(t)):
            return None
        return t

    @http.route(['/my/pm/x/task/users'], type='json', auth='user', website=False)
    def pm_x_task_users(self, **kw):
        users = request.env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True), ('id', '!=', request.env.user.id)], order='name', limit=100000)
        return {'ok': True, 'users': [[u.id, u.name] for u in users]}

    @http.route(['/my/pm/x/task/<int:rid>/forward'], type='json', auth='user', website=False)
    def pm_x_task_forward(self, rid=None, forward_to_id=None, reason=None, **kw):
        _g = self._x_deleg_check('tasks', 'write')
        if _g:
            return _g
        t = self._x_task_scope(rid)
        if not t:
            return {'ok': False, 'error': 'غير مصرّح'}
        if not forward_to_id:
            return {'ok': False, 'error': 'اختر المستخدم المُحال إليه'}
        try:
            t.write({'forward_to_id': int(forward_to_id), 'forward_reason': reason or ''})
            t.action_request_forward()
            return {'ok': True, 'msg': 'تم طلب تحويل المهمة'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/task/<int:rid>/faccept'], type='json', auth='user', website=False)
    def pm_x_task_faccept(self, rid=None, **kw):
        _g = self._x_deleg_check('tasks', 'write')
        if _g:
            return _g
        t = self._x_task_scope(rid)
        if not t:
            return {'ok': False, 'error': 'غير مصرّح'}
        if t.forward_to_id.id != request.env.user.id:
            return {'ok': False, 'error': 'القبول من صلاحية المُحال إليه فقط'}
        try:
            t.action_accept_forward()
            return {'ok': True, 'msg': 'تم قبول التحويل'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/task/<int:rid>/freject'], type='json', auth='user', website=False)
    def pm_x_task_freject(self, rid=None, reason=None, **kw):
        _g = self._x_deleg_check('tasks', 'write')
        if _g:
            return _g
        t = self._x_task_scope(rid)
        if not t:
            return {'ok': False, 'error': 'غير مصرّح'}
        if t.forward_to_id.id != request.env.user.id:
            return {'ok': False, 'error': 'الرفض من صلاحية المُحال إليه فقط'}
        try:
            if reason:
                t.forward_reason = reason
            t.action_reject_forward()
            return {'ok': True, 'msg': 'تم رفض التحويل'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ الملابس بالمقاسات: طلب زيّ لكل عامل حسب مقاسه ============
    _X_SIZE_FIELD = {'top': 'uniform_top_size', 'bottom': 'uniform_bottom_size',
                     'shoe': 'shoe_size', 'cap': 'cap_size'}

    @http.route(['/my/pm/x/clothing/data'], type='json', auth='user', website=False)
    def pm_x_clothing_data(self, type_id=None, product_id=None, **kw):
        env = request.env
        if 'care.pms.order.type' not in env or 'product.product' not in env:
            return {'ok': False, 'error': 'المتجر غير مُفعّل'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        Prod = env['product.product'].sudo()
        base = [('product_tmpl_id.pms_store_available', '=', True), ('product_tmpl_id.pms_size_type', '!=', 'none')]
        types = []
        for t in env['care.pms.order.type'].sudo().search([]):
            cnt = Prod.search_count(base + [('product_tmpl_id.pms_order_type_id', '=', t.id)])
            if cnt:
                types.append({'id': t.id, 'name': t.name, 'icon': t.icon or '👕', 'count': cnt})
        active_tid = int(type_id) if type_id else (types[0]['id'] if types else 0)
        products = []
        if active_tid:
            for pr in Prod.search(base + [('product_tmpl_id.pms_order_type_id', '=', active_tid)], limit=100000):
                products.append({'id': pr.id, 'name': pr.display_name, 'size_type': pr.product_tmpl_id.pms_size_type,
                                 'price': pr.list_price or 0})
        # العمّال مع **كل** مقاساتهم (علوي/سفلي/حذاء/قبعة) — لدعم طلب عدّة أصناف دفعةً
        workers = []
        if dept:
            SF = self._X_SIZE_FIELD
            for w in env['hr.employee'].sudo().search(self._x_emp_dom(dept.id), order='name', limit=100000):
                szs = {}
                for k, fld in SF.items():
                    if fld in w._fields and getattr(w, fld, False):
                        v = getattr(w, fld)
                        try:
                            v = dict(w._fields[fld]._description_selection(env)).get(v, v)
                        except Exception:
                            pass
                        szs[k] = v
                workers.append({'empId': w.id, 'name': w.name or '—', 'badge': w.barcode or '', 'sizes': szs})
        return {'ok': True, 'types': types, 'active': active_tid, 'products': products, 'workers': workers}

    @http.route(['/my/pm/x/clothing/create'], type='json', auth='user', website=False)
    def pm_x_clothing_create(self, order_type_id=None, product_id=None, product_ids=None, employees=None, submit=None, **kw):
        env = request.env
        _g = self._x_deleg_check('store', 'write')
        if _g:
            return _g
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        prods = []
        if product_ids:
            try:
                prods = [int(x) for x in product_ids if x]
            except Exception:
                prods = []
        if not prods and product_id:
            prods = [int(product_id)]
        if not order_type_id or not prods or not employees:
            return {'ok': False, 'error': 'اختر النوع والأصناف والعمّال'}
        # فرض النطاق: لا يُقبل إلا عمّال أقسام المدير (منع إدراج عمّال خارج النطاق عبر JSON مباشرةً)
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        try:
            want = [int(e) for e in employees]
        except Exception:
            return {'ok': False, 'error': 'قائمة عمّال غير صحيحة'}
        valid = set(env['hr.employee'].sudo().search(
            [('id', 'in', want)] + self._x_emp_dom(dept.id)).ids) if dept else set()
        emp_ids = [e for e in want if e in valid]
        if not emp_ids:
            return {'ok': False, 'error': 'العمّال المحدَّدون خارج نطاقك'}
        try:
            lines = [(0, 0, {'product_id': pid, 'employee_id': eid, 'qty': 1}) for eid in emp_ids for pid in prods]
            order = env['care.pms.store.order'].sudo().create({
                'project_id': p.id, 'user_id': env.user.id,
                'order_type_id': int(order_type_id), 'line_ids': lines})
            if submit and order.line_ids and not order.over_budget:
                order.action_submit()
                return {'ok': True, 'msg': 'تم إرسال طلب الملابس %s' % (order.name or ''), 'name': order.name, 'submitted': True}
            return {'ok': True, 'msg': 'تم حفظ طلب الملابس %s' % (order.name or ''), 'name': order.name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ التصاريح: إنشاء مجمّع (نوع + عدّة عمّال → طلب + بند لكل عامل) ============
    @http.route(['/my/pm/x/permit/meta'], type='json', auth='user', website=False)
    def pm_x_permit_meta(self, **kw):
        env = request.env
        if 'care.permit.type' not in env or 'care.permit.request' not in env:
            return {'ok': False, 'error': 'غير متاح لهذا النوع'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        types = [{'id': t.id, 'name': t.name, 'fee': t.fee or 0}
                 for t in env['care.permit.type'].sudo().search([])]
        workers = []
        if dept:
            for w in env['hr.employee'].sudo().search(self._x_emp_dom(dept.id), order='name', limit=100000):
                workers.append({'empId': w.id, 'name': w.name or '—', 'badge': w.barcode or ''})
        return {'ok': True, 'types': types, 'workers': workers}

    @http.route(['/my/pm/x/suspension/meta'], type='json', auth='user', website=False)
    def pm_x_suspension_meta(self, **kw):
        env = request.env
        if 'care.suspension.request' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        dept = p.pms_department_id if (p and 'pms_department_id' in p._fields) else False
        workers = []
        if dept:
            for w in env['hr.employee'].sudo().search(self._x_emp_dom(dept.id), order='name', limit=100000):
                cls, txt = _WS.get(getattr(w, 'worker_status', 'active') or 'active', ('ok', 'نشط'))
                workers.append({'empId': w.id, 'name': w.name or '—', 'badge': w.barcode or '', 'status': txt})
        reasons = []
        try:
            reasons = [[k, v] for k, v in (env['care.suspension.request.line']._fields['line_reason'].selection or [])]
        except Exception:
            reasons = []
        return {'ok': True, 'workers': workers, 'reasons': reasons}

    @http.route(['/my/pm/x/suspension/create'], type='json', auth='user', website=False)
    def pm_x_suspension_create(self, employees=None, effective_date=None, line_reason=None,
                               note=None, submit=None, **kw):
        """إنشاء طلب إيقاف عن العمل واحد ببند لكل عامل محدَّد (تعدّد العمّال كالباك-إند)."""
        env = request.env
        if 'care.suspension.request' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        _g = self._x_deleg_check('suspension', 'write')
        if _g:
            return _g
        if not employees or not effective_date:
            return {'ok': False, 'error': 'حدِّد العمّال وتاريخ الإيقاف'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        try:
            want = [int(e) for e in employees]
        except Exception:
            return {'ok': False, 'error': 'قائمة عمّال غير صحيحة'}
        valid = set(env['hr.employee'].sudo().search(
            [('id', 'in', want)] + self._x_emp_dom(dept.id)).ids) if dept else set()
        emp_ids = [e for e in want if e in valid]
        if not emp_ids:
            return {'ok': False, 'error': 'العمّال المحدَّدون خارج نطاقك'}
        SR = env['care.suspension.request'].sudo()
        try:
            lines = [(0, 0, dict({'employee_id': eid, 'effective_date': effective_date},
                                 **({'line_reason': line_reason} if line_reason else {}),
                                 **({'note': note} if note else {}))) for eid in emp_ids]
            vals = {'line_ids': lines}
            if 'project_id' in SR._fields:
                vals['project_id'] = p.id
            if line_reason and 'reason' in SR._fields:
                vals['reason'] = line_reason
            if note and 'note' in SR._fields:
                vals['note'] = note
            req = SR.create(vals)
            if submit and hasattr(req, 'action_submit'):
                try:
                    req.action_submit()
                    return {'ok': True, 'name': req.display_name,
                            'msg': 'تم إنشاء وإرسال طلب إيقاف لـ%d عامل' % len(emp_ids)}
                except Exception:
                    pass
            return {'ok': True, 'name': req.display_name,
                    'msg': 'تم إنشاء طلب إيقاف لـ%d عامل (مسودّة)' % len(emp_ids)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/permit/create'], type='json', auth='user', website=False)
    def pm_x_permit_create(self, type_id=None, employees=None, note=None, submit=None, **kw):
        env = request.env
        if 'care.permit.request' not in env:
            return {'ok': False, 'error': 'غير متاح لهذا النوع'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        _g = self._x_deleg_check('permits', 'write')
        if _g:
            return _g
        if not type_id or not employees:
            return {'ok': False, 'error': 'اختر نوع التصريح والعمّال'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        try:
            want = [int(e) for e in employees]
        except Exception:
            return {'ok': False, 'error': 'قائمة عمّال غير صحيحة'}
        valid = set(env['hr.employee'].sudo().search(
            [('id', 'in', want)] + self._x_emp_dom(dept.id)).ids) if dept else set()
        emp_ids = [e for e in want if e in valid]
        if not emp_ids:
            return {'ok': False, 'error': 'العمّال المحدَّدون خارج نطاقك'}
        try:
            pt = env['care.permit.type'].sudo().browse(int(type_id)).exists()
            if not pt:
                return {'ok': False, 'error': 'نوع تصريح غير معروف'}
            fee = pt.fee or 0
            lines = [(0, 0, {'employee_id': eid, 'type_id': pt.id, 'fee': fee}) for eid in emp_ids]
            req = env['care.permit.request'].sudo().create({
                'department_id': dept.id if dept else False,
                'default_type_id': pt.id, 'default_fee': fee,
                'note': note or '', 'line_ids': lines})
            if submit and hasattr(req, 'action_submit'):
                try:
                    req.action_submit()
                    return {'ok': True, 'msg': 'تم إرسال طلب التصاريح %s' % (req.name or ''),
                            'name': req.name, 'submitted': True}
                except Exception:
                    pass
            return {'ok': True, 'msg': 'تم حفظ طلب التصاريح %s' % (req.name or ''), 'name': req.name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/permit/img/<int:lid>'], type='http', auth='user', website=False)
    def pm_x_permit_img(self, lid=None, **kw):
        """بثّ صورة التصريح (care.permit.line.attachment) عبر sudo — ACL يمنع /web/image لمدير المشروع."""
        env = request.env
        if 'care.permit.line' not in env:
            return request.not_found()
        line = env['care.permit.line'].sudo().browse(int(lid or 0)).exists()
        if not (line and line.attachment and self._x_emp_allowed(
                line.employee_id, self._pm_projects().mapped('pms_department_id').ids)):
            return request.not_found()
        import base64
        try:
            data = base64.b64decode(line.attachment)
        except Exception:
            return request.not_found()
        fn = (line.attachment_name or '').lower()
        mt = ('image/png' if fn.endswith('.png') else 'application/pdf' if fn.endswith('.pdf')
              else 'image/gif' if fn.endswith('.gif') else 'image/jpeg')
        return request.make_response(data, headers=[('Content-Type', mt), ('Content-Disposition', 'inline')])

    @http.route(['/my/pm/x/emp/<int:eid>/photo'], type='http', auth='user', website=False)
    def pm_x_emp_photo(self, eid=None, size=None, **kw):
        """بثّ صورة العامل عبر sudo — /web/image/hr.employee محجوب لمدير المشروع (ACL)؛ مُنطَّق على فريقه."""
        env = request.env
        emp = env['hr.employee'].sudo().browse(int(eid or 0)).exists()
        dept_ids = self._pm_projects().mapped('pms_department_id').ids
        if not (emp and self._x_emp_allowed(emp, dept_ids)):
            return request.not_found()
        field = 'image_%s' % size if size in ('128', '256', '512', '1024', '1920') else 'image_256'
        data = emp[field] if field in emp._fields else emp.image_256
        if not data:
            return request.not_found()
        import base64
        try:
            raw = base64.b64decode(data)
        except Exception:
            return request.not_found()
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'), ('Cache-Control', 'private, max-age=3600'),
            ('Content-Disposition', 'inline')])

    # ============ العمل الإضافي (overtime.request): إنشاء مجمّع ببنود عمّال ============
    _X_OT_HOURLY = {'overtime_hours', 'weekend_holiday', 'night_shift', 'on_call', 'call_back',
                    'double_shift', 'shift_coverage', 'extra_duty'}

    @http.route(['/my/pm/x/overtime/meta'], type='json', auth='user', website=False)
    def pm_x_overtime_meta(self, **kw):
        env = request.env
        if 'overtime.request' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        OT = env['overtime.request']
        types = [[k, v, (k in self._X_OT_HOURLY)] for k, v in OT._fields['compensation_type'].selection]
        months = [[k, v] for k, v in (OT._fields['comp_month'].selection if 'comp_month' in OT._fields else [])]
        workers = []
        if dept:
            for w in env['hr.employee'].sudo().search(self._x_emp_dom(dept.id), order='name', limit=100000):
                workers.append({'empId': w.id, 'name': w.name or '—', 'badge': w.barcode or ''})
        import datetime as _dt
        return {'ok': True, 'types': types, 'months': months, 'year': _dt.date.today().year, 'workers': workers}

    @http.route(['/my/pm/x/overtime/create'], type='json', auth='user', website=False)
    def pm_x_overtime_create(self, comp_type=None, comp_month=None, comp_year=None, num_days=None,
                             num_hours=None, hourly_rate=None, comp_value=None, employees=None, submit=None, **kw):
        env = request.env
        _g = self._x_deleg_check('overtime', 'write')
        if _g:
            return _g
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        if not comp_type or not employees:
            return {'ok': False, 'error': 'اختر نوع التعويض والعمّال'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        try:
            want = [int(e) for e in employees]
        except Exception:
            return {'ok': False, 'error': 'قائمة عمّال غير صحيحة'}
        valid = set(env['hr.employee'].sudo().search([('id', 'in', want)] + self._x_emp_dom(dept.id)).ids) if dept else set()
        emp_ids = [e for e in want if e in valid]
        if not emp_ids:
            return {'ok': False, 'error': 'العمّال المحدَّدون خارج نطاقك'}

        def _f(x):
            try:
                return float(x or 0)
            except Exception:
                return 0.0
        hourly = comp_type in self._X_OT_HOURLY
        if hourly and _f(num_hours) <= 0:
            return {'ok': False, 'error': 'أدخل عدد الساعات.'}
        if hourly and _f(hourly_rate) <= 0:
            return {'ok': False, 'error': 'أدخل سعر الساعة.'}
        if not hourly and _f(comp_value) <= 0:
            return {'ok': False, 'error': 'أدخل قيمة التعويض.'}
        lines = []
        for eid in emp_ids:
            lv = {'employee_id': eid}
            if hourly:
                lv.update({'num_days': _f(num_days) or 1.0, 'num_hours': _f(num_hours), 'hourly_rate': _f(hourly_rate)})
            else:
                lv['compensation_value'] = _f(comp_value)
            lines.append((0, 0, lv))
        try:
            vals = {'compensation_type': comp_type, 'request_line_ids': lines}
            if dept:
                vals['department_id'] = dept.id
            if comp_month:
                vals['comp_month'] = comp_month
            if comp_year:
                vals['comp_year'] = int(comp_year)
            req = env['overtime.request'].sudo().create(vals)
            if submit:
                for _m in ('button_submit', 'action_submit', 'action_pm_approve'):
                    if hasattr(req, _m):
                        try:
                            getattr(req, _m)()
                            return {'ok': True, 'msg': 'تم إرسال طلب العمل الإضافي %s' % (req.display_name or ''), 'name': req.display_name, 'submitted': True}
                        except Exception:
                            break
            return {'ok': True, 'msg': 'تم حفظ طلب العمل الإضافي %s' % (req.display_name or ''), 'name': req.display_name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ محاضر استلام السيارات (care.vehicle.handover): meta + إنشاء بالصور ============
    _X_HANDOVER_CONTENTS = [
        ('has_book', 'دفتر المركبة'), ('has_extinguisher', 'طفاية حريق'),
        ('has_spare_tire', 'إطار احتياطي'), ('has_tool_kit', 'طقم عدّة'),
        ('has_jack', 'جاك'), ('has_first_aid', 'صندوق إسعافات'),
        ('has_plates', 'لوحات المركبة'), ('has_wipers', 'مساحات زجاج'),
        ('has_reflective_triangle', 'مثلث عاكس'), ('has_cassette', 'كاسيت'),
        ('has_curtains', 'ستائر'), ('has_tarpaulin', 'توربال'),
        ('has_top_lights', 'فنارات علوية'),
    ]

    @http.route(['/my/pm/x/handover/meta'], type='json', auth='user', website=False)
    def pm_x_handover_meta(self, **kw):
        env = request.env
        if 'care.vehicle.handover' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        vehicles = [{'id': v.id, 'name': (v.license_plate or v.name or '—'),
                     'sub': v.model_id.name or ''}
                    for v in env['fleet.vehicle'].sudo().search([], order='license_plate', limit=100000)]
        workers = []
        dept = p.pms_department_id if (p and 'pms_department_id' in p._fields) else False
        if dept:
            for w in env['hr.employee'].sudo().search(self._x_emp_dom(dept.id), order='name', limit=100000):
                workers.append({'id': w.id, 'name': w.name or '—', 'badge': w.barcode or ''})
        return {'ok': True, 'vehicles': vehicles, 'workers': workers,
                'contents': [[k, lbl] for k, lbl in self._X_HANDOVER_CONTENTS]}

    @http.route(['/my/pm/x/handover/create'], type='json', auth='user', website=False)
    def pm_x_handover_create(self, vehicle_id=None, to_driver_id=None, from_driver_id=None,
                             odometer=None, location_name=None, location_manager=None,
                             location_phone=None, contents=None, photo_front=None, photo_back=None,
                             photo_left=None, photo_right=None, submit=None, **kw):
        env = request.env
        if 'care.vehicle.handover' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        if not vehicle_id or not to_driver_id:
            return {'ok': False, 'error': 'اختر المركبة والسائق المستلم.'}
        veh = env['fleet.vehicle'].sudo().browse(int(vehicle_id)).exists()
        if not veh:
            return {'ok': False, 'error': 'المركبة غير موجودة.'}
        dept = p.pms_department_id if (p and 'pms_department_id' in p._fields) else False
        valid = set(env['hr.employee'].sudo().search(self._x_emp_dom(dept.id)).ids) if dept else set()
        if int(to_driver_id) not in valid:
            return {'ok': False, 'error': 'السائق المستلم خارج نطاق مشروعك.'}

        def _img(b64):
            if not b64:
                return False
            if isinstance(b64, str) and b64.startswith('data:') and ',' in b64:
                return b64.split(',', 1)[1] or False
            return b64 or False
        vals = {
            'vehicle_id': veh.id, 'to_driver_id': int(to_driver_id),
            'odometer': float(odometer or 0), 'pm_id': env.user.id,
            'location_name': location_name or '', 'location_manager': location_manager or '',
            'location_phone': location_phone or '',
            'photo_front': _img(photo_front), 'photo_back': _img(photo_back),
            'photo_left': _img(photo_left), 'photo_right': _img(photo_right),
        }
        if p:
            vals['project_id'] = p.id
        if from_driver_id and int(from_driver_id) in valid:
            vals['from_driver_id'] = int(from_driver_id)
        if isinstance(contents, dict):
            for k, _lbl in self._X_HANDOVER_CONTENTS:
                vals[k] = bool(contents.get(k))
        try:
            h = env['care.vehicle.handover'].sudo().create(vals)
            if submit:
                try:
                    h.action_submit()
                    return {'ok': True, 'submitted': True, 'name': h.name,
                            'msg': 'تم تقديم محضر الاستلام %s لاعتماد مدير الفليت.' % (h.name or '')}
                except Exception as e:
                    return {'ok': True, 'submitted': False, 'name': h.name,
                            'msg': 'حُفظ المحضر %s كمسوّدة — تعذّر التقديم: %s' % (h.name or '', _x_safe_error(e))}
            return {'ok': True, 'submitted': False, 'name': h.name,
                    'msg': 'تم حفظ محضر الاستلام %s كمسوّدة.' % (h.name or '')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/ts/new'], type='json', auth='user', website=False)
    def pm_x_ts_new(self, month=None, year=None, **kw):
        """إنشاء كشف تايم شيت للمشروع الحالي لشهر/سنة محدّدين ثم توليد الأيام من البصمات."""
        env = request.env
        if 'care.timesheet' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        import datetime as _dt
        import calendar as _cal
        try:
            m = int(month); y = int(year)
            df = _dt.date(y, m, 1)
            dt = _dt.date(y, m, _cal.monthrange(y, m)[1])
        except Exception:
            return {'ok': False, 'error': 'حدّد الشهر والسنة'}
        TS = env['care.timesheet'].sudo()
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        # لا تُكرّر كشفًا لنفس المشروع/الشهر
        exist = TS.search([('project_id', '=', p.id), ('date_from', '=', df)], limit=1)
        if exist:
            return {'ok': False, 'error': 'يوجد كشف لهذا الشهر بالفعل (%s)' % (exist.name or '')}
        vals = {'project_id': p.id, 'date_from': df, 'date_to': dt}
        if dept and 'department_id' in TS._fields:
            vals['department_id'] = dept.id
        try:
            ts = TS.create(vals)
            # توليد الشبكة اليومية (الخلايا P/A/O/H/X) — لا الأسطر المجمّعة فقط
            if hasattr(ts, 'button_generate_grid'):
                ts.button_generate_grid()
            elif hasattr(ts, 'button_generate_timesheet'):
                ts.button_generate_timesheet()
            return {'ok': True, 'id': ts.id, 'name': ts.name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ تايم شيت: الشبكة اليومية (reuse care.timesheet + care.timesheet.day) ============
    _X_TS_COLORS = {'P': 'ok', 'O': 'mut', 'A': 'crit', 'L': 'info', 'H': 'violet',
                    'S': 'warn', 'X': 'dark', 'T': 'amber', 'E': 'teal'}

    def _ts_line_stats(self, ln):
        """إحصاءات سطر عامل بعد تعديل فوري — لتحديث أعمدة المعتمد/البصمة/اليدوي بلا إعادة تحميل."""
        ln = ln[:1]
        if not ln:
            return {}
        bio = len(ln.day_ids.filtered(lambda d: getattr(d, 'source', '') == 'bio'))
        man = len(ln.day_ids.filtered(lambda d: getattr(d, 'source', '') == 'manual'))
        return {'emp': ln.employee_id.id, 'approved': ln.approved_days or 0,
                'bio': bio, 'manual': man, 'present': ln.present_days or 0,
                'absent': ln.absent_days or 0, 'salary': ln.salary_days or 0}

    @http.route(['/my/pm/x/ts/<int:tid>'], type='json', auth='user', website=False)
    def pm_x_ts_grid(self, tid=None, **kw):
        env = request.env
        _g = self._x_deleg_check('timesheet', 'read')
        if _g:
            return _g
        if 'care.timesheet' not in env:
            return {'ok': False, 'error': 'التايم شيت غير مُفعّل'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            dates = [str(d) for d in ts._dates_in_period()] if hasattr(ts, '_dates_in_period') else []
        except Exception:
            dates = []
        sel = env['care.timesheet.day']._fields['status'].selection if 'care.timesheet.day' in env else []
        states = [[c, l, self._X_TS_COLORS.get(c, 'mut')] for c, l in sel]
        # ===== العمل الإضافي كصفوف زرقاء (نفس المشروع أسفل العامل + الوارد بالنهاية) =====
        import datetime as _dt
        _pf, _pt = ts.date_from, ts.date_to
        _emp_ids = ts.line_ids.mapped('employee_id').ids
        _XW_STATES = ('active', 'paused', 'pause_requested', 'end_requested', 'pm_approved',
                      'hr_approved', 'submit', 'submitted', 'to_approve')
        same_rows_by_emp = {}   # {emp_id: [blue_row,...]}  صفوف نفس المشروع
        incoming_rows = []      # صفوف واردة من مشاريع أخرى (نهاية الكشف)
        sum_same = {'count': 0, 'hours': 0.0, 'amount': 0.0}
        sum_in = {'count': 0, 'hours': 0.0, 'amount': 0.0, 'workers': 0}
        xrecords = []

        def _cover_days(w):
            df = w.date_from or _pf
            dt = w.date_to if (w.duration_type == 'fixed' and w.date_to) else _pt
            a = max(df, _pf) if (df and _pf) else (df or _pf)
            b = min(dt, _pt) if (dt and _pt) else (dt or _pt)
            out = []
            if a and b and a <= b:
                cur = a
                while cur <= b:
                    out.append(str(cur)); cur = cur + _dt.timedelta(days=1)
            return out

        def _overlaps(w):
            return (w.duration_type == 'open' or not (w.date_from and w.date_to)
                    or (w.date_from <= _pt and w.date_to >= _pf))

        def _blue_row(w, kind):
            # يضمن أيام الإضافي (بصمة مشتركة من الصفّ الأساسي) ثم يبني صفًّا محاذيًا لتواريخ الشبكة
            try:
                w._ts_sync_days(ts)
            except Exception:
                pass
            dmap = {str(d.date): d for d in w.day_ids}
            cov = set(_cover_days(w))
            _std = round(w._ts_std_hours() or 8.0, 1)
            bdays = []
            for ds in dates:
                d = dmap.get(ds)
                bdays.append({'date': ds, 'id': (d.id if d else 0),
                              'status': (d.status if d else ''), 'in_cover': ds in cov,
                              'edited': bool(d.edited) if d else False,
                              'hours': round((d.work_hours or 0.0) if d else 0.0, 2)})
            amount = round(w._payable_amount(), 3)
            return {'xwid': w.id, 'kind': kind, 'empId': w.employee_id.id,
                    'name': w.employee_id.name or '—', 'badge': w.employee_id.barcode or '',
                    'ref': w.name or '', 'state': w.state, 'std': _std,
                    'home': (w.home_department_id.name or '—'),
                    'from': str(w.date_from or ''),
                    'to': (str(w.date_to or '') if w.duration_type == 'fixed' else 'مفتوح'),
                    'comp': w.comp_type, 'amount': amount,
                    'attended': w.ts_attended_days or 0, 'scheduled': w.ts_scheduled_days or 0,
                    'hours_adj': round(w._ts_hours_adjustment(), 3), 'days': bdays}

        if 'care.extra.work' in env and 'care.extra.work.day' in env:
            EW = env['care.extra.work'].sudo()
            # (1) نفس المشروع — لعمّال الكشف
            if _emp_ids:
                for _w in EW.search([('employee_id', 'in', _emp_ids), ('same_project', '=', True),
                                     ('state', 'in', _XW_STATES)]):
                    if not _overlaps(_w) or not _cover_days(_w):
                        continue
                    _row = _blue_row(_w, 'same')
                    same_rows_by_emp.setdefault(_w.employee_id.id, []).append(_row)
                    sum_same['count'] += 1; sum_same['amount'] += _row['amount']
                    xrecords.append({'id': _w.id, 'emp': _w.employee_id.name or '—', 'kind': 'same',
                                     'amount': _row['amount'], 'from': _row['from'], 'to': _row['to'],
                                     'benef': 'نفس المشروع', 'state': _w.state})
            # (2) وارد من مشروع آخر — هذا المشروع هو المستفيد
            if ts.department_id:
                _seen = set()
                for _w in EW.search([('same_project', '=', False), ('state', 'in', _XW_STATES)]):
                    _bproj = _w.benef_project_id or _w.project_id
                    _bdept = _bproj.pms_department_id if _bproj else False
                    if not (_bdept and _bdept.id == ts.department_id.id):
                        continue
                    if not _overlaps(_w) or not _cover_days(_w):
                        continue
                    _row = _blue_row(_w, 'incoming')
                    incoming_rows.append(_row)
                    sum_in['count'] += 1; sum_in['amount'] += _row['amount']
                    _seen.add(_w.employee_id.id)
                    xrecords.append({'id': _w.id, 'emp': _w.employee_id.name or '—', 'kind': 'incoming',
                                     'amount': _row['amount'], 'from': _row['from'], 'to': _row['to'],
                                     'benef': (_w.home_department_id.name or '—'), 'state': _w.state})
                sum_in['workers'] = len(_seen)
        for _k in ('hours', 'amount'):
            sum_same[_k] = round(sum_same[_k], 2); sum_in[_k] = round(sum_in[_k], 2)

        # نقل العامل: مصدر النقل (منقول من) ووجهته (نقل إلى) من طلبات النقل المنفّذة
        xfer = {}
        if 'employee.shift.request' in env and ts.department_id:
            _reqs = env['employee.shift.request'].sudo().search(
                [('employee_id', 'in', ts.line_ids.mapped('employee_id').ids), ('state', '=', 'done')])
            for _r in _reqs:
                _td = _r.transfer_date
                if not (_td and ts.date_from <= _td <= ts.date_to):
                    continue
                _e = xfer.setdefault(_r.employee_id.id, {})
                if _r.new_department and _r.new_department.id == ts.department_id.id and _r.current_department:
                    _e['in'] = _r.current_department.name       # منقول من
                if _r.current_department and _r.current_department.id == ts.department_id.id and _r.new_department:
                    _e['out'] = _r.new_department.name           # نقل إلى
        workers = []
        tot_bio = tot_man = 0
        has_src = 'source' in env['care.timesheet.day']._fields if 'care.timesheet.day' in env else False
        for ln in ts.line_ids.sorted(lambda l: l.employee_id.name or ''):
            daymap = {}
            bio = man = 0
            _wf = ln.project_window_from
            _wt = ln.project_window_to
            for d in ln.day_ids:
                dsrc = getattr(d, 'source', '') if has_src else ''
                is_man = (dsrc == 'manual')
                if dsrc == 'bio':
                    bio += 1
                elif is_man:
                    man += 1
                _xf = ''
                if (d.status or '') == 'X':
                    if _wf and d.date < _wf:
                        _xf = 'in'
                    elif _wt and d.date > _wt:
                        _xf = 'out'
                daymap[str(d.date)] = {'id': d.id, 'status': d.status or '',
                                       'weekend': bool(getattr(d, 'is_weekend', False)),
                                       'manual': bool(is_man),
                                       'edited': bool(getattr(d, 'edited', False)),
                                       'hours': round(getattr(d, 'work_hours', 0.0) or 0.0, 2),
                                       'xw': None,
                                       'xfer': _xf}
            tot_bio += bio
            tot_man += man
            days = [daymap.get(ds, {'id': 0, 'status': '', 'weekend': False, 'manual': False, 'edited': False, 'hours': 0, 'xw': None, 'xfer': ''}) for ds in dates]
            # علامة ✈️: أيام غياب بعد انتهاء إجازة دون تسجيل عودة (حتى أوّل يوم حضور)
            _seen_lv = False
            for _dd in days:
                _s = _dd.get('status') or ''
                if _s in ('L', 'S'):
                    _seen_lv = True; _dd['plane'] = False
                elif _s in ('P', 'T', 'E'):
                    _seen_lv = False; _dd['plane'] = False
                elif _s == 'A' and _seen_lv:
                    _dd['plane'] = True
                else:
                    _dd['plane'] = False
            _xw = xfer.get(ln.employee_id.id, {})
            workers.append({'line_id': ln.id, 'empId': ln.employee_id.id, 'name': ln.employee_id.name or '—',
                            'badge': ln.badge or '', 'approved': ln.approved_days or 0, 'days': days,
                            'bio': bio, 'manual': man, 'std': round(getattr(ln, 'std_hours', 8.0) or 8.0, 1),
                            'xfer_in': _xw.get('in', ''), 'xfer_out': _xw.get('out', ''),
                            'present': getattr(ln, 'present_days', 0) or 0,
                            'absent': getattr(ln, 'absent_days', 0) or 0,
                            'leave': getattr(ln, 'leave_days', 0) or 0,
                            'sick': getattr(ln, 'sick_days', 0) or 0,
                            'holiday': getattr(ln, 'holiday_days', 0) or 0,
                            'off': getattr(ln, 'off_days', 0) or 0,
                            'out': getattr(ln, 'out_days', 0) or 0,
                            'hadd': bool((getattr(ln, 'hours_add_amount', 0.0) or 0.0) > 0),
                            'hded': bool((getattr(ln, 'hours_ded_amount', 0.0) or 0.0) > 0),
                            'plane': any(dd.get('plane') for dd in days),
                            'salary': getattr(ln, 'salary_days', 0) or 0,
                            'is_new': bool(getattr(ln, 'is_newly_added', False)),
                            'xw_ids': [], 'extra_hours': 0,
                            'extra_rows': same_rows_by_emp.get(ln.employee_id.id, [])})
        can_bio = hasattr(ts, 'button_refresh_from_bio')
        # ===== صفوف البدلاء تحت العامل الغائب (معاينة فورية حتى قبل الاعتماد) =====
        # يظهر صفّ لكل طلب بديل: أيام البدل مظلَّلة بلون، وبقية الأيام مُعتَّمة (خارج التغطية).
        sub_total = 0
        if 'care.worker.substitution' in env:
            SBm = env['care.worker.substitution'].sudo()
            # معاينة فقط لما لم يُطبَّق بعد (draft/submitted/approved) — المُطبَّق «applied»
            # يُنشئ صفّ بديل حقيقيًّا (B) فيظهر كصفّ عامل عادي، فلا نُكرّره كمعاينة.
            subs = SBm.search(['&', ('state', 'not in', ('rejected', 'applied')), '|',
                               ('timesheet_id', '=', ts.id),
                               '&', '&', ('project_id', '=', ts.project_id.id),
                               ('date_from', '<=', ts.date_to), ('date_to', '>=', ts.date_from)])
            _rlbl = dict(SBm._fields['price_rule']._description_selection(env))
            _slbl = dict(SBm._fields['state']._description_selection(env))
            sub_by_emp = {}
            for s in subs:
                cov, d0 = set(), s.date_from
                while d0 and s.date_to and d0 <= s.date_to:
                    cov.add(str(d0)); d0 = d0 + _dt.timedelta(days=1)
                sub_by_emp.setdefault(s.absent_employee_id.id, []).append({
                    'sub_id': s.id, 'name': s.substitute_employee_id.name or '—',
                    'badge': s.substitute_employee_id.barcode or '',
                    'state': s.state, 'state_lbl': _slbl.get(s.state, s.state),
                    'rule_lbl': _rlbl.get(s.price_rule, ''), 'ref': s.name or '',
                    'cost': round(s.total_cost or 0.0, 3), 'day_count': s.day_count or 0,
                    'days': [{'date': ds, 'cover': ds in cov} for ds in dates]})
            for w in workers:
                w['sub_rows_x'] = sub_by_emp.get(w['empId'], [])
            sub_total = len(subs)
        # كشف الإضافي المنفصل الموجود لنفس المشروع/الفترة
        xts_id = 0
        if 'care.extra.timesheet' in env and ts.department_id:
            _XT = env['care.extra.timesheet'].sudo().search(
                [('department_id', '=', ts.department_id.id),
                 ('period_from', '<=', ts.date_to), ('period_to', '>=', ts.date_from)], limit=1)
            xts_id = _XT.id if _XT else 0
        for _k in ('hours', 'amount'):
            sum_same[_k] = round(sum_same[_k], 2); sum_in[_k] = round(sum_in[_k], 2)
        # معلومات القطع والترحيل (إن كانت إدارة الكشف بسياسة «قطع ولقطة»)
        _cut = {}
        try:
            dept = ts.department_id
            if (dept and getattr(dept, 'ts_cutoff_policy', 'end') == 'cut'
                    and ts.date_from and 'care.payroll.cutoff' in env):
                import calendar as _cal2
                comp = getattr(ts, 'company_id', False) or env.company
                cday = env['care.payroll.cutoff'].sudo().get_cutoff_day(
                    ts.date_from.year, ts.date_from.month, comp)
                dim = _cal2.monthrange(ts.date_from.year, ts.date_from.month)[1]
                if cday < dim:
                    snapped = 0
                    if 'care.payroll.snapshot' in env:
                        snapped = env['care.payroll.snapshot'].sudo().search_count([
                            ('year', '=', ts.date_from.year), ('month', '=', ts.date_from.month),
                            ('department_id', '=', dept.id)])
                    _cut = {'day': cday, 'dim': dim, 'snapped': bool(snapped),
                            'label': ('مدفوع على لقطة يوم %s — استمرّ في الإدخال؛ '
                                      'فروق أيام الذيل تُرحَّل تلقائيًّا للشهر التالي.' % cday)
                            if snapped else
                            ('إدارة «قطع ولقطة» · يوم القطع %s — تُؤخذ اللقطة عند ذلك اليوم.' % cday)}
        except Exception:
            _cut = {}
        return {'ok': True, 'dates': dates, 'states': states, 'workers': workers,
                'state': ts.state, 'can_edit': ts.state != 'approved', 'can_bio': can_bio,
                'can_reset': ts.state == 'submit', 'has_sub': 'care.worker.substitution' in env,
                'sub_total': sub_total,
                'totals': {'bio': tot_bio, 'manual': tot_man},
                'merged': bool(kw.get('merged')), 'cutoff': _cut,
                'extra_summary': {'same': sum_same, 'incoming': sum_in, 'records': xrecords[:40]},
                'incoming': [], 'incoming_rows': incoming_rows, 'xts_id': xts_id,
                'name': ts.display_name, 'from': str(ts.date_from or ''), 'to': str(ts.date_to or '')}

    # تعديل ساعات سجلّ عمل إضافي (care.extra.work) من داخل الشبكة
    @http.route(['/my/pm/x/ts/<int:tid>/extra-hours'], type='json', auth='user', website=False)
    def pm_x_ts_extra_hours(self, tid=None, xwid=None, hours=None, **kw):
        env = request.env
        if 'care.timesheet' not in env or 'care.extra.work' not in env:
            return {'ok': False, 'error': 'غير مُفعّل'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        w = env['care.extra.work'].sudo().browse(int(xwid or 0)).exists()
        if not (w and self._x_rec_allowed(w)):
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            h = float(hours)
            if h < 0:
                raise ValueError()
        except Exception:
            return {'ok': False, 'error': 'قيمة ساعات غير صالحة'}
        try:
            w.write({'est_hours': h})
            # مزامنة بند كشف الإضافي المنفصل إن وُجد لنفس الفترة
            if w.comp_type == 'hourly' and 'care.extra.timesheet.line' in env:
                _ln = env['care.extra.timesheet.line'].sudo().search([
                    ('extra_work_id', '=', w.id),
                    ('timesheet_id.state', '!=', 'approved'),
                    ('timesheet_id.period_from', '<=', ts.date_to),
                    ('timesheet_id.period_to', '>=', ts.date_from)], limit=1)
                if _ln:
                    _ln.write({'hours': h})
            return {'ok': True, 'hours': round(w.est_hours or 0.0, 1),
                    'amount': round(w.est_cost or 0.0, 3), 'msg': 'تم ضبط ساعات الإضافي'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # تعديل حالة يوم لعامل وارد من مشروع آخر (تُخزَّن في سطر كشف الإضافي — لا تمسّ شبكة الراتب العادية)
    @http.route(['/my/pm/x/ts/<int:tid>/extra-day'], type='json', auth='user', website=False)
    def pm_x_ts_extra_day(self, tid=None, xwid=None, date=None, status=None, **kw):
        env = request.env
        if 'care.timesheet' not in env or 'care.extra.work' not in env \
                or 'care.extra.timesheet' not in env:
            return {'ok': False, 'error': 'غير مُفعّل'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يمكن التعديل'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        w = env['care.extra.work'].sudo().browse(int(xwid or 0)).exists()
        if not (w and self._x_rec_allowed(w)):
            return {'ok': False, 'error': 'غير مصرّح'}
        # التحقّق من رمز الحالة مقابل تعداد يوم التايم شيت (يُسمح بالفراغ للمسح)
        _sel = dict(env['care.timesheet.day']._fields['status'].selection) if 'care.timesheet.day' in env else {}
        st = (status or '').strip()
        if st and st not in _sel:
            return {'ok': False, 'error': 'حالة غير صالحة'}
        # التأكّد أنّ التاريخ ضمن فترة الكشف
        try:
            import datetime as _dt2
            _d = _dt2.date.fromisoformat(str(date))
        except Exception:
            return {'ok': False, 'error': 'تاريخ غير صالح'}
        if not (ts.date_from and ts.date_to and ts.date_from <= _d <= ts.date_to):
            return {'ok': False, 'error': 'التاريخ خارج فترة الكشف'}
        try:
            proj = ts.project_id if 'project_id' in ts._fields else False
            sheet = env['care.extra.timesheet'].sudo()._portal_sheet_for(
                proj, ts.date_from, ts.date_to, create=True)
            if not sheet:
                return {'ok': False, 'error': 'تعذّر تحديد كشف الإضافي (لا مشروع)'}
            line = sheet._line_for_work(w, create=True)
            if not line:
                return {'ok': False, 'error': 'تعذّر إنشاء سطر العامل الوارد'}
            line.set_day(str(date), st)
            return {'ok': True, 'status': st, 'date': str(date), 'msg': 'تم حفظ حالة اليوم'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # تعديل حالة يوم في صفّ الإضافي الأزرق (care.extra.work.day) — بصمة مشتركة قابلة للتعديل اليدوي
    @http.route(['/my/pm/x/ts/<int:tid>/xw-day'], type='json', auth='user', website=False)
    def pm_x_ts_xw_day(self, tid=None, xwid=None, date=None, status=None, **kw):
        env = request.env
        if 'care.timesheet' not in env or 'care.extra.work.day' not in env:
            return {'ok': False, 'error': 'غير مُفعّل'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يمكن التعديل'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        w = env['care.extra.work'].sudo().browse(int(xwid or 0)).exists()
        if not (w and self._x_rec_allowed(w)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _sel = dict(env['care.extra.work.day']._fields['status'].selection)
        st = (status or '').strip()
        if st not in _sel:
            return {'ok': False, 'error': 'حالة غير صالحة'}
        try:
            import datetime as _dt3
            _d = _dt3.date.fromisoformat(str(date))
        except Exception:
            return {'ok': False, 'error': 'تاريخ غير صالح'}
        if not (ts.date_from and ts.date_to and ts.date_from <= _d <= ts.date_to):
            return {'ok': False, 'error': 'التاريخ خارج فترة الكشف'}
        try:
            w._ts_sync_days(ts)
            Day = env['care.extra.work.day'].sudo()
            day = Day.search([('extra_work_id', '=', w.id), ('date', '=', _d)], limit=1)
            if day:
                day.set_status(st)
            else:
                day = Day.create({'extra_work_id': w.id, 'date': _d, 'day_num': _d.day,
                                  'status': st, 'edited': True, 'source': 'manual'})
            return {'ok': True, 'status': st, 'date': str(date),
                    'attended': w.ts_attended_days or 0, 'scheduled': w.ts_scheduled_days or 0,
                    'amount': round(w._payable_amount(), 3), 'msg': 'تم الحفظ'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # تحديد ساعات العمل (±) لأيام صفّ الإضافي الأزرق → تُحتسب زيادة/نقصًا في مبلغ الإضافي
    @http.route(['/my/pm/x/ts/<int:tid>/xw-hours'], type='json', auth='user', website=False)
    def pm_x_ts_xw_hours(self, tid=None, xwid=None, dates=None, hours=None, **kw):
        env = request.env
        if 'care.timesheet' not in env or 'care.extra.work.day' not in env:
            return {'ok': False, 'error': 'غير مُفعّل'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يمكن التعديل'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        w = env['care.extra.work'].sudo().browse(int(xwid or 0)).exists()
        if not (w and self._x_rec_allowed(w)):
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            hv = float(hours)
            if hv < 0 or hv > 24:
                return {'ok': False, 'error': 'ساعات غير صالحة'}
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'ساعات غير صالحة'}
        dlist = [str(x) for x in (dates or []) if x]
        if not dlist:
            return {'ok': False, 'error': 'لم تُحدَّد أيام'}
        try:
            w._ts_sync_days(ts)
            Day = env['care.extra.work.day'].sudo()
            days = Day.search([('extra_work_id', '=', w.id), ('date', 'in', dlist),
                               ('status', 'in', ('P', 'T', 'E'))])
            days.write({'work_hours': hv})
            return {'ok': True, 'count': len(days), 'hours': hv,
                    'amount': round(w._payable_amount(), 3),
                    'hours_adj': round(w._ts_hours_adjustment(), 3),
                    'msg': 'تم ضبط الساعات على %d يوم' % len(days)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ملف مصغّر للعامل داخل سياق الكشف (حضور الكشف + راتب + إضافي + حالات مهمّة)
    @http.route(['/my/pm/x/ts/<int:tid>/emp/<int:eid>'], type='json', auth='user', website=False)
    def pm_x_ts_emp_mini(self, tid=None, eid=None, **kw):
        env = request.env
        if 'care.timesheet' not in env:
            return {'ok': False, 'error': 'غير متاح'}
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists()
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        e = env['hr.employee'].sudo().browse(int(eid or 0)).exists()
        if not e:
            return {'ok': False, 'error': 'عامل غير موجود'}
        ln = ts.line_ids.filtered(lambda l: l.employee_id.id == e.id)[:1]
        _g = lambda f: (getattr(e, f, None) if f in e._fields else None)

        def _gs(f):
            return str(_g(f)) if _g(f) else None
        # حضور هذا الكشف
        att = {}
        if ln:
            bio = len(ln.day_ids.filtered(lambda d: getattr(d, 'source', '') == 'bio'))
            man = len(ln.day_ids.filtered(lambda d: getattr(d, 'source', '') == 'manual'))
            att = {'present': ln.present_days or 0, 'absent': ln.absent_days or 0,
                   'leave': ln.leave_days or 0, 'off': ln.off_days or 0,
                   'holiday': ln.holiday_days or 0, 'out': ln.out_days or 0,
                   'sick': getattr(ln, 'sick_days', 0) or 0,
                   'salary': ln.salary_days or 0, 'approved': ln.approved_days or 0,
                   'bio': bio, 'manual': man}
        hours = {'std': round(getattr(ln, 'std_hours', 8.0) or 8.0, 1) if ln else 8.0,
                 'add': round(getattr(ln, 'hours_add_amount', 0.0) or 0.0, 3) if ln else 0.0,
                 'ded': round(getattr(ln, 'hours_ded_amount', 0.0) or 0.0, 3) if ln else 0.0}
        # الإضافي للعامل خلال الفترة (نفس المشروع + وارد)
        ex = {'hours': 0.0, 'amount': 0.0, 'same': 0, 'incoming': 0}
        if 'care.extra.work' in env:
            for w in env['care.extra.work'].sudo().search([
                    ('employee_id', '=', e.id),
                    ('state', 'in', ('active', 'paused', 'hr_approved', 'submit', 'submitted', 'to_approve'))]):
                if not (w.duration_type == 'open' or not (w.date_from and w.date_to)
                        or (w.date_from <= ts.date_to and w.date_to >= ts.date_from)):
                    continue
                ex['hours'] += (w.est_hours or 0.0); ex['amount'] += (w.est_cost or 0.0)
                if w.same_project:
                    ex['same'] += 1
                else:
                    ex['incoming'] += 1
        ex['hours'] = round(ex['hours'], 1); ex['amount'] = round(ex['amount'], 3)
        # الراتب
        wage = 0.0
        try:
            ct = env['hr.contract'].sudo().search(
                [('employee_id', '=', e.id), ('state', 'in', ('open', 'draft'))],
                order='date_start desc', limit=1)
            wage = ct.wage or 0.0
            if not wage and 'job_grade_id' in e._fields and e.job_grade_id:
                wage = getattr(e.job_grade_id, 'base_wage', 0.0) or 0.0
        except Exception:
            wage = 0.0
        # الحالة
        on_leave = False
        if 'hr.leave' in env:
            on_leave = bool(env['hr.leave'].sudo().search_count([
                ('employee_id', '=', e.id), ('state', '=', 'validate'),
                ('date_from', '<=', fields.Datetime.now()), ('date_to', '>=', fields.Datetime.now())]))
        status = ['info', 'في إجازة'] if on_leave else (['ok', 'نشط'] if e.active else ['mut', 'غير نشط'])
        resid = _gs('residency_expire_date') or _gs('residency_end_date') or _gs('residency_expiry')
        return {'ok': True, 'name': e.name, 'badge': _g('barcode') or '',
                'job': _g('job_title') or (e.job_id.name if e.job_id else '—'),
                'dept': e.department_id.name or '—', 'status': status,
                'photo': bool(e.image_128), 'att': att, 'hours': hours, 'extra': ex,
                'wage': round(wage, 3) if wage else 0.0,
                'residency_expiry': resid or '—',
                'work_permit_expiry': _gs('work_permit_expiration_date') or '—',
                'leave_balance': ('%g' % (_g('leave_remaining_total') or 0)) if ('leave_remaining_total' in e._fields) else '—',
                'mobile': _g('mobile_phone') or _g('work_phone') or '—'}

    # جلب/تحديث البصمة (غير متلف — يُحدّث أيام bio فقط ويبقي اليدوي) + تحديد متعدّد
    @http.route(['/my/pm/x/ts/<int:tid>/refresh-bio'], type='json', auth='user', website=False)
    def pm_x_ts_refresh_bio(self, tid=None, **kw):
        env = request.env
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يُحدَّث'}
        if not hasattr(ts, 'button_refresh_from_bio'):
            return {'ok': False, 'error': 'الشبكة اليومية غير مُفعّلة'}
        try:
            n = ts.button_refresh_from_bio() or 0
            return {'ok': True, 'updated': n, 'msg': 'تم جلب البصمة — %s يوم مُحدَّث' % n}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/ts/<int:tid>/bulk-status'], type='json', auth='user', website=False)
    def pm_x_ts_bulk_status(self, tid=None, day_ids=None, status=None, **kw):
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يُعدَّل'}
        ids = [int(x) for x in (day_ids or []) if x]
        if not ids or not status:
            return {'ok': False, 'error': 'حدّد خلايا وحالة'}
        days = env['care.timesheet.day'].sudo().browse(ids).exists()
        if days.filtered(lambda d: d.line_id.timesheet_id.id != ts.id):
            return {'ok': False, 'error': 'خلايا خارج الكشف'}
        done = 0
        for d in days:
            if d.status == 'X':
                continue
            try:
                d.set_status(status)
                done += 1
            except Exception:
                pass
        _stats = [self._ts_line_stats(l) for l in days.mapped('line_id')]
        return {'ok': True, 'count': done, 'status': status, 'stats': _stats, 'msg': 'تم ضبط %s خلية' % done}

    @http.route(['/my/pm/x/ts/<int:tid>/bulk-hours'], type='json', auth='user', website=False)
    def pm_x_ts_bulk_hours(self, tid=None, day_ids=None, hours=None, **kw):
        """ضبط ساعات العمل الفعلية لخلايا محدّدة — الفرق عن القياسية (8) يُحتسب
        زيادة/نقصان في الراتب."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يُعدَّل'}
        try:
            h = float(hours)
        except Exception:
            return {'ok': False, 'error': 'عدد ساعات غير صالح'}
        ids = [int(x) for x in (day_ids or []) if x]
        days = env['care.timesheet.day'].sudo().browse(ids).exists().filtered(
            lambda d: d.line_id.timesheet_id.id == ts.id and d.status in ('P', 'T', 'E'))
        days.write({'work_hours': h, 'edited': True})
        # ملخّص التعديل للخطوط المتأثّرة
        lines = days.mapped('line_id')
        add = sum(lines.mapped('hours_add_amount'))
        ded = sum(lines.mapped('hours_ded_amount'))
        return {'ok': True, 'count': len(days), 'hours': h,
                'stats': [self._ts_line_stats(l) for l in lines],
                'msg': 'ضُبطت %s ساعة لـ%d خلية (زيادة %.3f / نقصان %.3f)' % (h, len(days), add, ded)}

    @http.route(['/my/pm/x/ts/day/<int:day_id>'], type='json', auth='user', website=False)
    def pm_x_ts_day(self, day_id=None, status=None, **kw):
        env = request.env
        day = env['care.timesheet.day'].sudo().browse(int(day_id or 0)).exists() if 'care.timesheet.day' in env else None
        if not day:
            return {'ok': False, 'error': 'يوم غير موجود'}
        ts = day.line_id.timesheet_id
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        if ts.state == 'approved':
            return {'ok': False, 'error': 'الكشف معتمد — لا يُعدَّل'}
        if day.status == 'X':
            return {'ok': False, 'error': 'يوم خارج المشروع لا يُعدَّل من هنا'}
        try:
            day.set_status(status)
            return {'ok': True, 'status': day.status, 'stats': [self._ts_line_stats(day.line_id)]}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/ts/<int:tid>/approve'], type='json', auth='user', website=False)
    def pm_x_ts_approve(self, tid=None, **kw):
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'submit')
        if _g:
            return _g
        try:
            if hasattr(ts, 'button_approve_days'):
                ts.button_approve_days()
            elif hasattr(ts, 'button_approve'):
                ts.button_approve()
            else:
                ts.state = 'approved'
            return {'ok': True, 'msg': 'تم اعتماد الكشف', 'state': ts.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/ts/<int:tid>/reset'], type='json', auth='user', website=False)
    def pm_x_ts_reset(self, tid=None, **kw):
        """إعادة الكشف للمسودة من شبكة البوابة — متاحة فقط ما دام «بانتظار الاعتماد»
        (لم يُعتمد من الموارد البشرية). تفكّ أي اعتماد جزئي وتُصفّر الأيام المعتمدة والتواقيع."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        if ts.state != 'submit':
            return {'ok': False, 'error': 'الإعادة للمسودة متاحة فقط قبل الاعتماد (كشف بانتظار الاعتماد)'}
        try:
            if hasattr(ts, 'button_reset_draft'):
                ts.button_reset_draft()
            else:
                ts.state = 'draft'
            return {'ok': True, 'msg': 'أُعيد الكشف إلى المسودة', 'state': ts.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/ts/<int:tid>/sub-meta'], type='json', auth='user', website=False)
    def pm_x_ts_sub_meta(self, tid=None, **kw):
        """بيانات ديالوج «إرسال بديل عن الغائب»: عمّال الكشف (للغائب) + كل الموظّفين (للبديل) + قواعد التسعير."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        SB = env.get('care.worker.substitution')
        if SB is None:
            return {'ok': False, 'error': 'نظام البديل غير مُفعّل'}
        # كل موظّفي الشركة (غير مُفلتَرين على مشروع) — للبحث بالاسم ع/EN والبادج
        allemp = env['hr.employee'].sudo().search([], order='name', limit=20000)
        rules = SB._fields['price_rule']._description_selection(env)
        absent = [{'id': ln.employee_id.id, 'name': ln.employee_id.name,
                   'badge': ln.employee_id.barcode or '',
                   'en': ln.employee_id.english_name or ''}
                  for ln in ts.line_ids if ln.employee_id]
        return {'ok': True, 'absent': absent,
                'substitutes': [{'id': e.id, 'name': e.name, 'badge': e.barcode or '',
                                 'en': e.english_name or ''} for e in allemp],
                'rules': [{'id': k, 'name': v} for k, v in rules],
                'from': str(ts.date_from or ''), 'to': str(ts.date_to or '')}

    @http.route(['/my/pm/x/ts/<int:tid>/substitute'], type='json', auth='user', website=False)
    def pm_x_ts_substitute(self, tid=None, absent_employee_id=None, substitute_employee_id=None,
                           date_from=None, date_to=None, price_rule=None, reason=None, **kw):
        """إنشاء وتقديم طلب بديل عن غائب من شبكة البوابة (يُشعر مسؤول/مدير الموديول عبر action_submit)."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('timesheet', 'write')
        if _g:
            return _g
        SB = env.get('care.worker.substitution')
        if SB is None:
            return {'ok': False, 'error': 'نظام البديل غير مُفعّل'}
        if not (absent_employee_id and substitute_employee_id):
            return {'ok': False, 'error': 'اختر العامل الغائب والعامل البديل'}
        if int(absent_employee_id) == int(substitute_employee_id):
            return {'ok': False, 'error': 'لا يمكن أن يكون البديل هو الغائب نفسه'}
        if int(absent_employee_id) not in ts.line_ids.employee_id.ids:
            return {'ok': False, 'error': 'العامل الغائب ليس ضمن كشف هذا المشروع'}
        try:
            sub = SB.sudo().create({
                'project_id': ts.project_id.id,
                'timesheet_id': ts.id,
                'absent_employee_id': int(absent_employee_id),
                'substitute_employee_id': int(substitute_employee_id),
                'date_from': date_from or str(ts.date_from),
                'date_to': date_to or date_from or str(ts.date_to),
                'reason': reason or '',
                'price_rule': price_rule or 'substitute',
            })
            sub.action_submit()
            return {'ok': True, 'id': sub.id, 'name': sub.display_name, 'msg': 'تم تقديم طلب البديل عن الغائب'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # طباعة شبكة التايم شيت احترافيًّا (HTML بهوية CARE، أفقي)
    _X_TS_HEX = {'P': '#16a34a', 'O': '#94a3b8', 'A': '#dc2626', 'L': '#2563eb', 'H': '#7c3aed',
                 'S': '#d97706', 'X': '#1f2937', 'T': '#d97706', 'E': '#0d9488'}

    @http.route(['/my/pm/x/ts/<int:tid>/print-attendance',
                 '/my/pm/x/ts/<int:tid>/print-attendance/<string:lang>'],
                type='http', auth='user', website=False)
    def pm_x_ts_print_attendance(self, tid=None, lang='ar', **kw):
        """طباعة نموذج كشف الحضور الرسمي (report_attendance_sheet) باسم عربي/إنجليزي."""
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return request.not_found()
        if self._x_deleg_check('timesheet', 'print'):
            return request.make_response('غير مُصرّح بالطباعة', status=403)
        rep = env.ref('care_pms_timesheet.action_report_attendance_sheet', raise_if_not_found=False)
        if not rep:
            return request.not_found()
        nl = 'en' if (lang or 'ar').lower().startswith('en') else 'ar'
        try:
            pdf, _ct = rep.sudo().with_context(rpt_name_lang=nl)._render_qweb_pdf(rep.report_name, [ts.id])
        except Exception as e:
            return request.make_response('تعذّر توليد التقرير: %s' % e, status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="attendance_%s_%s.pdf"' % (ts.id, nl))])

    @http.route(['/my/pm/x/ts/<int:tid>/print-grid'], type='http', auth='user', website=False)
    def pm_x_ts_print_grid(self, tid=None, **kw):
        env = request.env
        ts = env['care.timesheet'].sudo().browse(int(tid or 0)).exists() if 'care.timesheet' in env else None
        if not (ts and self._x_rec_allowed(ts)):
            return request.not_found()
        if self._x_deleg_check('timesheet', 'print'):
            return request.make_response('غير مُصرّح بالطباعة', status=403)
        try:
            dates = [str(d) for d in ts._dates_in_period()] if hasattr(ts, '_dates_in_period') else []
        except Exception:
            dates = []
        company = (self._pm_projects()[:1].company_id or env.company)
        sel = dict(env['care.timesheet.day']._fields['status'].selection) if 'care.timesheet.day' in env else {}
        # رؤوس الأيام
        head = ''.join(u'<th>%s</th>' % d[8:] for d in dates)
        body = ''
        any_edited = False
        for ln in ts.line_ids.sorted(lambda l: l.employee_id.name or ''):
            daymap = {str(d.date): (d.status or '', bool(getattr(d, 'edited', False))) for d in ln.day_ids}
            cells = ''
            for ds in dates:
                st, ed = daymap.get(ds, ('', False))
                bg = self._X_TS_HEX.get(st, '#ffffff')
                fg = '#fff' if st else '#000'
                # علامة «عُدّل يدويًا» (✎) لتدقيق الكشف المطبوع
                mk = u'<sup style="font-size:7px;opacity:.9" title="عُدّل يدويًا">✎</sup>' if ed else ''
                if ed:
                    any_edited = True
                cells += u'<td style="background:%s;color:%s">%s%s</td>' % (bg, fg, st, mk)
            name = (ln.employee_id.name or '—')
            badge = (ln.badge or ln.employee_id.barcode or '')
            body += u'<tr><td class="nm">%s<div class="bc">%s</div></td>%s<td class="ap">%s</td></tr>' % (
                name, badge, cells, (ln.approved_days or 0))
        legend = ''.join(u'<span><i style="background:%s"></i>%s</span>' % (self._X_TS_HEX.get(c, '#ccc'), (l or '').split('/')[0])
                         for c, l in sel.items())
        if any_edited:
            legend += u'<span style="font-weight:700;color:#b45309"><sup style="font-size:9px">✎</sup> = عُدّلت يدويًا (غير البصمة)</span>'
        logo = '/web/image/res.company/%s/logo' % company.id
        html = u"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;800&display=swap" rel="stylesheet">
<title>تايم شيت %(name)s</title><style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Tajawal',Arial,sans-serif;background:#eef1f5;padding:12px;color:#1a2332}
.sheet{background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.1);max-width:1400px;margin:0 auto}
.hd{background:linear-gradient(135deg,#0a1f44,#12306e);color:#fff;padding:16px 22px;display:flex;justify-content:space-between;align-items:center}
.hd .lg{width:60px;height:60px;background:#fff;border-radius:10px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.hd .lg img{max-width:100%%;max-height:100%%}.hd h1{font-size:17px}.hd .sub{font-size:12px;color:#cfe0f2;margin-top:3px}
.legend{display:flex;gap:14px;flex-wrap:wrap;padding:10px 22px;font-size:11px;border-bottom:1px solid #eceff3}
.legend span{display:flex;align-items:center;gap:5px}.legend i{width:13px;height:13px;border-radius:3px;display:inline-block}
table{width:100%%;border-collapse:collapse;font-size:10px}
th,td{border:1px solid #d7dde6;text-align:center;padding:3px 2px}
thead th{background:#0a1f44;color:#fff;position:sticky;top:0}
td.nm{text-align:start;font-weight:700;min-width:130px;padding:4px 8px;font-size:11px}
td.nm .bc{font-size:9px;color:#888;font-weight:400}td.ap{font-weight:800;color:#0d9488;background:#f3f6f9}
.pr{text-align:center;padding:10px;font-size:11px;color:#8a94a2;border-top:1px solid #eceff3}
.tb{position:fixed;top:12px;inset-inline-start:12px}.tb button{background:#0a1f44;color:#fff;border:0;border-radius:8px;padding:9px 16px;font-weight:700;cursor:pointer}
@media print{body{background:#fff;padding:0}.sheet{box-shadow:none;max-width:100%%}.tb{display:none}@page{size:A4 landscape;margin:8mm}}
</style></head><body>
<div class="tb"><button onclick="window.print()">🖨️ طباعة</button></div>
<div class="sheet">
 <div class="hd"><div style="display:flex;align-items:center;gap:14px"><div class="lg"><img src="%(logo)s" onerror="this.parentNode.textContent='CARE'"></div>
   <div><h1>كشف الدوام · Timesheet</h1><div class="sub">%(company)s · %(name)s</div></div></div>
   <div style="text-align:end;font-size:12px">%(frm)s → %(to)s</div></div>
 <div class="legend">%(legend)s</div>
 <table><thead><tr><th class="nm" style="text-align:start">العامل</th>%(head)s<th>معتمد</th></tr></thead><tbody>%(body)s</tbody></table>
 <div class="pr">%(company)s · طُبع في %(today)s</div>
</div></body></html>""" % {
            'name': ts.display_name or '', 'company': company.name or 'CARE', 'logo': logo,
            'frm': str(ts.date_from or ''), 'to': str(ts.date_to or ''),
            'legend': legend, 'head': head, 'body': body,
            'today': fields.Date.to_string(fields.Date.today()),
        }
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ============ العهدة النقدية: إجراءات الحالة + إضافة مصروف ============
    _X_PETTY_ACTS = {'request': 'action_request', 'approve': 'action_approve',
                     'disburse': 'action_disburse', 'settle': 'action_settle',
                     'close': 'action_return_close', 'reopen': 'action_reopen'}

    @http.route(['/my/pm/x/petty/<int:rid>/<string:act>'], type='json', auth='user', website=False)
    def pm_x_petty_act(self, rid=None, act=None, **kw):
        env = request.env
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        cash = env['care.pms.petty.cash'].sudo().browse(int(rid or 0)).exists() if 'care.pms.petty.cash' in env else None
        if not (cash and self._x_rec_allowed(cash)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if act == 'reject':
            try:
                cash.write({'state': 'draft'})
                if hasattr(cash, 'message_post'):
                    cash.message_post(body='↩️ أُعيد الطلب لمسودّة من بوابة المشاريع.')
                return {'ok': True, 'msg': 'أُعيد لمسودّة', 'state': cash.state}
            except Exception as e:
                return {'ok': False, 'error': _x_safe_error(e)}
        m = self._X_PETTY_ACTS.get(act)
        if not m or not hasattr(cash, m):
            return {'ok': False, 'error': 'إجراء غير مدعوم'}
        try:
            getattr(cash, m)()
            label = {'request': 'التقديم', 'approve': 'الاعتماد', 'disburse': 'الصرف', 'settle': 'التسوية',
                     'close': 'الإقفال', 'reopen': 'إعادة الفتح'}.get(act, 'الإجراء')
            return {'ok': True, 'msg': 'تم %s' % label, 'state': cash.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/petty/<int:rid>/expense'], type='json', auth='user', website=False)
    def pm_x_petty_expense(self, rid=None, name=None, amount=None, date=None, category_id=None, note=None,
                           invoice_number=None, partner_id=None, **kw):
        env = request.env
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        cash = env['care.pms.petty.cash'].sudo().browse(int(rid or 0)).exists() if 'care.pms.petty.cash' in env else None
        if not (cash and self._x_rec_allowed(cash)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if cash.state != 'disbursed':
            return {'ok': False, 'error': 'تُضاف المصاريف للعهدة المصروفة فقط'}
        if not name or not amount:
            return {'ok': False, 'error': 'أدخل الوصف والمبلغ'}
        try:
            vals = {'cash_id': cash.id, 'name': name, 'amount': float(amount),
                    'date': date or str(fields.Date.today())}
            if category_id:
                vals['category_id'] = int(category_id)
            if note:
                vals['note'] = note
            if invoice_number:
                vals['invoice_number'] = invoice_number
            if partner_id:
                vals['partner_id'] = int(partner_id)
            env['care.pms.petty.cash.expense'].sudo().create(vals)
            return {'ok': True, 'msg': 'أُضيف المصروف', 'spent': cash.spent, 'remaining': cash.remaining}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/petty/<int:rid>/expense/<int:eid>/<string:op>'], type='json', auth='user', website=False)
    def pm_x_petty_expense_edit(self, rid=None, eid=None, op=None, **kw):
        env = request.env
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        exp = env['care.pms.petty.cash.expense'].sudo().browse(int(eid or 0)).exists() if 'care.pms.petty.cash.expense' in env else None
        if not exp or exp.cash_id.id != int(rid or 0) or not self._x_rec_allowed(exp.cash_id):
            return {'ok': False, 'error': 'غير مصرّح'}
        # بنود التسوية تُعدَّل من شاشة التسوية فقط (وإلا أمكن تغيير مبلغ تسوية مُعتمَدة من هنا)
        if exp.settlement_id:
            return {'ok': False, 'error': 'بند تسوية — عدّله من شاشة التسوية'}
        if exp.cash_id.state != 'disbursed':
            return {'ok': False, 'error': 'العهدة المصروفة فقط تقبل التعديل'}
        try:
            if op == 'delete':
                cash = exp.cash_id
                exp.unlink()
                return {'ok': True, 'msg': 'حُذف المصروف', 'spent': cash.spent, 'remaining': cash.remaining}
            if op == 'edit':
                vals = {}
                for k in ('name', 'note', 'invoice_number'):
                    if kw.get(k):
                        vals[k] = kw[k]
                if kw.get('amount'):
                    vals['amount'] = float(kw['amount'])
                if kw.get('date'):
                    vals['date'] = kw['date']
                if kw.get('category_id'):
                    vals['category_id'] = int(kw['category_id'])
                if kw.get('partner_id'):
                    vals['partner_id'] = int(kw['partner_id'])
                exp.write(vals)
                return {'ok': True, 'msg': 'حُدِّث المصروف', 'spent': exp.cash_id.spent, 'remaining': exp.cash_id.remaining}
            return {'ok': False, 'error': 'عملية غير معروفة'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # تسويات العهدة
    _X_SETTLE_ACTS = {'submit': 'action_submit', 'approve': 'action_approve',
                      'reject': 'action_reject', 'reset': 'action_reset'}

    @http.route(['/my/pm/x/petty/<int:rid>/settlement/new'], type='json', auth='user', website=False)
    def pm_x_petty_settlement_new(self, rid=None, **kw):
        env = request.env
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        cash = env['care.pms.petty.cash'].sudo().browse(int(rid or 0)).exists() if 'care.pms.petty.cash' in env else None
        if not (cash and self._x_rec_allowed(cash)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if 'care.pms.petty.settlement' not in env:
            return {'ok': False, 'error': 'وحدة التسويات غير مثبّتة'}
        if cash.state != 'disbursed':
            return {'ok': False, 'error': 'التسوية تُنشأ للعهدة المصروفة فقط'}
        try:
            s = env['care.pms.petty.settlement'].sudo().create({'cash_id': cash.id})
            return {'ok': True, 'id': s.id, 'name': s.name, 'msg': 'أُنشئت تسوية %s' % (s.name or '')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/settlement/<int:sid>/<string:act>'], type='json', auth='user', website=False)
    def pm_x_settlement_act(self, sid=None, act=None, **kw):
        env = request.env
        s = env['care.pms.petty.settlement'].sudo().browse(int(sid or 0)).exists() if 'care.pms.petty.settlement' in env else None
        if not (s and self._x_rec_allowed(s.cash_id)):
            return {'ok': False, 'error': 'غير مصرّح'}
        m = self._X_SETTLE_ACTS.get(act)
        if not m or not hasattr(s, m):
            return {'ok': False, 'error': 'إجراء غير مدعوم'}
        try:
            getattr(s, m)()
            return {'ok': True, 'msg': 'تم', 'state': s.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    def _settle_rec(self, sid):
        env = request.env
        if 'care.pms.petty.settlement' not in env:
            return None
        s = env['care.pms.petty.settlement'].sudo().browse(int(sid or 0)).exists()
        return s if (s and self._x_rec_allowed(s.cash_id)) else None

    @http.route(['/my/pm/x/settlement/<int:sid>/detail'], type='json', auth='user', website=False)
    def pm_x_settlement_detail(self, sid=None, **kw):
        s = self._settle_rec(sid)
        if not s:
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            sel = dict(s._fields['state']._description_selection(request.env))
        except Exception:
            sel = {}
        lines = [{'id': e.id, 'name': e.name or '—', 'amount': e.amount or 0,
                  'date': str(e.date or ''), 'category': (e.category_id.name if getattr(e, 'category_id', False) else ''),
                  'invoice': getattr(e, 'invoice_number', '') or '',
                  'partner': (e.partner_id.name if getattr(e, 'partner_id', False) else ''),
                  'has_file': bool(getattr(e, 'attachment', False))} for e in s.expense_ids]
        return {'ok': True, 'id': s.id, 'name': s.name, 'state': s.state, 'state_label': sel.get(s.state, s.state),
                'date': str(getattr(s, 'date', '') or ''), 'total': getattr(s, 'amount_total', 0) or 0,
                'cash_remaining': getattr(s, 'cash_remaining', 0) or 0,
                'currency': (s.currency_id.name if getattr(s, 'currency_id', False) else 'KWD'),
                'note': getattr(s, 'note', '') or '', 'can_edit': s.state == 'draft',
                'can_submit': s.state == 'draft' and bool(s.expense_ids), 'can_approve': s.state == 'submitted',
                'lines': lines}

    @http.route(['/my/pm/x/settlement/<int:sid>/line'], type='json', auth='user', website=False)
    def pm_x_settlement_line(self, sid=None, name=None, amount=None, date=None, category_id=None,
                             note=None, invoice_number=None, partner_id=None, **kw):
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        s = self._settle_rec(sid)
        if not s:
            return {'ok': False, 'error': 'غير مصرّح'}
        if s.state != 'draft' or s.cash_id.state != 'disbursed':
            return {'ok': False, 'error': 'تُعدَّل بنود التسوية المسوّدة والعهدة المصروفة فقط'}
        if not name or not amount:
            return {'ok': False, 'error': 'أدخل البيان والمبلغ'}
        try:
            vals = {'settlement_id': s.id, 'name': name, 'amount': float(amount),
                    'date': date or str(fields.Date.today())}
            if category_id:
                vals['category_id'] = int(category_id)
            if note:
                vals['note'] = note
            if invoice_number:
                vals['invoice_number'] = invoice_number
            if partner_id:
                vals['partner_id'] = int(partner_id)
            request.env['care.pms.petty.cash.expense'].sudo().create(vals)
            return {'ok': True, 'msg': 'أُضيف البند', 'total': s.amount_total or 0}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/settlement/<int:sid>/line/<int:eid>/<string:op>'], type='json', auth='user', website=False)
    def pm_x_settlement_line_edit(self, sid=None, eid=None, op=None, **kw):
        _g = self._x_deleg_check('petty', 'write')
        if _g:
            return _g
        s = self._settle_rec(sid)
        if not s:
            return {'ok': False, 'error': 'غير مصرّح'}
        exp = request.env['care.pms.petty.cash.expense'].sudo().browse(int(eid or 0)).exists()
        if not exp or exp.settlement_id.id != s.id:
            return {'ok': False, 'error': 'بند غير موجود'}
        if s.state != 'draft' or s.cash_id.state != 'disbursed':
            return {'ok': False, 'error': 'التسوية المسوّدة والعهدة المصروفة فقط'}
        try:
            if op == 'delete':
                exp.unlink()
                return {'ok': True, 'msg': 'حُذف البند', 'total': s.amount_total or 0}
            if op == 'edit':
                vals = {}
                for k in ('name', 'note', 'invoice_number'):
                    if kw.get(k):
                        vals[k] = kw[k]
                if kw.get('amount'):
                    vals['amount'] = float(kw['amount'])
                if kw.get('date'):
                    vals['date'] = kw['date']
                if kw.get('category_id'):
                    vals['category_id'] = int(kw['category_id'])
                exp.write(vals)
                return {'ok': True, 'msg': 'حُدِّث البند', 'total': s.amount_total or 0}
            return {'ok': False, 'error': 'عملية غير معروفة'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/settlement/<int:sid>/print'], type='http', auth='user', website=False)
    def pm_x_settlement_print(self, sid=None, **kw):
        s = self._settle_rec(sid)
        if not s:
            return request.not_found()
        rep_name = None
        # 1) مسار action_print الرسمي إن وُجد
        try:
            if hasattr(s, 'action_print'):
                act = s.action_print()
                rep_name = act.get('report_name') if isinstance(act, dict) else None
        except Exception:
            rep_name = None
        # 2) تراجع: أي تقرير PDF على موديل التسوية مباشرة
        if not rep_name:
            rep = request.env['ir.actions.report'].sudo().search(
                [('model', '=', s._name), ('report_type', '=', 'qweb-pdf')], limit=1)
            rep_name = rep.report_name if rep else None
        if rep_name:
            try:
                pdf, _ct = request.env['ir.actions.report'].sudo()._render_qweb_pdf(rep_name, [s.id])
                return request.make_response(pdf, headers=[('Content-Type', 'application/pdf'),
                    ('Content-Disposition', 'inline; filename=settlement_%s.pdf' % sid)])
            except Exception as e:
                return request.make_response('تعذّرت الطباعة / Printing failed: %s' % (str(e)),
                                             headers=[('Content-Type', 'text/plain; charset=utf-8')])
        # 3) لا تقرير متاح → رسالة واضحة بدل 404
        return request.make_response('لا يوجد تقرير قابل للطباعة لهذه التسوية. / No printable report for this settlement.',
                                     headers=[('Content-Type', 'text/plain; charset=utf-8')])

    # طباعة سند العهدة (3 أنواع)
    @http.route(['/my/pm/x/petty/<int:rid>/voucher/<string:kind>'], type='http', auth='user', website=False)
    def pm_x_petty_voucher(self, rid=None, kind='cash', **kw):
        env = request.env
        cash = env['care.pms.petty.cash'].sudo().browse(int(rid or 0)).exists() if 'care.pms.petty.cash' in env else None
        if not (cash and self._x_rec_allowed(cash)):
            return request.not_found()
        xmlid = {'cash': 'care_pms.action_report_petty_cash',
                 'request': 'care_pms.action_report_petty_cash_request',
                 'summary': 'care_pms.action_report_petty_cash_summary'}.get(kind, 'care_pms.action_report_petty_cash')
        try:
            report = env.ref(xmlid).sudo()
            pdf, _ct = report._render_qweb_pdf(report.report_name, [cash.id])
            return request.make_response(pdf, headers=[('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'inline; filename=petty_%s_%s.pdf' % (kind, rid))])
        except Exception:
            return request.not_found()

    # ============ التوريدات: الاستلام (كامل/جزئي بالأصناف) ============
    @http.route(['/my/pm/x/supply/<int:rid>/receive'], type='json', auth='user', website=False)
    def pm_x_supply_receive(self, rid=None, receiver=None, **kw):
        """استلام كل المتبقّي دفعةً واحدة → ينشئ سند استلام (GRN) بالكميات المتبقّية."""
        env = request.env
        sup = env['care.pms.supply'].sudo().browse(int(rid or 0)).exists() if 'care.pms.supply' in env else None
        if not (sup and self._x_rec_allowed(sup)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('supplies', 'write')
        if _g:
            return _g
        if sup.state not in ('sent', 'partial'):
            return {'ok': False, 'error': 'يُستلَم فقط ما هو قيد النقل/استلام جزئي'}
        try:
            batch = [{'supply_line_id': l.id, 'qty': l.remaining_qty}
                     for l in sup.line_ids
                     if getattr(l, 'line_state', '') != 'rejected' and (l.remaining_qty or 0) > 0]
            if not batch:
                return {'ok': False, 'error': 'لا توجد كمية متبقّية للاستلام'}
            grn = sup.register_receipt(batch, receiver=receiver)
            return {'ok': True, 'msg': 'تم استلام كل المتبقّي · سند %s' % grn.name,
                    'state': sup.state, 'grn_id': grn.id, 'grn': grn.name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/supply/<int:rid>/process'], type='json', auth='user', website=False)
    def pm_x_supply_process(self, rid=None, receiver=None, note=None, delivery_ref=None, lines=None, **kw):
        """استلام على دفعات: الكميات المُدخلة تُسجَّل في سند استلام واحد (GRN)؛ الرفض يُعالَج مباشرةً."""
        env = request.env
        sup = env['care.pms.supply'].sudo().browse(int(rid or 0)).exists() if 'care.pms.supply' in env else None
        if not (sup and self._x_rec_allowed(sup)):
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('supplies', 'write')
        if _g:
            return _g
        if sup.state not in ('sent', 'partial'):
            return {'ok': False, 'error': 'يُعالَج فقط ما هو قيد النقل/استلام جزئي'}
        try:
            lmap = {str(l['lid']): l for l in (lines or []) if l.get('lid')}
            batch = []
            for line in sup.line_ids:
                info = lmap.get(str(line.id))
                if not info:
                    continue
                act = info.get('action') or 'receive'
                if act == 'reject':
                    if (getattr(line, 'received_qty', 0) or 0) <= 0:
                        line.action_reject_line(info.get('reason') or '')
                    continue
                qty = info.get('qty')
                q = line.remaining_qty if qty in (None, '') else float(qty)
                if q and q > 0:
                    batch.append({'supply_line_id': line.id, 'qty': q})
            grn = None
            if batch:
                grn = sup.register_receipt(batch, receiver=receiver, note=note, delivery_ref=delivery_ref)
            elif not any((info.get('action') == 'reject') for info in (lines or [])):
                return {'ok': False, 'error': 'أدخل كمية استلام واحدة على الأقل'}
            return {'ok': True, 'state': sup.state,
                    'msg': ('تم تسجيل سند الاستلام %s' % grn.name) if grn else 'تمت معالجة الرفض',
                    'grn_id': grn.id if grn else 0, 'grn': grn.name if grn else ''}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/supply/<int:rid>/receipts'], type='json', auth='user', website=False)
    def pm_x_supply_receipts(self, rid=None, **kw):
        """قائمة سندات الاستلام (الدفعات) لتوريد — للعرض في التفاصيل."""
        env = request.env
        sup = env['care.pms.supply'].sudo().browse(int(rid or 0)).exists() if 'care.pms.supply' in env else None
        if not (sup and self._x_rec_allowed(sup)):
            return {'ok': False, 'error': 'غير مصرّح'}
        out = [{'id': g.id, 'name': g.name or '—', 'date': str(g.date or ''),
                'receiver': g.receiver_name or '', 'qty': round(g.qty_total or 0, 3),
                'state': g.state, 'delivery_ref': g.delivery_ref or ''}
               for g in sup.receipt_ids]
        return {'ok': True, 'receipts': out}

    # ============ صيانة المركبات: تسجيل صيانة/عطل على المركبة ============
    @http.route(['/my/pm/x/vehicle/<int:vid>/service'], type='json', auth='user', website=False)
    def pm_x_vehicle_service(self, vid=None, type=None, date=None, next_date=None,
                             amount=None, description=None, damage=None, **kw):
        env = request.env
        _g = self._x_deleg_check('vehicles', 'write')
        if _g:
            return _g
        veh = env['fleet.vehicle'].sudo().browse(int(vid or 0)).exists() if 'fleet.vehicle' in env else None
        if not (veh and self._x_rec_allowed(veh)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if not description:
            return {'ok': False, 'error': 'أدخل وصف الصيانة/العطل'}
        Svc = env['fleet.vehicle.log.services'].sudo()
        try:
            import datetime as _dt
            nd = next_date or str(fields.Date.today() + _dt.timedelta(days=180))
            desc = description + (('\nعطل: ' + damage) if damage else '')
            vals = {'vehicle_id': veh.id, 'type': type or 'maintenance',
                    'next_service_date': nd, 'description': desc,
                    'date': date or str(fields.Date.today())}
            if amount not in (None, ''):
                vals['amount'] = float(amount)
            if 'service_type_id' in Svc._fields and Svc._fields['service_type_id'].required:
                st = env['fleet.service.type'].sudo().search([], limit=1)
                if st:
                    vals['service_type_id'] = st.id
            rec = Svc.create(vals)
            return {'ok': True, 'msg': 'تم تسجيل الصيانة', 'id': rec.id}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/vehicle/<int:vid>/odometer'], type='json', auth='user', website=False)
    def pm_x_vehicle_odometer(self, vid=None, value=None, **kw):
        env = request.env
        _g = self._x_deleg_check('vehicles', 'write')
        if _g:
            return _g
        veh = env['fleet.vehicle'].sudo().browse(int(vid or 0)).exists() if 'fleet.vehicle' in env else None
        if not (veh and self._x_rec_allowed(veh)):
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            val = float(value or 0)
            if val <= 0:
                return {'ok': False, 'error': 'أدخل قراءة صحيحة'}
            if 'fleet.vehicle.odometer' in env:
                env['fleet.vehicle.odometer'].sudo().create({
                    'vehicle_id': veh.id, 'value': val, 'date': str(fields.Date.today())})
            else:
                veh.odometer = val
            return {'ok': True, 'msg': 'تم تحديث العدّاد', 'odometer': round(veh.odometer or val, 1)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/vehicle/drivers'], type='json', auth='user', website=False)
    def pm_x_vehicle_drivers(self, **kw):
        dep = self._pm_projects().mapped('pms_department_id').ids
        ws = []
        if dep:
            for w in request.env['hr.employee'].sudo().search(self._x_emp_dom(dep), order='name', limit=100000):
                ws.append([w.id, (w.name or '—') + ' — #' + (w.barcode or ''),
                           ' '.join(str(x) for x in [w.name, getattr(w, 'english_name', '') or '',
                                                      w.barcode or '', getattr(w, 'identification_id', '') or ''] if x)])
        return {'ok': True, 'workers': ws}

    @http.route(['/my/pm/x/vehicle/<int:vid>/driver'], type='json', auth='user', website=False)
    def pm_x_vehicle_driver(self, vid=None, employee_id=None, **kw):
        env = request.env
        _g = self._x_deleg_check('vehicles', 'write')
        if _g:
            return _g
        veh = env['fleet.vehicle'].sudo().browse(int(vid or 0)).exists() if 'fleet.vehicle' in env else None
        if not (veh and self._x_rec_allowed(veh)):
            return {'ok': False, 'error': 'غير مصرّح'}
        emp = env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not self._x_emp_allowed(emp, self._pm_projects().mapped('pms_department_id').ids):
            return {'ok': False, 'error': 'العامل خارج نطاقك'}
        try:
            done = False
            if 'driver_employee_id' in veh._fields:
                veh.driver_employee_id = emp.id
                done = True
            part = False
            for pf in ('address_home_id', 'work_contact_id'):
                if pf in emp._fields and getattr(emp, pf, False):
                    part = getattr(emp, pf)
                    break
            if not part and emp.user_id and emp.user_id.partner_id:
                part = emp.user_id.partner_id
            if part and 'driver_id' in veh._fields:
                veh.driver_id = part.id
                done = True
            if not done:
                return {'ok': False, 'error': 'تعذّر ربط السائق (لا جهة اتصال للعامل)'}
            return {'ok': True, 'msg': 'تم تعيين السائق: %s' % (emp.name or '')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/vehicle/<int:vid>/contract'], type='json', auth='user', website=False)
    def pm_x_vehicle_contract(self, vid=None, kind=None, expiration_date=None, start_date=None, amount=None, **kw):
        env = request.env
        _g = self._x_deleg_check('vehicles', 'write')
        if _g:
            return _g
        veh = env['fleet.vehicle'].sudo().browse(int(vid or 0)).exists() if 'fleet.vehicle' in env else None
        if not (veh and self._x_rec_allowed(veh)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if not expiration_date:
            return {'ok': False, 'error': 'أدخل تاريخ الانتهاء'}
        try:
            name = {'insurance': 'تأمين', 'registration': 'تسجيل (دفتر)'}.get(kind, 'عقد')
            vals = {'vehicle_id': veh.id, 'name': name, 'expiration_date': expiration_date, 'cost_frequency': 'no'}
            if start_date:
                vals['start_date'] = start_date
            if amount not in (None, ''):
                vals['amount'] = float(amount)
            env['fleet.vehicle.log.contract'].sudo().create(vals)
            return {'ok': True, 'msg': 'تم تسجيل %s' % name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ بطاقات الوقود: شحن/طلب تجديد/تجديد تلقائي ============
    def _x_fuelcard(self, cid):
        env = request.env
        if 'care.fuel.card' not in env:
            return None, {'ok': False, 'error': 'غير متاح'}
        c = env['care.fuel.card'].sudo().browse(int(cid or 0)).exists()
        if not (c and self._x_rec_allowed(c)):
            return None, {'ok': False, 'error': 'غير مصرّح'}
        return c, None

    @http.route(['/my/pm/x/fuelcard/<int:cid>/topup'], type='json', auth='user', website=False)
    def pm_x_fuelcard_topup(self, cid=None, amount=None, reference=None, **kw):
        c, err = self._x_fuelcard(cid)
        if err:
            return err
        _g = self._x_deleg_check('fuelcard', 'write')
        if _g:
            return _g
        try:
            amt = float(amount or 0)
            if amt <= 0:
                return {'ok': False, 'error': 'أدخل مبلغًا صحيحًا'}
            c._do_recharge(amt, reference or 'شحن يدوي من البوابة')
            return {'ok': True, 'msg': 'تمّت تعبئة الرصيد', 'balance': round(c.balance or 0, 3)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/fuelcard/<int:cid>/recharge'], type='json', auth='user', website=False)
    def pm_x_fuelcard_recharge(self, cid=None, amount=None, note=None, **kw):
        c, err = self._x_fuelcard(cid)
        if err:
            return err
        _g = self._x_deleg_check('fuelcard', 'write')
        if _g:
            return _g
        if 'care.fuel.recharge.request' not in request.env:
            return {'ok': False, 'error': 'غير متاح'}
        try:
            amt = float(amount or 0)
            if amt <= 0:
                return {'ok': False, 'error': 'أدخل مبلغًا صحيحًا'}
            r = request.env['care.fuel.recharge.request'].sudo().create({'card_id': c.id, 'amount': amt, 'note': note or ''})
            r.action_submit()
            return {'ok': True, 'msg': 'تم إرسال طلب تجديد الرصيد %s' % (r.name or '')}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/fuelcard/<int:cid>/autorecharge'], type='json', auth='user', website=False)
    def pm_x_fuelcard_autorecharge(self, cid=None, enable=None, amount=None, day=None, **kw):
        c, err = self._x_fuelcard(cid)
        if err:
            return err
        _g = self._x_deleg_check('fuelcard', 'write')
        if _g:
            return _g
        try:
            vals = {'auto_recharge': bool(enable) and enable not in ('false', '0', 0, False)}
            if amount not in (None, ''):
                vals['recharge_amount'] = float(amount)
            if day not in (None, ''):
                vals['recharge_day'] = max(1, min(28, int(day)))
            c.write(vals)
            return {'ok': True, 'msg': 'تم تحديث إعداد التجديد التلقائي'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ محطّة البترول: شحن/استهلاك/تحويل (petrol.tank.*) ============
    @http.route(['/my/pm/x/petrol/meta'], type='json', auth='user', website=False)
    def pm_x_petrol_meta(self, **kw):
        env = request.env
        tanks = [[t.id, t.name, round(t.balance or 0, 1)] for t in env['petrol.tank'].sudo().search([])] if 'petrol.tank' in env else []
        vehs = []
        if 'fleet.vehicle' in env:
            _dep = self._pm_projects().mapped('pms_department_id').ids
            _vdom = self._x_emp_dom(_dep) if _dep else [('id', '=', 0)]
            for v in env['fleet.vehicle'].sudo().search(_vdom, limit=100000):
                vehs.append([v.id, v.name or v.license_plate or '—'])
        return {'ok': True, 'tanks': tanks, 'vehicles': vehs}

    @http.route(['/my/pm/x/petrol/<int:tid>/charge'], type='json', auth='user', website=False)
    def pm_x_petrol_charge(self, tid=None, quantity=None, cost=None, date=None, **kw):
        env = request.env
        tank = env['petrol.tank'].sudo().browse(int(tid or 0)).exists() if 'petrol.tank' in env else None
        if not tank:
            return {'ok': False, 'error': 'خزان غير معروف'}
        if not self._pm_projects():
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('petrol', 'write')
        if _g:
            return _g
        if not quantity or float(quantity) <= 0:
            return {'ok': False, 'error': 'أدخل كمية صحيحة'}
        try:
            vals = {'tank_id': tank.id, 'quantity': float(quantity),
                    'charge_date': date or str(fields.Date.today())}
            if cost not in (None, ''):
                vals['cost'] = float(cost)
            env['petrol.tank.charge'].sudo().create(vals)
            return {'ok': True, 'msg': 'تمّت إضافة الشحنة', 'balance': round(tank.balance or 0, 1)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/petrol/<int:tid>/use'], type='json', auth='user', website=False)
    def pm_x_petrol_use(self, tid=None, quantity=None, vehicle_id=None, odometer=None, **kw):
        env = request.env
        tank = env['petrol.tank'].sudo().browse(int(tid or 0)).exists() if 'petrol.tank' in env else None
        if not tank:
            return {'ok': False, 'error': 'خزان غير معروف'}
        if not self._pm_projects():
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('petrol', 'write')
        if _g:
            return _g
        if not quantity or float(quantity) <= 0:
            return {'ok': False, 'error': 'أدخل كمية صحيحة'}
        if not vehicle_id:
            return {'ok': False, 'error': 'اختر المركبة (الاستهلاك يُسجَّل لمركبة)'}
        _dep = self._pm_projects().mapped('pms_department_id').ids
        if not (_dep and env['fleet.vehicle'].sudo().search_count(
                [('id', '=', int(vehicle_id))] + self._x_emp_dom(_dep))):
            return {'ok': False, 'error': 'المركبة خارج نطاقك'}
        try:
            vals = {'tank_id': tank.id, 'quantity': float(quantity), 'datetime': str(fields.Datetime.now()),
                    'vehicle_id': int(vehicle_id)}
            if odometer not in (None, ''):
                vals['odometer_value'] = float(odometer)
            env['petrol.tank.use'].sudo().create(vals)
            return {'ok': True, 'msg': 'تمّ تسجيل الاستهلاك', 'balance': round(tank.balance or 0, 1)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/petrol/<int:tid>/transfer'], type='json', auth='user', website=False)
    def pm_x_petrol_transfer(self, tid=None, to_tank_id=None, quantity=None, date=None, **kw):
        env = request.env
        tank = env['petrol.tank'].sudo().browse(int(tid or 0)).exists() if 'petrol.tank' in env else None
        if not tank:
            return {'ok': False, 'error': 'خزان غير معروف'}
        if not self._pm_projects():
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('petrol', 'write')
        if _g:
            return _g
        if not to_tank_id or not quantity or float(quantity) <= 0:
            return {'ok': False, 'error': 'اختر الخزان المستلِم وكمية صحيحة'}
        try:
            env['petrol.tank.transfer'].sudo().create({
                'tank_id': tank.id, 'from_tank_id': tank.id, 'to_tank_id': int(to_tank_id),
                'quantity': float(quantity), 'date': date or str(fields.Date.today())})
            return {'ok': True, 'msg': 'تمّ التحويل', 'balance': round(tank.balance or 0, 1)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/petty/<int:rid>/categories'], type='json', auth='user', website=False)
    def pm_x_petty_categories(self, rid=None, **kw):
        env = request.env
        if 'care.pms.petty.category' not in env:
            return {'ok': True, 'categories': []}
        cats = env['care.pms.petty.category'].sudo().search([], limit=100000)
        return {'ok': True, 'categories': [[c.id, c.name] for c in cats]}

    # ============ التايم شيت الإضافي (care.extra.timesheet) ============
    def _xts_rec(self, tid):
        env = request.env
        if 'care.extra.timesheet' not in env:
            return None
        ts = env['care.extra.timesheet'].sudo().browse(int(tid or 0)).exists()
        return ts if (ts and self._x_rec_allowed(ts)) else None

    @http.route(['/my/pm/x/xts/<int:tid>'], type='json', auth='user', website=False)
    def pm_x_xts_sheet(self, tid=None, **kw):
        _g = self._x_deleg_check('xts', 'read')
        if _g:
            return _g
        ts = self._xts_rec(tid)
        if not ts:
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            sel = dict(ts._fields['state']._description_selection(request.env))
        except Exception:
            sel = {}
        can_edit = ts.state in ('draft', 'submitted')
        lines = []
        for ln in ts.line_ids:
            lines.append({'lid': ln.id, 'empId': ln.employee_id.id, 'name': _dname(ln.employee_id),
                          'badge': getattr(ln, 'employee_no', '') or (ln.employee_id.barcode or ''),
                          'home_dept': (ln.home_department_id.name if getattr(ln, 'home_department_id', False) else ''),
                          'comp_type': getattr(ln, 'comp_type', ''), 'comp_label': getattr(ln, 'comp_label', '') or '',
                          'rate': getattr(ln, 'hourly_rate', 0) or 0, 'multiplier': getattr(ln, 'multiplier', '') or '',
                          'fixed': getattr(ln, 'fixed_amount', 0) or 0, 'hours': getattr(ln, 'hours', 0) or 0,
                          'amount': getattr(ln, 'amount', 0) or 0, 'note': getattr(ln, 'note', '') or ''})
        return {'ok': True, 'name': ts.display_name, 'state': ts.state, 'state_label': sel.get(ts.state, ts.state),
                'period_from': str(ts.period_from or ''), 'period_to': str(ts.period_to or ''),
                'period_label': getattr(ts, 'period_label', '') or '',
                'project': (ts.project_id.name if ts.project_id else ''),
                'currency': (ts.currency_id.name if getattr(ts, 'currency_id', False) else 'KWD'),
                'can_edit': can_edit, 'can_submit': can_edit and bool(ts.line_ids), 'can_approve': ts.state == 'submitted',
                'can_cancel': can_edit,
                'totals': {'workers': getattr(ts, 'worker_count', len(ts.line_ids)), 'hours': ts.total_hours or 0, 'amount': ts.total_amount or 0},
                'lines': lines}

    @http.route(['/my/pm/x/xts/<int:tid>/line/<int:lid>'], type='json', auth='user', website=False)
    def pm_x_xts_line(self, tid=None, lid=None, hours=None, note=None, **kw):
        ts = self._xts_rec(tid)
        if not ts:
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state not in ('draft', 'submitted'):
            return {'ok': False, 'error': 'الكشف غير قابل للتعديل'}
        ln = ts.line_ids.filtered(lambda l: l.id == int(lid or 0))
        if not ln:
            return {'ok': False, 'error': 'سطر غير موجود'}
        try:
            if getattr(ln, 'comp_type', '') == 'hourly' and hours is not None:
                ln.hours = max(0.0, float(hours))
            if note is not None:
                ln.note = note
            return {'ok': True, 'amount': ln.amount or 0,
                    'totals': {'workers': ts.worker_count, 'hours': ts.total_hours or 0, 'amount': ts.total_amount or 0}}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/xts/<int:tid>/refresh'], type='json', auth='user', website=False)
    def pm_x_xts_refresh(self, tid=None, **kw):
        _g = self._x_deleg_check('xts', 'write')
        if _g:
            return _g
        ts = self._xts_rec(tid)
        if not ts:
            return {'ok': False, 'error': 'غير مصرّح'}
        if ts.state not in ('draft', 'submitted'):
            return {'ok': False, 'error': 'الكشف غير قابل للتحديث'}
        try:
            ts.action_populate()
            return {'ok': True, 'msg': 'تم تحديث العمّال'}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/xts/<int:tid>/<string:act>'], type='json', auth='user', website=False)
    def pm_x_xts_act(self, tid=None, act=None, **kw):
        _g = self._x_deleg_check('xts', {'submit': 'submit', 'approve': 'submit',
                                         'reject': 'cancel'}.get(act, 'write'))
        if _g:
            return _g
        ts = self._xts_rec(tid)
        if not ts:
            return {'ok': False, 'error': 'غير مصرّح'}
        meth = {'submit': 'action_submit', 'approve': 'action_approve', 'reject': 'action_cancel'}.get(act)
        if not meth or not hasattr(ts, meth):
            return {'ok': False, 'error': 'إجراء غير مدعوم'}
        try:
            getattr(ts, meth)()
            return {'ok': True, 'msg': 'تم', 'state': ts.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/xts/new'], type='json', auth='user', website=False)
    def pm_x_xts_new(self, project_id=None, period_from=None, period_to=None, **kw):
        env = request.env
        _g = self._x_deleg_check('xts', 'write')
        if _g:
            return _g
        if 'care.extra.timesheet' not in env:
            return {'ok': False, 'error': 'الوحدة غير مثبّتة'}
        projs = self._pm_projects()
        pid = int(project_id) if project_id else 0
        proj = projs.filtered(lambda x: x.id == pid)[:1] or projs[:1]
        if not proj:
            return {'ok': False, 'error': 'لا مشروع ضمن نطاقك'}
        try:
            vals = {'project_id': proj.id}
            if period_from:
                vals['period_from'] = period_from
            if period_to:
                vals['period_to'] = period_to
            ts = env['care.extra.timesheet'].sudo().create(vals)
            if not ts.line_ids:
                ts.unlink()
                return {'ok': False, 'error': 'لا يوجد عمّال عمل إضافي واردون لهذا المشروع في هذه الفترة'}
            return {'ok': True, 'id': ts.id, 'name': ts.display_name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ جرد الأصول (care.asset.inventory) — صندوق المدير + ورقة الجرد ============
    def _inv_rec(self, inv_id):
        env = request.env
        if 'care.asset.inventory' not in env:
            return None
        inv = env['care.asset.inventory'].sudo().browse(int(inv_id or 0)).exists()
        if not inv:
            return None
        # النطاق: مشروع الجرد ضمن مشاريع المدير
        return inv if inv.project_id.id in self._pm_projects().ids else None

    @http.route(['/my/pm/x/inventory/list'], type='json', auth='user', website=False)
    def pm_x_inventory_list(self, project_id=None, **kw):
        env = request.env
        if 'care.asset.inventory' not in env:
            return {'ok': True, 'rows': []}
        p = self._x_current_project(int(project_id) if project_id else None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        invs = env['care.asset.inventory'].sudo().search(
            [('project_id', '=', p.id), ('state', 'in', ('requested', 'in_progress', 'submitted'))], order='id desc')
        return {'ok': True, 'rows': [{'id': i.id, 'name': i.name, 'state': i.state,
                                      'date': str(i.scheduled_date or ''), 'total': i.line_count,
                                      'counted': i.counted_count, 'progress': i.progress} for i in invs]}

    @http.route(['/my/pm/x/inventory/<int:inv_id>'], type='json', auth='user', website=False)
    def pm_x_inventory_sheet(self, inv_id=None, **kw):
        inv = self._inv_rec(inv_id)
        if not inv:
            return {'ok': False, 'error': 'غير مصرّح'}
        try:
            csel = dict(inv.line_ids._fields['condition']._description_selection(request.env))
        except Exception:
            csel = {}
        lines = [{'id': l.id, 'asset_id': l.asset_id.id, 'name': l.asset_id.name or '—',
                  'barcode': l.barcode or '', 'expected': l.expected_qty, 'counted_qty': l.counted_qty,
                  'condition': l.condition or '', 'note': l.pm_note or '', 'done': bool(l.counted),
                  'has_photo': bool(l.photo)} for l in inv.line_ids]
        return {'ok': True, 'id': inv.id, 'name': inv.name, 'state': inv.state,
                'project': inv.project_id.name, 'progress': inv.progress, 'total': inv.line_count,
                'counted': inv.counted_count, 'can_edit': inv.state in ('requested', 'in_progress'),
                'can_submit': inv.state in ('requested', 'in_progress') and inv.counted_count > 0,
                'conditions': [[k, v] for k, v in csel.items()], 'lines': lines}

    @http.route(['/my/pm/x/inventory/<int:inv_id>/line/<int:line_id>'], type='json', auth='user', website=False)
    def pm_x_inventory_line(self, inv_id=None, line_id=None, counted_qty=None, condition=None,
                            pm_note=None, photo_b64=None, **kw):
        import base64
        inv = self._inv_rec(inv_id)
        if not inv:
            return {'ok': False, 'error': 'غير مصرّح'}
        if inv.state not in ('requested', 'in_progress'):
            return {'ok': False, 'error': 'الجرد غير قابل للتعديل'}
        _g = self._x_deleg_check('inventory', 'write')
        if _g:
            return _g
        ln = inv.line_ids.filtered(lambda l: l.id == int(line_id or 0))
        if not ln:
            return {'ok': False, 'error': 'بند غير موجود'}
        try:
            vals = {'counted': True, 'counted_by': request.env.user.id, 'counted_date': fields.Datetime.now()}
            if counted_qty is not None:
                vals['counted_qty'] = int(counted_qty)
            if condition:
                vals['condition'] = condition
            if pm_note is not None:
                vals['pm_note'] = pm_note
            ln.write(vals)
            if inv.state == 'requested':
                inv.state = 'in_progress'
            # الصورة منفصلة: صورة فاسدة يجب ألا تُفشل حفظ الجرد
            photo_ok = True
            if photo_b64:
                try:
                    ln.write({'photo': photo_b64.split(',')[-1] if isinstance(photo_b64, str) else photo_b64})
                except Exception:
                    photo_ok = False
            return {'ok': True, 'msg': 'حُفظ' if photo_ok else 'حُفظ (تعذّر حفظ الصورة)',
                    'progress': inv.progress, 'counted': inv.counted_count, 'match': ln.match or '', 'photo_ok': photo_ok}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/inventory/<int:inv_id>/submit'], type='json', auth='user', website=False)
    def pm_x_inventory_submit(self, inv_id=None, **kw):
        inv = self._inv_rec(inv_id)
        if not inv:
            return {'ok': False, 'error': 'غير مصرّح'}
        _g = self._x_deleg_check('inventory', 'submit')
        if _g:
            return _g
        try:
            inv.action_submit()
            return {'ok': True, 'msg': 'قُدّم الجرد', 'state': inv.state}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ الأصول: بحث بالباركود + ملصقات QR مجمّعة ============
    @http.route(['/my/pm/x/asset/find'], type='json', auth='user', website=False)
    def pm_x_asset_find(self, barcode=None, **kw):
        env = request.env
        if not barcode or 'account.asset' not in env:
            return {'ok': False, 'error': 'أدخل باركود'}
        a = env['account.asset'].sudo().search([('barcode', '=', str(barcode).strip())], limit=1)
        if not (a and self._x_rec_allowed(a)):
            return {'ok': False, 'error': 'لا أصل بهذا الباركود ضمن مشاريعك'}
        return {'ok': True, 'id': a.id, 'name': a.name or ''}

    @http.route(['/my/pm/x/assets/labels'], type='http', auth='user', website=False)
    def pm_x_asset_labels(self, project_id=None, **kw):
        env = request.env
        p = self._x_current_project(int(project_id) if project_id else None)
        if not p or 'account.asset' not in env:
            return request.not_found()
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        dom = ['|', ('project_id', '=', p.id)]
        dom += [('department_id', '=', dept.id)] if dept else [('project_id', '=', p.id)]
        assets = env['account.asset'].sudo().search(dom, limit=100000)
        cards = ''
        for a in assets:
            qr = '/web/image/account.asset/%s/qr_image' % a.id
            cards += (u'<div class="lbl"><div class="nm">%s</div><img class="qr" src="%s" onerror="this.style.visibility=\'hidden\'">'
                      u'<div class="bc">%s</div></div>') % ((a.name or '—'), qr, (a.barcode or ''))
        html = u"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>ملصقات أصول %(proj)s</title><style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Tajawal',Arial,sans-serif;background:#eef1f5;padding:14px}
.tb{position:fixed;top:12px;inset-inline-start:12px}.tb button{background:#0a1f44;color:#fff;border:0;border-radius:8px;padding:9px 16px;font-weight:700;cursor:pointer}
h2{text-align:center;margin:6px 0 14px;color:#0a1f44}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;max-width:900px;margin:0 auto}
.lbl{border:1px solid #c9d2de;border-radius:8px;background:#fff;padding:10px;text-align:center;page-break-inside:avoid}
.lbl .nm{font-weight:700;font-size:12px;margin-bottom:6px;min-height:30px;display:flex;align-items:center;justify-content:center}
.lbl .qr{width:96px;height:96px;object-fit:contain}
.lbl .bc{font-size:11px;color:#555;margin-top:4px;font-family:monospace}
@media print{body{background:#fff;padding:0}.tb{display:none}@page{size:A4;margin:8mm}}
</style></head><body>
<div class="tb"><button onclick="window.print()">🖨️ طباعة الملصقات</button></div>
<h2>ملصقات أصول · %(proj)s (%(n)s)</h2>
<div class="grid">%(cards)s</div></body></html>""" % {
            'proj': (p.name or ''), 'n': len(assets), 'cards': cards}
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ============ الحضور: استعلام بفلاتر (شهر/مدى/عامل/حالة) ============
    @http.route(['/my/pm/x/attendance/query'], type='json', auth='user', website=False)
    def pm_x_attendance_query(self, project_id=None, month=None, date_from=None,
                              date_to=None, worker_id=None, status='all', badges=None, **kw):
        import datetime as _dt
        env = request.env
        p = self._x_current_project(int(project_id) if project_id else None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        dept = p.pms_department_id if 'pms_department_id' in p._fields else False
        if not dept:
            return {'ok': False, 'error': 'لا قسم للمشروع'}
        emps = env['hr.employee'].sudo().search(self._x_emp_dom(dept.id))
        if worker_id:
            emps = emps.filtered(lambda e: e.id == int(worker_id))
        # بحث مجمّع بأكثر من رقم عامل (أرقام ملفات/أسماء مفصولة بمسافة أو فاصلة)
        if badges:
            import re as _re
            toks = [t for t in _re.split(r'[\s,;،]+', str(badges).strip()) if t]
            if toks:
                toks_l = [t.lower() for t in toks]
                emps = emps.filtered(lambda e: any(
                    (t == (e.barcode or '').lower() or t in (e.barcode or '').lower()
                     or t in (e.name or '').lower()) for t in toks_l))
        emp_ids = emps.ids
        if not emp_ids:
            return {'ok': True, 'cols': ['العامل', 'الحالة', 'التاريخ', 'الدخول', 'الخروج', 'الساعات', ''],
                    'rows': [], 'ids': [], 'stats': [], 'workers': []}
        today = _dt.date.today()
        if month:
            y, m = [int(x) for x in str(month).split('-')[:2]]
            d0 = _dt.date(y, m, 1)
            d1 = _dt.date(y + (1 if m == 12 else 0), (m % 12) + 1, 1) - _dt.timedelta(days=1)
        else:
            # الافتراضي عند الفتح بلا فلاتر: اليوم فقط (بصمة اليوم + إحصاءات اليوم)
            d0 = fields.Date.from_string(date_from) if date_from else today
            d1 = fields.Date.from_string(date_to) if date_to else today
        if (d1 - d0).days > 92:
            d0 = d1 - _dt.timedelta(days=92)
        dstart = _dt.datetime.combine(d0, _dt.time.min)
        dend = _dt.datetime.combine(d1, _dt.time.max)
        import pytz
        Att = env['hr.attendance'].sudo()
        dom = [('employee_id', 'in', emp_ids),
               ('check_in', '>=', fields.Datetime.to_string(dstart)),
               ('check_in', '<=', fields.Datetime.to_string(dend))]
        # منطقة زمنية للمستخدم (تحويل UTC→محلي لتجميع الأيام بدقّة)
        try:
            tz = pytz.timezone(env.user.tz or 'Asia/Kuwait')
        except Exception:
            tz = pytz.utc
        # حضور دقيق بلا سقف (كان limit=100000 يُضخّم الغياب آلاف المرّات) — search_read خفيف لحقلين
        present_days = set()
        total_hours = 0.0
        try:
            for r in Att.search_read(dom, ['employee_id', 'check_in', 'worked_hours'], limit=200000):
                emp_ref = r.get('employee_id')
                eid = emp_ref[0] if emp_ref else None
                total_hours += r.get('worked_hours') or 0.0
                ci = r.get('check_in')
                if not (eid and ci):
                    continue
                if isinstance(ci, str):
                    ci = fields.Datetime.from_string(ci)
                try:
                    local = pytz.utc.localize(ci).astimezone(tz).date()
                except Exception:
                    local = ci.date()
                present_days.add((eid, local))
        except Exception:
            pass
        # أيام الإجازات المعتمدة (كي لا يُحسب المُجاز غائبًا)
        leave_days = {}
        Leave = env['hr.leave'].sudo() if 'hr.leave' in env else None
        if Leave is not None:
            try:
                lvs = Leave.search([('employee_id', 'in', emp_ids), ('state', '=', 'validate'),
                                    ('date_from', '<=', fields.Datetime.to_string(dend)),
                                    ('date_to', '>=', fields.Datetime.to_string(dstart))])
                for lv in lvs:
                    try:
                        ls = max(d0, fields.Datetime.from_string(str(lv.date_from)).date())
                        le = min(d1, fields.Datetime.from_string(str(lv.date_to)).date())
                        s = leave_days.setdefault(lv.employee_id.id, set())
                        dd = ls
                        while dd <= le:
                            s.add(dd)
                            dd += _dt.timedelta(days=1)
                    except Exception:
                        pass
            except Exception:
                pass
        # مخبّأ أيام عمل كل تقويم (أداء: بدل مسح attendance_ids لكل عامل×يوم)
        cal_dows = {}

        def _works_dow(emp, day):
            cal = emp.resource_calendar_id
            if not cal:
                return day.weekday() not in (4, 5)
            if cal.id not in cal_dows:
                cal_dows[cal.id] = set(int(c.dayofweek) for c in cal.attendance_ids) if cal.attendance_ids else None
            dows = cal_dows[cal.id]
            if dows is None:
                return day.weekday() not in (4, 5)
            return day.weekday() in dows

        def _is_late(a, grace=0.25):
            emp = a.employee_id
            cal = emp.resource_calendar_id
            if not cal or not cal.attendance_ids or not a.check_in:
                return False
            ts = fields.Datetime.context_timestamp(a, a.check_in)
            dow = str(ts.weekday())
            hr = ts.hour + ts.minute / 60.0
            starts = [c.hour_from for c in cal.attendance_ids if c.dayofweek == dow]
            return bool(starts) and hr > (min(starts) + grace)

        # الغياب الدقيق: يوم عمل بلا بصمة وليس إجازة وبعد تاريخ التعيين
        absent_n = 0
        absent_rows = []
        ndays = (d1 - d0).days + 1
        for emp in emps:
            eid = emp.id
            ldays = leave_days.get(eid)
            hire = getattr(emp, 'first_contract_date', False) or False
            for i in range(ndays):
                day = d0 + _dt.timedelta(days=i)
                if day > today or (hire and day < hire) or not _works_dow(emp, day):
                    continue
                if (eid, day) in present_days or (ldays and day in ldays):
                    continue
                absent_n += 1
                if status == 'absent':
                    absent_rows.append([['f', emp.name, '#' + (emp.barcode or '')] + _wstag(emp),
                                        'pill:crit:غائب', str(day), '—', '—', '—'])
        # تحويل وقت لمنطقة المستخدم المحلّية (للعرض: تاريخ + ساعة دخول/خروج)
        def _loc(dtv):
            if not dtv:
                return None
            try:
                v = fields.Datetime.from_string(str(dtv))
                return pytz.utc.localize(v).astimezone(tz)
            except Exception:
                return None
        # صفوف العرض: التاريخ + ساعة الدخول + ساعة الخروج + عدد الساعات
        rows, ids, late_n = [], [], 0
        for a in Att.search(dom, order='check_in desc', limit=100000):
            late = _is_late(a)
            late_n += 1 if late else 0
            if status in ('late',) and not late:
                continue
            if status == 'absent':
                continue
            out = a.check_out
            st_pill = 'pill:crit:متأخّر' if late else ('pill:ok:بالداخل' if not out else 'pill:mut:انصرف')
            cl = _loc(a.check_in)
            ol = _loc(out)
            cdate = cl.strftime('%Y-%m-%d') if cl else (str(a.check_in or '')[:10] or '—')
            citime = cl.strftime('%H:%M') if cl else '—'
            cotime = ol.strftime('%H:%M') if ol else '—'
            rows.append([['f', a.employee_id.name, '#' + (a.employee_id.barcode or '')] + _wstag(a.employee_id),
                         st_pill, cdate, citime, cotime, _f(a.worked_hours or 0)])
            ids.append(a.id)
        if status == 'absent':
            rows, ids = absent_rows, [0] * len(absent_rows)
        # إحصاء موثوق من كشوف الدوام المعتمدة (care.timesheet.day: P/A/O/L/H/S)
        # إن توفّرت للفترة — أدقّ من استنتاج الغياب من البصمات الخام؛ وإلا نعود للبصمات.
        stats = None
        src = 'punch'
        tsd = env['care.timesheet.day'].sudo() if 'care.timesheet.day' in env else None
        if tsd is not None:
            try:
                dg = tsd.read_group([('employee_id', 'in', emp_ids),
                                     ('date', '>=', str(d0)), ('date', '<=', str(d1))],
                                    ['status'], ['status'], lazy=False)
                sc = {x.get('status'): x.get('__count', 0) for x in dg}
                if sum(sc.values()):
                    src = 'timesheet'
                    stats = [_stat('حضور', sc.get('P', 0) + sc.get('T', 0) + sc.get('E', 0), 'check', 'var(--ok)'),
                             _stat('غياب', sc.get('A', 0), 'alert', 'var(--crit)', 'down'),
                             _stat('إجازة', sc.get('L', 0) + sc.get('S', 0), 'play', 'var(--info)'),
                             _stat('عطلة', sc.get('O', 0) + sc.get('H', 0), 'clock', 'var(--muted)'),
                             _stat('تأخير', late_n, 'clock', 'var(--warn)')]
            except Exception:
                stats = None
        if stats is None:
            stats = [_stat('حضور', len(present_days), 'check', 'var(--ok)'),
                     _stat('غياب', absent_n, 'alert', 'var(--crit)', 'down'),
                     _stat('تأخير', late_n, 'clock', 'var(--warn)'),
                     _stat('إجمالي الساعات', _f(total_hours), 'timer', 'var(--navy-600)')]
        # أعمدة تفصيل البصمة: العامل · الحالة · التاريخ · الدخول · الخروج · الساعات
        cols = ['العامل', 'الحالة', 'التاريخ', 'الدخول', 'الخروج', 'الساعات', '']
        return {'ok': True, 'cols': cols,
                'rows': rows, 'ids': ids, 'stats': stats, 'src': src,
                'workers': [{'id': e.id, 'name': e.name} for e in emps],
                'range': {'from': str(d0), 'to': str(d1)}}

    # ============ طلب صرف من المخزون (سند تسليم) ============
    @http.route(['/my/pm/x/disburse/create'], type='json', auth='user', website=False)
    def pm_x_disburse_create(self, location=None, date=None, receiver_name=None, lines=None, confirm=None, **kw):
        env = request.env
        _g = self._x_deleg_check('allowances', 'write')
        if _g:
            return _g
        p = self._x_current_project(None)
        if not p:
            return {'ok': False, 'error': 'لا مشروع'}
        if 'care.pms.delivery.note' not in env:
            return {'ok': False, 'error': 'وحدة سندات التسليم غير مثبّتة'}
        items = [l for l in (lines or []) if l.get('material_id') and float(l.get('qty') or 0) > 0]
        if not items:
            return {'ok': False, 'error': 'أضف صنفًا واحدًا على الأقل بكمية صحيحة'}
        Mat = env['care.pms.material'].sudo()
        valid = set(Mat.search([('id', 'in', [int(l['material_id']) for l in items]),
                                ('project_id', '=', p.id)]).ids)
        vlines = []
        for l in items:
            mid = int(l['material_id'])
            if mid not in valid:
                return {'ok': False, 'error': 'صنف خارج مخزون مشروعك'}
            vlines.append((0, 0, {'material_id': mid, 'qty': float(l['qty'])}))
        try:
            note = env['care.pms.delivery.note'].sudo().create({
                'project_id': p.id, 'location': location or '', 'receiver_name': receiver_name or '',
                'date': date or fields.Date.today(), 'line_ids': vlines})
            if confirm:
                note.action_confirm()
            return {'ok': True, 'id': note.id, 'name': note.name,
                    'print_url': '/my/pm/x/delivery/%s/note' % note.id,
                    'msg': ('تم صرف المخزون %s' % note.name) if confirm else ('حُفظت مسوّدة الصرف %s' % note.name)}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # قائمة مواد المشروع (لمنتقي الصرف)
    @http.route(['/my/pm/x/disburse/materials'], type='json', auth='user', website=False)
    def pm_x_disburse_materials(self, **kw):
        env = request.env
        p = self._x_current_project(None)
        if not p or 'care.pms.material' not in env:
            return {'ok': False, 'error': 'لا مشروع'}
        mats = env['care.pms.material'].sudo().search([('project_id', '=', p.id)], limit=100000)
        return {'ok': True, 'materials': [{'id': m.id, 'name': m.name or (m.product_id.display_name or '—'),
                                           'uom': m.uom_name or 'وحدة', 'avail': m.available_qty or 0} for m in mats]}

    # سند تسليم/صرف احترافي بهوية CARE (HTML قابل للطباعة)
    @http.route(['/my/pm/x/delivery/<int:did>/note'], type='http', auth='user', website=False)
    def pm_x_delivery_note(self, did=None, **kw):
        env = request.env
        d = env['care.pms.delivery.note'].sudo().browse(int(did or 0)).exists()
        if not (d and self._x_rec_allowed(d)):
            return request.not_found()
        company = (self._pm_projects()[:1].company_id or env.company)
        st_map = {'draft': ('مسوّدة', '#b7791f'), 'done': ('معتمد', '#2f855a')}
        stx, stc = st_map.get(d.state or 'draft', (d.state or '', '#1f3a5f'))
        rows = ''
        tot = 0.0
        for i, ln in enumerate(d.line_ids, 1):
            tot += ln.qty or 0
            rows += (u'<tr><td>%d</td><td style="text-align:start">%s</td><td>%s</td>'
                     u'<td><b>%s</b></td><td>%s</td></tr>' % (
                         i, (ln.material_id.name or '—'), (ln.material_id.uom_name or 'وحدة'),
                         ('%g' % (ln.qty or 0)), ('%g' % (ln.material_id.available_qty or 0))))
        logo = '/web/image/res.company/%s/logo' % company.id
        sign = ''
        if d.receiver_signature:
            sign = '<img src="/web/image/care.pms.delivery.note/%s/receiver_signature" style="max-height:60px">' % d.id
        else:
            sign = '<div style="border-bottom:1px dotted #999;height:40px"></div>'
        html = u"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<title>سند صرف %(name)s</title><style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Tajawal',sans-serif;background:#eef1f5;color:#1a2332;padding:18px}
.sheet{max-width:820px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.12)}
.hd{background:linear-gradient(135deg,#0a1f44,#12306e);color:#fff;padding:22px 26px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.hd .lg{width:74px;height:74px;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.hd .lg img{max-width:100%%;max-height:100%%}
.hd h1{font-size:20px;font-weight:800}.hd .sub{font-size:12.5px;color:#cfe0f2;margin-top:3px}
.badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;color:#fff;background:%(stc)s}
.info{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e4e8ee}
.info>div{background:#fff;padding:12px 26px}.info .l{font-size:11px;color:#6b7686;margin-bottom:3px}.info .v{font-weight:700;font-size:14px}
table{width:100%%;border-collapse:collapse;margin:0}th,td{padding:11px 10px;text-align:center;font-size:13px;border-bottom:1px solid #eceff3}
thead th{background:#0a1f44;color:#fff;font-weight:700}tbody tr:nth-child(even){background:#f7f9fb}
tfoot td{font-weight:800;background:#f0f3f7}
.ft{display:grid;grid-template-columns:1fr 1fr;gap:30px;padding:26px}
.ft .b{font-size:12px;color:#6b7686;margin-bottom:8px;font-weight:700}
.pr{text-align:center;padding:14px;color:#8a94a2;font-size:11px;border-top:1px solid #eceff3}
.tb{position:fixed;top:14px;inset-inline-start:14px}
.tb button{background:#0a1f44;color:#fff;border:0;border-radius:9px;padding:10px 18px;font-family:inherit;font-weight:700;cursor:pointer}
@media print{body{background:#fff;padding:0}.sheet{box-shadow:none;border-radius:0;max-width:100%%}.tb{display:none}@page{size:A4;margin:12mm}}
</style></head><body>
<div class="tb"><button onclick="window.print()">🖨️ طباعة</button></div>
<div class="sheet">
 <div class="hd"><div style="display:flex;align-items:center;gap:16px"><div class="lg"><img src="%(logo)s" onerror="this.parentNode.textContent='CARE'"></div>
   <div><h1>سند صرف مواد · Materials Delivery Note</h1><div class="sub">%(company)s</div></div></div>
   <div style="text-align:end"><div style="font-size:18px;font-weight:800">%(name)s</div><div style="margin-top:6px"><span class="badge">%(stx)s</span></div></div></div>
 <div class="info">
   <div><div class="l">المشروع · Project</div><div class="v">%(project)s</div></div>
   <div><div class="l">الموقع · Site</div><div class="v">%(location)s</div></div>
   <div><div class="l">المستلِم · Received by</div><div class="v">%(receiver)s</div></div>
   <div><div class="l">التاريخ · Date</div><div class="v">%(date)s</div></div>
 </div>
 <table><thead><tr><th>#</th><th>الصنف · Item</th><th>الوحدة · Unit</th><th>الكمية المصروفة · Issued</th><th>المتبقّي · Remaining</th></tr></thead>
   <tbody>%(rows)s</tbody>
   <tfoot><tr><td colspan="3">الإجمالي · Total</td><td>%(tot)g</td><td></td></tr></tfoot></table>
 <div class="ft"><div><div class="b">أمين المخزن · Storekeeper</div><div style="border-bottom:1px dotted #999;height:40px"></div></div>
   <div><div class="b">توقيع المستلِم · Recipient signature</div>%(sign)s</div></div>
 <div class="pr">%(company)s · طُبع في %(today)s</div>
</div></body></html>""" % {
            'name': d.name or '', 'stx': stx, 'stc': stc, 'logo': logo,
            'company': company.name or 'CARE', 'project': (d.project_id.name or '—'),
            'location': (d.location or '—'), 'receiver': (d.receiver_name or '—'),
            'date': str(d.date or ''), 'rows': rows, 'tot': tot, 'sign': sign,
            'today': fields.Date.to_string(fields.Date.today()),
        }
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route(['/my/pm/x/form/<string:code>'], type='json', auth='user', website=False)
    def pm_x_form(self, code=None, rid=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env or code not in self.pm_x_create_models():
            return {'ok': False, 'error': 'الإنشاء غير متاح لهذا القسم من البوابة'}
        _g = self._x_deleg_check(code, 'write')
        if _g:
            return _g
        # وضع التعديل: سجلّ قائم (مسوّدة فقط، ضمن نطاق المدير)
        edit_rec = None
        if rid:
            edit_rec = request.env[model].sudo().browse(int(rid)).exists()
            if not (edit_rec and self._x_rec_allowed(edit_rec)):
                return {'ok': False, 'error': 'غير مصرّح بتعديل هذا السجل'}
            if not self._x_editable(edit_rec):
                return {'ok': False, 'error': 'لا يمكن التعديل إلا للمسوّدات/قبل الاعتماد'}
        # #11a: تسميات الحقول بلغة البوابة (عربي افتراضًا) لا بلغة حساب أودو للمستخدم
        _lang = kw.get('lang') or 'ar_001'
        M = request.env[model].sudo().with_context(lang=_lang)
        projs = self._pm_projects()
        dept_ids = projs.mapped('pms_department_id').ids
        fg = M.fields_get()
        override = self._X_FORM_FIELDS.get(model)  # قائمة حقول منتقاة إن وُجدت
        _req_model = self._X_FORM_REQUIRED.get(model, ())
        fields = []
        for nm, meta in fg.items():
            # #11c: لا تُعرض الحقول المالية الحسّاسة في النموذج إطلاقًا
            if any(s in nm for s in _X_SENSITIVE):
                continue
            _is_required = bool(meta.get('required')) or (nm in _req_model)
            if override is not None:
                # #11d: لا نُسقط حقلًا **مطلوبًا** حتى لو لم يكن ضمن القائمة المنتقاة (وإلا قُبِل طلب ناقص)،
                # بشرط أن يكون نوعًا قابلًا للعرض وغير محسوب/للقراءة فقط.
                _renderable_req = (_is_required and meta.get('type') in self._X_FORM_TYPES
                                   and not meta.get('readonly')
                                   and not (meta.get('compute') and not meta.get('related') and not meta.get('inverse')))
                # حقل في قائمة الاستبعاد (مثل payslip_state) يُسقَط دائمًا ولو كان مطلوبًا — له default.
                _force_skip = (nm in self._X_FORM_SKIP or nm.startswith(self._X_FORM_SKIP_PREFIX))
                if nm not in override and (not _renderable_req or _force_skip):
                    continue
            else:
                if nm in self._X_FORM_SKIP or nm.startswith(self._X_FORM_SKIP_PREFIX):
                    continue
                t = meta.get('type')
                if t not in self._X_FORM_TYPES:
                    continue
                if meta.get('readonly'):
                    continue
                if meta.get('compute') and not meta.get('related') and not meta.get('inverse'):
                    continue
            t = meta.get('type')
            f = {'name': nm, 'label': self._X_FORM_LABEL.get(model, {}).get(nm) or meta.get('string') or nm, 'type': t,
                 'required': bool(meta.get('required')) or (nm in self._X_FORM_REQUIRED.get(model, ()))}
            if t == 'selection':
                f['options'] = [[k, v] for k, v in (meta.get('selection') or [])]
            elif t == 'many2one':
                co = meta.get('relation')
                recs = []
                try:
                    if co == 'hr.employee' and dept_ids:
                        _ex = self._x_exclude_dept_ids()
                        _edom = [('department_id', 'child_of', dept_ids)]
                        if _ex:
                            _edom += ['!', ('department_id', 'child_of', _ex)]
                        recs = request.env['hr.employee'].sudo().search(_edom, limit=100000)
                    elif co == 'project.project':
                        recs = projs
                    elif co in request.env:
                        recs = request.env[co].sudo().search([], limit=100000)
                except Exception:
                    recs = []
                if co == 'hr.employee':
                    # حالة العامل بجانب كل خانة اختيار عامل (نص في الخيار + خريطة لشارة ملوّنة)
                    smap, opts = {}, []
                    for r in recs:
                        cls, txt = _WS.get(getattr(r, 'worker_status', 'active') or 'active', ('ok', 'نشط'))
                        smap[str(r.id)] = [cls, txt]
                        # #13: نصّ بحث = الاسم عربي/إنجليزي + البادج + الرقم المدني + رقم الجواز
                        _srch = ' '.join(str(x) for x in [
                            r.name, getattr(r, 'english_name', '') or '', getattr(r, 'barcode', '') or '',
                            getattr(r, 'identification_id', '') or '', getattr(r, 'civil_code', '') or '',
                            getattr(r, 'passport_no', '') or ''] if x)
                        opts.append([r.id, u'%s — %s' % (_dname(r), txt), _srch])
                    f['options'] = opts
                    f['is_employee'] = True
                    f['status_map'] = smap
                else:
                    f['options'] = [[r.id, _dname(r)] for r in recs]
            _sw = self._X_FIELD_SHOW.get(model, {}).get(nm)
            if _sw:
                f['show_when'] = _sw
            fields.append(f)
        if override is not None:
            # حافظ على ترتيب القائمة المنتقاة
            fields.sort(key=lambda x: override.index(x['name']) if x['name'] in override else 99)
        else:
            # الحقول المطلوبة أولاً ثم أبجديًّا، بحدٍّ أقصى معقول
            fields.sort(key=lambda x: (not x['required'], x['label']))
            fields = fields[:16]
        defaults = {}
        if 'project_id' in fg and projs:
            defaults['project_id'] = projs[:1].id
        # في وضع التعديل: القيم الحالية للسجلّ
        if edit_rec is not None:
            for f in fields:
                try:
                    val = edit_rec[f['name']]
                    if f['type'] == 'many2one':
                        val = val.id if val else ''
                    elif f['type'] in ('date', 'datetime'):
                        val = str(val) if val else ''
                    elif f['type'] == 'boolean':
                        val = bool(val)
                    defaults[f['name']] = val if val not in (False,) else ''
                except Exception:
                    pass
            return {'ok': True, 'model': model, 'fields': fields, 'defaults': defaults, 'edit': True, 'rid': edit_rec.id}
        return {'ok': True, 'model': model, 'fields': fields, 'defaults': defaults}

    def _x_create_validate(self, code, vals):
        """#1/#14: تحقّق منطقي خاص بنوع الطلب قبل الإنشاء (الطلبات العكسية).
        يرجع نصّ خطأ عند الرفض أو None عند القبول."""
        env = request.env
        eid = vals.get('employee_id')
        emp = env['hr.employee'].sudo().browse(eid).exists() if eid else None
        if emp and 'worker_status' in emp._fields:
            ws = emp.worker_status
            if code == 'leavereturn' and ws != 'on_leave':
                today = fields.Date.today()
                onlv = env['hr.leave'].sudo().search_count([
                    ('employee_id', '=', emp.id), ('state', 'in', ('validate', 'validate1')),
                    ('request_date_from', '<=', today), ('request_date_to', '>=', today)]) if 'hr.leave' in env else 0
                if not onlv:
                    return 'لا يمكن تسجيل «عودة من إجازة» لعامل ليس في إجازة حاليًّا.'
            if code == 'resume' and ws != 'suspended':
                return 'لا يمكن تسجيل «العودة من الإيقاف» لعامل غير موقوف حاليًّا.'
            if code == 'suspension' and ws == 'suspended':
                return 'العامل موقوف بالفعل.'
        # ===== قواعد تحقّق عامّة وخاصّة بالموديول (منع بيانات مضلِّلة) =====
        model = CODE_MODEL.get(code)

        def _num(k):
            try:
                return float(vals.get(k) or 0)
            except Exception:
                return 0.0
        # ترتيب التواريخ: البداية ≤ النهاية
        for a, b in (('date_from', 'date_to'), ('request_date_from', 'request_date_to'),
                     ('start_date', 'end_date'), ('new_start_date', 'new_expire_date'),
                     ('date_start', 'date_end')):
            if vals.get(a) and vals.get(b) and str(vals[a]) > str(vals[b]):
                return 'تاريخ البداية يجب أن يسبق تاريخ النهاية.'
        # مبالغ/كمّيات موجبة حسب الموديول
        if model == 'care.loan':
            if 'amount' in vals and _num('amount') <= 0:
                return 'أدخل مبلغ سلفة صحيحًا (أكبر من صفر).'
            if 'installments' in vals and vals.get('installments') and int(vals.get('installments') or 0) < 1:
                return 'عدد الأقساط يجب أن يكون 1 على الأقل.'
        if model in ('care.penalty', 'care.bonus') and 'amount' in vals and _num('amount') <= 0:
            return 'أدخل مبلغًا صحيحًا (أكبر من صفر).'
        if model == 'care.fuel.entry' and 'amount' in vals and _num('amount') <= 0:
            return 'أدخل مبلغ الوقود (أكبر من صفر).'
        if model == 'care.extra.work':
            _ct = vals.get('comp_type') or 'hourly'
            if _ct == 'hourly' and ('est_hours' in vals or 'hourly_rate' in vals) and _num('est_hours') <= 0:
                return 'أدخل عدد الساعات المقدّرة (طريقة الاحتساب: بالساعة).'
            if _ct in ('fixed', 'hours_fixed') and 'fixed_amount' in vals and _num('fixed_amount') <= 0:
                return 'أدخل المبلغ المقطوع للعمل الإضافي.'
        if model == 'overtime.request' and 'overtime_hours' in vals and _num('overtime_hours') <= 0:
            return 'أدخل عدد ساعات العمل الإضافي (أكبر من صفر).'

        # ===== قواعد قابلة للإعداد (تُقرأ من إعدادات care_pms في الباك‑إند) + بوابات حالة العامل =====
        ICP = env['ir.config_parameter'].sudo()

        def _cfgf(k):
            try:
                return float(ICP.get_param('care_pms.' + k) or 0)
            except Exception:
                return 0.0

        def _cfgb(k, d=True):
            v = ICP.get_param('care_pms.' + k)
            if v in (None, False, ''):
                return d
            return str(v).lower() in ('1', 'true', 'yes')
        # بوّابة حالة العامل حسب نوع الطلب (لا يُقدَّم طلب لعامل في حالة غير مناسبة)
        _block = {'leaves': ('suspended', 'absconding', 'eos', 'resignation', 'arrested'),
                  'suspension': ('suspended', 'eos', 'resignation', 'absconding'),
                  'allowances': ('eos', 'resignation'),
                  'overtime': ('suspended', 'eos', 'resignation', 'absconding'),
                  'extrawork': ('suspended', 'eos', 'resignation', 'absconding')}.get(code)
        if emp and _block and getattr(emp, 'worker_status', None) in _block:
            try:
                _wsl = dict(emp._fields['worker_status']._description_selection(env)).get(emp.worker_status, emp.worker_status)
            except Exception:
                _wsl = emp.worker_status
            return 'لا يمكن تقديم هذا الطلب لعامل حالته: %s' % _wsl
        # صلاحيات إنشاء حسّاسة (افتراضيًّا مسموح — تُضبط من الإعدادات)
        if code == 'eos' and not _cfgb('pmx_pm_can_create_eos', True):
            return 'إنشاء طلب نهاية الخدمة من البوابة غير مسموح (راجع إعدادات تحقّق البوابة).'
        if code == 'resignations' and not _cfgb('pmx_pm_can_create_resignation', True):
            return 'إنشاء طلب الاستقالة من البوابة غير مسموح (راجع إعدادات تحقّق البوابة).'
        # حدود قابلة للإعداد (0 = بلا حدّ)
        if model == 'hr.leave':
            mx = _cfgf('pmx_leave_max_days')
            days = _num('number_of_days')
            if not days and vals.get('request_date_from') and vals.get('request_date_to'):
                try:
                    import datetime as _dt
                    d1 = _dt.date.fromisoformat(str(vals['request_date_from'])[:10])
                    d2 = _dt.date.fromisoformat(str(vals['request_date_to'])[:10])
                    days = (d2 - d1).days + 1
                except Exception:
                    days = 0
            if mx and days and days > mx:
                return 'أيام الإجازة (%g) تتجاوز الحدّ المسموح (%g). راجع إعدادات تحقّق البوابة.' % (days, mx)
        if model == 'care.loan':
            a, i = _cfgf('pmx_loan_max_amount'), _cfgf('pmx_loan_max_installments')
            if a and _num('amount') > a:
                return 'مبلغ السلفة يتجاوز الحدّ المسموح (%g).' % a
            if i and vals.get('installments') and int(vals.get('installments') or 0) > i:
                return 'عدد الأقساط يتجاوز الحدّ المسموح (%g).' % i
        if model == 'care.penalty':
            a = _cfgf('pmx_penalty_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ الجزاء يتجاوز الحدّ المسموح (%g).' % a
        if model == 'care.bonus':
            a = _cfgf('pmx_bonus_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ المكافأة يتجاوز الحدّ المسموح (%g).' % a
        if model == 'overtime.request':
            h = _cfgf('pmx_overtime_max_hours')
            if h and _num('overtime_hours') > h:
                return 'ساعات العمل الإضافي تتجاوز الحدّ المسموح (%g).' % h
        if model == 'care.allowance':
            a = _cfgf('pmx_allowance_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ البدل يتجاوز الحدّ المسموح (%g).' % a
        if model == 'care.fuel.entry':
            a = _cfgf('pmx_fuel_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ تعبئة الوقود يتجاوز الحدّ المسموح (%g).' % a
        if model == 'care.pms.petty.cash':
            a = _cfgf('pmx_petty_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ العهدة يتجاوز الحدّ المسموح (%g).' % a
        if model == 'care.expense.claim':
            a = _cfgf('pmx_expense_max_amount')
            if a and _num('amount') > a:
                return 'مبلغ المطالبة يتجاوز الحدّ المسموح (%g).' % a
        if model == 'project.task' and vals.get('date_deadline') and _cfgb('pmx_task_deadline_future', True):
            if str(vals['date_deadline']) < str(fields.Date.today()):
                return 'موعد المهمة يجب أن يكون في المستقبل.'
        # مبالغ موجبة إضافية
        if model == 'care.expense.claim' and 'amount' in vals and _num('amount') <= 0:
            return 'أدخل مبلغ المطالبة (أكبر من صفر).'
        if model == 'care.pms.petty.cash' and 'amount' in vals and _num('amount') <= 0:
            return 'أدخل مبلغ العهدة (أكبر من صفر).'
        # طلب مستند: لا بدّ من تحديد ما يُرفع (أمامي أو خلفي)
        if model == 'care.document.request' and ('need_front' in vals or 'need_back' in vals):
            if not (vals.get('need_front') or vals.get('need_back')):
                return 'حدّد المطلوب رفعه: الوجه الأمامي أو الخلفي على الأقل.'
        # نقل بين الإدارات: القسم الجديد يجب أن يختلف عن الحالي
        if model == 'employee.shift.request':
            if vals.get('new_department') and emp and emp.department_id and int(vals['new_department']) == emp.department_id.id:
                return 'القسم الجديد يجب أن يختلف عن القسم الحالي للعامل.'
            # تكليف إضافي: لا بدّ من مشروع + بداية + (أيام×أجر يومي أو مبلغ مقطوع) وإلا يدخل 0 للرواتب
            if vals.get('shift_type') == 'additional':
                if not vals.get('additional_project_id'):
                    return 'حدّد المشروع/الإدارة الإضافية للتكليف.'
                if not vals.get('additional_start_date'):
                    return 'حدّد تاريخ بداية التكليف الإضافي.'
                if not ((_num('additional_days') > 0 and _num('additional_daily_rate') > 0) or _num('additional_wage') > 0):
                    return 'أدخل (أيام + أجر يومي) أو مبلغًا مقطوعًا للتكليف الإضافي.'
        # معاملة حكومية: الموعد ≥ تاريخ التقديم
        if model == 'care.gov.transaction' and vals.get('submit_date') and vals.get('deadline'):
            if str(vals['deadline']) < str(vals['submit_date']):
                return 'الموعد النهائي يجب أن يكون بعد تاريخ التقديم.'
        return None

    def _x_create_prefill(self, model, vals):
        """يعوّض عن onchange (لا يعمل عبر JSON): يملأ القيم المحسوبة من النوع/العامل لمنع
        سجلّات بمبالغ/حقول فارغة (بدل/جزاء/نهاية خدمة/كارت بنك/طلب مستند)."""
        env = request.env
        try:
            if model == 'care.allowance' and vals.get('allowance_type_id') and not vals.get('amount'):
                t = env['care.allowance.type'].sudo().browse(int(vals['allowance_type_id'])).exists()
                if t:
                    vals.setdefault('amount', t.default_amount or 0.0)
                    if getattr(t, 'payment_method', False):
                        vals.setdefault('payment_method', t.payment_method)
                    vals.setdefault('frequency', getattr(t, 'default_frequency', False) or 'monthly')
            elif model == 'care.penalty' and vals.get('penalty_type_id') and not vals.get('amount'):
                t = env['care.penalty.type'].sudo().browse(int(vals['penalty_type_id'])).exists()
                if t:
                    vals['amount'] = t.amount or 0.0
            elif model == 'care.eos' and vals.get('employee_id'):
                e = env['hr.employee'].sudo().browse(int(vals['employee_id'])).exists()
                if e:
                    if not vals.get('join_date'):
                        vals['join_date'] = e.first_contract_date or (e.contract_id.date_start if e.contract_id else False)
                    if not vals.get('basic_wage') and e.contract_id:
                        vals['basic_wage'] = e.contract_id.wage
            elif model == 'care.bank.card.request' and vals.get('employee_id') and not vals.get('account_number'):
                e = env['hr.employee'].sudo().browse(int(vals['employee_id'])).exists()
                if e:
                    vals['account_number'] = (getattr(e, 'bank_card_account', '') or
                                              (e.bank_account_id.acc_number if e.bank_account_id else '') or '')
            elif model == 'care.document.request' and vals.get('type_id'):
                t = env['care.worker.document.type'].sudo().browse(int(vals['type_id'])).exists()
                if t and 'need_back' not in vals and 'needs_back' in t._fields:
                    vals['need_back'] = t.needs_back
        except Exception:
            pass
        return vals

    @http.route(['/my/pm/x/create/<string:code>'], type='json', auth='user', website=False)
    def pm_x_create(self, code=None, values=None, **kw):
        model = CODE_MODEL.get(code)
        if not model or model not in request.env or code not in self.pm_x_create_models():
            return {'ok': False, 'error': 'الإنشاء غير متاح'}
        _g = self._x_deleg_check(code, 'write')
        if _g:
            return _g
        fg = request.env[model].sudo().fields_get()
        projs = self._pm_projects()
        # حصر الحقول المقبولة بحقول نموذج الإنشاء فقط (منع mass-assignment عبر JSON:
        # كان يقبل أيّ حقل موجود ⇒ أمكن ضبط state='validate'/amount/*_approved_by تجاوزًا لسير العمل)
        override = self._X_FORM_FIELDS.get(model)
        _hard_block = {'state', 'active', 'create_uid', 'write_uid', 'id'}
        vals = {}
        for k, v in dict(values or {}).items():
            if k not in fg or v in ('', None) or k in _hard_block:
                continue
            meta = fg[k]
            if override is not None:
                if k not in override:
                    continue
            elif (k in self._X_FORM_SKIP or k.startswith(self._X_FORM_SKIP_PREFIX)
                  or meta.get('readonly') or meta.get('type') not in self._X_FORM_TYPES
                  or (meta.get('compute') and not meta.get('related') and not meta.get('inverse'))):
                continue
            t = meta['type']
            try:
                if t in ('integer',):
                    vals[k] = int(v)
                elif t in ('float', 'monetary'):
                    vals[k] = float(v)
                elif t == 'many2one':
                    vals[k] = int(v)
                elif t == 'boolean':
                    vals[k] = bool(v) and v not in ('false', '0', 0, False)
                else:
                    vals[k] = v
            except Exception:
                vals[k] = v
        # افتراض المشروع/القسم من نطاق المستخدم إن لم يُحدَّد
        if 'project_id' in fg and not vals.get('project_id') and projs:
            vals['project_id'] = projs[:1].id
        if 'benef_project_id' in fg and not vals.get('benef_project_id') and projs:
            vals['benef_project_id'] = projs[:1].id
        # العمل الإضافي: same_project=True إن كان المستفيد = المشروع الأصلي (قيد الموديل)،
        # وإلا (المستخدم اختار مستفيداً مختلفاً) = عمل وارد same_project=False
        if 'same_project' in fg and vals.get('benef_project_id'):
            vals['same_project'] = bool(vals.get('project_id') and vals['benef_project_id'] == vals.get('project_id'))
        if 'department_id' in fg and not vals.get('department_id') and projs and projs[:1].pms_department_id:
            vals['department_id'] = projs[:1].pms_department_id.id
        # فرض النطاق: رفض قيم خارج مشاريع/أقسام المدير (منع تجاوز النموذج عبر JSON مباشرةً)
        proj_ids = projs.ids
        dept_ids = projs.mapped('pms_department_id').ids
        for pf in ('project_id', 'benef_project_id'):
            if vals.get(pf) and proj_ids and vals[pf] not in proj_ids:
                return {'ok': False, 'error': 'المشروع المحدَّد خارج نطاقك'}
        if vals.get('employee_id') and not self._x_emp_allowed(
                request.env['hr.employee'].sudo().browse(vals['employee_id']), dept_ids):
            return {'ok': False, 'error': 'العامل المحدَّد خارج نطاقك'}
        # #1/#14: تحقّق منطق الطلبات العكسية (عودة من إجازة/إيقاف)
        _verr = self._x_create_validate(code, vals)
        if _verr:
            return {'ok': False, 'error': _verr}
        # سياسة «طلب واحد مفتوح»: لا طلب جديد لنفس العامل ونوع الطلب وثمّة غير منجَز
        if code in self._X_SINGLE_OPEN and vals.get('employee_id'):
            blk = self._x_open_blocker(model, vals['employee_id'])
            if blk:
                return {'ok': False, 'error': 'يوجد طلب غير منجَز لهذا العامل من نفس النوع (%s) — أنجِزه أو ألغِه أولاً.' % (blk.display_name or '')}
        # قيم تُحقن تلقائياً (مثل holiday_type للإجازة)
        for k, v in self._X_CREATE_INJECT.get(model, {}).items():
            vals.setdefault(k, v)
        # تعويض onchange (ملء القيم المحسوبة من النوع/العامل)
        self._x_create_prefill(model, vals)
        # إنشاء مخصّص: الإيقاف/المباشرة = طلب أصل بسطر واحد للعامل
        parent = self._X_CREATE_PARENT.get(code)
        if parent:
            pmodel, line_fields = parent
            line_vals = {k: vals[k] for k in line_fields if k in vals}
            if 'employee_id' not in line_vals:
                return {'ok': False, 'error': 'اختر العامل'}
            try:
                req = request.env[pmodel].sudo().create({'line_ids': [(0, 0, line_vals)]})
                ln = req.line_ids[:1]
                return {'ok': True, 'id': (ln.id if ln else req.id), 'name': req.display_name}
            except Exception as e:
                return {'ok': False, 'error': _x_safe_error(e)}
        try:
            rec = request.env[model].sudo().create(vals)
            # تقديم تلقائي (إشعار المسؤول) لأكواد محدّدة مثل المواصلات
            if code in self._X_CREATE_AUTOSUBMIT and hasattr(rec, 'action_submit'):
                try:
                    rec.action_submit()
                except Exception:
                    pass
            return {'ok': True, 'id': rec.id, 'name': rec.display_name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    @http.route(['/my/pm/x/update/<string:code>/<int:rid>'], type='json', auth='user', website=False)
    def pm_x_update(self, code=None, rid=None, values=None, **kw):
        """تحديث سجلّ موجود (مسوّدة/قبل الاعتماد) من البوابة — نفس حقول نموذج الإنشاء."""
        model = CODE_MODEL.get(code)
        if not model or model not in request.env or code not in self.pm_x_create_models() or model in _X_READONLY_MODELS:
            return {'ok': False, 'error': 'التعديل غير متاح'}
        _g = self._x_deleg_check(code, 'write')
        if _g:
            return _g
        rec = request.env[model].sudo().browse(int(rid or 0)).exists()
        if not (rec and self._x_rec_allowed(rec)):
            return {'ok': False, 'error': 'غير مصرّح'}
        if not self._x_editable(rec):
            return {'ok': False, 'error': 'لا يمكن التعديل إلا للمسوّدات/قبل الاعتماد'}
        fg = request.env[model].sudo().fields_get()
        allowed = self._X_FORM_FIELDS.get(model)  # حصر الكتابة بحقول النموذج
        # لا يُسمح بنقل السجل عبر النطاق في التعديل (منع تغيير العامل/المشروع/القسم)
        _scope_locked = ('employee_id', 'project_id', 'benef_project_id', 'department_id',
                         'state', 'active', 'new_department', 'current_department')
        vals = {}
        for k, v in dict(values or {}).items():
            if k not in fg or k in _scope_locked or (allowed is not None and k not in allowed):
                continue
            if v in ('', None):
                continue
            t = fg[k]['type']
            try:
                if t == 'integer':
                    vals[k] = int(v)
                elif t in ('float', 'monetary'):
                    vals[k] = float(v)
                elif t == 'many2one':
                    vals[k] = int(v)
                elif t == 'boolean':
                    vals[k] = bool(v) and v not in ('false', '0', 0, False)
                else:
                    vals[k] = v
            except Exception:
                vals[k] = v
        try:
            rec.write(vals)
            return {'ok': True, 'id': rec.id, 'name': rec.display_name}
        except Exception as e:
            return {'ok': False, 'error': _x_safe_error(e)}

    # ============ البدلات: طلب إيقاف + طباعة نموذج الإيقاف ============
    def _x_allowance_allowed(self, al):
        """يتحقّق أن البدل يخصّ عاملًا ضمن مشاريع مدير المشروع الحالي."""
        if not (al and al.employee_id and al.employee_id.department_id):
            return False
        dept_ids = self._pm_projects().mapped('pms_department_id').ids
        if not dept_ids:
            return False
        return self._x_emp_allowed(al.employee_id, dept_ids)

    @http.route(['/my/pm/x/allowance/<int:aid>/stop'], type='http', auth='user', website=False, methods=['POST'], csrf=False)
    def pm_x_allowance_stop(self, aid=None, reason=None, stop_date=None, **kw):
        al = request.env['care.allowance'].sudo().browse(int(aid or 0)).exists()
        ok = {'ok': False, 'msg': 'غير مصرّح'}
        if al and self._x_allowance_allowed(al):
            try:
                vals = {}
                if reason:
                    vals['stop_reason'] = reason
                if stop_date:
                    vals['stop_effective_date'] = stop_date  # تاريخ الإيقاف الفعلي
                if vals:
                    al.write(vals)
                al.action_request_stop()
                ok = {'ok': True, 'state': al.stop_state}
            except Exception as e:
                ok = {'ok': False, 'msg': _x_safe_error(e)}
        return request.make_response(json.dumps(ok), headers=[('Content-Type', 'application/json')])

    @http.route(['/my/pm/x/allowance/<int:aid>/stop-report'], type='http', auth='user', website=False)
    def pm_x_allowance_stop_report(self, aid=None, **kw):
        al = request.env['care.allowance'].sudo().browse(int(aid or 0)).exists()
        if not (al and self._x_allowance_allowed(al)):
            return request.not_found()
        pdf, _ct = request.env['ir.actions.report'].sudo()._render_qweb_pdf('care_hr.report_allowance_stop', [al.id])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename=allowance_stop_%s.pdf' % al.id)])
