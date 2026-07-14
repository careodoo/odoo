# -*- coding: utf-8 -*-
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError


class PMManagerPortal(CustomerPortal):

    # ==================== helpers ====================
    def _pm_projects(self):
        return request.env['project.project'].search([
            '|', ('project_manager_id', '=', request.env.user.id),
            ('portal_user_ids', 'in', request.env.user.ids)]).sudo()

    def _pm_access(self, project_id):
        return self._document_check_access('project.project', project_id).sudo()

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'pm_project_count' in counters:
            values['pm_project_count'] = len(self._pm_projects())
        return values

    def _menu_global(self, active):
        return [
            {'label': 'الرئيسية', 'url': '/my/pm', 'icon': '🏠', 'active': active == 'home'},
            {'label': 'مشاريعي', 'url': '/my/pm/projects', 'icon': '📁', 'active': active == 'projects'},
            {'label': 'كل التاسكات', 'url': '/my/pm/tasks', 'icon': '📋', 'active': active == 'tasks'},
            {'label': 'الواردة إليّ', 'url': '/my/pm/inbox', 'icon': '📥', 'active': active == 'inbox'},
        ]

    def _menu_project(self, project, active):
        b = '/my/pm/p/%s' % project.id
        pending_sup = request.env['care.pms.supply'].sudo().search_count(
            [('project_id', '=', project.id), ('state', '=', 'sent')])
        return [
            {'label': '← مشاريعي', 'url': '/my/pm/projects', 'icon': '', 'active': False},
            {'label': project.name, 'url': b, 'icon': '📌', 'active': False, 'header': True},
            {'label': 'نظرة عامة', 'url': b, 'icon': '📊', 'active': active == 'overview'},
            {'label': 'التاسكات', 'url': b + '/tasks', 'icon': '📋', 'active': active == 'tasks'},
            {'label': 'المخزون', 'url': b + '/materials', 'icon': '📦', 'active': active == 'materials'},
            {'label': 'سندات التسليم', 'url': b + '/deliveries', 'icon': '🚚', 'active': active == 'deliveries'},
            {'label': 'الواردات', 'url': b + '/supplies', 'icon': '📥', 'active': active == 'supplies',
             'badge': pending_sup or ''},
            {'label': 'العُهد النقدية', 'url': b + '/petty', 'icon': '💰', 'active': active == 'petty'},
            {'label': 'طلبات المستندات', 'url': b + '/requests', 'icon': '📄', 'active': active == 'requests'},
            {'label': 'العقود', 'url': b + '/contracts', 'icon': '📜', 'active': active == 'contracts'},
            {'label': 'الأصول والعُهد', 'url': b + '/assets', 'icon': '🧰', 'active': active == 'assets'},
            {'label': 'الامتثال والإقامات', 'url': b + '/compliance', 'icon': '🛂', 'active': active == 'compliance'},
            {'label': 'المحروقات', 'url': b + '/fuel', 'icon': '⛽', 'active': active == 'fuel'},
            {'label': 'الفريق والعمال', 'url': b + '/team', 'icon': '👷', 'active': active == 'team'},
            {'label': 'الحضور والانصراف', 'url': b + '/attendance', 'icon': '⏱️', 'active': active == 'attendance'},
            {'label': 'التايم شيت', 'url': b + '/timesheet', 'icon': '🗓️', 'active': active == 'timesheet'},
            {'label': 'الملف المالي', 'url': b + '/finance', 'icon': '💵', 'active': active == 'finance'},
            {'label': 'أداء الفريق', 'url': b + '/performance', 'icon': '📈', 'active': active == 'performance'},
        ]

    def _base(self, menu, title, **extra):
        v = {'menu': menu, 'user_name': request.env.user.name, 'title': title,
             'company': request.env.company}
        v.update(extra)
        return v

    # ==================== dashboard ====================
    @http.route(['/my/pm'], type='http', auth='user', website=True)
    def pm_home(self, **kw):
        projects = self._pm_projects()
        Task = request.env['project.task'].sudo()
        pids = projects.ids
        kpi = {
            'projects': len(projects),
            'open': Task.search_count([('project_id', 'in', pids), ('stage_id.fold', '=', False)]),
            'overdue': Task.search_count([('project_id', 'in', pids), ('is_overdue', '=', True)]),
            'pending_fwd': Task.search_count([('project_id', 'in', pids), ('forward_state', '=', 'pending')]),
            'at_risk': len(projects.filtered(lambda p: p.risk_level == 'high')),
            'workers': sum(projects.mapped('worker_count')),
        }
        kind_labels = dict(Task._fields['task_kind'].selection)
        raw = Task.read_group([('project_id', 'in', pids), ('task_kind', '!=', False)], ['task_kind'], ['task_kind'])
        by_kind = [{'key': g['task_kind'], 'label': kind_labels.get(g['task_kind'], g['task_kind']),
                    'value': g['task_kind_count']} for g in raw]
        maxk = max([k['value'] for k in by_kind], default=1) or 1
        for k in by_kind:
            k['pct'] = round(100.0 * k['value'] / maxk)
        risk = {'low': 0, 'medium': 0, 'high': 0}
        for p in projects:
            risk[p.risk_level or 'low'] += 1
        total = len(projects) or 1
        risk_bars = [
            {'k': 'low', 'label': 'مستقر', 'value': risk['low'], 'pct': round(100.0 * risk['low'] / total), 'color': '#1a9f6d'},
            {'k': 'medium', 'label': 'متوسط', 'value': risk['medium'], 'pct': round(100.0 * risk['medium'] / total), 'color': '#e08a00'},
            {'k': 'high', 'label': 'خطر عالٍ', 'value': risk['high'], 'pct': round(100.0 * risk['high'] / total), 'color': '#e2513f'},
        ]
        top = sorted([{'id': p.id, 'name': p.name, 'overdue': p.pms_task_overdue} for p in projects],
                     key=lambda x: x['overdue'], reverse=True)[:6]
        maxo = max([t['overdue'] for t in top], default=1) or 1
        for t in top:
            t['pct'] = round(100.0 * t['overdue'] / maxo)
        return request.render('care_pms.pm_dashboard', self._base(
            self._menu_global('home'), 'الرئيسية', kpi=kpi, by_kind=by_kind,
            risk_bars=risk_bars, top_overdue=top))

    @http.route(['/my/pm/projects'], type='http', auth='user', website=True)
    def pm_projects(self, risk=None, q=None, **kw):
        projects = self._pm_projects()
        if risk in ('low', 'medium', 'high'):
            projects = projects.filtered(lambda p: p.risk_level == risk)
        if q:
            ql = q.lower()
            projects = projects.filtered(lambda p: ql in (p.name or '').lower()
                                         or ql in (p.pms_department_id.name or '').lower())
        return request.render('care_pms.pm_projects', self._base(
            self._menu_global('projects'), 'مشاريعي', projects=projects, q=q or ''))

    @http.route(['/my/pm/inbox'], type='http', auth='user', website=True)
    def pm_inbox(self, **kw):
        uid = request.env.user.id
        Task = request.env['project.task'].sudo()
        incoming = Task.search([('forward_to_id', '=', uid), ('forward_state', '=', 'pending')], limit=100)
        assigned = Task.search([('user_ids', 'in', uid)], order='date_deadline asc', limit=100)
        return request.render('care_pms.pm_inbox', self._base(
            self._menu_global('inbox'), 'الواردة إليّ', incoming=incoming, assigned=assigned))

    @http.route(['/my/pm/tasks'], type='http', auth='user', website=True)
    def pm_tasks_global(self, f=None, kind=None, **kw):
        pids = self._pm_projects().ids
        domain = [('project_id', 'in', pids)]
        title = 'كل التاسكات'
        if f == 'overdue':
            domain.append(('is_overdue', '=', True)); title = 'التاسكات المتأخرة'
        elif f == 'open':
            domain.append(('stage_id.fold', '=', False)); title = 'التاسكات المفتوحة'
        elif f == 'pending':
            domain.append(('forward_state', '=', 'pending')); title = 'الإحالات المعلّقة'
        if kind:
            domain.append(('task_kind', '=', kind))
        tasks = request.env['project.task'].sudo().search(domain, limit=300)
        by_stage = {}
        for t in tasks:
            key = t.stage_id.name or 'بدون مرحلة'
            grp = by_stage.setdefault(key, {
                'name': key, 'seq': (t.stage_id.sequence if t.stage_id else 99), 'tasks': []})
            grp['tasks'].append(t)
        stage_groups = sorted(by_stage.values(), key=lambda g: (g['seq'], g['name']))
        return request.render('care_pms.pm_tasks_global', self._base(
            self._menu_global('tasks'), title, tasks=tasks, title_txt=title,
            stage_groups=stage_groups, cur_f=f or ''))

    # ==================== project sections ====================
    def _proj_or_redirect(self, project_id):
        try:
            return self._pm_access(project_id), None
        except (AccessError, MissingError):
            return None, request.redirect('/my')

    @http.route(['/my/pm/p/<int:project_id>'], type='http', auth='user', website=True)
    def pm_overview(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        return request.render('care_pms.pm_overview', self._base(
            self._menu_project(p, 'overview'), p.name, project=p,
            recent_tasks=env['project.task'].sudo().search([('project_id', '=', p.id)], limit=8),
            low_materials=env['care.pms.material'].sudo().search([('project_id', '=', p.id), ('is_low', '=', True)]),
            pending_supplies=env['care.pms.supply'].sudo().search_count([('project_id', '=', p.id), ('state', '=', 'sent')])))

    @http.route(['/my/pm/p/<int:project_id>/tasks'], type='http', auth='user', website=True)
    def pm_p_tasks(self, project_id=None, q=None, f=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        domain = [('project_id', '=', p.id)]
        if f == 'overdue':
            domain.append(('is_overdue', '=', True))
        elif f == 'open':
            domain.append(('stage_id.fold', '=', False))
        elif f == 'pending':
            domain.append(('forward_state', '=', 'pending'))
        if q:
            domain += ['|', ('name', 'ilike', q), ('pms_category_id.name', 'ilike', q)]
        tasks = env['project.task'].sudo().search(domain, limit=300)
        # group tasks by status (stage) into ordered lists
        by_stage = {}
        for t in tasks:
            key = t.stage_id.name or 'بدون مرحلة'
            grp = by_stage.setdefault(key, {
                'name': key, 'seq': (t.stage_id.sequence if t.stage_id else 99), 'tasks': []})
            grp['tasks'].append(t)
        stage_groups = sorted(by_stage.values(), key=lambda g: (g['seq'], g['name']))
        return request.render('care_pms.pm_p_tasks', self._base(
            self._menu_project(p, 'tasks'), p.name, project=p,
            tasks=tasks, stage_groups=stage_groups,
            categories=env['care.task.category'].sudo().search([]),
            q=q or '', cur_f=f or '', ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/materials'], type='http', auth='user', website=True)
    def pm_p_materials(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_materials', self._base(
            self._menu_project(p, 'materials'), p.name, project=p,
            materials=request.env['care.pms.material'].sudo().search([('project_id', '=', p.id)]),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/deliveries'], type='http', auth='user', website=True)
    def pm_p_deliveries(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_deliveries', self._base(
            self._menu_project(p, 'deliveries'), p.name, project=p,
            deliveries=request.env['care.pms.delivery.note'].sudo().search([('project_id', '=', p.id)], limit=100)))

    @http.route(['/my/pm/p/<int:project_id>/supplies'], type='http', auth='user', website=True)
    def pm_p_supplies(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_supplies', self._base(
            self._menu_project(p, 'supplies'), p.name, project=p,
            supplies=request.env['care.pms.supply'].sudo().search([('project_id', '=', p.id)], limit=100),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/supply/<int:supply_id>/receive'],
                type='http', auth='user', website=True, methods=['POST'])
    def pm_receive_supply(self, project_id=None, supply_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        try:
            sup = request.env['care.pms.supply'].sudo().browse(int(supply_id))
            if not sup.exists() or sup.project_id.id != p.id:
                return request.redirect('/my/pm/p/%s/supplies?err=1' % project_id)
            if sup.state != 'sent':
                return request.redirect('/my/pm/p/%s/supplies?err=state' % project_id)
            sup.action_receive()
        except (UserError, ValidationError):
            return request.redirect('/my/pm/p/%s/supplies?err=1' % project_id)
        except Exception:
            return request.redirect('/my/pm/p/%s/supplies?err=1' % project_id)
        return request.redirect('/my/pm/p/%s/supplies?ok=1' % project_id)

    @http.route(['/my/pm/p/<int:project_id>/performance'], type='http', auth='user', website=True)
    def pm_p_performance(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        perf_total = 0.0
        perf_rows = []
        perf_events = []
        available = 'care.performance.log' in env
        if available and p.pms_department_id:
            Log = env['care.performance.log'].sudo()
            emps = env['hr.employee'].sudo().search([('department_id', '=', p.pms_department_id.id)])
            year_start = fields.Date.today().replace(month=1, day=1)
            logs = Log.search([('employee_id', 'in', emps.ids), ('date', '>=', year_start)])
            perf_total = sum(logs.mapped('points'))
            by = {}
            for l in logs:
                by.setdefault(l.employee_id, [0.0, 0])
                by[l.employee_id][0] += l.points
                by[l.employee_id][1] += 1
            perf_rows = sorted(
                [{'emp': e, 'score': v[0], 'count': v[1]} for e, v in by.items()],
                key=lambda r: r['score'])
            perf_events = logs.sorted(lambda l: l.id, reverse=True)[:40]
        return request.render('care_pms.pm_p_performance', self._base(
            self._menu_project(p, 'performance'), p.name, project=p,
            available=available, perf_total=perf_total, perf_rows=perf_rows, perf_events=perf_events))

    @http.route(['/my/pm/p/<int:project_id>/petty'], type='http', auth='user', website=True)
    def pm_p_petty(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_petty', self._base(
            self._menu_project(p, 'petty'), p.name, project=p,
            pettys=request.env['care.pms.petty.cash'].sudo().search([('project_id', '=', p.id)]),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/requests'], type='http', auth='user', website=True)
    def pm_p_requests(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        emps = (env['hr.employee'].sudo().search([('department_id', '=', p.pms_department_id.id)], limit=300)
                if p.pms_department_id else env['hr.employee'].sudo().browse())
        return request.render('care_pms.pm_p_requests', self._base(
            self._menu_project(p, 'requests'), p.name, project=p, employees=emps,
            doc_requests=env['care.pms.doc.request'].sudo().search([('project_id', '=', p.id)], limit=50),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/contracts'], type='http', auth='user', website=True)
    def pm_p_contracts(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_contracts', self._base(
            self._menu_project(p, 'contracts'), p.name, project=p, contracts=p.experience_ids))

    @http.route(['/my/pm/p/<int:project_id>/assets'], type='http', auth='user', website=True)
    def pm_p_assets(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        dept = p.pms_department_id.id
        custody = env['care.custody'].sudo().search([('department_id', '=', dept)]) if dept else env['care.custody'].sudo().browse()
        assets = (env['account.asset'].sudo().search([('department_id', '=', dept)])
                  if dept and 'department_id' in env['account.asset']._fields else env['account.asset'].sudo().browse())
        return request.render('care_pms.pm_p_assets', self._base(
            self._menu_project(p, 'assets'), p.name, project=p, custody=custody, assets=assets))

    @http.route(['/my/pm/p/<int:project_id>/compliance'], type='http', auth='user', website=True)
    def pm_p_compliance(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        emps = request.env['hr.employee'].sudo().search(p._compliance_domain()) if p.pms_department_id else request.env['hr.employee'].sudo().browse()
        today = fields.Date.today()
        far = today + relativedelta(years=99)

        def _nearest(e):
            ds = [d for d in [e.residency_end_date, e.affairs_permit_end_date,
                              e.visa_expire, e.work_permit_expiration_date] if d and d >= today]
            return min(ds) if ds else far
        emps = emps.sorted(key=_nearest)
        rows = [{'e': e, 'near': _nearest(e), 'days': (_nearest(e) - today).days} for e in emps]
        return request.render('care_pms.pm_p_compliance', self._base(
            self._menu_project(p, 'compliance'), p.name, project=p, employees=emps, rows=rows))

    @http.route(['/my/pm/p/<int:project_id>/fuel'], type='http', auth='user', website=True)
    def pm_p_fuel(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        dept = p.pms_department_id.id
        uses = (request.env['petrol.tank.use'].sudo().search([('vehicle_id.department_id', '=', dept)], limit=100)
                if dept and 'petrol.tank.use' in request.env else request.env['petrol.tank.use'].sudo().browse())
        return request.render('care_pms.pm_p_fuel', self._base(
            self._menu_project(p, 'fuel'), p.name, project=p, uses=uses))

    @http.route(['/my/pm/p/<int:project_id>/team'], type='http', auth='user', website=True)
    def pm_p_team(self, project_id=None, q=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        emps = request.env['hr.employee'].sudo().browse()
        if p.pms_department_id:
            domain = [('department_id', '=', p.pms_department_id.id)]
            if q:
                domain += ['|', '|', '|', '|', '|', '|',
                           ('name', 'ilike', q), ('barcode', 'ilike', q), ('english_name', 'ilike', q),
                           ('civil_code', 'ilike', q), ('passport_no', 'ilike', q),
                           ('permit_no', 'ilike', q), ('mobile_phone', 'ilike', q)]
            emps = request.env['hr.employee'].sudo().search(domain, limit=500)
        return request.render('care_pms.pm_p_team', self._base(
            self._menu_project(p, 'team'), p.name, project=p, employees=emps, q=q or ''))

    @http.route(['/my/pm/p/<int:project_id>/finance'], type='http', auth='user', website=True)
    def pm_p_finance(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        return request.render('care_pms.pm_p_finance', self._base(
            self._menu_project(p, 'finance'), p.name, project=p))

    @http.route(['/my/pm/p/<int:project_id>/attendance'], type='http', auth='user', website=True)
    def pm_p_attendance(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        emps = env['hr.employee'].sudo().search([('department_id', '=', p.pms_department_id.id)], limit=500) if p.pms_department_id else env['hr.employee'].sudo().browse()
        Att = env['hr.attendance'].sudo()
        today = fields.Date.today()
        start = datetime.combine(today, time.min)
        today_att = Att.search([('employee_id', 'in', emps.ids), ('check_in', '>=', start)]) if emps else Att.browse()
        present_ids = set(today_att.mapped('employee_id').ids)
        att_by_emp = {a.employee_id.id: a for a in today_att}
        present = emps.filtered(lambda e: e.id in present_ids)
        absent = emps.filtered(lambda e: e.id not in present_ids)
        recent = Att.search([('employee_id', 'in', emps.ids)], order='check_in desc', limit=60) if emps else Att.browse()
        return request.render('care_pms.pm_p_attendance', self._base(
            self._menu_project(p, 'attendance'), p.name, project=p, today=today,
            total=len(emps), present=present, absent=absent, att_by_emp=att_by_emp, recent=recent))

    @http.route(['/my/pm/p/<int:project_id>/timesheet'], type='http', auth='user', website=True)
    def pm_p_timesheet(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        sheets = env['care.timesheet'].sudo().search(
            [('department_id', '=', p.pms_department_id.id)], order='id desc', limit=30) if p.pms_department_id else env['care.timesheet'].sudo().browse()
        return request.render('care_pms.pm_p_timesheet', self._base(
            self._menu_project(p, 'timesheet'), p.name, project=p, sheets=sheets,
            today=fields.Date.today(), ok=kw.get('ok'), err=kw.get('err')))

    def _mgr_departments(self):
        return self._pm_projects().mapped('pms_department_id')

    # ---------- task detail + interaction ----------
    @http.route(['/my/pm/p/<int:project_id>/task/<int:task_id>'], type='http', auth='user', website=True)
    def pm_task_detail(self, project_id=None, task_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.project_id.id != project_id:
            return request.redirect('/my/pm/p/%s/tasks' % project_id)
        fwd_users = request.env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name')
        messages = task.message_ids.filtered(lambda m: m.message_type in ('comment', 'notification') and m.body)
        attachments = request.env['ir.attachment'].sudo().search(
            [('res_model', '=', 'project.task'), ('res_id', '=', task.id)], order='id desc')
        return request.render('care_pms.pm_task_detail', self._base(
            self._menu_project(p, 'tasks'), task.name, project=p, task=task,
            fwd_users=fwd_users, messages=messages[:20], attachments=attachments,
            is_recipient=(task.forward_to_id.id == request.env.user.id),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/task/<int:task_id>/comment'], type='http', auth='user', website=True, methods=['POST'])
    def pm_task_comment(self, project_id=None, task_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        task = request.env['project.task'].sudo().browse(task_id)
        if task.exists() and kw.get('body'):
            task.message_post(body=kw['body'], author_id=request.env.user.partner_id.id,
                              message_type='comment', subtype_xmlid='mail.mt_comment')
        return request.redirect('/my/pm/p/%s/task/%s?ok=comment' % (project_id, task_id))

    @http.route(['/my/pm/p/<int:project_id>/task/<int:task_id>/forward'], type='http', auth='user', website=True, methods=['POST'])
    def pm_task_forward(self, project_id=None, task_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        task = request.env['project.task'].sudo().browse(task_id)
        try:
            task.write({'forward_to_id': int(kw['forward_to_id']), 'forward_reason': kw.get('reason') or ''})
            task.action_request_forward()
        except Exception:
            return request.redirect('/my/pm/p/%s/task/%s?err=1' % (project_id, task_id))
        return request.redirect('/my/pm/p/%s/task/%s?ok=forward' % (project_id, task_id))

    @http.route(['/my/pm/p/<int:project_id>/task/<int:task_id>/accept'], type='http', auth='user', website=True, methods=['POST'])
    def pm_task_accept(self, project_id=None, task_id=None, **kw):
        self._proj_or_redirect(project_id)
        task = request.env['project.task'].sudo().browse(task_id)
        if task.exists() and task.forward_to_id.id == request.env.user.id:
            task.action_accept_forward()
        return request.redirect('/my/pm/p/%s/task/%s?ok=accept' % (project_id, task_id))

    @http.route(['/my/pm/p/<int:project_id>/task/<int:task_id>/reject'], type='http', auth='user', website=True, methods=['POST'])
    def pm_task_reject(self, project_id=None, task_id=None, **kw):
        self._proj_or_redirect(project_id)
        task = request.env['project.task'].sudo().browse(task_id)
        if task.exists() and task.forward_to_id.id == request.env.user.id:
            task.forward_reason = kw.get('reason') or task.forward_reason
            task.action_reject_forward()
        return request.redirect('/my/pm/p/%s/task/%s?ok=reject' % (project_id, task_id))

    # ---------- employee & vehicle files ----------
    @http.route(['/my/pm/p/<int:project_id>/employee/<int:emp_id>'], type='http', auth='user', website=True)
    def pm_employee_file(self, project_id=None, emp_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        emp = request.env['hr.employee'].sudo().browse(emp_id)
        if not emp.exists() or emp.department_id not in self._mgr_departments():
            return request.redirect('/my/pm/p/%s/team' % project_id)
        env = request.env

        def _s(model, domain, limit=20):
            return env[model].sudo().search(domain, limit=limit) if model in env else env['hr.employee'].sudo().browse()

        docs = _s('care.pms.doc.request', [('employee_id', '=', emp_id)])
        loans_hr = _s('hr.loan', [('employee_id', '=', emp_id)])
        loans_care = _s('care.loan', [('employee_id', '=', emp_id)])
        penalties = _s('penalty.request', [('employee_id', '=', emp_id)])
        bonuses = _s('bonus.request', [('employee_id', '=', emp_id)])
        wage = emp.contract_id.wage if emp.contract_id else 0.0
        attendance = env['hr.attendance'].sudo().search([('employee_id', '=', emp_id)], order='check_in desc', limit=30)
        # Social-affairs permit end date defaults to one year after the start date
        affairs_end = emp.affairs_permit_end_date
        if not affairs_end and emp.affairs_permit_start_date:
            affairs_end = emp.affairs_permit_start_date + relativedelta(years=1)
        return request.render('care_pms.pm_employee_file', self._base(
            self._menu_project(p, 'team'), emp.name, project=p, emp=emp, docs=docs,
            loans_hr=loans_hr, loans_care=loans_care, penalties=penalties, bonuses=bonuses,
            wage=wage, attendance=attendance, affairs_end=affairs_end))

    @http.route(['/my/pm/p/<int:project_id>/vehicle/<int:veh_id>'], type='http', auth='user', website=True)
    def pm_vehicle_file(self, project_id=None, veh_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        veh = request.env['fleet.vehicle'].sudo().browse(veh_id)
        if not veh.exists() or veh.department_id not in self._mgr_departments():
            return request.redirect('/my/pm/p/%s/fuel' % project_id)
        uses = request.env['petrol.tank.use'].sudo().search([('vehicle_id', '=', veh_id)], limit=50) if 'petrol.tank.use' in request.env else request.env['fleet.vehicle'].sudo().browse()
        return request.render('care_pms.pm_vehicle_file', self._base(
            self._menu_project(p, 'fuel'), veh.display_name, project=p, veh=veh, uses=uses))

    # ==================== POST actions ====================
    @http.route(['/my/pm/p/<int:project_id>/task'], type='http', auth='user', website=True, methods=['POST'])
    def pm_create_task(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        vals = {'name': kw.get('name') or _('مهمة'), 'project_id': project_id,
                'task_kind': kw.get('task_kind') or 'task', 'pms_department_id': p.pms_department_id.id,
                'description': kw.get('description') or ''}
        if kw.get('pms_category_id'):
            vals['pms_category_id'] = int(kw['pms_category_id'])
        if kw.get('date_deadline'):
            vals['date_deadline'] = kw['date_deadline']
        request.env['project.task'].sudo().create(vals)
        return request.redirect('/my/pm/p/%s/tasks?ok=1' % project_id)

    @http.route(['/my/pm/p/<int:project_id>/delivery'], type='http', auth='user', website=True, methods=['POST'])
    def pm_create_delivery(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        try:
            note = request.env['care.pms.delivery.note'].sudo().create({
                'project_id': project_id, 'location': kw.get('location') or '',
                'receiver_name': kw.get('receiver_name') or ''})
            request.env['care.pms.delivery.note.line'].sudo().create({
                'note_id': note.id, 'material_id': int(kw['material_id']), 'qty': float(kw.get('qty') or 0)})
            note.action_confirm()
        except (UserError, ValidationError):
            return request.redirect('/my/pm/p/%s/materials?err=balance' % project_id)
        except Exception:
            return request.redirect('/my/pm/p/%s/materials?err=1' % project_id)
        return request.redirect('/my/pm/p/%s/materials?ok=1' % project_id)

    @http.route(['/my/pm/p/<int:project_id>/expense'], type='http', auth='user', website=True, methods=['POST'])
    def pm_create_expense(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        try:
            if kw.get('cash_id'):
                cash = env['care.pms.petty.cash'].sudo().browse(int(kw['cash_id']))
            else:
                cash = env['care.pms.petty.cash'].sudo().create({
                    'project_id': project_id, 'amount': float(kw.get('amount') or 0)})
            _exp_amt = float(kw.get('exp_amount') or 0)
            env['care.pms.petty.cash.expense'].sudo().create({
                'cash_id': cash.id, 'name': kw.get('name') or _('مصروف'),
                'category': kw.get('category') or 'misc',
                'amount': _exp_amt, 'foreign_amount': _exp_amt, 'rate': 1.0})
        except (UserError, ValidationError):
            return request.redirect('/my/pm/p/%s/petty?err=overspend' % project_id)
        except Exception:
            return request.redirect('/my/pm/p/%s/petty?err=1' % project_id)
        return request.redirect('/my/pm/p/%s/petty?ok=1' % project_id)

    @http.route(['/my/pm/p/<int:project_id>/timesheet'], type='http', auth='user', website=True, methods=['POST'])
    def pm_create_timesheet(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        if not p.pms_department_id:
            return request.redirect('/my/pm/p/%s/timesheet?err=nodept' % project_id)
        try:
            ts = request.env['care.timesheet'].sudo().create({
                'department_id': p.pms_department_id.id,
                'date_from': kw['date_from'],
                'date_to': kw['date_to'],
            })
            ts.button_generate_timesheet()   # pulls present-days per employee from biometric attendance
            ts.button_submit()               # send for approval
        except Exception:
            return request.redirect('/my/pm/p/%s/timesheet?err=1' % project_id)
        return request.redirect('/my/pm/p/%s/timesheet?ok=1' % project_id)

    @http.route(['/my/pm/p/<int:project_id>/docrequest'], type='http', auth='user', website=True, methods=['POST'])
    def pm_create_docrequest(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        try:
            request.env['care.pms.doc.request'].sudo().create({
                'employee_id': int(kw['employee_id']), 'project_id': project_id,
                'doc_type': kw.get('doc_type') or 'civil_id', 'description': kw.get('description') or ''})
        except Exception:
            return request.redirect('/my/pm/p/%s/requests?err=1' % project_id)
        return request.redirect('/my/pm/p/%s/requests?ok=1' % project_id)
