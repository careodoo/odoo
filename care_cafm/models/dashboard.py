# -*- coding: utf-8 -*-
"""Native in-frame CAFM dashboard: one @api.model call returns every KPI,
breakdown and recent-activity row the OWL client action renders."""
from datetime import timedelta

from odoo import api, fields, models


class CafmWorkorder(models.Model):
    _inherit = 'care.cafm.workorder'

    @api.model
    def _dash_date_field(self):
        """Best available date field to build time-series on."""
        for f in ('create_date', 'request_datetime', 'scheduled_date', 'deadline'):
            if f in self._fields:
                return f
        return 'create_date'

    @api.model
    def get_cafm_dashboard(self):
        env = self.env
        WO = env['care.cafm.workorder']
        total = WO.search_count([])
        open_states = ('new', 'assigned', 'in_progress')
        open_wo = WO.search_count([('state', 'in', open_states)])
        overdue = WO.search_count([('is_overdue', '=', True)])
        done_recs = WO.search([('state', 'in', ('done', 'verified')),
                               ('done_datetime', '!=', False), ('deadline', '!=', False)])
        in_sla = done_recs.filtered(lambda w: w.done_datetime <= w.deadline)
        sla = round(100.0 * len(in_sla) / len(done_recs), 1) if done_recs else 100.0
        done_total = WO.search_count([('state', 'in', ('done', 'verified'))])
        unassigned = WO.search_count([('employee_id', '=', False), ('state', 'in', open_states)])

        state_lbl = dict(WO._fields['state'].selection)
        by_state = []
        state_color = {'new': '#64748b', 'assigned': '#3b82f6', 'in_progress': '#f59e0b',
                       'done': '#16a34a', 'verified': '#0891b2', 'cancelled': '#94a3b8'}
        for st in ('new', 'assigned', 'in_progress', 'done', 'verified'):
            c = WO.search_count([('state', '=', st)])
            by_state.append({'key': st, 'label': state_lbl.get(st, st), 'count': c,
                             'pct': round(100.0 * c / total, 1) if total else 0,
                             'color': state_color.get(st, '#64748b')})

        services = env['care.cafm.service'].search([])
        by_service = []
        for s in services:
            c = WO.search_count([('service_id', '=', s.id)])
            if c:
                by_service.append({'id': s.id, 'label': (s.icon or '') + ' ' + s.name, 'count': c,
                                   'pct': round(100.0 * c / total, 1) if total else 0,
                                   'color': s.color if hasattr(s, 'color') and isinstance(s.color, str) else '#6366f1'})
        by_service.sort(key=lambda d: -d['count'])

        facilities = env['care.cafm.facility'].search([])
        fac_rows = []
        for f in facilities[:12]:
            fo = WO.search_count([('facility_id', '=', f.id), ('state', 'in', open_states)])
            fov = WO.search_count([('facility_id', '=', f.id), ('is_overdue', '=', True)])
            fac_rows.append({'id': f.id, 'name': f.name, 'open': fo, 'overdue': fov})
        fac_rows.sort(key=lambda d: (-d['overdue'], -d['open']))

        recent = []
        for w in WO.search([], order='id desc', limit=8):
            recent.append({'id': w.id, 'name': w.name or ('WO-%s' % w.id), 'title': w.title or '',
                           'facility': w.facility_id.name or '', 'employee': w.employee_id.name or '—',
                           'state': w.state, 'state_label': state_lbl.get(w.state, w.state),
                           'color': state_color.get(w.state, '#64748b')})

        def _cnt(model, dom):
            return env[model].sudo().search_count(dom) if model in env else 0

        # ---- clients (partners with facilities) ----
        clients = env['res.partner'].search([('is_cafm_client', '=', True)]) if 'is_cafm_client' in env['res.partner']._fields else env['res.partner'].browse()
        client_rows = []
        for c in clients[:12]:
            cfacs = facilities.filtered(lambda f: f.partner_id.id == c.id)
            copen = WO.search_count([('facility_id', 'in', cfacs.ids), ('state', 'in', open_states)]) if cfacs else 0
            client_rows.append({'id': c.id, 'name': c.name, 'facilities': len(cfacs), 'open': copen})
        client_rows.sort(key=lambda d: -d['open'])

        # ---- buildings / locations ----
        buildings = _cnt('care.cafm.building', []) if 'care.cafm.building' in env else 0
        locations = _cnt('care.cafm.location', [])
        floors = _cnt('care.cafm.floor', []) if 'care.cafm.floor' in env else 0

        # ---- workforce breakdown ----
        Emp = env['hr.employee']
        team_total = Emp.search_count([('user_id', '!=', False)])
        top_workers = []
        busy = WO.read_group([('employee_id', '!=', False)], ['employee_id'], ['employee_id'],
                             orderby='employee_id_count desc', limit=8)
        for g in busy:
            eid = g['employee_id'][0]
            emp = Emp.browse(eid)
            top_workers.append({
                'id': eid, 'name': g['employee_id'][1],
                'total': g['employee_id_count'],
                'open': WO.search_count([('employee_id', '=', eid), ('state', 'in', open_states)]),
                'done': WO.search_count([('employee_id', '=', eid), ('state', 'in', ('done', 'verified'))]),
                'job': emp.job_title or '',
            })

        # ---- per-service detail (open/done/overdue + team) ----
        svc_detail = []
        for s in services:
            sc = WO.search_count([('service_id', '=', s.id)])
            if not sc:
                continue
            svc_detail.append({
                'id': s.id, 'name': s.name, 'icon': s.icon or '🧩', 'type': s.service_type,
                'total': sc,
                'open': WO.search_count([('service_id', '=', s.id), ('state', 'in', open_states)]),
                'overdue': WO.search_count([('service_id', '=', s.id), ('is_overdue', '=', True)]),
                'done': WO.search_count([('service_id', '=', s.id), ('state', 'in', ('done', 'verified'))]),
                'teams': len(s.team_ids) if 'team_ids' in s._fields else 0,
            })
        svc_detail.sort(key=lambda d: -d['total'])

        # ---- time series (day / month / year) ----
        df = self._dash_date_field()
        today = fields.Date.context_today(self)

        def _series(kind):
            rows = []
            if kind == 'day':
                for i in range(13, -1, -1):
                    d = today - timedelta(days=i)
                    n = WO.search_count([(df, '>=', fields.Datetime.to_string(fields.Datetime.to_datetime(str(d)))),
                                         (df, '<', fields.Datetime.to_string(fields.Datetime.to_datetime(str(d + timedelta(days=1)))))])
                    rows.append({'label': d.strftime('%m-%d'), 'value': n})
            elif kind == 'month':
                y, m = today.year, today.month
                for _ in range(12):
                    start = today.replace(year=y, month=m, day=1)
                    nm_y, nm_m = (y + 1, 1) if m == 12 else (y, m + 1)
                    end = start.replace(year=nm_y, month=nm_m)
                    n = WO.search_count([(df, '>=', str(start)), (df, '<', str(end))])
                    rows.append({'label': start.strftime('%Y-%m'), 'value': n})
                    m -= 1
                    if m == 0:
                        m = 12
                        y -= 1
                rows.reverse()
            else:  # year
                for i in range(4, -1, -1):
                    yr = today.year - i
                    n = WO.search_count([(df, '>=', '%s-01-01' % yr), (df, '<', '%s-01-01' % (yr + 1))])
                    rows.append({'label': str(yr), 'value': n})
            return rows

        series = {'day': _series('day'), 'month': _series('month'), 'year': _series('year')}

        # priority split
        prio_lbl = {'0': 'عادية', '1': 'متوسطة', '2': 'عالية', '3': 'عاجلة'}
        prio_color = {'0': '#94a3b8', '1': '#3b82f6', '2': '#f59e0b', '3': '#e11d48'}
        by_priority = []
        if 'priority' in WO._fields:
            for pv in ('3', '2', '1', '0'):
                c = WO.search_count([('priority', '=', pv)])
                if c:
                    by_priority.append({'label': prio_lbl.get(pv, pv), 'count': c,
                                        'pct': round(100.0 * c / total, 1) if total else 0,
                                        'color': prio_color.get(pv, '#64748b')})

        # ---- شريط الأيقونات العلوي: اختصار لكل قوائم إدارة المرافق تلقائياً ----
        # نبني الشريط ديناميكياً من شجرة قوائم تطبيق إدارة المرافق (كل قائمة لها
        # إجراء) حتى لا تُترك أي أيقونة، ونحترم صلاحية المستخدم (بحث ir.ui.menu
        # كالمستخدم الحالي يُظهر فقط ما يراه). نستخرج الإيموجي من اسم القائمة.
        import re as _re

        def _split_icon(name):
            name = (name or '').strip()
            m = _re.match(r'^([^\w\s؀-ۿ]+)\s*(.*)$', name)
            if m and m.group(1).strip():
                rest = (m.group(2) or '').strip()
                return m.group(1).strip(), (rest or name)
            return None, name

        _fallback_icons = [
            ('حشر', '🐜'), ('نظاف', '🧹'), ('ضياف', '🛎️'), ('مسبح', '🏊'), ('مسابح', '🏊'),
            ('خزان', '🚰'), ('مياه', '🚰'), ('تعقيم', '🧴'), ('سيار', '🚗'), ('مناول', '📦'),
            ('زراع', '🌳'), ('حديق', '🌳'), ('شجر', '🌳'), ('نبات', '🌳'), ('ريّ', '💧'), ('ري ', '💧'),
            ('واجه', '🧼'), ('نفاي', '♻️'), ('أمن', '🛡️'), ('حراس', '🛡️'), ('حارس', '👮'),
            ('دوري', '🚶'), ('جولات', '🚶'), ('بلاغ', '🚨'), ('مفاتيح', '🔑'), ('مفتاح', '🔑'),
            ('تفتيش', '🔎'), ('تدقيق', '🔎'), ('فحص', '🔎'), ('فحوص', '🔎'), ('عهد', '📋'),
            ('زوّار', '🚪'), ('زوار', '🚪'), ('زيار', '🚪'), ('تصريح', '🚪'), ('صيان', '🔧'),
            ('عطل', '🔩'), ('أصول', '🏗️'), ('وقائ', '🛠️'), ('قطع', '⚙️'), ('مرفق', '🏢'),
            ('مبان', '🏢'), ('طابق', '🏢'), ('أدوار', '🏢'), ('وحدات', '🚪'), ('موقع', '📍'),
            ('عميل', '📁'), ('عملاء', '📁'), ('مشروع', '🗂️'), ('مشاريع', '🗂️'), ('فريق', '👥'),
            ('فِرَق', '👥'), ('فرق', '👥'), ('أعضاء', '👥'), ('موظف', '🧑‍🔧'), ('عامل', '🧑‍🔧'),
            ('حضور', '🕐'), ('وردي', '🕐'), ('التحاق', '🔁'), ('إشعار', '🔔'), ('اشعار', '🔔'),
            ('طلب', '📥'), ('أمر', '🔧'), ('عمل', '🔧'), ('مهام', '✅'), ('مهم', '✅'),
            ('جودة', '⭐'), ('ملاحظ', '⭐'), ('كتالوج', '📚'), ('برامج', '🗓️'), ('محطّ', '📍'),
            ('محط', '📍'), ('مطهّر', '🧪'), ('مطهر', '🧪'), ('قراء', '🌡️'), ('استهلاك', '📉'),
            ('مواد', '📦'), ('صنف', '📦'), ('مخز', '📦'), ('مخازن', '🏬'), ('رصيد', '📦'),
            ('حرك', '🔄'), ('صرف', '🧾'), ('سند', '🧾'), ('نقد', '💵'), ('كاش', '💵'),
            ('دفع', '💳'), ('تذاكر', '🎫'), ('تذكرة', '🎫'), ('رحل', '🚛'), ('جمع', '🚛'),
            ('وسائط', '🖼️'), ('قسم', '🗄️'), ('أقسام', '🗄️'), ('تقرير', '📄'), ('تقارير', '📄'),
            ('لوحة', '📊'), ('إحصائ', '📊'), ('تحليل', '📈'), ('إعداد', '⚙️'), ('اعداد', '⚙️'),
            ('مشتري', '🛒'), ('بوابة', '📱'), ('مسح', '📷'), ('عقد', '📄'), ('عقود', '📄'),
            ('حذف', '🗑️'), ('ارتفاع', '🪜'), ('جدول', '🗓️'), ('روست', '🗓️'),
            # كلمات إنجليزية (نظام الأمن الكامل)
            ('Key', '🔑'), ('Patrol', '🚶'), ('Guard', '👮'), ('Team', '👥'), ('Incident', '🚨'),
            ('Inspection', '🔎'), ('Gate', '🚪'), ('Visit', '🚪'), ('Cashier', '💵'), ('Cash', '💵'),
            ('Payment', '💳'), ('Floor', '🏢'), ('Unit', '🚪'), ('Premise', '🏢'), ('Client', '📁'),
            ('Contact', '📇'), ('Schedule', '🗓️'), ('Shift', '🕐'), ('Task', '✅'), ('Dashboard', '📊'),
            ('Report', '📄'), ('Handling', '📦'), ('Equipment', '🧰'), ('Scanner', '📷'),
            ('Assignment', '🗓️'), ('Point', '📍'), ('Summary', '📊'), ('Activity', '📈'),
            ('Parking', '🅿️'), ('Vehicle', '🚗'), ('Security', '🛡️'), ('Attendance', '🕐'),
        ]

        def _icon_for(label):
            lo = label or ''
            for kw, ic in _fallback_icons:
                if kw in lo:
                    return ic
            return '📌'

        # نستبعد: النظام القديم (Studio)، وأشجار الإعداد/التقنية، والتصنيفات/المراحل/
        # الوسوم — فنُبقي القوائم الوظيفية فقط (خدمات وعمليات وأمن…).
        _stop_branch = ('إعداد', 'اعداد', 'Configuration', 'Config', 'Setting',
                        'تقني', 'Technical', 'القديم', 'Studio', 'الإعداد')
        _stop_leaf = ('Tag', 'Stage', 'Category', 'تصنيف', 'مرحل', 'مراحل', 'وسم',
                      'وسوم', 'فئة', 'فئات', 'أنواع', 'Made', 'Type', 'Plate', 'category')
        try:
            legacy_root = env.ref('care_cafm.menu_cafm_root', raise_if_not_found=False)
        except Exception:
            legacy_root = None

        def _excluded(menu):
            m = menu
            hops = 0
            while m and hops < 12:
                nm = m.name or ''
                if any(s in nm for s in _stop_branch):
                    return True
                m = m.parent_id
                hops += 1
            return any(s in (menu.name or '') for s in _stop_leaf)

        shortcuts = []          # مسطّحة (توافق)
        shortcut_groups = []    # مجمّعة حسب الخدمة/القسم — مربّعات احترافية
        try:
            root = env.ref('care_cafm.menu_cafm_root')
            spec = env.ref('care_cafm.menu_cafm_services', raise_if_not_found=False)
            spec_id = spec.id if spec else 0

            def _depth(menu):
                d, m = 0, menu
                while m and m.id != root.id and d < 12:
                    m = m.parent_id
                    d += 1
                return d

            def _group_node(menu):
                """عقدة التجميع: الخدمة (تحت الخدمات المتخصّصة) وإلا القسم العلوي.
                يُعيد None للعناصر العليا المفردة (تُجمَّع في «الرئيسية واللوحات»)."""
                node = menu
                while node.parent_id and node.parent_id.id != root.id:
                    node = node.parent_id
                if node.id == menu.id:          # عنصر علوي مفرد
                    return None
                if spec_id and node.id == spec_id:   # خدمة متخصّصة → المجموعة = الخدمة
                    sub = menu
                    while sub.parent_id and sub.parent_id.id != node.id:
                        sub = sub.parent_id
                    return sub
                return node

            Menu = env['ir.ui.menu']  # بحث كالمستخدم الحالي => يحترم الصلاحيات
            menus = Menu.search([('id', 'child_of', root.id)], order='sequence, id')
            seen = set()
            gmap = {}   # gid -> group dict
            for m in menus:
                act = m.action
                if not act or act._name not in ('ir.actions.act_window', 'ir.actions.client'):
                    continue
                key = (act._name, act.id)
                if key in seen or _excluded(m) or _depth(m) > 3:
                    continue
                seen.add(key)
                icon, label = _split_icon(m.name)
                if not icon:
                    icon = _icon_for(label)
                item = {'icon': icon, 'label': label, 'action_id': act.id, 'action_type': act._name}
                shortcuts.append(item)
                gnode = _group_node(m)
                if gnode is None:
                    gid, gicon, gtitle, gseq = -1, '🏠', 'الرئيسية واللوحات', -1
                else:
                    gicon, gtitle = _split_icon(gnode.name)
                    if not gicon:
                        gicon = _icon_for(gtitle)
                    gid, gseq = gnode.id, gnode.sequence
                g = gmap.get(gid)
                if not g:
                    g = {'icon': gicon, 'title': gtitle, 'seq': gseq, 'items': []}
                    gmap[gid] = g
                g['items'].append(item)
            shortcut_groups = [g for g in sorted(gmap.values(), key=lambda x: (x['seq'], x['title'])) if g['items']]
        except Exception:
            shortcut_groups = []
            shortcuts = [{'icon': '🔧', 'label': 'أوامر العمل', 'model': 'care.cafm.workorder'}]

        # ---- مؤشّرات الأمن والتشغيل الإضافية ----
        security_kpis = {
            'guards': _cnt('security.guard', []),
            'teams': _cnt('security.team', []),
            'incidents': _cnt('security.incident.report', [('state', 'not in', ('closed', 'resolved'))]),
            'patrols': _cnt('security.patrol', [('state', '=', 'in_progress')]),
        }
        ops_kpis = {
            'faults': _cnt('care.cafm.maint.fault', []),
            'waste_trips': _cnt('cafm.waste.trip', []),
            'hosp': _cnt('care.hosp.order', []),
            'projects': _cnt('care.cafm.project', []),
            'scans': _cnt('care.cafm.scan', []),
            'valet': _cnt('care.valet.ticket', []),
            'pest': _cnt('care.pest.program', []),
        }

        # ---- مؤشّرات مالية (عبر العقود care.experience + المشتريات) ----
        financial = {'contracts': 0, 'contract_value': 0, 'insurance': 0, 'po_spend': 0}
        if 'care.experience' in env:
            E = env['care.experience'].sudo()
            contracts = E.search([])
            financial['contracts'] = len(contracts)
            if 'contract_amount' in E._fields:
                financial['contract_value'] = round(sum(contracts.mapped('contract_amount') or [0]), 0)
            if 'insurance_amount' in E._fields:
                financial['insurance'] = round(sum(contracts.mapped('insurance_amount') or [0]), 0)
        if 'purchase.order' in env:
            po = env['purchase.order'].sudo().search([('state', 'in', ('purchase', 'done'))])
            financial['po_spend'] = round(sum(po.mapped('amount_total') or [0]), 0)

        # ---- خريطة حرارية للمرافق (حسب الحِمل المفتوح/المتأخر) ----
        heatmap = []
        for f in facilities[:40]:
            fo = WO.search_count([('facility_id', '=', f.id), ('state', 'in', open_states)])
            fov = WO.search_count([('facility_id', '=', f.id), ('is_overdue', '=', True)])
            if fov >= 3:
                lvl, color = 'critical', '#e11d48'
            elif fov >= 1:
                lvl, color = 'high', '#f59e0b'
            elif fo >= 5:
                lvl, color = 'busy', '#3b82f6'
            elif fo >= 1:
                lvl, color = 'active', '#0ea5a4'
            else:
                lvl, color = 'clear', '#16a34a'
            heatmap.append({'id': f.id, 'name': f.name, 'open': fo, 'overdue': fov,
                            'level': lvl, 'color': color})
        heatmap.sort(key=lambda d: (-d['overdue'], -d['open']))

        return {
            'shortcuts': shortcuts,
            'shortcut_groups': shortcut_groups,
            'security': security_kpis,
            'ops': ops_kpis,
            'financial': financial,
            'heatmap': heatmap,
            'kpis': {
                'total': total, 'open': open_wo, 'overdue': overdue,
                'done': done_total, 'unassigned': unassigned, 'sla': sla,
                'requests': _cnt('care.cafm.service.request', [('state', '=', 'new')]),
                'assets': _cnt('care.cafm.asset', []),
                'ppm': _cnt('care.cafm.ppm', [('active', '=', True)]),
                'observations': _cnt('care.cafm.observation', [('state', 'not in', ('closed', 'cancelled'))]),
                'facilities': len(facilities),
                'team': team_total,
                'clients': len(clients),
                'buildings': buildings, 'floors': floors, 'locations': locations,
            },
            'by_state': by_state,
            'by_service': by_service,
            'by_priority': by_priority,
            'facilities': fac_rows,
            'clients': client_rows,
            'workers': top_workers,
            'services_detail': svc_detail,
            'series': series,
            'recent': recent,
        }
