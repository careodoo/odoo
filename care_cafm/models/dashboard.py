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

        return {
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
