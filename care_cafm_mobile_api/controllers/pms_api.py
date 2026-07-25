# -*- coding: utf-8 -*-
"""Native PROJECT MANAGEMENT (PMS) API.

The app opened /my/pm in a WebView; these endpoints expose projects and tasks as
real data so it can be rendered natively — with the full detail (assignees,
deadline, priority, hours, progress, tags, sub-tasks, description, chatter), not
a summary.

Security: everything reads/writes with the CALLER's env — never sudo — so the
per-user project record rules already in place scope what each user sees.
"""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, API



# This DB closes tasks via project.task.state (Odoo 17), not by moving them to a
# folded stage: stage_id.fold matches 0 records while state='1_done' matches 1127.
DONE_STATES = ('1_done',)
CLOSED_STATES = ('1_done', '1_canceled')
DOM_DONE = [('state', 'in', list(DONE_STATES))]
DOM_OPEN = [('state', 'not in', list(CLOSED_STATES))]


def _d(v):
    return v and str(v) or None


def _m2o(v):
    # sudo the DISPLAY name only: a PMS portal user (project manager) can see a
    # project but not read its customer/partner res.partner — reading just the
    # name for display must never 403 the whole screen (no write, id is stored).
    return {'id': v.id, 'name': v.sudo().display_name} if v else None


class PmsApi(Controller):

    # ---- helpers ---------------------------------------------------------
    def _task_row(self, t):
        return {
            'id': t.id,
            'name': t.name,
            'project': _m2o(t.project_id),
            'stage': _m2o(t.stage_id),
            'priority': t.priority,
            'deadline': _d(t.date_deadline),
            'overdue': self._overdue(t),
            'assignees': [{'id': u.id, 'name': u.name,
                           'avatar': _abs('/pms/user/%s/avatar' % u.id)}
                          for u in t.user_ids],
            'state': t.state if 'state' in t._fields else None,
            'done': (t.state in DONE_STATES) if 'state' in t._fields else False,
            'progress': round(t.progress or 0, 1) if 'progress' in t._fields else 0,
            'subtasks': len(t.child_ids) if 'child_ids' in t._fields else 0,
            'tags': [tg.name for tg in t.tag_ids] if 'tag_ids' in t._fields else [],
            'forward_state': (t.forward_state if 'forward_state' in t._fields else None),
            'urgent': t.priority == '1',
        }

    def _overdue(self, t):
        # date_deadline is a DATETIME in Odoo 17 — comparing it to a date raises
        # "can't compare datetime.datetime to datetime.date" and killed the list.
        dl = t.date_deadline
        if not dl:
            return False
        from odoo import fields as of
        closed = t.state in CLOSED_STATES if 'state' in t._fields else False
        if closed:
            return False
        ref = of.Datetime.now() if hasattr(dl, 'hour') else of.Date.context_today(t)
        return bool(dl < ref)

    # ---- overview --------------------------------------------------------
    @route(API + '/pms/overview', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_overview(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'project.project' not in env:
            return _err('غير متاح', 404)
        from odoo import fields as of
        P, T = env['project.project'], env['project.task']
        today = of.Date.context_today(P)
        dl_is_dt = T._fields['date_deadline'].type == 'datetime'
        past = of.Datetime.now() if dl_is_dt else today
        mine = [('user_ids', 'in', [env.user.id])]
        open_dom = list(DOM_OPEN)
        return _ok({
            'projects': P.search_count([]),
            'tasks': T.search_count([]),
            'my_tasks': T.search_count(mine + open_dom),
            'overdue': T.search_count(open_dom + [('date_deadline', '<', past), ('date_deadline', '!=', False)]),
            'due_today': T.search_count(open_dom + ([('date_deadline', '>=', '%s 00:00:00' % today),
                                                     ('date_deadline', '<=', '%s 23:59:59' % today)]
                                                    if dl_is_dt else [('date_deadline', '=', today)])),
            'done': T.search_count(DOM_DONE),
        })

    # ---- projects --------------------------------------------------------
    @route(API + '/pms/projects', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_projects(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        P = env['project.project']  # no sudo → record rules scope it
        dom = []
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', ('name', 'ilike', q), ('partner_id.name', 'ilike', q)]
        recs = P.search(dom, order='name', limit=200)
        T = env['project.task']
        # Two grouped queries instead of two search_counts per project — the loop
        # was ~244 queries for 122 projects and took 1.5s on the list screen.
        def _by_project(extra):
            rows = T.read_group([('project_id', 'in', recs.ids)] + extra,
                                ['project_id'], ['project_id'])
            return {r['project_id'][0]: r['project_id_count'] for r in rows if r['project_id']}
        from odoo import fields as of
        totals = _by_project([])
        dones = _by_project(DOM_DONE)
        dl_is_dt = T._fields['date_deadline'].type == 'datetime'
        past = of.Datetime.now() if dl_is_dt else of.Date.today()
        overdues = _by_project(DOM_OPEN + [('date_deadline', '<', past), ('date_deadline', '!=', False)])
        # Team size per project's department (one grouped query).
        team = {}
        dept_of = {p.id: (p.pms_department_id.id if 'pms_department_id' in p._fields and p.pms_department_id else None)
                   for p in recs}
        dept_ids = [d for d in dept_of.values() if d]
        if dept_ids and 'hr.employee' in env:
            grp = env['hr.employee'].sudo().read_group(
                [('department_id', 'in', dept_ids)], ['department_id'], ['department_id'])
            by_dept = {g['department_id'][0]: g['department_id_count'] for g in grp if g['department_id']}
            team = {pid: by_dept.get(did, 0) for pid, did in dept_of.items()}
        out = []
        for p in recs:
            total = totals.get(p.id, 0)
            done = dones.get(p.id, 0)
            overdue = overdues.get(p.id, 0)
            progress = round(done * 100.0 / total, 1) if total else 0.0
            health = ('done' if total and done == total
                      else 'at_risk' if overdue > 0
                      else 'on_track')
            out.append({
                'id': p.id, 'name': p.name,
                'partner': _m2o(p.partner_id),
                'manager': _m2o(p.user_id),
                'date_start': _d(p.date_start), 'date_end': _d(p.date),
                'tasks': total, 'done': done, 'open': total - done,
                'overdue': overdue,
                'progress': progress,
                'team': team.get(p.id, 0),
                'health': health,
            })
        return _ok(out)

    def _project_stats(self, env, p):
        """Everything about the project as clickable headline counts — people,
        vehicles, custody, correspondence, materials, cash — each opening its
        own section (code) where one exists."""
        dept = p.pms_department_id.id if 'pms_department_id' in p._fields and p.pms_department_id else None
        stats = []

        def add(code, label, icon, counter):
            try:
                c = counter()
            except Exception:
                return
            if c:
                stats.append({'code': code, 'label': label, 'icon': icon, 'count': c})

        from odoo import fields as of
        T = env['project.task']
        dl_is_dt = T._fields['date_deadline'].type == 'datetime'
        past = of.Datetime.now() if dl_is_dt else of.Date.today()
        # ---- task split (each opens the matching task filter) ----
        stats.append({'code': '__tasks__', 'label': 'إجمالي المهام', 'icon': 'checklist',
                      'count': T.search_count([('project_id', '=', p.id)])})
        add('__open__', 'مهام مفتوحة', 'pending_actions',
            lambda: T.search_count([('project_id', '=', p.id)] + DOM_OPEN))
        add('__done__', 'مهام منجزة', 'check_circle',
            lambda: T.search_count([('project_id', '=', p.id)] + DOM_DONE))
        add('__overdue__', 'مهام متأخرة', 'local_fire_department',
            lambda: T.search_count(DOM_OPEN + [('project_id', '=', p.id),
                                               ('date_deadline', '<', past), ('date_deadline', '!=', False)]))
        if not dept:
            return stats
        # ---- people ----
        add('team', 'العمّال', 'groups',
            lambda: env['hr.employee'].sudo().search_count([('department_id', '=', dept)]))
        # on site right now
        def _onsite():
            start = of.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            emps = env['hr.employee'].sudo().search([('department_id', '=', dept)])
            att = env['hr.attendance'].sudo().search(
                [('employee_id', 'in', emps.ids), ('check_in', '>=', start), ('check_out', '=', False)])
            return len(set(att.mapped('employee_id').ids))
        add('attendance', 'بالموقع الآن', 'fmd_good', _onsite)
        # documents expiring/expired (compliance)
        def _expiring():
            E = env['hr.employee'].sudo()
            if 'residency_end_date' not in E._fields:
                return 0
            soon = of.Date.add(of.Date.today(), days=60)
            return E.search_count([('department_id', '=', dept), ('residency_end_date', '!=', False),
                                   ('residency_end_date', '<=', soon)])
        add('compliance', 'وثائق تنتهي', 'verified_user', _expiring)
        # ---- fleet ----
        if 'fleet.vehicle' in env and 'department_id' in env['fleet.vehicle']._fields:
            add('fuel', 'السيارات', 'directions_car',
                lambda: env['fleet.vehicle'].sudo().search_count([('department_id', '=', dept)]))
        # ---- custody / letters ----
        if 'care.custody' in env:
            add('assets', 'العُهد', 'inventory_2',
                lambda: env['care.custody'].sudo().search_count([('department_id', '=', dept)]))
        for lm in ('care.letter', 'letter.file'):
            if lm in env and 'department_id' in env[lm]._fields:
                add('__letters__', 'الكتب والمراسلات', 'mail',
                    lambda lm=lm: env[lm].sudo().search_count([('department_id', '=', dept)]))
                break
        # ---- project records ----
        add('materials', 'المواد', 'inventory',
            lambda: env['care.pms.material'].sudo().search_count([('project_id', '=', p.id)]))
        add('deliveries', 'إشعارات التسليم', 'receipt',
            lambda: env['care.pms.delivery.note'].sudo().search_count([('project_id', '=', p.id)]))
        add('supplies', 'التوريدات', 'local_shipping',
            lambda: env['care.pms.supply'].sudo().search_count([('project_id', '=', p.id)]))
        add('requests', 'طلبات المستندات', 'description',
            lambda: env['care.pms.doc.request'].sudo().search_count([('project_id', '=', p.id)]))
        add('timesheet', 'كشوف الساعات', 'timer',
            lambda: env['care.timesheet'].sudo().search_count([('department_id', '=', dept)]))
        add('petty', 'العهدة النقدية', 'payments',
            lambda: env['care.pms.petty.cash'].sudo().search_count([('project_id', '=', p.id)]))
        if 'project_id' in env['account.move']._fields:
            add('invoices', 'فواتير المشروع', 'receipt_long',
                lambda: env['account.move'].sudo().search_count(
                    [('project_id', '=', p.id), ('move_type', 'in', ('out_invoice', 'out_refund'))]))
        return stats

    @route(API + '/pms/project/<int:pid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_project(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['project.project'].browse(pid)
        try:
            p.check_access_rule('read')
            p.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        T = env['project.task']
        stages = []
        for s in env['project.task.type'].search([]):
            n = T.search_count([('project_id', '=', pid), ('stage_id', '=', s.id)])
            if n:
                stages.append({'id': s.id, 'name': s.name, 'fold': s.fold, 'count': n})
        total = T.search_count([('project_id', '=', pid)])
        done = T.search_count([('project_id', '=', pid)] + DOM_DONE)
        # Recent tasks (activity) + soonest upcoming deadlines — makes the
        # project page a live view, not just counters.
        recent = [self._task_row(t) for t in T.search(
            [('project_id', '=', pid)], order='write_date desc', limit=6)]
        upcoming = [self._task_row(t) for t in T.search(
            DOM_OPEN + [('project_id', '=', pid), ('date_deadline', '!=', False)],
            order='date_deadline asc', limit=5)]
        # Team preview — a few faces from the project's department.
        team_preview = []
        dept = self._dept(p) if hasattr(self, '_dept') else (
            p.pms_department_id.id if 'pms_department_id' in p._fields and p.pms_department_id else None)
        if dept and 'hr.employee' in env:
            for e in env['hr.employee'].sudo().search([('department_id', '=', dept)], limit=8):
                team_preview.append({'id': e.id, 'name': e.name,
                                     'job': e.job_title or None,
                                     'avatar': _abs('/api/v1/pms/employee/%s/photo' % e.id)})
        return _ok({
            'id': p.id, 'name': p.name,
            'partner': _m2o(p.partner_id), 'manager': _m2o(p.user_id),
            'date_start': _d(p.date_start), 'date_end': _d(p.date),
            'description': p.description or None,
            'tasks': total, 'done': done, 'open': total - done,
            'progress': round(done * 100.0 / total, 1) if total else 0.0,
            'stages': stages,
            'stats': self._project_stats(env, p),
            'recent_tasks': recent,
            'upcoming': upcoming,
            'team_preview': team_preview,
        })

    # ---- tasks -----------------------------------------------------------
    @route(API + '/pms/tasks', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_tasks(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from odoo import fields as of
        T = env['project.task']
        base = []
        if kw.get('project_id') and str(kw['project_id']).isdigit():
            base.append(('project_id', '=', int(kw['project_id'])))
        if kw.get('stage_id') and str(kw['stage_id']).isdigit():
            base.append(('stage_id', '=', int(kw['stage_id'])))
        f = kw.get('filter') or ''
        today = of.Date.context_today(T)
        now = of.Datetime.now()
        dl_is_dt = T._fields['date_deadline'].type == 'datetime'
        past = now if dl_is_dt else today
        dom = list(base)
        if f == 'mine':
            dom.append(('user_ids', 'in', [env.user.id]))
        elif f == 'overdue':
            dom += DOM_OPEN + [('date_deadline', '<', past), ('date_deadline', '!=', False)]
        elif f == 'today':
            dom += DOM_OPEN + ([('date_deadline', '>=', '%s 00:00:00' % today),
                                ('date_deadline', '<=', '%s 23:59:59' % today)]
                               if dl_is_dt else [('date_deadline', '=', today)])
        elif f == 'open':
            dom += DOM_OPEN
        elif f == 'done':
            dom += DOM_DONE
        elif f == 'starred':
            dom += DOM_OPEN + [('priority', '=', '1')]
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', ('name', 'ilike', q), ('project_id.name', 'ilike', q)]
        try:
            limit = min(int(kw.get('limit') or 80), 200)
        except Exception:
            limit = 80
        recs = T.search(dom, order='priority desc, date_deadline asc, id desc', limit=limit)
        overdue_dom = DOM_OPEN + [('date_deadline', '<', past), ('date_deadline', '!=', False)]
        stats = {
            'total': T.search_count(base),
            'open': T.search_count(base + DOM_OPEN),
            'done': T.search_count(base + DOM_DONE),
            'overdue': T.search_count(base + overdue_dom),
            'urgent': T.search_count(base + DOM_OPEN + [('priority', '=', '1')]),
        }
        return _ok({'count': T.search_count(dom), 'stats': stats,
                    'rows': [self._task_row(t) for t in recs]})

    @route(API + '/pms/task/<int:tid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_task(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('read')
            t.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        d = self._task_row(t)
        can_write = True
        try:
            t.check_access_rule('write')
        except Exception:
            can_write = False
        d.update({
            'description': (t.description or '') or None,
            'partner': _m2o(t.partner_id),
            'parent': _m2o(t.parent_id) if 'parent_id' in t._fields else None,
            'date_assign': _d(t.date_assign) if 'date_assign' in t._fields else None,
            'date_end': _d(t.date_end) if 'date_end' in t._fields else None,
            'allocated_hours': round(t.allocated_hours or 0, 2) if 'allocated_hours' in t._fields else 0,
            'effective_hours': round(t.effective_hours or 0, 2) if 'effective_hours' in t._fields else 0,
            'department': _m2o(t.pms_department_id) if 'pms_department_id' in t._fields else None,
            'category': _m2o(t.pms_category_id) if 'pms_category_id' in t._fields else None,
            'time_committed': bool(t.x_time_committed) if 'x_time_committed' in t._fields else None,
            'photos': [_abs('/api/v1/pms/task-photo/%s' % a.id)
                       for a in env['ir.attachment'].sudo().search(
                           [('res_model', '=', 'project.task'), ('res_id', '=', t.id),
                            ('mimetype', 'like', 'image/')], limit=8)],
            'children': [{'id': c.id, 'name': c.name, 'stage': c.stage_id.name,
                          'done': c.state in DONE_STATES} for c in t.child_ids] if 'child_ids' in t._fields else [],
            'can_write': can_write,
            'forward_to': _m2o(t.forward_to_id) if 'forward_to_id' in t._fields else None,
            'forward_from': _m2o(t.forward_from_id) if 'forward_from_id' in t._fields else None,
            'forward_state': (t.forward_state if 'forward_state' in t._fields else None),
            'forward_reason': (t.forward_reason or None) if 'forward_reason' in t._fields else None,
            # Whether THIS caller is the one being asked to accept/reject.
            'is_recipient': bool('forward_to_id' in t._fields and t.forward_to_id
                                 and t.forward_to_id.id == env.uid),
            # ---- close-request workflow ----
            'close_state': (t.close_state if 'close_state' in t._fields else None),
            'needs_close_request': bool('close_state' in t._fields and t._pms_needs_close_request()),
            # evaluated as the REAL caller (no sudo — sudo would bypass the check)
            'can_close_directly': bool('close_state' in t._fields and t._pms_can_close()),
            'is_close_approver': bool('close_state' in t._fields
                                      and t.close_requested_by_id
                                      and t._pms_can_close()),
            'close_requested_by': (t.close_requested_by_id.name
                                   if 'close_state' in t._fields and t.close_requested_by_id else None),
            'close_requested_on': _d(t.close_requested_on) if 'close_state' in t._fields else None,
            'close_auto': bool(t.close_auto) if 'close_state' in t._fields else False,
            'stages': [{'id': s.id, 'name': s.name, 'fold': s.fold}
                       for s in env['project.task.type'].search(
                           [('project_ids', 'in', [t.project_id.id])] if t.project_id else [])],
            'messages': [{'author': m.author_id.display_name or '—', 'date': _d(m.date),
                          'body': (m.body or '')[:600],
                          # images attached to THIS comment, shown inline in it
                          'images': [_abs('/api/v1/pms/task-photo/%s' % a.id)
                                     for a in m.attachment_ids
                                     if (a.mimetype or '').startswith('image/')]}
                         for m in t.message_ids.filtered(lambda x: x.body or x.attachment_ids)[:12]],
        })
        return _ok(d)

    # ---- write actions ---------------------------------------------------
    @route(API + '/pms/task/<int:tid>/stage', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_stage(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        sid = (_body() or {}).get('stage_id')
        if not sid:
            return _err('اختر مرحلة', 422)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            t.write({'stage_id': int(sid)})   # caller's env → Odoo enforces
        except Exception as e:
            return _err(str(e) or 'غير مصرّح', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/note', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_note(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        body = (_body() or {}).get('note')
        if not (body or '').strip():
            return _err('اكتب ملاحظة', 422)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('read')
            t.message_post(body=body)
        except Exception as e:
            return _err(str(e) or 'غير مصرّح', 403)
        return _ok({'ok': True})

    @route(API + '/pms/task/<int:tid>/priority', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_priority(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        p = (_body() or {}).get('priority')
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            t.write({'priority': '1' if str(p) in ('1', 'true', 'True') else '0'})
        except Exception as e:
            return _err(str(e) or 'غير مصرّح', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/forward', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_forward(self, tid, **kw):
        """Route a task to another internal user — the portal's forward action."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        b = _body() or {}
        to_uid = b.get('forward_to_id')
        if not to_uid:
            return _err('اختر المستخدم', 422)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            vals = {'forward_to_id': int(to_uid), 'forward_reason': b.get('reason') or ''}
            # optional new deadline (else keep the current one)
            if b.get('deadline'):
                vals['date_deadline'] = b.get('deadline')
            t.write(vals)
            if hasattr(t, 'action_request_forward'):
                t.action_request_forward()
        except Exception as e:
            return _err(str(e) or 'تعذّرت الإحالة', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/accept', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_accept(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('read')
            # Only the person the task was forwarded TO may accept it — mirrors
            # the portal's own guard.
            if not ('forward_to_id' in t._fields and t.forward_to_id and t.forward_to_id.id == env.uid):
                return _err('هذه الإحالة ليست موجَّهة إليك', 403)
            if hasattr(t, 'action_accept_forward'):
                t.action_accept_forward()
        except Exception as e:
            return _err(str(e) or 'تعذّر القبول', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/reject', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_reject(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('read')
            if not ('forward_to_id' in t._fields and t.forward_to_id and t.forward_to_id.id == env.uid):
                return _err('هذه الإحالة ليست موجَّهة إليك', 403)
            reason = (_body() or {}).get('reason')
            if reason:
                t.sudo().forward_reason = reason
            if hasattr(t, 'action_reject_forward'):
                t.action_reject_forward()
        except Exception as e:
            return _err(str(e) or 'تعذّر الرفض', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    # ---- close-request workflow ----
    @route(API + '/pms/task/<int:tid>/request-close', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_request_close(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('read')
            note = (_body() or {}).get('note')
            if note:
                t.sudo().close_request_note = note
            if hasattr(t, 'action_request_close'):
                t.sudo().action_request_close()
        except Exception as e:
            return _err(str(e) or 'تعذّر طلب الإغلاق', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/approve-close', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_approve_close(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            if not t.sudo()._pms_can_close():
                return _err('اعتماد الإغلاق من صلاحية منشئ التاسك أو مدير المشروع', 403)
            t.sudo().action_approve_close()
        except Exception as e:
            return _err(str(e) or 'تعذّر اعتماد الإغلاق', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/reject-close', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_reject_close(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            if not t.sudo()._pms_can_close():
                return _err('رفض الإغلاق من صلاحية منشئ التاسك أو مدير المشروع', 403)
            reason = (_body() or {}).get('reason')
            if reason:
                t.sudo().close_request_note = reason
            t.sudo().action_reject_close()
        except Exception as e:
            return _err(str(e) or 'تعذّر رفض الإغلاق', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/task/<int:tid>/close', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_close(self, tid, **kw):
        """Directly close a task (mark done). The model's write-guard blocks a
        plain assignee on a deadline task — they must use request-close."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        note = (_body() or {}).get('note')
        t = env['project.task'].browse(tid)
        try:
            t.check_access_rule('write')
            t.write({'state': '1_done'})   # caller env → close-request guard applies
            if 'close_state' in t._fields:
                t.sudo().close_state = 'approved'
            # "what was done" note → chatter + activity log
            if (note or '').strip():
                import markupsafe
                body = markupsafe.Markup('<b>✅ %s</b><br/>%s') % (
                    'تم إغلاق المهمة — ما تم:', note)
                t.message_post(body=body, subject='إغلاق المهمة')
        except Exception as e:
            return _err(str(e) or 'تعذّر الإغلاق', 403)
        t.invalidate_recordset()
        return _ok(self._task_row(t))

    @route(API + '/pms/project/<int:pid>/task/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_task_create(self, pid, **kw):
        """Create a task in a project the caller may write to."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        b = _body() or {}
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اكتب عنوان المهمة', 422)
        proj = env['project.project'].browse(int(pid))
        try:
            proj.check_access_rule('read')
        except Exception:
            return _err('لا صلاحية على هذا المشروع', 403)
        vals = {'name': name, 'project_id': proj.id}
        if b.get('description'):
            vals['description'] = b['description']
        if b.get('date_deadline'):
            vals['date_deadline'] = b['date_deadline']
        if b.get('priority') in ('0', '1'):
            vals['priority'] = b['priority']
        if b.get('user_id'):
            # Odoo 17: assignees are a many2many.
            vals['user_ids'] = [(6, 0, [int(b['user_id'])])]
        if b.get('category_id') and 'pms_category_id' in env['project.task']._fields:
            vals['pms_category_id'] = int(b['category_id'])
        if b.get('department_id') and 'pms_department_id' in env['project.task']._fields:
            vals['pms_department_id'] = int(b['department_id'])
        if 'x_time_committed' in env['project.task']._fields:
            vals['x_time_committed'] = bool(b.get('time_committed'))
        try:
            # The task is created as the caller, so create-rights are enforced.
            t = env['project.task'].create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر الإنشاء', 403)
        # Optional photo (camera or gallery) → an attachment on the task.
        img = b.get('image')
        if img:
            import base64
            try:
                raw = base64.b64decode(img.split(',')[-1])
                env['ir.attachment'].sudo().create({
                    'name': 'task-photo.jpg',
                    'datas': base64.b64encode(raw),
                    'res_model': 'project.task',
                    'res_id': t.id,
                    'mimetype': 'image/jpeg',
                })
            except Exception:
                pass  # a bad image must never lose the task
        return _ok(self._task_row(t))

    @route(API + '/pms/project/<int:pid>/task-meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_task_meta(self, pid, **kw):
        """Everything the new-task form needs: departments, categories, and the
        users a task may be assigned to — all scoped by the caller's access."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        T = env['project.task']
        out = {'departments': [], 'categories': [], 'users': []}
        if 'pms_department_id' in T._fields:
            comodel = T._fields['pms_department_id'].comodel_name
            try:
                for d in env[comodel].search([], limit=200):
                    out['departments'].append({'id': d.id, 'name': d.display_name})
            except Exception:
                pass
        if 'pms_category_id' in T._fields:
            comodel = T._fields['pms_category_id'].comodel_name
            try:
                for c in env[comodel].search([], limit=200):
                    out['categories'].append({'id': c.id, 'name': c.display_name})
            except Exception:
                pass
        try:
            proj = env['project.project'].browse(int(pid))
            members = proj.message_partner_ids.mapped('user_ids') if proj.exists() else env['res.users']
            users = members or env['res.users'].search([('share', '=', False)], limit=100)
            for u in users[:100]:
                out['users'].append({'id': u.id, 'name': u.name})
        except Exception:
            pass
        return _ok(out)

    @route(API + '/pms/project/<int:pid>/forward-users', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_forward_users(self, pid, **kw):
        """Internal users a task may be forwarded to (mirrors the portal list)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        users = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name', limit=400)
        out = []
        for u in users:
            emp = u.employee_id if 'employee_id' in u._fields and u.employee_id else None
            job = (emp.job_title if emp else None) or (u.function if 'function' in u._fields else None)
            dept = emp.department_id.name if emp and emp.department_id else None
            out.append({'id': u.id, 'name': u.name,
                        'avatar': _abs('/pms/user/%s/avatar' % u.id),
                        'job': job or None, 'department': dept,
                        'search': ('%s %s %s' % (u.name or '', job or '', dept or '')).lower()})
        return _ok(out)



# ---------------------------------------------------------------------------
# Project sections — parity with the /my/pm portal.
#
# The portal exposes 14 sections per project (materials, deliveries, supplies,
# petty cash, team, attendance, timesheet, assets, fuel, compliance, finance,
# contracts, requests, performance). Rather than 14 near-identical endpoints and
# 14 near-identical screens, each section declares how to fetch its rows and how
# to label them, and one endpoint + one screen render any of them.
#
# Reads use the caller's env wherever the record is reachable that way. Some
# sections read HR/fleet models a project manager has no direct ACL for; those
# use sudo but are hard-scoped to the project's own department, so a PM can only
# ever see their own project's people and vehicles.
# ---------------------------------------------------------------------------
class PmsSectionsApi(Controller):

    def _project(self, env, pid):
        """The project, if this user may see it. Record rules do the deciding —
        a project outside the caller's scope raises and becomes a 403."""
        p = env['project.project'].browse(int(pid))
        p.check_access_rights('read')
        p.check_access_rule('read')
        return p.exists()

    def _dept(self, p):
        return p.pms_department_id.id if 'pms_department_id' in p._fields and p.pms_department_id else None

    # ---- per-section builders -------------------------------------------
    def _sec_materials(self, env, p):
        rows = []
        M = env['care.pms.material'].sudo()
        recs = M.search([('project_id', '=', p.id)], limit=400)
        low = 0
        for m in recs:
            avail = round(m.available_qty, 1) if 'available_qty' in m._fields else None
            is_low = bool('is_low' in m._fields and m.is_low)
            if is_low:
                low += 1
            uom = (m.uom_name if 'uom_name' in m._fields and m.uom_name
                   else (m.uom_id.name if 'uom_id' in m._fields and m.uom_id else None))
            has_img = bool('product_id' in m._fields and m.product_id and m.product_id.image_128)
            rows.append({
                'id': m.id, 'title': m.name or m.display_name,
                'subtitle': uom,
                'value': avail, 'value_label': 'المتاح',
                'state': 'low' if is_low else 'ok',
                'state_label': 'منخفض' if is_low else 'متوفّر',
                'open': 'material',
                'image': (_abs('/pms/product/%s/image' % m.product_id.id) if has_img else None),
                'badges': [x for x in [
                    ('استُلم: %s' % round(m.received_qty, 1)) if 'received_qty' in m._fields else None,
                    ('صُرف: %s' % round(m.issued_qty, 1)) if 'issued_qty' in m._fields else None,
                ] if x],
                'search': ('%s %s' % (m.name or '', (m.product_id.name if 'product_id' in m._fields and m.product_id else ''))).lower(),
            })
        return {'rows': rows, 'stats': {
            'الأصناف': len(rows),
            'المتاح الكلي': round(sum(r['value'] or 0 for r in rows), 1),
            'أصناف منخفضة': low}}

    def _sec_deliveries(self, env, p):
        D = env['care.pms.delivery.note'].sudo()
        recs = D.search([('project_id', '=', p.id)], order='id desc', limit=200)
        state_lbl = dict(D._fields['state'].selection) if 'state' in D._fields else {}
        rows = [{
            'id': d.id, 'title': d.name or d.display_name,
            'subtitle': _d(d.date) if 'date' in d._fields else None,
            'state': (d.state if 'state' in d._fields else None),
            'state_label': state_lbl.get(d.state) if 'state' in d._fields else None,
            'badges': [x for x in [
                ('المستلم: %s' % d.receiver_id.name) if 'receiver_id' in d._fields and d.receiver_id else None,
                ('%s بند' % len(d.line_ids)) if 'line_ids' in d._fields else None,
            ] if x],
        } for d in recs]
        return {'rows': rows, 'stats': {'الإشعارات': len(rows)}}

    def _sec_supplies(self, env, p):
        S = env['care.pms.supply'].sudo()
        recs = S.search([('project_id', '=', p.id)], order='id desc', limit=200)
        state_lbl = dict(S._fields['state'].selection) if 'state' in S._fields else {}
        rows = []
        for s in recs:
            lines = s.line_ids if 'line_ids' in s._fields else []
            pend = sum(1 for l in lines if getattr(l, 'line_state', 'pending') == 'pending')
            rows.append({
                'id': s.id, 'title': s.name or s.display_name,
                'subtitle': _d(s.date) if 'date' in s._fields else None,
                'state': (s.state if 'state' in s._fields else None),
                'state_label': state_lbl.get(s.state) if 'state' in s._fields else None,
                'can_receive': bool('state' in s._fields and s.state in ('sent', 'partial')),
                'open': 'supply',
                'badges': (['%s بند' % len(lines)] +
                           (['%s بانتظار' % pend] if pend else [])),
            })
        return {'rows': rows, 'stats': {
            'الطلبات': len(rows),
            'بانتظار الاستلام': sum(1 for r in rows if r['can_receive']),
            'مكتملة': sum(1 for r in rows if r.get('state') == 'received')}}

    def _sec_petty(self, env, p):
        P = env['care.pms.petty.cash'].sudo()
        recs = P.search([('project_id', '=', p.id)], order='id desc', limit=100)
        state_lbl = dict(P._fields['state'].selection) if 'state' in P._fields else {}
        total = sum(r.amount for r in recs) if 'amount' in P._fields else 0
        spent = sum(r.spent for r in recs) if 'spent' in P._fields else 0
        rows = [{
            'id': r.id, 'title': r.name or r.display_name,
            'subtitle': _d(r.date) if 'date' in r._fields else None,
            'state': (r.state if 'state' in r._fields else None),
            'state_label': state_lbl.get(r.state) if 'state' in r._fields else None,
            'value': r.amount if 'amount' in r._fields else None,
            'value_label': 'العهدة',
            'spent': round(r.spent, 3) if 'spent' in r._fields else None,
            'remaining': round(r.remaining, 3) if 'remaining' in r._fields else None,
            'open': 'pettycash',
            'badges': [x for x in [
                ('المصروف: %s' % round(r.spent, 3)) if 'spent' in r._fields else None,
                ('المتبقي: %s' % round(r.remaining, 3)) if 'remaining' in r._fields else None,
            ] if x],
        } for r in recs]
        return {'rows': rows, 'stats': {'العُهد': len(rows), 'إجمالي العهدة': round(total, 3),
                                        'المصروف': round(spent, 3)}}

    def _sec_requests(self, env, p):
        R = env['care.pms.doc.request'].sudo()
        recs = R.search([('project_id', '=', p.id)], order='id desc', limit=300)
        state_lbl = dict(R._fields['state'].selection) if 'state' in R._fields else {}
        uid = env.uid

        def _row(r):
            emp = r.employee_id if 'employee_id' in r._fields and r.employee_id else None
            return {
                'id': r.id, 'title': r.display_name,
                'subtitle': (emp.name if emp else None),
                'state': (r.state if 'state' in r._fields else None),
                'state_label': state_lbl.get(r.state) if 'state' in r._fields else None,
                'badge': (emp.barcode if emp and 'barcode' in emp._fields else None),
                'image': _abs('/api/v1/pms/employee/%s/photo' % emp.id) if emp else None,
                'open': 'employee' if emp else None,
                'search': ('%s %s' % (emp.name or '', emp.barcode or '')).lower() if emp else '',
                'badges': ([_d(r.create_date)] if r.create_date else [])
                          + ([('طلب: %s' % r.requested_by.name)]
                             if 'requested_by' in r._fields and r.requested_by else []),
            }

        # Outgoing = requests THIS user raised; Incoming = raised by others in
        # the project (that a manager here oversees / must action).
        outgoing, incoming = [], []
        for r in recs:
            row = _row(r)
            mine = ('requested_by' in r._fields and r.requested_by and r.requested_by.id == uid)
            (outgoing if mine else incoming).append(row)
        pend_in = sum(1 for r in incoming if r['state'] in ('submitted', 'draft', 'pending'))
        return {
            'rows': outgoing, 'incoming': incoming,
            'tab_out': 'الصادرة', 'tab_in': 'الواردة',
            'stats': {'الصادرة': len(outgoing), 'الواردة': len(incoming),
                      'واردة معلّقة': pend_in},
        }

    def _sec_team(self, env, p):
        dept = self._dept(p)
        if not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا قسم مرتبط بهذا المشروع.'}
        from odoo import fields as of
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)], limit=500)
        # Live duty status from today's biometric attendance (two sets, one query).
        start = of.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        att = env['hr.attendance'].sudo().search(
            [('employee_id', 'in', emps.ids), ('check_in', '>=', start)]) if emps else env['hr.attendance']
        attended = set(att.mapped('employee_id').ids)
        on_site = set(att.filtered(lambda a: not a.check_out).mapped('employee_id').ids)

        def _srch(e):
            # A search blob so the list filters by badge / civil / passport /
            # phone / Arabic + English name — none of it displayed.
            parts = [e.name, e.job_title,
                     e.civil_code if 'civil_code' in e._fields else None,
                     e.identification_id if 'identification_id' in e._fields else None,
                     e.passport_id if 'passport_id' in e._fields else None,
                     e.barcode if 'barcode' in e._fields else None,
                     e.work_phone, e.mobile_phone,
                     e.registration_number if 'registration_number' in e._fields else None]
            return ' '.join(str(x) for x in parts if x).lower()

        wsel = dict(env['hr.employee']._fields['worker_status']._description_selection(env)) \
            if 'worker_status' in env['hr.employee']._fields else {}

        def _marks(e):
            out = []
            if 'current_leave_state' in e._fields and e.current_leave_state in ('validate', 'validate1'):
                out.append({'icon': 'flight', 'color': '#2563EB', 'label': 'إجازة'})
            if 'worker_status' in e._fields and e.worker_status:
                wl = (wsel.get(e.worker_status) or e.worker_status)
                low = ('%s %s' % (e.worker_status, wl)).lower()
                col = '#B91C1C' if ('abscond' in low or 'هروب' in low or 'هارب' in low) else \
                      ('#D97706' if ('suspend' in low or 'موقوف' in low or 'stop' in low) else
                       ('#16A34A' if ('active' in low or 'يعمل' in low) else '#6B7280'))
                out.append({'icon': 'badge', 'color': col, 'label': wl})
            return out

        rows = []
        for e in emps:
            if e.id in on_site:
                st, stl = 'on_site', 'بالموقع الآن'
            elif e.id in attended:
                st, stl = 'attended', 'داوم اليوم'
            else:
                st, stl = 'off', 'لم يداوم اليوم'
            rows.append({
                'id': e.id, 'title': e.name,
                'subtitle': e.job_title or None,
                'image': _abs('/api/v1/pms/employee/%s/photo' % e.id),
                'state': st, 'state_label': stl,
                'badge': e.barcode or None,
                'open': 'employee',
                'search': _srch(e),
                'marks': _marks(e),
                'tags': [t.name for t in e.category_ids] if 'category_ids' in e._fields else [],
                'badges': [x for x in [e.work_phone or None] if x],
            })
        return {'rows': rows, 'stats': {
            'العاملون': len(rows),
            'بالموقع الآن': len(on_site),
            'داوموا اليوم': len(attended)}}

    def _sec_attendance(self, env, p):
        dept = self._dept(p)
        if not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا قسم مرتبط بهذا المشروع.'}
        from odoo import fields as of
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)], limit=500)
        Att = env['hr.attendance'].sudo()
        start = of.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today = Att.search([('employee_id', 'in', emps.ids), ('check_in', '>=', start)]) if emps else Att.browse()
        recent = Att.search([('employee_id', 'in', emps.ids)], order='check_in desc', limit=80) if emps else Att.browse()
        here = set(today.filtered(lambda a: not a.check_out).mapped('employee_id').ids)
        attended_ids = set(today.mapped('employee_id').ids)
        rows = [{
            'id': a.id, 'title': a.employee_id.name,
            'subtitle': '%s → %s' % (_d(a.check_in) or '—', _d(a.check_out) or '—'),
            'value': round(a.worked_hours or 0.0, 1), 'value_label': 'ساعة',
            'state': 'open' if not a.check_out else 'closed',
            'state_label': 'بالموقع' if not a.check_out else 'انصرف',
            'search': (a.employee_id.name or '').lower(),
        } for a in recent]
        # Non-attendees split into ON-LEAVE (shown as «في إجازة», not counted as
        # absent) and truly ABSENT.
        absentees, on_leave = [], []
        for e in emps:
            if e.id in attended_ids:
                continue
            leave = ('current_leave_state' in e._fields and e.current_leave_state in ('validate', 'validate1'))
            base = {
                'id': e.id, 'title': e.name,
                'subtitle': e.job_title or None,
                'image': _abs('/api/v1/pms/employee/%s/photo' % e.id),
                'badge': e.barcode or None,
                'open': 'employee',
                'search': ('%s %s' % (e.name or '', e.barcode or '')).lower(),
            }
            if leave:
                base.update({'state': 'leave', 'state_label': 'في إجازة',
                             'marks': [{'icon': 'flight', 'color': '#2563EB', 'label': 'إجازة'}]})
                on_leave.append(base)
            else:
                base.update({'state': 'off', 'state_label': 'غائب اليوم'})
                absentees.append(base)
        # on-leave people surface at the top of the "absent" tab, clearly marked,
        # but are NOT in the absent count.
        return {'rows': rows, 'absentees': on_leave + absentees, 'stats': {
            'العاملون': len(emps), 'حضروا اليوم': len(attended_ids),
            'بالموقع الآن': len(here), 'في إجازة': len(on_leave),
            'الغائبون': len(absentees),
            'ساعات اليوم': round(sum(today.mapped('worked_hours') or [0]), 1)}}

    def _sec_timesheet(self, env, p):
        # care.timesheet is scoped by department and holds a period + lines —
        # it has no project_id and no hours field (checked against the model,
        # not assumed).
        dept = self._dept(p)
        if 'care.timesheet' not in env or not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا كشوف ساعات لهذا المشروع.'}
        T = env['care.timesheet'].sudo()
        recs = T.search([('department_id', '=', dept)], order='date_from desc, id desc', limit=100)
        state_lbl = dict(T._fields['state'].selection) if 'state' in T._fields else {}
        has_new = 'period_label' in T._fields
        rows = []
        total_appr = 0
        for t in recs:
            period = t.period_label if has_new and t.period_label else (
                '%s → %s' % (_d(t.date_from) or '—', _d(t.date_to) or '—'))
            appr = t.total_approved if has_new else 0
            total_appr += appr
            badges = []
            if has_new:
                badges = [x for x in [
                    ('بصمة: %s' % t.total_biometric) if t.total_biometric else None,
                    ('معتمد: %s' % appr) if appr else None,
                    ('بانتظار: %s' % t.pending_count) if t.pending_count else None,
                ] if x]
            rows.append({
                'id': t.id, 'title': '%s · %s' % (t.name or t.display_name, period),
                'subtitle': '%s عامل' % (len(t.line_ids)) if 'line_ids' in t._fields else None,
                'state': (t.state if 'state' in t._fields else None),
                'state_label': state_lbl.get(t.state) if 'state' in t._fields else None,
                'value': (t.emp_count if has_new else len(t.line_ids)),
                'value_label': 'عامل',
                'open': 'timesheet', 'badges': badges,
                'search': ('%s %s' % (t.name or '', period)).lower(),
            })
        return {'rows': rows, 'stats': {'الكشوف': len(rows),
                                        'العمال': sum(r['value'] or 0 for r in rows),
                                        'إجمالي المعتمد': total_appr}}

    def _sec_assets(self, env, p):
        dept = self._dept(p)
        if not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا قسم مرتبط بهذا المشروع.'}
        rows = []
        if 'care.custody' in env:
            for c in env['care.custody'].sudo().search([('department_id', '=', dept)], limit=200):
                rows.append({'id': c.id, 'title': c.display_name,
                             'subtitle': (c.employee_id.name if 'employee_id' in c._fields and c.employee_id else None),
                             'badges': ['عهدة']})
        if 'account.asset' in env:
            for a in env['account.asset'].sudo().search([('department_id', '=', dept)], limit=200):
                rows.append({'id': a.id, 'title': a.name, 'subtitle': None, 'badges': ['أصل']})
        return {'rows': rows, 'stats': {'السجلات': len(rows)}}

    def _sec_fuel(self, env, p):
        # New fuel module (cards + cash + receipts) takes over when installed.
        if 'care.fuel.entry' in env:
            return self._sec_fuel_new(env, p)
        dept = self._dept(p)
        if not dept or 'petrol.tank.use' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'لا بيانات وقود لهذا المشروع.'}
        from odoo import fields as of
        U = env['petrol.tank.use'].sudo()
        uses = U.search([('vehicle_id.department_id', '=', dept)], order='id desc', limit=300)
        month_start = of.Date.today().replace(day=1)
        rows = []
        month_l = 0.0
        vehset = set()
        for u in uses:
            qty = (u.use_quantity if 'use_quantity' in U._fields else
                   (u.quantity if 'quantity' in U._fields else 0.0)) or 0.0
            dt = u.datetime if 'datetime' in U._fields else None
            if dt and dt.date() >= month_start:
                month_l += qty
            if u.vehicle_id:
                vehset.add(u.vehicle_id.id)
            rows.append({
                'id': u.id,
                'vehicle_id': u.vehicle_id.id if u.vehicle_id else None,
                'title': (u.vehicle_id.display_name if u.vehicle_id else u.display_name),
                'subtitle': _d(dt),
                'open': 'vehicle' if u.vehicle_id else None,
                'value': round(qty, 1), 'value_label': 'لتر',
                'search': ('%s %s %s' % (u.vehicle_id.display_name if u.vehicle_id else '',
                                         _d(dt) or '',
                                         (u.vehicle_id.license_plate or '') if u.vehicle_id else '')).lower(),
                'badges': [x for x in [
                    ('العدّاد: %s' % int(u.odometer_value)) if 'odometer_value' in U._fields and u.odometer_value else None,
                ] if x],
            })
        total_l = round(sum(r['value'] or 0 for r in rows), 1)
        return {'rows': rows, 'stats': {
            'التعبئات': len(rows),
            'إجمالي اللترات': total_l,
            'لترات الشهر': round(month_l, 1),
            'متوسط التعبئة': round(total_l / len(rows), 1) if rows else 0,
            'السيارات': len(vehset)}}

    def _sec_fuel_new(self, env, p):
        """Fuel section backed by care.fuel.entry (prepaid cards / cash + receipts)."""
        from odoo import fields as of
        E = env['care.fuel.entry'].sudo()
        msel = dict(E._fields['method'].selection)
        ssel = dict(E._fields['state'].selection)
        recs = E.search([('project_id', '=', p.id)], order='date desc, id desc', limit=300)
        month_start = of.Date.today().replace(day=1)
        rows, month_amt, month_l = [], 0.0, 0.0
        for e in recs:
            if e.date and e.date.date() >= month_start:
                month_amt += e.amount or 0.0
                month_l += e.liters or 0.0
            rows.append({
                'id': e.id, 'title': (e.vehicle_id.display_name if e.vehicle_id else e.name),
                'subtitle': '%s · %s' % (msel.get(e.method, e.method), _d(e.date)),
                'value': round(e.amount or 0.0, 2), 'value_label': (e.currency_id.name or ''),
                'state': e.state, 'state_label': ssel.get(e.state, e.state),
                'open': 'fuel',
                'badges': [x for x in [
                    ('%s لتر' % round(e.liters, 1)) if e.liters else None,
                    ('بطاقة: %s' % e.card_id.name) if e.method == 'card' and e.card_id else None,
                    'عهدة نقدية' if e.method == 'cash' else None,
                    '📎 إيصال' if e.receipt else None,
                ] if x],
                'search': ('%s %s %s %s' % (
                    e.name or '', e.vehicle_id.display_name if e.vehicle_id else '',
                    e.station or '', e.card_id.name if e.card_id else '')).lower(),
            })
        cards = env['care.fuel.card'].sudo().search([('project_id', '=', p.id)])
        return {'rows': rows, 'stats': {
            'التعبئات': len(rows),
            'مبلغ الشهر': round(month_amt, 2),
            'لترات الشهر': round(month_l, 1),
            'البطاقات': len(cards),
            'رصيد البطاقات': round(sum(cards.mapped('balance')), 2)}}

    def _sec_compliance(self, env, p):
        dept = self._dept(p)
        if not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا قسم مرتبط بهذا المشروع.'}
        E = env['hr.employee'].sudo()
        from odoo import fields as of
        today = of.Date.today()
        # The real field names on this DB — checked against the model rather
        # than guessed (residency_expiry/permit_expiry do not exist here).
        docs = [('residency_end_date', 'الإقامة'), ('affairs_permit_end_date', 'إذن الشؤون'),
                ('visa_expire', 'التأشيرة'), ('work_permit_expiration_date', 'تصريح العمل'),
                ('passport_expiry_date', 'الجواز')]
        docs = [(f, l) for f, l in docs if f in E._fields]
        emps = E.search([('department_id', '=', dept)], limit=500)
        rows, soon, expired = [], 0, 0
        for e in emps:
            items, worst = [], None
            for fld, lbl in docs:
                if not e[fld]:
                    continue
                days = (e[fld] - today).days
                items.append({'label': lbl, 'date': str(e[fld]), 'days': days})
                if worst is None or days < worst:
                    worst = days
            if not items:
                continue
            if worst is not None and worst < 0:
                expired += 1
            elif worst is not None and worst <= 60:
                soon += 1
            rows.append({
                'id': e.id, 'title': e.name, 'subtitle': e.job_title or None,
                'image': _abs('/api/v1/pms/employee/%s/photo' % e.id),
                'badge': e.barcode or None,
                'open': 'employee',
                'value': worst, 'value_label': 'يوم',
                'state': ('expired' if (worst is not None and worst < 0)
                          else 'soon' if (worst is not None and worst <= 60) else 'ok'),
                'state_label': ('منتهية' if (worst is not None and worst < 0)
                                else 'تنتهي قريبًا' if (worst is not None and worst <= 60) else 'سارية'),
                'badges': ['%s: %s (%s يوم)' % (i['label'], i['date'], i['days']) for i in items],
                'search': ('%s %s' % (e.name or '', e.barcode or '')).lower(),
            })
        # Worst first — this section exists to surface what is about to lapse.
        rows.sort(key=lambda r: (r['value'] if r['value'] is not None else 9999))
        return {'rows': rows, 'stats': {'العاملون بوثائق': len(rows),
                                        'منتهية': expired, 'تنتهي خلال 60 يومًا': soon}}

    _INV_PAY_LABEL = {'not_paid': 'غير مدفوعة', 'in_payment': 'قيد الدفع',
                      'paid': 'مدفوعة', 'partial': 'مدفوعة جزئيًّا', 'reversed': 'معكوسة',
                      'invoicing_legacy': 'قديمة'}

    def _sec_invoices(self, env, p):
        M = env['account.move'].sudo()
        if 'project_id' not in M._fields:
            return {'rows': [], 'stats': {}, 'empty': 'لا فواتير مرتبطة بهذا المشروع.'}
        recs = M.search([('project_id', '=', p.id),
                         ('move_type', 'in', ('out_invoice', 'out_refund'))],
                        order='invoice_date desc, id desc', limit=200)
        st_lbl = dict(M._fields['state'].selection)
        rows, total, residual, paid_n = [], 0.0, 0.0, 0
        for m in recs:
            total += m.amount_total
            residual += m.amount_residual
            if m.payment_state in ('paid', 'in_payment'):
                paid_n += 1
            rows.append({
                'id': m.id, 'title': m.name or '/',
                'subtitle': m.partner_id.name or None,
                'value': round(m.amount_total, 2), 'value_label': m.currency_id.name or '',
                'state': m.payment_state,
                'state_label': self._INV_PAY_LABEL.get(m.payment_state, m.payment_state),
                'open': 'invoice',
                'badges': [x for x in [
                    _d(m.invoice_date),
                    st_lbl.get(m.state),
                    ('متبقّي: %s' % round(m.amount_residual, 2)) if m.amount_residual > 0.001 else None,
                ] if x],
                'search': ('%s %s' % (m.name or '', m.partner_id.name or '')).lower(),
            })
        return {'rows': rows, 'stats': {
            'الفواتير': len(rows),
            'الإجمالي': round(total, 2),
            'المتبقّي': round(residual, 2),
            'مدفوعة': paid_n}}

    def _sec_finance(self, env, p):
        rows, stats = [], {}
        try:
            SO = env['sale.order'].sudo()
            orders = SO.search([('project_id', '=', p.id)], limit=100) if 'project_id' in SO._fields else SO.browse()
            for o in orders:
                rows.append({'id': o.id, 'title': o.name, 'subtitle': _d(o.date_order),
                             'value': o.amount_total, 'value_label': o.currency_id.name,
                             'state': o.state, 'state_label': dict(SO._fields['state'].selection).get(o.state)})
            stats['أوامر البيع'] = len(rows)
            stats['الإجمالي'] = round(sum(r['value'] or 0 for r in rows), 3)
        except Exception:
            pass
        return {'rows': rows, 'stats': stats}

    def _sec_contracts(self, env, p):
        rows = []
        model = 'care.experience.contract' if 'care.experience.contract' in env else None
        if model and 'project_id' in env[model]._fields:
            for c in env[model].sudo().search([('project_id', '=', p.id)], limit=100):
                rows.append({'id': c.id, 'title': c.display_name,
                             'subtitle': (_d(c.date_start) if 'date_start' in c._fields else None),
                             'state': (c.state if 'state' in c._fields else None)})
        return {'rows': rows, 'stats': {'العقود': len(rows)},
                'empty': None if rows else 'لا عقود مرتبطة بهذا المشروع.'}

    def _sec_performance(self, env, p):
        dept = self._dept(p)
        if not dept or 'care.performance.log' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'لا سجل أداء لهذا المشروع.'}
        from odoo import fields as of
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)], limit=300)
        year_start = of.Date.today().replace(month=1, day=1)
        logs = env['care.performance.log'].sudo().search(
            [('employee_id', 'in', emps.ids), ('date', '>=', year_start)])
        by_emp = {}
        for l in logs:
            d = by_emp.setdefault(l.employee_id.id, {'name': l.employee_id.name, 'points': 0.0, 'n': 0})
            d['points'] += (l.points if 'points' in l._fields else 0.0)
            d['n'] += 1
        rows = [{'id': k, 'title': v['name'], 'subtitle': '%s حدث' % v['n'],
                 'value': round(v['points'], 1), 'value_label': 'نقطة'}
                for k, v in sorted(by_emp.items(), key=lambda i: -i[1]['points'])]
        return {'rows': rows, 'stats': {'العاملون': len(rows), 'الأحداث': len(logs)}}

    def _sec_permits(self, env, p):
        """Project permits (security / health / food …) with expiry status."""
        if 'care.project.permit' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'وحدة تصاريح المشاريع غير مثبّتة.'}
        M = env['care.project.permit'].sudo()
        tsel = dict(M._fields['permit_type'].selection)
        stsel = dict(M._fields['status'].selection)
        recs = M.search([('project_id', '=', p.id)], order='expiry_date', limit=300)
        rows, expiring, expired = [], 0, 0
        for r in recs:
            if r.status == 'expiring':
                expiring += 1
            elif r.status == 'expired':
                expired += 1
            state_map = {'valid': 'ok', 'expiring': 'soon', 'expired': 'expired', 'none': 'draft'}
            rows.append({
                'id': r.id, 'title': r.title or r.name,
                'subtitle': '%s · %s' % (tsel.get(r.permit_type, r.permit_type or ''),
                                         (r.authority or '—')),
                'state': state_map.get(r.status, 'draft'),
                'state_label': stsel.get(r.status, r.status),
                'value': r.days_to_expiry if r.expiry_date else None, 'value_label': 'يوم',
                'open': 'permit',
                'badges': [x for x in [
                    ('ينتهي: %s' % _d(r.expiry_date)) if r.expiry_date else None,
                    ('رقم: %s' % r.permit_number) if r.permit_number else None,
                    '📎 مرفق' if r.attachment else None,
                ] if x],
                'search': ('%s %s %s' % (r.title or '', r.authority or '', r.permit_number or '')).lower(),
            })
        return {'rows': rows, 'stats': {
            'التصاريح': len(rows), 'قاربت الانتهاء': expiring, 'منتهية': expired}}

    def _sec_manpower(self, env, p):
        """Manpower requisitions raised for this project."""
        if 'manpower.requisition' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'وحدة طلب القوى العاملة غير مثبّتة.'}
        M = env['manpower.requisition'].sudo()
        ssel = dict(M._fields['state'].selection)
        tsel = dict(M._fields['type'].selection)
        recs = M.search([('project_id', '=', p.id)], order='id desc', limit=300)
        rows, pend, total_req = [], 0, 0
        for r in recs:
            if r.state == 'submit':
                pend += 1
            total_req += r.requirement_number or 0
            titles = ', '.join(r.required_title.mapped('name')) if r.required_title else '—'
            rows.append({
                'id': r.id, 'title': titles,
                'subtitle': '%s · %s' % (tsel.get(r.type, r.type or ''), _d(r.request_date)),
                'value': r.requirement_number, 'value_label': 'عدد',
                'state': r.state, 'state_label': ssel.get(r.state, r.state),
                'open': 'manpower',
                'badges': [x for x in [
                    ('الراتب: %s' % round(r.salary, 2)) if r.salary else None,
                    (r.location or None),
                ] if x],
                'search': ('%s %s' % (titles, r.location or '')).lower(),
            })
        return {'rows': rows, 'stats': {
            'الطلبات': len(rows), 'إجمالي المطلوب': total_req, 'بانتظار الاعتماد': pend}}

    def _sec_items(self, env, p):
        """Item/material requests raised by the PM for this project."""
        if 'care.item.request' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'وحدة طلب الأصناف غير مثبّتة.'}
        R = env['care.item.request'].sudo()
        ssel = dict(R._fields['state'].selection)
        recs = R.search([('project_id', '=', p.id)], order='id desc', limit=300)
        rows, pend = [], 0
        for r in recs:
            if r.state == 'submitted':
                pend += 1
            rows.append({
                'id': r.id, 'title': r.name,
                'subtitle': '%s صنف · %s' % (r.line_count, _d(r.request_date)),
                'state': r.state, 'state_label': ssel.get(r.state, r.state),
                'value': round(r.total_qty, 1), 'value_label': 'كمية',
                'open': 'item_request',
                'badges': [x for x in [
                    'عاجل' if r.priority == '1' else None,
                    ('التوريد: %s' % r.supply_id.name) if r.supply_id else None,
                ] if x],
                'search': ('%s' % (r.name or '')).lower(),
            })
        return {'rows': rows, 'stats': {
            'الطلبات': len(rows), 'بانتظار الاعتماد': pend,
            'معتمدة': sum(1 for r in recs if r.state == 'approved')}}

    def _sec_suspension(self, env, p):
        """Work-suspension requests raised for this project's workers."""
        if 'care.suspension.request' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'وحدة الإيقاف عن العمل غير مثبّتة.'}
        S = env['care.suspension.request'].sudo()
        rsel = dict(S._fields['reason'].selection)
        ssel = dict(S._fields['state'].selection)
        recs = S.search([('project_id', '=', p.id)], order='id desc', limit=300)
        rows, pend = [], 0
        for r in recs:
            if r.state == 'submitted':
                pend += 1
            rows.append({
                'id': r.id, 'title': r.employee_id.name or r.name,
                'subtitle': '%s · %s' % (rsel.get(r.reason, r.reason or '—'), _d(r.date)),
                'state': r.state, 'state_label': ssel.get(r.state, r.state),
                'open': 'suspension',
                'badges': [x for x in [
                    ('بادج: %s' % r.badge) if r.badge else None,
                    'لديه بدلات' if r.has_allowance else None,
                ] if x],
                'search': ('%s %s %s' % (r.name or '', r.employee_id.name or '', r.badge or '')).lower(),
            })
        return {'rows': rows, 'stats': {
            'الطلبات': len(rows),
            'بانتظار الاعتماد': pend,
            'معتمدة': sum(1 for r in recs if r.state == 'approved')}}

    SECTIONS = {
        'materials': ('المواد', 'inventory', _sec_materials),
        'deliveries': ('إشعارات التسليم', 'receipt', _sec_deliveries),
        'supplies': ('التوريدات', 'local_shipping', _sec_supplies),
        'petty': ('العهدة النقدية', 'payments', _sec_petty),
        'requests': ('طلبات المستندات', 'description', _sec_requests),
        'team': ('الفريق', 'groups', _sec_team),
        'attendance': ('الحضور', 'schedule', _sec_attendance),
        'timesheet': ('ساعات العمل', 'timer', _sec_timesheet),
        'assets': ('الأصول والعهد', 'precision_manufacturing', _sec_assets),
        'fuel': ('الوقود', 'local_gas_station', _sec_fuel),
        'compliance': ('الامتثال والوثائق', 'verified_user', _sec_compliance),
        'invoices': ('فواتير المشروع', 'receipt_long', _sec_invoices),
        'finance': ('المالية', 'account_balance', _sec_finance),
        'contracts': ('العقود', 'assignment', _sec_contracts),
        'performance': ('الأداء', 'trending_up', _sec_performance),
        'suspension': ('الإيقاف عن العمل', 'block', _sec_suspension),
        'items': ('طلب الأصناف', 'playlist_add_check', _sec_items),
        'manpower': ('طلب قوى عاملة', 'groups_3', _sec_manpower),
        'permits': ('التصاريح', 'verified_user', _sec_permits),
    }

    @route(API + '/pms/project/<int:pid>/sections', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_sections(self, pid, **kw):
        """The menu of sections available for this project."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            p = self._project(env, pid)
        except Exception:
            return _err('لا صلاحية على هذا المشروع', 403)
        if not p:
            return _err('غير موجود', 404)
        # which sections are delegated (to show a small badge on the tile)
        deleg = {}
        if 'care.pms.delegation' in env:
            for d in env['care.pms.delegation'].sudo().search([('project_id', '=', pid)]):
                if getattr(d, 'active', True):
                    deleg[d.section_code] = (d.delegate_id.name if d.delegate_id else None)
        return _ok({
            'project': {'id': p.id, 'name': p.name},
            'sections': [{'code': c, 'label': v[0], 'icon': v[1],
                          'delegated': c in deleg,
                          'delegate': deleg.get(c)} for c, v in self.SECTIONS.items()],
        })

    @route(API + '/pms/project/<int:pid>/section/<string:code>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_section(self, pid, code, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self.SECTIONS.get(code)
        if not spec:
            return _err('قسم غير معروف', 404)
        try:
            p = self._project(env, pid)
        except Exception:
            return _err('لا صلاحية على هذا المشروع', 403)
        if not p:
            return _err('غير موجود', 404)
        try:
            data = spec[2](self, env, p)
        except Exception as e:
            # A section whose model is missing on this DB must not take the
            # whole screen down — say what happened instead.
            return _ok({'code': code, 'label': spec[0], 'rows': [], 'stats': {},
                        'empty': 'تعذّر تحميل هذا القسم: %s' % e})
        data.update({'code': code, 'label': spec[0], 'project': {'id': p.id, 'name': p.name}})
        data.setdefault('empty', None)
        return _ok(data)

    def _writable_project(self, env, pid):
        """The project if the caller may act on it, else None. Uses the caller's
        access rules — sudo writes below are hard-scoped to this project."""
        p = env['project.project'].browse(int(pid))
        try:
            p.check_access_rule('read')
        except Exception:
            return None
        return p.exists() or None

    def _emp_pick(self, env, dept):
        """Rich employee pick-list (name + badge + photo + status), scoped to the
        project department — used by every employee picker for a consistent,
        searchable-by-badge list."""
        if not dept:
            return []
        E = env['hr.employee']
        wsel = dict(E._fields['worker_status']._description_selection(env)) if 'worker_status' in E._fields else {}
        out = []
        for e in E.sudo().search([('department_id', '=', dept)], limit=800):
            status = (wsel.get(e.worker_status, e.worker_status)
                      if 'worker_status' in e._fields and e.worker_status else None)
            out.append({
                'id': e.id, 'name': e.name, 'badge': e.barcode or None,
                'avatar': _abs('/api/v1/pms/employee/%s/photo' % e.id),
                'status': status,
                'on_leave': bool('current_leave_state' in e._fields
                                 and e.current_leave_state in ('validate', 'validate1')),
                'job': e.job_title or None,
                'search': ('%s %s %s' % (
                    e.name or '', e.barcode or '',
                    (e.civil_code if 'civil_code' in e._fields else '') or '')).lower(),
            })
        return out

    @route(API + '/pms/project/<int:pid>/section/<string:code>/options', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_section_options(self, pid, code, **kw):
        """The pick-lists a section's create form needs (materials, employees,
        expense categories, doc types…), scoped to this project."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        dept = self._dept(p)
        out = {}
        if code == 'deliveries':
            out['materials'] = [{'id': m.id, 'name': m.display_name}
                                for m in env['care.pms.material'].sudo().search([('project_id', '=', p.id)], limit=300)]
        elif code == 'supplies':
            # Only supplies still in transit can be received.
            out['receivable'] = [{'id': s.id, 'name': s.display_name}
                                 for s in env['care.pms.supply'].sudo().search(
                                     [('project_id', '=', p.id), ('state', '=', 'sent')], limit=200)]
        elif code == 'petty':
            EX = env['care.pms.petty.cash.expense']
            out['categories'] = [{'value': k, 'label': v}
                                 for k, v in EX._fields['category'].selection]
            out['cash'] = [{'id': c.id, 'name': c.display_name}
                           for c in env['care.pms.petty.cash'].sudo().search([('project_id', '=', p.id)], limit=100)]
        elif code == 'requests':
            DR = env['care.pms.doc.request']
            out['doc_types'] = [{'value': k, 'label': v}
                                for k, v in DR._fields['doc_type'].selection]
            out['employees'] = self._emp_pick(env, dept)
        elif code == 'assets':
            if 'care.custody' in env and 'item_type' in env['care.custody']._fields:
                out['item_types'] = [{'value': k, 'label': v}
                                     for k, v in env['care.custody']._fields['item_type'].selection]
            out['employees'] = self._emp_pick(env, dept)
        elif code == 'fuel':
            out['vehicles'] = [{'id': v.id, 'name': v.display_name}
                               for v in (env['fleet.vehicle'].sudo().search(
                                   [('department_id', '=', dept)], limit=300)
                                   if dept and 'fleet.vehicle' in env else [])]
            if 'care.fuel.entry' in env:
                out['new_fuel'] = True
                out['methods'] = [{'value': k, 'label': v}
                                  for k, v in env['care.fuel.entry']._fields['method'].selection]
                out['cards'] = [{'id': c.id, 'name': '%s — %s %s' % (
                                    c.name, round(c.balance, 2), c.currency_id.name or ''),
                                 'balance': round(c.balance, 2)}
                                for c in env['care.fuel.card'].sudo().search(
                                    [('project_id', '=', p.id), ('state', '=', 'active')], limit=200)]
                out['petty'] = [{'id': c.id, 'name': c.display_name}
                                for c in env['care.pms.petty.cash'].sudo().search(
                                    [('project_id', '=', p.id)], limit=100)] if 'care.pms.petty.cash' in env else []
                # employees (drivers) for this project's department
                out['drivers'] = self._emp_pick(env, dept)
        elif code == 'timesheet':
            # optional single-worker (custom) timesheet
            out['employees'] = self._emp_pick(env, dept)
        elif code == 'manpower':
            if 'manpower.requisition' in env:
                out['types'] = [{'value': k, 'label': v}
                                for k, v in env['manpower.requisition']._fields['type'].selection]
                out['jobs'] = [{'id': j.id, 'name': j.name}
                               for j in env['hr.job'].sudo().search([], limit=300)]
        elif code == 'permits':
            if 'care.project.permit' in env:
                out['types'] = [{'value': k, 'label': v}
                                for k, v in env['care.project.permit']._fields['permit_type'].selection]
                out['employees'] = self._emp_pick(env, dept)
        elif code == 'suspension':
            out['employees'] = self._emp_pick(env, dept)
            if 'care.suspension.request' in env:
                out['reasons'] = [{'value': k, 'label': v}
                                  for k, v in env['care.suspension.request']._fields['reason'].selection]
        return _ok(out)

    @route(API + '/pms/project/<int:pid>/custody/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_custody_create(self, pid, **kw):
        """Raise a custody request (طلب عهدة) against a project's department."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        if 'care.custody' not in env:
            return _err('نظام العهد غير متاح', 404)
        dept = self._dept(p)
        if not dept:
            return _err('لا قسم مرتبط بهذا المشروع', 422)
        from .api import _body
        b = _body() or {}
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اكتب اسم العهدة', 422)
        if not b.get('employee_id'):
            return _err('اختر الموظف المستلم', 422)
        vals = {'name': name, 'department_id': dept,
                'employee_id': int(b['employee_id'])}
        C = env['care.custody'].sudo()
        if b.get('item_type') and 'item_type' in C._fields:
            vals['item_type'] = b['item_type']
        if b.get('description') and 'description' in C._fields:
            vals['description'] = b['description']
        if b.get('note') and 'note' in C._fields:
            vals['note'] = b['note']
        if b.get('value') and 'value' in C._fields:
            try:
                vals['value'] = float(b['value'])
            except (TypeError, ValueError):
                pass
        if b.get('issue_date') and 'issue_date' in C._fields:
            vals['issue_date'] = b['issue_date']
        try:
            rec = C.create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء طلب العهدة', 422)
        return _ok({'id': rec.id, 'name': rec.display_name,
                    'state': rec.state if 'state' in C._fields else None})

    @route(API + '/pms/project/<int:pid>/material/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_material_create(self, pid, **kw):
        """Register a material on the project."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        if 'care.pms.material' not in env:
            return _err('غير متاح', 404)
        from .api import _body
        b = _body() or {}
        name = (b.get('name') or '').strip()
        if not name:
            return _err('اكتب اسم المادة', 422)
        M = env['care.pms.material'].sudo()
        vals = {'name': name, 'project_id': p.id}
        for q in ('qty', 'quantity', 'qty_available'):
            if q in M._fields and b.get('qty'):
                try:
                    vals[q] = float(b['qty'])
                except (TypeError, ValueError):
                    pass
                break
        try:
            rec = M.create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر إضافة المادة', 422)
        return _ok({'id': rec.id, 'name': rec.display_name})

    @route(API + '/pms/material/<int:mid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_material_detail(self, mid, **kw):
        """A material's full ledger: receipts (in), issues (out), available."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = env['care.pms.material'].sudo().browse(int(mid)).exists()
        if not m:
            return _err('غير موجود', 404)
        try:
            env['project.project'].browse(m.project_id.id).check_access_rule('read')
        except Exception:
            return _err('لا صلاحية', 403)
        receipts = [{'id': r.id, 'date': _d(r.date) if 'date' in r._fields else None,
                     'qty': round(r.qty, 1), 'ref': (r.ref or None) if 'ref' in r._fields else None}
                    for r in m.receipt_ids] if 'receipt_ids' in m._fields else []
        issues = []
        if 'line_ids' in m._fields:
            for l in m.line_ids:
                note = l.note_id if 'note_id' in l._fields else None
                issues.append({
                    'id': l.id, 'qty': round(l.qty, 1),
                    'date': _d(note.date) if note and 'date' in note._fields else None,
                    'note': note.name if note else None,
                    'state': note.state if note and 'state' in note._fields else None,
                    'state_label': (dict(note._fields['state'].selection).get(note.state)
                                    if note and 'state' in note._fields else None),
                })
        uom = (m.uom_name if 'uom_name' in m._fields and m.uom_name
               else (m.uom_id.name if 'uom_id' in m._fields and m.uom_id else None))
        has_img = bool('product_id' in m._fields and m.product_id and m.product_id.image_128)
        return _ok({
            'id': m.id, 'name': m.name, 'uom': uom,
            'image': (_abs('/pms/product/%s/image' % m.product_id.id) if has_img else None),
            'received': round(m.received_qty, 1) if 'received_qty' in m._fields else 0,
            'issued': round(m.issued_qty, 1) if 'issued_qty' in m._fields else 0,
            'available': round(m.available_qty, 1) if 'available_qty' in m._fields else 0,
            'min_qty': round(m.min_qty, 1) if 'min_qty' in m._fields else 0,
            'is_low': bool('is_low' in m._fields and m.is_low),
            'receipts': receipts, 'issues': issues,
        })

    @route(API + '/pms/material/<int:mid>/delete', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_material_delete(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = env['care.pms.material'].browse(int(mid))
        try:
            m.check_access_rule('unlink')
            m.sudo().unlink()
        except Exception as e:
            return _err(str(e) or 'تعذّر الحذف (قد توجد حركات مرتبطة)', 422)
        return _ok({'deleted': True})

    @route(API + '/pms/project/<int:pid>/fuel/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_fuel_create(self, pid, **kw):
        """Record a fuel fill for a project vehicle."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        from odoo import fields as of
        b = _body() or {}
        # New fuel module: card / cash fill with receipt.
        if 'care.fuel.entry' in env:
            return self._fuel_new_create(env, p, b)
        if 'petrol.tank.use' not in env:
            return _err('نظام الوقود غير متاح', 404)
        if not b.get('vehicle_id'):
            return _err('اختر السيارة', 422)
        try:
            liters = float(b.get('liters') or 0)
        except (TypeError, ValueError):
            liters = 0
        if liters <= 0:
            return _err('أدخل كمية اللترات', 422)
        U = env['petrol.tank.use'].sudo()
        vals = {'vehicle_id': int(b['vehicle_id'])}
        if 'use_quantity' in U._fields:
            vals['use_quantity'] = liters
        elif 'quantity' in U._fields:
            vals['quantity'] = liters
        if b.get('odometer') and 'odometer_value' in U._fields:
            try:
                vals['odometer_value'] = float(b['odometer'])
            except (TypeError, ValueError):
                pass
        if 'datetime' in U._fields:
            vals['datetime'] = b.get('datetime') or of.Datetime.now()
        if 'name' in U._fields and 'name' not in vals:
            vals['name'] = b.get('name') or '/'
        try:
            rec = U.create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر تسجيل التعبئة', 422)
        return _ok({'id': rec.id, 'name': rec.display_name})

    # ============ NEW FUEL MODULE (cards / cash + receipt) ============
    def _fuel_json(self, env, e):
        E = env['care.fuel.entry']
        msel = dict(E._fields['method'].selection)
        ssel = dict(E._fields['state'].selection)
        return {
            'id': e.id, 'name': e.name, 'date': _d(e.date),
            'project': e.project_id.name if e.project_id else None,
            'vehicle': e.vehicle_id.display_name if e.vehicle_id else None,
            'vehicle_id': e.vehicle_id.id if e.vehicle_id else None,
            'driver': e.driver_id.name if e.driver_id else None,
            'method': e.method, 'method_label': msel.get(e.method, e.method),
            'card': e.card_id.name if e.card_id else None,
            'card_balance': round(e.card_id.balance, 2) if e.card_id else None,
            'petty': e.petty_cash_id.display_name if e.petty_cash_id else None,
            'amount': e.amount, 'currency': e.currency_id.name if e.currency_id else None,
            'liters': e.liters, 'price_per_liter': round(e.price_per_liter, 3),
            'odometer': e.odometer, 'station': e.station or None, 'note': e.note or None,
            'state': e.state, 'state_label': ssel.get(e.state, e.state),
            'is_latest': e.is_latest, 'editable': e.is_latest,
            'has_receipt': bool(e.receipt),
            'receipt_url': _abs('/api/v1/pms/fuel/%s/receipt' % e.id) if e.receipt else None,
            'report_url': _abs('/api/v1/pms/fuel/%s/report' % e.id),
            'can_confirm': e.state == 'draft',
            'can_draft': e.state == 'confirmed' and e.is_latest,
        }

    def _fuel_new_create(self, env, p, b):
        from odoo import fields as of
        method = b.get('method') or 'card'
        try:
            liters = float(b.get('liters') or 0)
            amount = float(b.get('amount') or 0)
        except (TypeError, ValueError):
            return _err('قيم غير صحيحة', 422)
        if amount <= 0:
            return _err('أدخل المبلغ', 422)
        if method == 'card' and not b.get('card_id'):
            return _err('اختر بطاقة الوقود', 422)
        vals = {
            'project_id': p.id, 'method': method, 'amount': amount, 'liters': liters,
            'date': b.get('date') or of.Datetime.now(),
            'station': b.get('station') or False, 'note': b.get('note') or False,
        }
        if b.get('vehicle_id'):
            vals['vehicle_id'] = int(b['vehicle_id'])
        if b.get('driver_id'):
            vals['driver_id'] = int(b['driver_id'])
        if method == 'card' and b.get('card_id'):
            vals['card_id'] = int(b['card_id'])
        if method == 'cash' and b.get('petty_cash_id'):
            vals['petty_cash_id'] = int(b['petty_cash_id'])
        if b.get('odometer'):
            try:
                vals['odometer'] = float(b['odometer'])
            except (TypeError, ValueError):
                pass
        if b.get('receipt'):
            import re
            raw = re.sub(r'^data:[^,]+,', '', b['receipt'])
            vals['receipt'] = raw
            vals['receipt_filename'] = b.get('receipt_filename') or 'receipt.jpg'
        try:
            rec = env['care.fuel.entry'].sudo().create(vals)
            if b.get('confirm'):
                rec.action_confirm()
        except Exception as e:
            return _err(str(e) or 'تعذّر تسجيل التعبئة', 422)
        return _ok(self._fuel_json(env, rec))

    def _fuel_scoped(self, env, fid):
        if 'care.fuel.entry' not in env:
            return None
        e = env['care.fuel.entry'].sudo().browse(int(fid)).exists()
        if not e:
            return None
        if not self._writable_project(env, e.project_id.id) and not (
                env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')):
            return None
        return e

    @route(API + '/pms/fuel/<int:fid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_fuel_get(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        e = self._fuel_scoped(env, fid)
        if not e:
            return _err('غير موجود أو لا صلاحية', 404)
        return _ok(self._fuel_json(env, e))

    @route(API + '/pms/fuel/<int:fid>/update', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_fuel_update(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        e = self._fuel_scoped(env, fid)
        if not e:
            return _err('غير موجود أو لا صلاحية', 404)
        from .api import _body
        b = _body() or {}
        vals = {}
        for f, cast in (('amount', float), ('liters', float), ('odometer', float),
                        ('station', str), ('note', str), ('method', str)):
            if f in b and b[f] not in (None, ''):
                try:
                    vals[f] = cast(b[f])
                except (TypeError, ValueError):
                    pass
        for f in ('vehicle_id', 'driver_id', 'card_id', 'petty_cash_id'):
            if b.get(f):
                vals[f] = int(b[f])
        if b.get('receipt'):
            import re
            vals['receipt'] = re.sub(r'^data:[^,]+,', '', b['receipt'])
            vals['receipt_filename'] = b.get('receipt_filename') or 'receipt.jpg'
        try:
            e.write(vals)
        except Exception as ex:
            return _err(str(ex) or 'تعذّر التعديل', 422)
        return _ok(self._fuel_json(env, e))

    @route(API + '/pms/fuel/<int:fid>/<string:act>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_fuel_action(self, fid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        e = self._fuel_scoped(env, fid)
        if not e:
            return _err('غير موجود أو لا صلاحية', 404)
        try:
            if act == 'confirm':
                e.action_confirm()
            elif act == 'draft':
                e.action_draft()
            elif act == 'delete':
                if not e.is_latest:
                    return _err('لا يمكن حذف عملية قديمة', 422)
                e.unlink()
                return _ok({'deleted': fid})
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as ex:
            return _err(str(ex) or 'تعذّر تنفيذ الإجراء', 422)
        return _ok(self._fuel_json(env, e))

    @route(API + '/pms/fuel/<int:fid>/receipt', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_fuel_receipt(self, fid, **kw):
        # Token-free image endpoint (same pattern as petty-expense receipts) so it
        # renders inline in Image.network without threading an auth header.
        e = request.env['care.fuel.entry'].sudo().browse(int(fid)).exists()
        if not e or not e.receipt:
            return request.not_found()
        import base64
        data = base64.b64decode(e.receipt)
        return request.make_response(data, headers=[
            ('Content-Type', 'image/jpeg'),
            ('Content-Disposition', 'inline; filename="receipt-%s.jpg"' % fid)])

    @route(API + '/pms/fuel/<int:fid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_fuel_report(self, fid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        e = self._fuel_scoped(env, fid)
        if not e:
            return request.make_response('لا صلاحية', status=403)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(
                'care_fuel.report_fuel_entry_doc', [e.id])
        except Exception as ex:
            return request.make_response(str(ex), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="fuel-%s.pdf"' % fid)])

    # ---- timesheet: view, edit lines (policy), submit, delete draft --------
    @route(API + '/pms/timesheet/<int:tid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_timesheet_detail(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.timesheet' not in env:
            return _err('غير متاح', 404)
        ts = env['care.timesheet'].sudo().browse(tid).exists()
        if not ts:
            return _err('غير موجود', 404)
        st_lbl = dict(ts._fields['state'].selection) if 'state' in ts._fields else {}
        is_draft = (ts.state == 'draft') if 'state' in ts._fields else False
        has_new = 'adjusted_days' in env['care.timesheet.line']._fields
        is_hr = bool(env.user.has_group('hr.group_hr_user')
                     or env.user.has_group('base.group_erp_manager')
                     or env.user.has_group('base.group_system'))
        lsel = dict(env['care.timesheet.line']._fields['line_state'].selection) if has_new else {}
        lines = []
        for l in ts.line_ids:
            row = {
                'id': l.id,
                'employee': l.employee_id.name if l.employee_id else '—',
                'employee_id': l.employee_id.id if l.employee_id else None,
                'badge': l.employee_id.barcode if l.employee_id and 'barcode' in l.employee_id._fields else None,
                'biometric': l.actual if 'actual' in l._fields else None,
                'search': ('%s %s' % (
                    l.employee_id.name or '',
                    (l.employee_id.barcode or '') if 'barcode' in l.employee_id._fields else '')
                ).lower() if l.employee_id else '',
            }
            if has_new:
                row.update({
                    'adjusted': l.adjusted_days, 'approved': l.approved_days,
                    'diff': l.diff, 'note': l.note or None,
                    'has_doc': bool(l.document),
                    'doc_url': _abs('/api/v1/pms/timesheet/line/%s/doc' % l.id) if l.document else None,
                    'line_state': l.line_state, 'line_state_label': lsel.get(l.line_state, l.line_state),
                    'approved_by': l.approved_by.name if l.approved_by else None,
                    # HR may approve/reject; the PM may adjust while pending & not final
                    'can_approve': is_hr and l.line_state == 'pending',
                    'can_reject': is_hr and l.line_state == 'pending',
                    'can_edit': l.line_state == 'pending' and ts.state != 'approved',
                })
            else:
                row.update({'actual': l.actual, 'count': l.count, 'diff': l.diff})
            lines.append(row)
        actions = []
        if is_draft:
            actions.append({'key': 'submit', 'ar': 'تقديم للاعتماد', 'style': 'primary'})
        if has_new and is_hr and ts.state in ('submit', 'draft') and ts.pending_count:
            actions.append({'key': 'approve_all', 'ar': 'اعتماد الكل', 'style': 'success'})
            actions.append({'key': 'reject_all', 'ar': 'رفض الكل', 'style': 'danger'})
        if is_draft:
            actions.append({'key': 'delete', 'ar': 'حذف المسودة', 'style': 'danger', 'confirm': True})
        out = {
            'id': ts.id, 'name': ts.name or ts.display_name,
            'date_from': _d(ts.date_from) if 'date_from' in ts._fields else None,
            'date_to': _d(ts.date_to) if 'date_to' in ts._fields else None,
            'department': ts.department_id.name if 'department_id' in ts._fields and ts.department_id else None,
            'state': ts.state if 'state' in ts._fields else None,
            'state_label': st_lbl.get(ts.state) if 'state' in ts._fields else None,
            'can_edit': is_draft, 'is_hr': is_hr,
            'lines': lines, 'actions': actions,
            'report_url': _abs('/api/v1/pms/timesheet/%s/report' % ts.id),
        }
        if has_new:
            out.update({
                'period': ts.period_label, 'new_model': True,
                'stats': {'العمال': ts.emp_count, 'أيام البصمة': ts.total_biometric,
                          'المعتمد': ts.total_approved, 'بانتظار': ts.pending_count}})
        return _ok(out)

    @route(API + '/pms/timesheet/line/<int:lid>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_timesheet_line_write(self, lid, **kw):
        """Edit a line's actual days — only while the sheet is a draft."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        L = env['care.timesheet.line'].sudo()
        line = L.browse(lid).exists()
        if not line:
            return _err('غير موجود', 404)
        ts = line.timesheet_id if 'timesheet_id' in line._fields else None
        has_new = 'adjusted_days' in L._fields
        # New model: edit the ADJUSTED value (biometric stays the source of truth),
        # allowed while the line is still pending and the sheet not finalised.
        if has_new:
            if line.line_state != 'pending' or (ts and ts.state == 'approved'):
                return _err('لا يمكن التعديل بعد الاعتماد', 422)
        elif ts and 'state' in ts._fields and ts.state != 'draft':
            return _err('لا يمكن التعديل بعد التقديم', 422)
        from .api import _body
        b = _body() or {}
        vals = {}
        if has_new:
            if 'adjusted' in b:
                try:
                    vals['adjusted_days'] = int(b['adjusted'])
                except (TypeError, ValueError):
                    return _err('قيمة غير صحيحة', 422)
            if 'note' in b:
                vals['note'] = b['note'] or False
            if b.get('document'):
                import re
                vals['document'] = re.sub(r'^data:[^,]+,', '', b['document'])
                vals['document_filename'] = b.get('document_filename') or 'doc.jpg'
        else:
            if 'actual' in b and 'actual' in L._fields:
                try:
                    vals['actual'] = int(b['actual'])
                except (TypeError, ValueError):
                    return _err('قيمة غير صحيحة', 422)
        if not vals:
            return _err('لا تغييرات', 422)
        try:
            line.write(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر الحفظ', 422)
        return _ok({'id': line.id,
                    'biometric': line.actual,
                    'adjusted': line.adjusted_days if has_new else None,
                    'note': (line.note or None) if has_new else None,
                    'has_doc': bool(line.document) if has_new else False,
                    'diff': line.diff if 'diff' in line._fields else None})

    @route(API + '/pms/timesheet/line/<int:lid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_timesheet_line_action(self, lid, act, **kw):
        """HR approves or rejects a single line (approved days = salary days)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not (env.user.has_group('hr.group_hr_user')
                or env.user.has_group('base.group_erp_manager')
                or env.user.has_group('base.group_system')):
            return _err('الاعتماد من صلاحية الموارد البشرية', 403)
        line = env['care.timesheet.line'].sudo().browse(lid).exists()
        if not line:
            return _err('غير موجود', 404)
        try:
            if act == 'approve':
                line.action_approve_line()
            elif act == 'reject':
                line.action_reject_line()
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر التنفيذ', 422)
        return _ok({'id': line.id, 'line_state': line.line_state, 'approved': line.approved_days})

    @route(API + '/pms/timesheet/line/<int:lid>/doc', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_timesheet_line_doc(self, lid, **kw):
        # token-free image endpoint (attachment for a timesheet adjustment)
        line = request.env['care.timesheet.line'].sudo().browse(int(lid)).exists()
        if not line or not line.document:
            return request.not_found()
        import base64
        return request.make_response(base64.b64decode(line.document), headers=[
            ('Content-Type', 'image/jpeg'),
            ('Content-Disposition', 'inline; filename="ts-doc-%s.jpg"' % lid)])

    @route(API + '/pms/timesheet/<int:tid>/report', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_timesheet_report(self, tid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        ts = env['care.timesheet'].sudo().browse(int(tid)).exists()
        if not ts:
            return request.make_response('غير موجود', status=404)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(
                'care_timesheet.report_timesheet_doc', [ts.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="timesheet-%s.pdf"' % tid)])

    @route(API + '/pms/timesheet/<int:tid>/action', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_timesheet_action(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        ts = env['care.timesheet'].sudo().browse(tid).exists()
        if not ts:
            return _err('غير موجود', 404)
        from .api import _body
        akey = (_body() or {}).get('action')
        is_hr = bool(env.user.has_group('hr.group_hr_user')
                     or env.user.has_group('base.group_erp_manager')
                     or env.user.has_group('base.group_system'))
        st = ts.state if 'state' in ts._fields else None
        try:
            if akey == 'submit' and st == 'draft' and hasattr(ts, 'button_submit'):
                ts.button_submit()
                return _ok({'id': ts.id, 'state': ts.state})
            if akey == 'delete' and st == 'draft':
                ts.unlink()
                return _ok({'deleted': tid})
            if akey == 'approve_all' and is_hr and hasattr(ts, 'button_approve_all'):
                ts.button_approve_all()
                return _ok({'id': ts.id, 'state': ts.state})
            if akey == 'reject_all' and is_hr and hasattr(ts, 'button_reject_all'):
                ts.button_reject_all()
                return _ok({'id': ts.id, 'state': ts.state})
            if akey == 'approve' and is_hr and hasattr(ts, 'button_approve'):
                ts.button_approve()
                return _ok({'id': ts.id, 'state': ts.state})
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        return _err('إجراء غير معروف أو غير مسموح', 422)

    # ---- cash custody (العهدة النقدية): request + settle workflow ----------
    _PETTY_ACTIONS = [
        {'key': 'request', 'method': 'action_request', 'ar': 'تقديم الطلب', 'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'action_approve', 'ar': 'اعتماد', 'states': ['requested'], 'style': 'primary'},
        {'key': 'disburse', 'method': 'action_disburse', 'ar': 'صرف العهدة', 'states': ['approved'], 'style': 'primary'},
        {'key': 'settle', 'method': 'action_settle', 'ar': 'تقديم التسوية', 'states': ['disbursed'], 'style': 'primary'},
        {'key': 'close', 'method': 'action_return_close', 'ar': 'إرجاع وإغلاق', 'states': ['settled'], 'style': 'primary'},
        {'key': 'reopen', 'method': 'action_reopen', 'ar': 'إعادة فتح', 'states': ['settled', 'closed'], 'style': 'plain'},
    ]

    @route(API + '/pms/project/<int:pid>/pettycash/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_pettycash_create(self, pid, **kw):
        """Raise a cash-custody request (طلب عهدة نقدية) against a project."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        if 'care.pms.petty.cash' not in env:
            return _err('نظام العهد النقدية غير متاح', 404)
        from .api import _body
        b = _body() or {}
        try:
            amount = float(b.get('amount') or 0)
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            return _err('أدخل مبلغ العهدة', 422)
        P = env['care.pms.petty.cash'].sudo()
        vals = {'project_id': p.id, 'amount': amount,
                'reason': (b.get('reason') or '').strip() or False,
                'beneficiary_type': b.get('beneficiary_type') or 'project'}
        if b.get('beneficiary_department_id') and 'beneficiary_department_id' in P._fields:
            vals['beneficiary_department_id'] = int(b['beneficiary_department_id'])
        elif self._dept(p) and 'beneficiary_department_id' in P._fields:
            vals['beneficiary_department_id'] = self._dept(p)
        try:
            rec = P.create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء العهدة', 422)
        return _ok({'id': rec.id, 'name': rec.name or rec.display_name, 'state': rec.state})

    def _petty_actions_for(self, rec):
        return [{'key': a['key'], 'ar': a['ar'], 'style': a.get('style', 'plain')}
                for a in self._PETTY_ACTIONS
                if rec.state in a['states'] and hasattr(rec, a['method'])]

    @route(API + '/pms/pettycash/<int:cid>/expense', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_pettycash_expense(self, cid, **kw):
        """Add an expense line (with optional receipt photo) to a cash custody."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cash = env['care.pms.petty.cash'].browse(int(cid))
        try:
            cash.check_access_rule('write')
            cash.read(['id'])
        except Exception:
            return _err('لا صلاحية', 403)
        from .api import _body
        b = _body() or {}
        try:
            amt = float(b.get('amount') or 0)
        except (TypeError, ValueError):
            amt = 0
        if amt <= 0:
            return _err('أدخل المبلغ', 422)
        vals = {'cash_id': cash.id, 'name': b.get('name') or 'مصروف',
                'category': b.get('category') or 'misc',
                'amount': amt, 'foreign_amount': amt, 'rate': 1.0}
        if b.get('note'):
            vals['note'] = b['note']
        if b.get('invoice_number'):
            vals['invoice_number'] = b['invoice_number']
        if b.get('attachment') or b.get('image'):
            vals['attachment'] = b.get('attachment') or b.get('image')
            vals['attachment_name'] = b.get('filename') or 'receipt.jpg'
        try:
            e = env['care.pms.petty.cash.expense'].sudo().create(vals)
        except Exception as ex:
            return _err(str(ex) or 'تعذّر تسجيل المصروف (قد يتجاوز العهدة)', 422)
        return _ok({'id': e.id, 'remaining': round(cash.sudo().remaining, 3)})

    @route(API + '/pms/pettycash/<int:cid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_pettycash_detail(self, cid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        rec = env['care.pms.petty.cash'].sudo().browse(cid).exists()
        if not rec:
            return _err('غير موجودة', 404)
        state_lbl = dict(rec._fields['state'].selection)
        expenses = [{'id': e.id, 'name': e.name or e.display_name,
                     'amount': round(e.amount, 3) if 'amount' in e._fields else None,
                     'date': _d(e.date) if 'date' in e._fields else None,
                     'category': (e.category if 'category' in e._fields else None),
                     'note': (e.note or None) if 'note' in e._fields else None,
                     'invoice_number': (e.invoice_number or None) if 'invoice_number' in e._fields else None,
                     'has_receipt': bool(e.attachment) if 'attachment' in e._fields else False,
                     'receipt': (_abs('/pms/petty-expense/%s/receipt' % e.id)
                                 if 'attachment' in e._fields and e.attachment else None)}
                    for e in rec.expense_ids]
        return _ok({
            'id': rec.id, 'name': rec.name or rec.display_name, 'state': rec.state,
            'state_label': state_lbl.get(rec.state),
            'amount': round(rec.amount, 3), 'spent': round(rec.spent, 3),
            'remaining': round(rec.remaining, 3),
            'returned_amount': round(rec.returned_amount, 3) if 'returned_amount' in rec._fields else 0,
            'reason': rec.reason or None,
            'custodian': rec.manager_id.name if rec.manager_id else None,
            'request_date': _d(rec.request_date) if 'request_date' in rec._fields else None,
            'disbursed_date': _d(rec.disbursed_date) if 'disbursed_date' in rec._fields else None,
            'expenses': expenses,
            'settlements': rec.settlement_count if 'settlement_count' in rec._fields else 0,
            'settlement_list': [{
                'id': s.id, 'name': s.name or s.display_name,
                'date': _d(s.date) if 'date' in s._fields else None,
                'amount': round(s.amount_total, 3) if 'amount_total' in s._fields else None,
                'state': s.state if 'state' in s._fields else None,
                'state_label': (dict(s._fields['state'].selection).get(s.state)
                                if 'state' in s._fields else None),
                'report_url': _abs('/api/v1/pms/settlement/%s/report' % s.id),
            } for s in rec.settlement_ids] if 'settlement_ids' in rec._fields else [],
            'actions': self._petty_actions_for(rec),
        })

    @route(API + '/pms/pettycash/<int:cid>/action', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_pettycash_action(self, cid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        rec = env['care.pms.petty.cash'].browse(cid)  # caller env → ACL enforced
        try:
            rec.check_access_rule('write')
            rec.read(['id'])
        except Exception:
            return _err('غير مصرّح', 403)
        from .api import _body
        akey = (_body() or {}).get('action')
        adef = next((a for a in self._PETTY_ACTIONS if a['key'] == akey), None)
        if not adef:
            return _err('إجراء غير معروف', 422)
        if rec.state not in adef['states']:
            return _err('لا يمكن تنفيذ هذا الإجراء في الحالة الحالية', 422)
        if not hasattr(rec, adef['method']):
            return _err('الإجراء غير متاح', 422)
        try:
            getattr(rec.sudo(), adef['method'])()
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        rec.invalidate_recordset()
        return _ok({'id': rec.id, 'state': rec.state,
                    'actions': self._petty_actions_for(rec.sudo())})

    @route(API + '/pms/pettycash/<int:cid>/settlement', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_pettycash_settlement(self, cid, **kw):
        """Open+fill a settlement for a cash custody: its data, expense lines and
        attachments, then submit it for approval."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.pms.petty.settlement' not in env:
            return _err('نظام التسويات غير متاح', 404)
        cash = env['care.pms.petty.cash'].browse(cid)  # caller env → ACL
        try:
            cash.check_access_rule('write')
            cash.read(['id'])
        except Exception:
            return _err('غير مصرّح', 403)
        cash = cash.sudo()
        from .api import _body
        import base64
        b = _body() or {}
        S = env['care.pms.petty.settlement'].sudo()
        vals = {'cash_id': cash.id}
        if b.get('note'):
            vals['note'] = b['note']
        if b.get('date') and 'date' in S._fields:
            vals['date'] = b['date']
        if cash.project_id and 'project_id' in S._fields:
            vals['project_id'] = cash.project_id.id
        try:
            s = S.create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء التسوية', 422)
        # expense lines being settled
        EX = env['care.pms.petty.cash.expense'].sudo()
        for e in (b.get('expenses') or []):
            try:
                amt = float(e.get('amount') or 0)
            except (TypeError, ValueError):
                amt = 0
            nm = (e.get('name') or '').strip()
            if not nm or amt <= 0:
                continue
            ev = {'cash_id': cash.id, 'settlement_id': s.id, 'name': nm, 'amount': amt}
            if e.get('category') and 'category' in EX._fields:
                ev['category'] = e['category']
            try:
                EX.create(ev)
            except Exception:
                pass
        # attachments (receipts / photos)
        for img in (b.get('images') or []):
            try:
                raw = base64.b64decode(img.split(',')[-1])
                env['ir.attachment'].sudo().create({
                    'name': 'settlement-receipt.jpg', 'datas': base64.b64encode(raw),
                    'res_model': 'care.pms.petty.settlement', 'res_id': s.id,
                    'mimetype': 'image/jpeg'})
            except Exception:
                pass
        submitted = False
        if b.get('submit', True) and hasattr(s, 'action_submit'):
            try:
                s.action_submit()
                submitted = True
            except Exception as e:
                return _err('أُنشئت التسوية لكن تعذّر تقديمها: %s' % e, 422)
        return _ok({'id': s.id, 'name': s.display_name,
                    'state': s.state if 'state' in s._fields else None,
                    'submitted': submitted})

    # ---- dashboard delegation: a manager hands a section to a supervisor ----
    @route(API + '/pms/project/<int:pid>/delegations', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_delegations(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        D = env['care.pms.delegation'].sudo()
        recs = D.search([('project_id', '=', pid), ('active', '=', True)], order='id desc')
        users = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name', limit=400)
        return _ok({
            'delegations': [{
                'id': d.id, 'section_code': d.section_code, 'section_label': d.section_label,
                'delegate': d.delegate_id.name, 'delegate_id': d.delegate_id.id,
                'granted_by': d.granted_by.name if d.granted_by else None,
                'date_until': _d(d.date_until), 'note': d.note or None,
            } for d in recs],
            'users': [{'id': u.id, 'name': u.name} for u in users],
        })

    @route(API + '/pms/project/<int:pid>/delegate', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_delegate(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('delegate_id') or not b.get('section_code'):
            return _err('اختر المشرف والقسم', 422)
        D = env['care.pms.delegation'].sudo()
        # One active delegation per (project, section, delegate).
        exist = D.search([('project_id', '=', pid), ('section_code', '=', b['section_code']),
                          ('delegate_id', '=', int(b['delegate_id'])), ('active', '=', True)], limit=1)
        if exist:
            return _err('هذا التفويض قائم بالفعل', 422)
        rec = D.create({
            'project_id': pid,
            'section_code': b['section_code'],
            'section_label': b.get('section_label') or b['section_code'],
            'delegate_id': int(b['delegate_id']),
            'granted_by': env.user.id,
            'date_until': b.get('date_until') or False,
            'note': (b.get('note') or '').strip() or False,
        })
        # Notify the supervisor.
        try:
            dp = rec.delegate_id.partner_id
            if dp:
                rec.message_subscribe(partner_ids=[dp.id])
                rec.message_post(
                    body='📌 تم تفويضك بمتابعة «%s» في مشروع %s' % (rec.section_label, p.name),
                    partner_ids=[dp.id])
        except Exception:
            pass
        return _ok({'id': rec.id, 'delegate': rec.delegate_id.name,
                    'section_label': rec.section_label})

    @route(API + '/pms/delegation/<int:did>/revoke', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_delegation_revoke(self, did, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        D = env['care.pms.delegation'].sudo()
        rec = D.browse(did).exists()
        if not rec:
            return _err('غير موجود', 404)
        if not self._writable_project(env, rec.project_id.id):
            return _err('لا صلاحية', 403)
        rec.active = False
        return _ok({'revoked': did})

    @route(API + '/pms/my-delegations', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def pms_my_delegations(self, **kw):
        """Sections delegated TO the caller — what they follow up."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from odoo import fields as of
        D = env['care.pms.delegation'].sudo()
        recs = D.search([('delegate_id', '=', env.user.id), ('active', '=', True)], order='id desc')
        out = []
        for d in recs:
            if d.date_until and d.date_until < of.Date.today():
                continue
            out.append({
                'id': d.id, 'project_id': d.project_id.id, 'project': d.project_id.name,
                'section_code': d.section_code, 'section_label': d.section_label,
                'granted_by': d.granted_by.name if d.granted_by else None,
                'date_until': _d(d.date_until), 'note': d.note or None,
                'state': d.state if 'state' in d._fields else 'accepted',
            })
        return _ok({'delegations': out})

    @route(API + '/pms/delegation/<int:did>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_delegation_respond(self, did, act, **kw):
        """The delegate accepts or rejects a follow-up assignment made to them."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        d = env['care.pms.delegation'].sudo().browse(int(did)).exists()
        if not d or d.delegate_id.id != env.user.id:
            return _err('هذا التفويض ليس لك', 403)
        from .api import _body
        b = _body() or {}
        try:
            if act == 'accept':
                d.action_accept()
            elif act == 'reject':
                if b.get('note'):
                    d.response_note = b['note']
                d.action_reject()
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        return _ok({'id': d.id, 'state': d.state})

    @route(API + '/pms/supply/<int:sid>/receive', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_supply_receive(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        sup = env['care.pms.supply'].sudo().browse(int(sid))
        if not sup.exists():
            return _err('غير موجود', 404)
        if not self._writable_project(env, sup.project_id.id):
            return _err('لا صلاحية', 403)
        if sup.state not in ('sent', 'partial'):
            return _err('هذا التوريد ليس قيد الاستلام', 422)
        try:
            sup.action_receive()
        except Exception as e:
            return _err(str(e) or 'تعذّر الاستلام', 422)
        return _ok({'id': sup.id, 'state': sup.state})

    # ---- supply DETAIL: header + product lines (image/qty/received/state) ----
    @route(API + '/pms/supply/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_supply_detail(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        sup = env['care.pms.supply'].sudo().browse(int(sid))
        if not sup.exists():
            return _err('غير موجود', 404)
        if not self._writable_project(env, sup.project_id.id):
            return _err('لا صلاحية', 403)
        state_lbl = dict(sup._fields['state'].selection)
        line_lbl = dict(sup.line_ids._fields['line_state'].selection) if sup.line_ids else {
            'pending': 'قيد الانتظار', 'received': 'مستلم', 'rejected': 'مرفوض'}
        lines = []
        for l in sup.line_ids:
            has_img = bool(l.product_id and l.product_id.image_128)
            lines.append({
                'id': l.id, 'name': l.name,
                'product_id': l.product_id.id if l.product_id else None,
                'image': (_abs('/pms/product/%s/image' % l.product_id.id) if has_img else None),
                'qty': l.qty, 'uom': l.uom_name or '',
                'received_qty': l.received_qty,
                'line_state': l.line_state,
                'line_state_label': line_lbl.get(l.line_state, l.line_state),
                'reject_reason': l.reject_reason or None,
            })
        voucher = None
        if sup.delivery_note:
            voucher = {'name': sup.delivery_note_name or 'سند التسليم',
                       'path': '/pms/supply/%s/voucher-file' % sup.id,
                       'is_pdf': bool((sup.delivery_note_name or '').lower().endswith('.pdf'))}
        return _ok({
            'id': sup.id, 'name': sup.name, 'state': sup.state,
            'state_label': state_lbl.get(sup.state), 'source': sup.source or None,
            'date': _d(sup.date), 'received_date': _d(sup.received_date),
            'project': sup.project_id.name, 'can_write': True,
            'lines': lines, 'voucher': voucher,
            'summary': {
                'total': len(lines),
                'received': sum(1 for l in lines if l['line_state'] == 'received'),
                'rejected': sum(1 for l in lines if l['line_state'] == 'rejected'),
                'pending': sum(1 for l in lines if l['line_state'] == 'pending'),
            }})

    @route(API + '/pms/supply/line/<int:lid>/receive', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_supply_line_receive(self, lid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        line = env['care.pms.supply.line'].sudo().browse(int(lid))
        if not line.exists():
            return _err('غير موجود', 404)
        if not self._writable_project(env, line.supply_id.project_id.id):
            return _err('لا صلاحية', 403)
        from .api import _body
        b = _body() or {}
        try:
            qty = float(b.get('qty')) if b.get('qty') not in (None, '') else line.qty
        except (TypeError, ValueError):
            qty = line.qty
        if qty <= 0:
            return _err('أدخل كمية صحيحة', 422)
        try:
            line.action_receive_line(qty)
        except Exception as e:
            return _err(str(e) or 'تعذّر الاستلام', 422)
        return _ok({'id': line.id, 'line_state': line.line_state,
                    'received_qty': line.received_qty, 'supply_state': line.supply_id.state})

    @route(API + '/pms/supply/line/<int:lid>/reject', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_supply_line_reject(self, lid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        line = env['care.pms.supply.line'].sudo().browse(int(lid))
        if not line.exists():
            return _err('غير موجود', 404)
        if not self._writable_project(env, line.supply_id.project_id.id):
            return _err('لا صلاحية', 403)
        from .api import _body
        b = _body() or {}
        try:
            line.action_reject_line(b.get('reason') or '')
        except Exception as e:
            return _err(str(e) or 'تعذّر الرفض', 422)
        return _ok({'id': line.id, 'line_state': line.line_state,
                    'supply_state': line.supply_id.state})

    @route(API + '/pms/supply/<int:sid>/voucher', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_supply_voucher(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        sup = env['care.pms.supply'].sudo().browse(int(sid))
        if not sup.exists():
            return _err('غير موجود', 404)
        if not self._writable_project(env, sup.project_id.id):
            return _err('لا صلاحية', 403)
        from .api import _body
        b = _body() or {}
        data = b.get('data') or b.get('file')
        if not data:
            return _err('أرفق الملف', 422)
        try:
            sup.write({'delivery_note': data,
                       'delivery_note_name': b.get('filename') or 'سند التسليم.jpg'})
        except Exception as e:
            return _err(str(e) or 'تعذّر الرفع', 422)
        return _ok({'id': sup.id, 'name': sup.delivery_note_name})

    @route(API + '/pms/supply/<int:sid>/voucher-file', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_supply_voucher_file(self, sid, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        sup = env['care.pms.supply'].sudo().browse(int(sid))
        if not sup.exists() or not sup.delivery_note:
            return request.not_found()
        import base64
        raw = base64.b64decode(sup.delivery_note)
        name = sup.delivery_note_name or 'delivery_note'
        ctype = 'application/pdf' if name.lower().endswith('.pdf') else 'image/jpeg'
        return request.make_response(raw, headers=[('Content-Type', ctype),
                                                   ('Content-Disposition', 'inline; filename="%s"' % name)])

    @route('/pms/petty-expense/<int:eid>/receipt', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_petty_receipt(self, eid, **kw):
        """Serve a petty-cash expense receipt image/PDF."""
        import base64
        e = request.env['care.pms.petty.cash.expense'].sudo().browse(int(eid)).exists()
        if not e or not e.attachment:
            return request.not_found()
        raw = base64.b64decode(e.attachment)
        name = (e.attachment_name or 'receipt').lower()
        ctype = 'application/pdf' if name.endswith('.pdf') else 'image/jpeg'
        return request.make_response(raw, headers=[('Content-Type', ctype),
                                                   ('Content-Disposition', 'inline; filename="%s"' % (e.attachment_name or 'receipt'))])

    @route('/pms/user/<int:uid>/avatar', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_user_avatar(self, uid, **kw):
        """Token-free res.users avatar (for task assignees / forward list)."""
        import base64
        u = request.env['res.users'].sudo().browse(int(uid)).exists()
        raw = None
        if u and (u.avatar_128 or u.image_128):
            try:
                raw = base64.b64decode(u.avatar_256 or u.avatar_128 or u.image_128)
            except Exception:
                raw = None
        if raw is None:
            raw = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        return request.make_response(raw, headers=[('Content-Type', 'image/png'),
                                                    ('Cache-Control', 'public, max-age=86400')])

    @route('/pms/emp-doc-file/<int:aid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_emp_doc_file(self, aid, **kw):
        """Serve an employee-document attachment (image or PDF)."""
        import base64
        a = request.env['ir.attachment'].sudo().browse(int(aid)).exists()
        if not a or a.res_model != 'hr.employee.document' or not a.datas:
            return request.not_found()
        raw = base64.b64decode(a.datas)
        return request.make_response(raw, headers=[
            ('Content-Type', a.mimetype or 'application/octet-stream'),
            ('Content-Disposition', 'inline; filename="%s"' % (a.name or 'doc'))])

    @route('/pms/product/<int:pid>/image', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_product_image(self, pid, **kw):
        prod = request.env['product.product'].sudo().browse(int(pid))
        if not prod.exists() or not prod.image_128:
            return request.not_found()
        import base64
        return request.make_response(base64.b64decode(prod.image_256 or prod.image_128),
                                     headers=[('Content-Type', 'image/png'),
                                              ('Cache-Control', 'public, max-age=86400')])

    # ================= ATTENDANCE: rich filters + PDF report =================
    def _attendance_data(self, env, p, kw):
        """Shared attendance query for both the JSON records view and the PDF
        report. Filters: month(YYYY-MM) | date_from/date_to | employee_id |
        status(all/present/absent) | q(name/badge)."""
        from datetime import datetime, timedelta
        from odoo import fields as of
        dept = self._dept(p)
        if not dept:
            return None
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)])
        # ---- resolve the date window ----
        month = (kw.get('month') or '').strip()
        if month:
            y, m = int(month[:4]), int(month[5:7])
            d0 = datetime(y, m, 1)
            d1 = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
            label = month
        else:
            df, dt = kw.get('date_from'), kw.get('date_to')
            d0 = (datetime.strptime(df, '%Y-%m-%d') if df
                  else of.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
            d1 = (datetime.strptime(dt, '%Y-%m-%d') + timedelta(days=1) if dt
                  else of.Datetime.now() + timedelta(days=1))
            label = '%s → %s' % (d0.strftime('%Y-%m-%d'), (d1 - timedelta(days=1)).strftime('%Y-%m-%d'))
        dom = [('employee_id', 'in', emps.ids), ('check_in', '>=', d0), ('check_in', '<', d1)]
        eid = kw.get('employee_id')
        if eid:
            dom.append(('employee_id', '=', int(eid)))
        atts = env['hr.attendance'].sudo().search(dom, order='check_in desc')
        q = (kw.get('q') or '').strip().lower()
        # ---- per-employee rollup ----
        by_emp = {}
        for a in atts:
            e = a.employee_id
            b = by_emp.setdefault(e.id, {'employee': e, 'days': set(), 'hours': 0.0, 'atts': []})
            b['hours'] += a.worked_hours or 0.0
            if a.check_in:
                b['days'].add(a.check_in.date())
            b['atts'].append(a)
        present_ids = set(by_emp.keys())
        summary = []
        for e in emps:
            b = by_emp.get(e.id)
            blob = ('%s %s' % (e.name or '', e.barcode or '')).lower()
            if q and q not in blob:
                continue
            summary.append({
                'id': e.id, 'name': e.name, 'badge': e.barcode or None,
                'job': e.job_title or None,
                'image': _abs('/api/v1/pms/employee/%s/photo' % e.id),
                'present': bool(b), 'days': len(b['days']) if b else 0,
                'hours': round(b['hours'], 1) if b else 0.0,
            })
        # ---- flat attendance rows (filtered by q) ----
        rows = []
        for a in atts:
            blob = ('%s %s' % (a.employee_id.name or '', a.employee_id.barcode or '')).lower()
            if q and q not in blob:
                continue
            rows.append({
                'id': a.id, 'employee': a.employee_id.name,
                'badge': a.employee_id.barcode or None,
                'check_in': _d(a.check_in), 'check_out': _d(a.check_out) or None,
                'hours': round(a.worked_hours or 0.0, 1),
                'open_now': not a.check_out,
            })
        absentees = [s for s in summary if not s['present']]
        total_hours = round(sum(a.worked_hours or 0.0 for a in atts), 1)
        return {
            'emps': emps, 'atts': atts, 'summary': summary, 'rows': rows,
            'absentees': absentees, 'label': label, 'd0': d0, 'd1': d1,
            'stats': {
                'العاملون': len(emps),
                'الحاضرون': len(present_ids),
                'الغائبون': len(emps) - len(present_ids),
                'السجلات': len(atts),
                'إجمالي الساعات': total_hours,
            },
        }

    @route(API + '/pms/project/<int:pid>/attendance/records', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_attendance_records(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['project.project'].browse(int(pid))
        if not p.exists():
            return _err('غير موجود', 404)
        try:
            p.check_access_rule('read')
        except Exception:
            return _err('لا صلاحية', 403)
        data = self._attendance_data(env, p, kw)
        if data is None:
            return _err('لا قسم مرتبط بهذا المشروع.', 404)
        status = (kw.get('status') or 'all').strip()
        rows = data['rows']
        summary = data['summary']
        if status == 'present':
            summary = [s for s in summary if s['present']]
        elif status == 'absent':
            summary = data['absentees']
            rows = []
        return _ok({
            'rows': rows, 'summary': summary, 'absentees': data['absentees'],
            'stats': data['stats'], 'period': data['label'],
            'employees': [{'id': e.id, 'name': e.name, 'badge': e.barcode or None}
                          for e in data['emps']],
        })

    @route(API + '/pms/project/<int:pid>/attendance/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_attendance_report(self, pid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        p = env['project.project'].browse(int(pid))
        if not p.exists():
            return request.not_found()
        try:
            p.check_access_rule('read')
        except Exception:
            return request.make_response('لا صلاحية', status=403)
        data = self._attendance_data(env, p, kw)
        if data is None:
            return request.not_found()
        from markupsafe import escape
        from odoo import fields as of
        printed = of.Date.today().strftime('%Y-%m-%d')
        st = data['stats']
        srows = ''.join(
            '<tr><td>%s</td><td style="text-align:center">%s</td>'
            '<td style="text-align:center;color:%s;font-weight:bold">%s</td>'
            '<td style="text-align:center">%s</td><td style="text-align:center">%s</td></tr>' % (
                escape(s['name'] or ''), escape(s['badge'] or '—'),
                ('#1a9f6d' if s['present'] else '#c0392b'),
                ('حاضر' if s['present'] else 'غائب'),
                s['days'], s['hours'])
            for s in data['summary'])
        html = (
            '<html dir="rtl"><head><meta charset="utf-8"><style>'
            'body{font-family:Tahoma,Arial,sans-serif;color:#1d2433;font-size:12px;}'
            'h1{color:#15213b;font-size:19px;margin:0 0 2px;}'
            '.sub{color:#8a93a8;font-size:12px;margin:0 0 14px;}'
            '.bar{background:#15213b;color:#fff;padding:10px 16px;border-radius:8px;margin:0 0 14px;}'
            '.bar b{color:#f0663c;font-size:16px;}'
            '.kpis{width:100%%;border-collapse:collapse;margin:0 0 16px;}'
            '.kpis td{border:1px solid #e4e8f0;padding:8px;text-align:center;}'
            '.kpis .n{font-size:17px;font-weight:bold;color:#15213b;}'
            '.kpis .l{font-size:11px;color:#8a93a8;}'
            'table.t{width:100%%;border-collapse:collapse;}'
            'table.t th{background:#f6f8fc;color:#5b6577;font-size:11px;padding:7px;border:1px solid #e4e8f0;}'
            'table.t td{padding:6px 8px;border:1px solid #eef1f6;font-size:11.5px;}'
            '</style></head><body>'
            '<div class="bar"><b>CARE</b> · تقرير الحضور</div>'
            '<h1>%s</h1><div class="sub">الفترة: %s · تاريخ الطباعة: %s</div>'
            '<table class="kpis"><tr>'
            '<td><div class="n">%s</div><div class="l">العاملون</div></td>'
            '<td><div class="n" style="color:#1a9f6d">%s</div><div class="l">الحاضرون</div></td>'
            '<td><div class="n" style="color:#c0392b">%s</div><div class="l">الغائبون</div></td>'
            '<td><div class="n">%s</div><div class="l">سجلات الحضور</div></td>'
            '<td><div class="n">%s</div><div class="l">إجمالي الساعات</div></td>'
            '</tr></table>'
            '<table class="t"><tr><th>الموظف</th><th>البادج</th><th>الحالة</th>'
            '<th>أيام الحضور</th><th>الساعات</th></tr>%s</table>'
            '</body></html>') % (
                escape(p.name or ''), escape(data['label']), printed,
                st['العاملون'], st['الحاضرون'], st['الغائبون'], st['السجلات'], st['إجمالي الساعات'],
                srows)
        try:
            pdf = env['ir.actions.report'].sudo()._run_wkhtmltopdf(
                [html], landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 10, 'data-report-margin-bottom': 10,
                    'data-report-margin-left': 8, 'data-report-margin-right': 8})
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', "inline; filename=\"attendance-%s.pdf\"" % pid)])

    # ================= PERFORMANCE: rich KPI dashboard =================
    @route(API + '/pms/project/<int:pid>/performance', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_performance(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['project.project'].browse(int(pid))
        if not p.exists():
            return _err('غير موجود', 404)
        try:
            p.check_access_rule('read')
        except Exception:
            return _err('لا صلاحية', 403)
        dept = self._dept(p)
        if not dept or 'care.performance.log' not in env:
            return _ok({'empty': True, 'kpis': {}, 'leaderboard': [], 'by_source': [],
                        'by_month': [], 'recent': []})
        from odoo import fields as of
        from datetime import date
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)])
        year_start = of.Date.today().replace(month=1, day=1)
        L = env['care.performance.log'].sudo()
        logs = L.search([('employee_id', 'in', emps.ids), ('date', '>=', year_start)], order='date desc')
        src_lbl = dict(L._fields['source'].selection)
        total = sum(l.points or 0.0 for l in logs)
        pos = sum(1 for l in logs if (l.points or 0) > 0)
        neg = sum(1 for l in logs if (l.points or 0) < 0)
        # per-employee rollup
        by_emp = {}
        for l in logs:
            e = l.employee_id
            b = by_emp.setdefault(e.id, {'e': e, 'points': 0.0, 'n': 0, 'pos': 0, 'neg': 0})
            b['points'] += l.points or 0.0
            b['n'] += 1
            if (l.points or 0) > 0:
                b['pos'] += 1
            elif (l.points or 0) < 0:
                b['neg'] += 1
        leaderboard = [{
            'id': b['e'].id, 'name': b['e'].name, 'badge': b['e'].barcode or None,
            'job': b['e'].job_title or None,
            'image': _abs('/api/v1/pms/employee/%s/photo' % b['e'].id),
            'points': round(b['points'], 1), 'events': b['n'],
            'pos': b['pos'], 'neg': b['neg'],
        } for b in sorted(by_emp.values(), key=lambda x: -x['points'])]
        # by source
        src = {}
        for l in logs:
            s = src.setdefault(l.source, {'points': 0.0, 'n': 0})
            s['points'] += l.points or 0.0
            s['n'] += 1
        by_source = [{'source': k, 'label': src_lbl.get(k, k), 'points': round(v['points'], 1),
                      'events': v['n']} for k, v in sorted(src.items(), key=lambda i: -i[1]['n'])]
        # by month (last 6)
        months = {}
        for l in logs:
            key = '%04d-%02d' % (l.date.year, l.date.month)
            months[key] = months.get(key, 0.0) + (l.points or 0.0)
        today = of.Date.today()
        order_keys = []
        y, m = today.year, today.month
        for _i in range(6):
            order_keys.append('%04d-%02d' % (y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        by_month = [{'month': k, 'points': round(months.get(k, 0.0), 1)} for k in reversed(order_keys)]
        recent = [{
            'employee': l.employee_id.name, 'badge': l.employee_id.barcode or None,
            'source': l.source, 'source_label': src_lbl.get(l.source, l.source),
            'name': l.name, 'points': round(l.points or 0.0, 1),
            'date': _d(l.date), 'polarity': l.polarity,
        } for l in logs[:20]]
        evaluated = len(by_emp)
        return _ok({
            'empty': not logs,
            'kpis': {
                'total_points': round(total, 1),
                'events': len(logs),
                'evaluated': evaluated,
                'workers': len(emps),
                'avg': round(total / evaluated, 1) if evaluated else 0.0,
                'positive': pos, 'negative': neg,
                'top': leaderboard[0]['name'] if leaderboard else None,
                'top_points': leaderboard[0]['points'] if leaderboard else 0,
            },
            'leaderboard': leaderboard[:30],
            'by_source': by_source,
            'by_month': by_month,
            'recent': recent,
        })

    # ================= PAYSLIP PDF =================
    @route(API + '/pms/payslip/<int:sid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_payslip_report(self, sid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        ps = env['hr.payslip'].sudo().browse(int(sid))
        if not ps.exists() or not self._emp_in_scope(env, ps.employee_id.id):
            return request.make_response('لا صلاحية', status=403)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf('hr_payroll.report_payslip_lang', [ps.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="payslip-%s.pdf"' % sid)])

    # ============ EMPLOYEE ATTENDANCE: filtered PDF + Excel ============
    def _emp_att_data(self, env, emp, kw):
        from datetime import datetime, timedelta
        from odoo import fields as of
        month = (kw.get('month') or '').strip()
        if month:
            y, m = int(month[:4]), int(month[5:7])
            d0 = datetime(y, m, 1)
            d1 = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
            label = month
        else:
            df, dt = kw.get('date_from'), kw.get('date_to')
            d0 = datetime.strptime(df, '%Y-%m-%d') if df else of.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            d1 = (datetime.strptime(dt, '%Y-%m-%d') + timedelta(days=1)) if dt else of.Datetime.now() + timedelta(days=1)
            label = '%s → %s' % (d0.strftime('%Y-%m-%d'), (d1 - timedelta(days=1)).strftime('%Y-%m-%d'))
        atts = env['hr.attendance'].sudo().search(
            [('employee_id', '=', emp.id), ('check_in', '>=', d0), ('check_in', '<', d1)], order='check_in desc')
        return atts, label

    @route(API + '/pms/employee/<int:eid>/attendance/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_emp_att_report(self, eid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return request.make_response('لا صلاحية', status=403)
        atts, label = self._emp_att_data(env, emp, kw)
        from markupsafe import escape
        from odoo import fields as of
        total = round(sum(a.worked_hours or 0 for a in atts), 1)
        rows = ''.join(
            '<tr><td>%s</td><td style="text-align:center">%s</td>'
            '<td style="text-align:center">%s</td><td style="text-align:center;font-weight:bold">%s</td></tr>' % (
                escape(_d(a.check_in) or ''), escape(_d(a.check_in)[11:] if a.check_in else '—'),
                escape((_d(a.check_out) or '—')[11:] if a.check_out else '—'),
                round(a.worked_hours or 0, 1))
            for a in atts)
        html = (
            '<html dir="rtl"><head><meta charset="utf-8"><style>'
            'body{font-family:Tahoma,Arial;color:#1d2433;font-size:12px}'
            '.bar{background:#15213b;color:#fff;padding:10px 16px;border-radius:8px;margin:0 0 12px}'
            '.bar b{color:#f0663c;font-size:16px}h1{font-size:18px;margin:0 0 2px}'
            '.sub{color:#8a93a8;font-size:12px;margin:0 0 12px}'
            'table{width:100%%;border-collapse:collapse}th{background:#f6f8fc;color:#5b6577;font-size:11px;padding:7px;border:1px solid #e4e8f0}'
            'td{padding:6px 8px;border:1px solid #eef1f6;font-size:11.5px}'
            '.tot{margin-top:10px;font-weight:bold;color:#15213b}'
            '</style></head><body>'
            '<div class="bar"><b>CARE</b> · تقرير حضور عامل</div>'
            '<h1>%s</h1><div class="sub">البادج: %s · الفترة: %s · طُبع: %s</div>'
            '<table><tr><th>التاريخ</th><th>دخول</th><th>خروج</th><th>ساعات</th></tr>%s</table>'
            '<div class="tot">إجمالي الساعات: %s · عدد الأيام: %s</div>'
            '</body></html>') % (
                escape(emp.name or ''), escape(emp.barcode or '—'), escape(label),
                of.Date.today().strftime('%Y-%m-%d'), rows, total, len(atts))
        try:
            pdf = env['ir.actions.report'].sudo()._run_wkhtmltopdf([html], landscape=False)
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="attendance-emp-%s.pdf"' % eid)])

    @route(API + '/pms/employee/<int:eid>/attendance/excel', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_emp_att_excel(self, eid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return request.make_response('لا صلاحية', status=403)
        atts, label = self._emp_att_data(env, emp, kw)
        import io
        import xlsxwriter
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Attendance')
        ws.right_to_left()
        h = wb.add_format({'bold': True, 'bg_color': '#15213b', 'font_color': 'white', 'border': 1})
        c = wb.add_format({'border': 1})
        ws.write(0, 0, 'العامل: %s   البادج: %s   الفترة: %s' % (emp.name or '', emp.barcode or '', label))
        for i, t in enumerate(['التاريخ', 'دخول', 'خروج', 'ساعات']):
            ws.write(2, i, t, h)
        ws.set_column(0, 3, 18)
        r = 3
        for a in atts:
            ws.write(r, 0, _d(a.check_in) or '', c)
            ws.write(r, 1, (_d(a.check_in) or '')[11:] if a.check_in else '', c)
            ws.write(r, 2, (_d(a.check_out) or '')[11:] if a.check_out else '', c)
            ws.write(r, 3, round(a.worked_hours or 0, 1), c)
            r += 1
        ws.write(r + 1, 0, 'الإجمالي', h)
        ws.write(r + 1, 3, round(sum(a.worked_hours or 0 for a in atts), 1), h)
        wb.close()
        buf.seek(0)
        return request.make_response(buf.read(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="attendance-emp-%s.xlsx"' % eid)])

    # ============ EMPLOYEE DOCUMENT: upload new + request HR approval ============
    @route(API + '/pms/employee/<int:eid>/doc-types', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_emp_doc_types(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.pms.doc.request' not in env:
            return _ok({'types': []})
        sel = env['care.pms.doc.request']._fields['doc_type'].selection
        ar = {'civil_id': 'البطاقة المدنية', 'passport': 'الجواز', 'photo': 'صورة شخصية',
              'work_permit': 'إذن العمل', 'residence': 'الإقامة', 'medical': 'الكرت الصحي', 'other': 'أخرى'}
        return _ok({'types': [{'code': k, 'label': ar.get(k, v)} for k, v in sel]})

    @route(API + '/pms/employee/<int:eid>/doc-request', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_emp_doc_request(self, eid, **kw):
        """Project manager uploads a fresh document image → a doc request that HR
        approves (approval attaches it to the employee)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return _err('هذا الموظف ليس ضمن مشاريعك', 403)
        if 'care.pms.doc.request' not in env:
            return _err('نظام طلبات المستندات غير متاح', 404)
        from .api import _body
        b = _body() or {}
        data = b.get('data') or b.get('image')
        if not data:
            return _err('أرفق صورة المستند', 422)
        vals = {
            'employee_id': emp.id,
            'doc_type': b.get('doc_type') or 'other',
            'attachment': data,
            'attachment_name': b.get('filename') or 'document.jpg',
            'description': b.get('notes') or '',
        }
        if 'department_id' in env['care.pms.doc.request']._fields and emp.department_id:
            vals['department_id'] = emp.department_id.id
        try:
            req = env['care.pms.doc.request'].sudo().create(vals)
            if hasattr(req, 'action_submit'):
                req.action_submit()
        except Exception as e:
            return _err(str(e) or 'تعذّر إرسال الطلب', 422)
        return _ok({'id': req.id, 'state': req.state if 'state' in req._fields else None})

    # ============ PM: submit LEAVE for a worker (+ printable report) ============
    @route(API + '/pms/employee/<int:eid>/leave-types', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_leave_types(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'hr.leave.type' not in env:
            return _ok({'types': []})
        return _ok({'types': [{'id': t.id, 'name': t.name}
                              for t in env['hr.leave.type'].sudo().search([], limit=50)]})

    @route(API + '/pms/employee/<int:eid>/leave-create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_leave_create(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return _err('هذا الموظف ليس ضمن مشاريعك', 403)
        from .api import _body
        b = _body() or {}
        if not (b.get('leave_type_id') and b.get('date_from') and b.get('date_to')):
            return _err('حدّد نوع الإجازة والفترة', 422)
        try:
            leave = env['hr.leave'].sudo().create({
                'employee_id': emp.id,
                'holiday_status_id': int(b['leave_type_id']),
                'holiday_type': 'employee',
                'request_date_from': b['date_from'],
                'request_date_to': b['date_to'],
                'name': b.get('note') or '',
            })
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الإجازة', 422)
        return _ok({'id': leave.id, 'name': leave.display_name,
                    'state': leave.state if 'state' in leave._fields else None,
                    'days': round(leave.number_of_days or 0, 1)})

    @route(API + '/pms/leave/<int:lid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_leave_report(self, lid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        leave = env['hr.leave'].sudo().browse(int(lid))
        if not leave.exists() or not self._emp_in_scope(env, leave.employee_id.id):
            return request.make_response('لا صلاحية', status=403)
        rep = None
        for cand in ('care_hr.leave_request_report', 'care_hr.leave_request_header_report'):
            if env.ref(cand, raise_if_not_found=False):
                rep = cand
                break
        if not rep:
            return request.make_response('لا يوجد تقرير للإجازات', status=404)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(rep, [leave.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="leave-%s.pdf"' % lid)])

    # ============ PM: submit LOAN for a worker ============
    @route(API + '/pms/employee/<int:eid>/loan-create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_loan_create(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return _err('هذا الموظف ليس ضمن مشاريعك', 403)
        from .api import _body
        from odoo import fields as of
        b = _body() or {}
        if not b.get('amount'):
            return _err('أدخل المبلغ', 422)
        model = 'care.loan' if 'care.loan' in env else ('hr.loan' if 'hr.loan' in env else None)
        if not model:
            return _err('نظام السُّلف غير متاح', 404)
        try:
            vals = {'employee_id': emp.id}
            if model == 'care.loan':
                vals.update({'amount': float(b['amount']),
                             'installments': int(b.get('installments') or 1),
                             'date': b.get('date') or of.Date.today(),
                             'reason': b.get('reason') or '',
                             'name': b.get('name') or ('سلفة %s' % (emp.name or ''))})
            else:
                vals.update({'loan_amount': float(b['amount']),
                             'installment': int(b.get('installments') or 1),
                             'date': b.get('date') or of.Date.today(),
                             'name': b.get('name') or ('سلفة %s' % (emp.name or ''))})
            loan = env[model].sudo().create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء السلفة', 422)
        return _ok({'id': loan.id, 'name': loan.display_name,
                    'state': loan.state if 'state' in loan._fields else None})

    # ============ WORK SUSPENSION (طلب الإيقاف عن العمل) ============
    def _susp_can_approve(self, env):
        return bool(env.user.has_group('hr.group_hr_user')
                    or env.user.has_group('base.group_erp_manager')
                    or env.user.has_group('base.group_system'))

    def _susp_json(self, env, r):
        S = env['care.suspension.request']
        rsel = dict(S._fields['reason'].selection)
        ssel = dict(S._fields['state'].selection)
        return {
            'id': r.id, 'name': r.name,
            'employee_id': r.employee_id.id, 'employee': r.employee_id.name,
            'avatar': _abs('/api/v1/pms/employee/%s/photo' % r.employee_id.id),
            'badge': r.badge or None, 'job': r.job_title or None,
            'department': r.department_id.name if r.department_id else None,
            'project': r.project_id.name if r.project_id else None,
            'reason': r.reason, 'reason_label': rsel.get(r.reason, r.reason),
            'other_reason': r.other_reason or None,
            'date': _d(r.date), 'effective_date': _d(r.effective_date),
            'note': r.note or None,
            'wage': r.wage, 'currency': r.currency_id.name if r.currency_id else None,
            'has_allowance': r.has_allowance, 'allowance_note': r.allowance_note or None,
            'state': r.state, 'state_label': ssel.get(r.state, r.state),
            'requested_by': r.requested_by.name if r.requested_by else None,
            'approved_by': r.approved_by.name if r.approved_by else None,
            'approval_date': _d(r.approval_date) if r.approval_date else None,
            'can_submit': r.state == 'draft',
            'can_approve': r.state == 'submitted' and self._susp_can_approve(env),
            'can_reject': r.state == 'submitted' and self._susp_can_approve(env),
            'can_reset': r.state in ('submitted', 'rejected'),
            'report_url': _abs('/api/v1/pms/suspension/%s/report' % r.id),
        }

    def _susp_scoped(self, env, sid):
        if 'care.suspension.request' not in env:
            return None
        r = env['care.suspension.request'].sudo().browse(int(sid)).exists()
        if not r:
            return None
        # visible if the worker is in the caller's scope, or the caller may approve
        if self._susp_can_approve(env) or self._emp_in_scope(env, r.employee_id.id):
            return r
        return None

    @route(API + '/pms/suspension/<int:sid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_suspension_get(self, sid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._susp_scoped(env, sid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        return _ok(self._susp_json(env, r))

    @route(API + '/pms/employee/<int:eid>/suspension-create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_suspension_create(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.suspension.request' not in env:
            return _err('وحدة الإيقاف عن العمل غير مثبّتة', 404)
        emp = self._emp_in_scope(env, eid)
        if not emp:
            return _err('هذا الموظف ليس ضمن مشاريعك', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('reason'):
            return _err('اختر سبب الإيقاف', 422)
        vals = {'employee_id': emp.id, 'reason': b['reason'],
                'other_reason': b.get('other_reason') or False,
                'note': b.get('note') or False}
        if b.get('project_id'):
            vals['project_id'] = int(b['project_id'])
        else:
            # default to a project of this worker's department the caller manages
            pj = env['project.project'].search(
                [('pms_department_id', '=', emp.department_id.id)], limit=1)
            if pj:
                vals['project_id'] = pj.id
        if b.get('date'):
            vals['date'] = b['date']
        if b.get('effective_date'):
            vals['effective_date'] = b['effective_date']
        try:
            rec = env['care.suspension.request'].sudo().create(vals)
            if b.get('submit'):
                rec.action_submit()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الطلب', 422)
        return _ok(self._susp_json(env, rec))

    @route(API + '/pms/suspension/<int:sid>/<string:act>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_suspension_action(self, sid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._susp_scoped(env, sid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        if act in ('approve', 'reject') and not self._susp_can_approve(env):
            return _err('الاعتماد من صلاحية الموارد البشرية فقط', 403)
        try:
            if act == 'submit':
                r.action_submit()
            elif act == 'approve':
                r.action_approve()
            elif act == 'reject':
                r.action_reject()
            elif act == 'reset':
                r.action_reset()
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        return _ok(self._susp_json(env, r))

    @route(API + '/pms/suspension/<int:sid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_suspension_report(self, sid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        r = self._susp_scoped(env, sid)
        if not r:
            return request.make_response('لا صلاحية', status=403)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(
                'care_suspension.report_suspension_doc', [r.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="suspension-%s.pdf"' % sid)])

    # ============ REQUEST ITEMS (طلب الأصناف) ============
    def _item_can_approve(self, env):
        return bool(env.user.has_group('care_item_request.group_item_manager')
                    if 'care.item.request' in env else False) or bool(
                    env.user.has_group('base.group_erp_manager')
                    or env.user.has_group('base.group_system'))

    def _item_json(self, env, r):
        R = env['care.item.request']
        ssel = dict(R._fields['state'].selection)
        psel = dict(R._fields['priority'].selection)
        return {
            'id': r.id, 'name': r.name,
            'project': r.project_id.name if r.project_id else None,
            'requested_by': r.requested_by.name if r.requested_by else None,
            'request_date': _d(r.request_date), 'needed_by': _d(r.needed_by),
            'priority': r.priority, 'priority_label': psel.get(r.priority, r.priority),
            'note': r.note or None, 'reject_reason': r.reject_reason or None,
            'state': r.state, 'state_label': ssel.get(r.state, r.state),
            'approved_by': r.approved_by.name if r.approved_by else None,
            'approval_date': _d(r.approval_date) if r.approval_date else None,
            'supply': r.supply_id.name if r.supply_id else None,
            'supply_id': r.supply_id.id if r.supply_id else None,
            'lines': [{'id': l.id, 'name': l.name, 'qty': l.qty,
                       'uom': l.uom_name or 'وحدة', 'note': l.note or None} for l in r.line_ids],
            'total_qty': round(r.total_qty, 1), 'line_count': r.line_count,
            'can_submit': r.state == 'draft',
            'can_approve': r.state == 'submitted' and self._item_can_approve(env),
            'can_reject': r.state == 'submitted' and self._item_can_approve(env),
            'can_reset': r.state in ('submitted', 'rejected'),
            'report_url': _abs('/api/v1/pms/item-request/%s/report' % r.id),
        }

    def _item_scoped(self, env, rid):
        if 'care.item.request' not in env:
            return None
        r = env['care.item.request'].sudo().browse(int(rid)).exists()
        if not r:
            return None
        if self._item_can_approve(env) or self._writable_project(env, r.project_id.id):
            return r
        return None

    @route(API + '/pms/project/<int:pid>/item-request/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_item_request_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.item.request' not in env:
            return _err('وحدة طلب الأصناف غير مثبّتة', 404)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        lines = b.get('lines') or []
        lines = [l for l in lines if (l.get('name') or '').strip() and float(l.get('qty') or 0) > 0]
        if not lines:
            return _err('أضف صنفًا واحدًا على الأقل بكمية', 422)
        vals = {'project_id': p.id, 'priority': b.get('priority') or '0',
                'needed_by': b.get('needed_by') or False, 'note': b.get('note') or False,
                'line_ids': [(0, 0, {'name': l['name'].strip(), 'qty': float(l['qty']),
                                     'uom_name': l.get('uom') or 'وحدة',
                                     'note': l.get('note') or False}) for l in lines]}
        try:
            r = env['care.item.request'].sudo().create(vals)
            if b.get('submit'):
                r.action_submit()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الطلب', 422)
        return _ok(self._item_json(env, r))

    @route(API + '/pms/item-request/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_item_request_get(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._item_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        return _ok(self._item_json(env, r))

    @route(API + '/pms/item-request/<int:rid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_item_request_action(self, rid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._item_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        if act in ('approve', 'reject') and not self._item_can_approve(env):
            return _err('الاعتماد من صلاحية المشتريات', 403)
        from .api import _body
        b = _body() or {}
        try:
            if act == 'submit':
                r.action_submit()
            elif act == 'approve':
                r.action_approve()
            elif act == 'reject':
                if b.get('reason'):
                    r.reject_reason = b['reason']
                r.action_reject()
            elif act == 'reset':
                r.action_reset()
            elif act == 'delete':
                if r.state != 'draft':
                    return _err('لا يمكن حذف طلب بعد الإرسال', 422)
                r.unlink()
                return _ok({'deleted': rid})
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر التنفيذ', 422)
        return _ok(self._item_json(env, r))

    @route(API + '/pms/item-request/<int:rid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_item_request_report(self, rid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        r = self._item_scoped(env, rid)
        if not r:
            return request.make_response('لا صلاحية', status=403)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(
                'care_item_request.report_item_request_doc', [r.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="item-request-%s.pdf"' % rid)])

    # ============ MANPOWER REQUISITION (طلب قوى عاملة) ============
    def _mp_can_approve(self, env):
        return bool(env.user.has_group('hr.group_hr_user')
                    or env.user.has_group('base.group_erp_manager')
                    or env.user.has_group('base.group_system'))

    def _mp_json(self, env, r):
        M = env['manpower.requisition']
        ssel = dict(M._fields['state'].selection)
        tsel = dict(M._fields['type'].selection)
        # what approval step is pending next
        next_step = None
        if r.state == 'submit':
            if r.need_hr_approve and not r.hr_approve:
                next_step = 'hr'
            elif r.need_manager_approve and not r.manager_approve:
                next_step = 'manager'
            elif r.need_parent_approve:
                next_step = 'parent'
            else:
                next_step = 'final'
        return {
            'id': r.id, 'name': r.name,
            'project': r.project_id.name if r.project_id else None,
            'department': r.department_id.name if r.department_id else None,
            'type': r.type, 'type_label': tsel.get(r.type, r.type),
            'titles': r.required_title.mapped('name'),
            'requirement_number': r.requirement_number,
            'location': r.location or None,
            'request_date': _d(r.request_date),
            'salary': r.salary or None, 'working_hours': r.working_hours or None,
            'requirement_reason': r.requirement_reason or None,
            'specific_requirements': r.specific_requirements or None,
            'manager': r.manager_id.name if r.manager_id else None,
            'state': r.state, 'state_label': ssel.get(r.state, r.state),
            'hr_approve': r.hr_approve, 'manager_approve': r.manager_approve,
            'next_step': next_step,
            'can_submit': r.state == 'draft',
            'can_approve': r.state == 'submit' and self._mp_can_approve(env),
            'can_reject': r.state == 'submit' and self._mp_can_approve(env),
            'report_url': _abs('/api/v1/pms/manpower/%s/report' % r.id),
        }

    def _mp_scoped(self, env, rid):
        if 'manpower.requisition' not in env:
            return None
        r = env['manpower.requisition'].sudo().browse(int(rid)).exists()
        if not r:
            return None
        if self._mp_can_approve(env) or self._writable_project(env, r.project_id.id):
            return r
        return None

    @route(API + '/pms/project/<int:pid>/manpower/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_manpower_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'manpower.requisition' not in env:
            return _err('وحدة طلب القوى العاملة غير مثبّتة', 404)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        from odoo import fields as of
        b = _body() or {}
        if not b.get('type'):
            return _err('حدّد نوع الطلب (محلي/خارجي)', 422)
        if not (b.get('requirement_number') and int(b.get('requirement_number') or 0) > 0):
            return _err('حدّد عدد المطلوب', 422)
        vals = {
            'type': b['type'], 'project_id': p.id,
            'department_id': self._dept(p),
            'requirement_number': int(b['requirement_number']),
            'request_date': b.get('request_date') or of.Date.today(),
            'location': b.get('location') or False,
            'requirement_reason': b.get('requirement_reason') or False,
            'specific_requirements': b.get('specific_requirements') or False,
        }
        if b.get('salary'):
            try:
                vals['salary'] = float(b['salary'])
            except (TypeError, ValueError):
                pass
        if b.get('working_hours'):
            try:
                vals['working_hours'] = float(b['working_hours'])
            except (TypeError, ValueError):
                pass
        if b.get('job_ids'):
            vals['required_title'] = [(6, 0, [int(j) for j in b['job_ids']])]
        try:
            r = env['manpower.requisition'].sudo().create(vals)
            if b.get('submit'):
                r.button_submit()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الطلب', 422)
        return _ok(self._mp_json(env, r))

    @route(API + '/pms/manpower/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_manpower_get(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._mp_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        return _ok(self._mp_json(env, r))

    @route(API + '/pms/manpower/<int:rid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_manpower_action(self, rid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._mp_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        if act in ('approve', 'reject') and not self._mp_can_approve(env):
            return _err('الاعتماد من صلاحية الموارد البشرية/الإدارة', 403)
        try:
            if act == 'submit':
                r.button_submit()
            elif act == 'reject':
                r.button_reject()
            elif act == 'approve':
                # advance the pending approval step until state becomes approve
                if r.need_hr_approve and not r.hr_approve:
                    r.button_hr_approve()
                elif r.need_manager_approve and not r.manager_approve:
                    r.button_manager_approve()
                elif r.need_parent_approve:
                    r.button_parent_approve()
                else:
                    r.state = 'approve'
            elif act == 'delete':
                if r.state != 'draft':
                    return _err('لا يمكن حذف طلب بعد الإرسال', 422)
                r.unlink()
                return _ok({'deleted': rid})
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر التنفيذ', 422)
        return _ok(self._mp_json(env, r))

    @route(API + '/pms/manpower/<int:rid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_manpower_report(self, rid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        r = self._mp_scoped(env, rid)
        if not r:
            return request.make_response('لا صلاحية', status=403)
        rep = 'manpower_requisition.manpower_requisition_report'
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(rep, [r.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="manpower-%s.pdf"' % rid)])

    # ============ PROJECT PERMITS (التصاريح) ============
    def _permit_json(self, env, r):
        M = env['care.project.permit']
        tsel = dict(M._fields['permit_type'].selection)
        stsel = dict(M._fields['status'].selection)
        ssel = dict(M._fields['state'].selection)
        return {
            'id': r.id, 'name': r.name, 'title': r.title,
            'project': r.project_id.name if r.project_id else None,
            'permit_type': r.permit_type, 'permit_type_label': tsel.get(r.permit_type, r.permit_type),
            'authority': r.authority or None, 'permit_number': r.permit_number or None,
            'responsible': r.responsible_id.name if r.responsible_id else None,
            'issue_date': _d(r.issue_date), 'expiry_date': _d(r.expiry_date),
            'days_to_expiry': r.days_to_expiry,
            'status': r.status, 'status_label': stsel.get(r.status, r.status),
            'state': r.state, 'state_label': ssel.get(r.state, r.state),
            'note': r.note or None,
            'has_attachment': bool(r.attachment),
            'attachment_url': _abs('/api/v1/pms/permit/%s/attachment' % r.id) if r.attachment else None,
            'report_url': _abs('/api/v1/pms/permit/%s/report' % r.id),
            'can_activate': r.state != 'active',
            'can_renew': r.state == 'active',
            'can_archive': r.state != 'archived',
        }

    def _permit_scoped(self, env, rid):
        if 'care.project.permit' not in env:
            return None
        r = env['care.project.permit'].sudo().browse(int(rid)).exists()
        if not r:
            return None
        if self._writable_project(env, r.project_id.id) or env.user.has_group('base.group_erp_manager') \
                or env.user.has_group('base.group_system'):
            return r
        return None

    @route(API + '/pms/project/<int:pid>/permit/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_permit_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.project.permit' not in env:
            return _err('وحدة التصاريح غير مثبّتة', 404)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        if not (b.get('title') or '').strip():
            return _err('اكتب اسم التصريح', 422)
        vals = {'project_id': p.id, 'title': b['title'].strip(),
                'permit_type': b.get('permit_type') or 'security',
                'authority': b.get('authority') or False,
                'permit_number': b.get('permit_number') or False,
                'issue_date': b.get('issue_date') or False,
                'expiry_date': b.get('expiry_date') or False,
                'note': b.get('note') or False}
        if b.get('responsible_id'):
            vals['responsible_id'] = int(b['responsible_id'])
        if b.get('attachment'):
            import re
            vals['attachment'] = re.sub(r'^data:[^,]+,', '', b['attachment'])
            vals['attachment_filename'] = b.get('attachment_filename') or 'permit.jpg'
        try:
            r = env['care.project.permit'].sudo().create(vals)
            if b.get('activate'):
                r.action_activate()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء التصريح', 422)
        return _ok(self._permit_json(env, r))

    @route(API + '/pms/permit/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_permit_get(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._permit_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        return _ok(self._permit_json(env, r))

    @route(API + '/pms/permit/<int:rid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def pms_permit_action(self, rid, act, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        r = self._permit_scoped(env, rid)
        if not r:
            return _err('غير موجود أو لا صلاحية', 404)
        try:
            if act == 'activate':
                r.action_activate()
            elif act == 'renew':
                r.action_start_renewal()
            elif act == 'archive':
                r.action_archive_permit()
            elif act == 'delete':
                r.unlink()
                return _ok({'deleted': rid})
            else:
                return _err('إجراء غير معروف', 422)
        except Exception as e:
            return _err(str(e) or 'تعذّر التنفيذ', 422)
        return _ok(self._permit_json(env, r))

    @route(API + '/pms/permit/<int:rid>/attachment', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_permit_attachment(self, rid, **kw):
        # token-free image endpoint (same pattern as fuel receipts)
        r = request.env['care.project.permit'].sudo().browse(int(rid)).exists()
        if not r or not r.attachment:
            return request.not_found()
        import base64
        return request.make_response(base64.b64decode(r.attachment), headers=[
            ('Content-Type', 'image/jpeg'),
            ('Content-Disposition', 'inline; filename="permit-%s.jpg"' % rid)])

    @route(API + '/pms/permit/<int:rid>/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_permit_report(self, rid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        r = self._permit_scoped(env, rid)
        if not r:
            return request.make_response('لا صلاحية', status=403)
        try:
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(
                'care_permits.report_permit_doc', [r.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="permit-%s.pdf"' % rid)])

    # ============ SAVED FILTERS (قوائم محفوظة) ============
    @route(API + '/pms/saved-filters', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_saved_filters(self, project_id=None, section=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.pms.saved.filter' not in env:
            return _ok({'filters': []})
        dom = [('user_id', '=', env.user.id)]
        if project_id:
            dom.append(('project_id', '=', int(project_id)))
        if section:
            dom.append(('section_code', '=', section))
        recs = env['care.pms.saved.filter'].sudo().search(dom)
        return _ok({'filters': [{
            'id': r.id, 'name': r.name, 'section': r.section_code,
            'project_id': r.project_id.id if r.project_id else None,
            'terms': [t for t in (r.terms or '').split('||') if t],
        } for r in recs]})

    @route(API + '/pms/saved-filters/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_saved_filter_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.pms.saved.filter' not in env:
            return _err('غير متاح', 404)
        from .api import _body
        b = _body() or {}
        name = (b.get('name') or '').strip()
        terms = [str(t).strip() for t in (b.get('terms') or []) if str(t).strip()]
        if not name or not terms:
            return _err('اكتب اسمًا وحدّد كلمات البحث', 422)
        rec = env['care.pms.saved.filter'].sudo().create({
            'name': name, 'user_id': env.user.id,
            'project_id': int(b['project_id']) if b.get('project_id') else False,
            'section_code': b.get('section') or False,
            'terms': '||'.join(terms),
        })
        return _ok({'id': rec.id, 'name': rec.name})

    @route(API + '/pms/saved-filter/<int:fid>/delete', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_saved_filter_delete(self, fid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        rec = env['care.pms.saved.filter'].sudo().browse(int(fid)).exists()
        if not rec or rec.user_id.id != env.user.id:
            return _err('غير موجود', 404)
        rec.unlink()
        return _ok({'deleted': fid})

    # ============ GENERIC RECORD VIEWER (open any notification's record) ======
    @route(API + '/pms/record', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_generic_record(self, model=None, id=None, **kw):
        """Read any single record the caller may see — grouped fields + a bound
        report if one exists. Powers 'tap a notification → open its record' for
        models without a dedicated screen. The caller's ACL decides visibility."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not model or not id or model not in env:
            return _err('سجل غير معروف', 404)
        try:
            rec = env[model].browse(int(id))
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو لا صلاحية', 403)
        skip = ('binary', 'image', 'one2many', 'many2many', 'html')
        buckets = {'parties': ('🔗 الأطراف', []), 'amounts': ('💰 المبالغ', []),
                   'dates': ('📅 التواريخ', []), 'info': ('📋 معلومات', [])}
        for fname, f in rec._fields.items():
            if f.type in skip or fname.startswith(('message_', 'activity_', 'website_', '__')):
                continue
            if fname in ('id', 'display_name', 'create_uid', 'write_uid', 'write_date', 'create_date'):
                continue
            try:
                v = rec[fname]
                if f.type == 'many2one':
                    v = v.display_name if v else None
                elif f.type == 'selection':
                    v = dict(f._description_selection(env)).get(v, v)
                elif f.type in ('date', 'datetime'):
                    v = str(v) if v else None
                elif f.type == 'boolean':
                    v = 'نعم' if v else 'لا'
                elif f.type in ('float', 'monetary', 'integer'):
                    v = v if v else None
            except Exception:
                continue
            if v in (None, '', False):
                continue
            sec = ('amounts' if f.type in ('monetary', 'float') else
                   'dates' if f.type in ('date', 'datetime') else
                   'parties' if f.type == 'many2one' else 'info')
            buckets[sec][1].append({'label': f.string, 'value': str(v)})
        sections = [{'title': t, 'fields': fs} for _k, (t, fs) in buckets.items() if fs]
        rep = env['ir.actions.report'].sudo().search([('model', '=', model)], limit=1)
        return _ok({
            'model': model, 'id': rec.id, 'title': rec.display_name,
            'sections': sections,
            'report': ('/api/v1/pms/record/report?model=%s&id=%s&report=%s' % (model, rec.id, rep.report_name)) if rep else None,
        })

    @route(API + '/pms/record/report', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_generic_record_report(self, model=None, id=None, report=None, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        if not (model and id and report) or model not in env:
            return request.not_found()
        try:
            rec = env[model].browse(int(id))
            rec.check_access_rule('read')
            pdf, _t = env['ir.actions.report'].sudo()._render_qweb_pdf(report, [rec.id])
        except Exception as e:
            return request.make_response(str(e), status=500)
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="record-%s.pdf"' % id)])

    # ============ PROJECT INVOICE — professional detail ============
    @route(API + '/pms/invoice/<int:mid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_invoice(self, mid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        m = env['account.move'].sudo().browse(int(mid)).exists()
        if not m:
            return _err('غير موجود', 404)
        # scope: the PM must be able to read the invoice's project
        proj = m.project_id if 'project_id' in m._fields and m.project_id else None
        ok = False
        if proj:
            try:
                ok = bool(self._project(env, proj.id))
            except Exception:
                ok = False
        if not ok and not (env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')):
            return _err('لا صلاحية', 403)
        token = None
        try:
            token = m._portal_ensure_token()
        except Exception:
            pass
        payments = []
        try:
            for pinfo in m._get_reconciled_info_JSON_values():
                payments.append({'name': pinfo.get('name') or pinfo.get('ref') or '—',
                                 'method': pinfo.get('journal_name') or None,
                                 'date': str(pinfo.get('date')) if pinfo.get('date') else None,
                                 'amount': pinfo.get('amount')})
        except Exception:
            pass
        pay_lbl = {'not_paid': 'غير مدفوعة', 'in_payment': 'قيد الدفع', 'paid': 'مدفوعة',
                   'partial': 'مدفوعة جزئياً', 'reversed': 'معكوسة'}
        from odoo import fields as of
        _today = of.Date.today()
        return _ok({
            'id': m.id, 'name': m.name, 'ref': m.ref or None,
            'invoice_date': str(m.invoice_date) if m.invoice_date else None,
            'due_date': str(m.invoice_date_due) if m.invoice_date_due else None,
            'amount_total': m.amount_total, 'amount_residual': m.amount_residual,
            'amount_untaxed': m.amount_untaxed, 'amount_tax': m.amount_tax,
            'amount_paid': m.amount_total - m.amount_residual, 'currency': m.currency_id.name,
            'payment_state': m.payment_state, 'payment_label': pay_lbl.get(m.payment_state, m.payment_state),
            'partner': m.partner_id.name, 'project': proj.name if proj else None,
            'client_approval': m.cafm_client_approval if 'cafm_client_approval' in m._fields else None,
            'overdue': bool(m.invoice_date_due and m.amount_residual > 0 and m.invoice_date_due < _today),
            'lines': [{'name': l.name, 'qty': l.quantity, 'price': l.price_unit,
                       'subtotal': l.price_subtotal, 'tax': ', '.join(l.tax_ids.mapped('name'))}
                      for l in m.invoice_line_ids if l.display_type in (False, 'product')],
            'payments': payments,
            'pdf_url': _abs('/my/invoices/%s?access_token=%s&report_type=pdf&download=true' % (m.id, token)) if token else None,
        })

    # ================= FINANCE dashboard (contract + costs + target) =================
    @route(API + '/pms/project/<int:pid>/finance', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_finance(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = env['project.project'].browse(int(pid))
        if not p.exists():
            return _err('غير موجود', 404)
        try:
            p.check_access_rule('read')
        except Exception:
            return _err('لا صلاحية', 403)
        from odoo import fields as of
        dept = self._dept(p)
        cur = p.company_id.currency_id.name if p.company_id else ''
        today = of.Date.today()
        m0 = today.replace(day=1)

        # -- contract (care.experience linked by project_id) --
        contract = None
        if 'care.experience' in env:
            c = env['care.experience'].sudo().search([('project_id', '=', p.id)], limit=1)
            if c:
                contract = {
                    'id': c.id, 'name': c.display_name,
                    'no': (c.x_studio_contract_no if 'x_studio_contract_no' in c._fields else None) or None,
                    'amount': round(c.contract_amount, 3) if 'contract_amount' in c._fields else None,
                    'type': (c.contract_type if 'contract_type' in c._fields else None),
                    'insurance': round(c.insurance_amount, 3) if 'insurance_amount' in c._fields else None,
                    'renewals': c.renewal_count if 'renewal_count' in c._fields else 0,
                    'expiry': str(c.contract_expiry_date) if 'contract_expiry_date' in c._fields and c.contract_expiry_date else None,
                    'has_copy': bool(c.contract_copy) if 'contract_copy' in c._fields else False,
                }

        # -- invoices (this month + total) --
        inv_month = inv_total = inv_residual = 0.0
        inv_count = 0
        if 'project_id' in env['account.move']._fields:
            M = env['account.move'].sudo()
            invs = M.search([('project_id', '=', p.id), ('move_type', '=', 'out_invoice')])
            for m in invs:
                inv_total += m.amount_total
                inv_residual += m.amount_residual
                if m.invoice_date and m.invoice_date >= m0:
                    inv_month += m.amount_total
            inv_count = len(invs)

        # -- salaries (monthly wage of department employees) --
        salaries = 0.0
        emp_n = 0
        if dept:
            emps = env['hr.employee'].sudo().search([('department_id', '=', dept)])
            emp_n = len(emps)
            for e in emps:
                if e.contract_id and e.contract_id.wage:
                    salaries += e.contract_id.wage

        # -- allowances (best-effort: transport allowance on contract) --
        allowances = 0.0
        if dept:
            for e in env['hr.employee'].sudo().search([('department_id', '=', dept)]):
                ct = e.contract_id
                if ct:
                    for fld in ('transport_allowance', 'allowance', 'housing_allowance'):
                        if fld in ct._fields and ct[fld]:
                            allowances += ct[fld]

        # -- materials (received qty) --
        mat_total_qty = 0.0
        mat_n = 0
        if 'care.pms.material' in env:
            mats = env['care.pms.material'].sudo().search([('project_id', '=', p.id)])
            mat_n = len(mats)
            for mt in mats:
                if 'receipt_ids' in mt._fields:
                    mat_total_qty += sum(mt.receipt_ids.mapped('qty') or [0])

        # -- fuel / diesel --
        fuel_total = 0.0
        fuel_n = 0
        for fm in ('care.pms.fuel', 'fuel.log'):
            if fm in env:
                recs = env[fm].sudo().search([('project_id', '=', p.id)]) if 'project_id' in env[fm]._fields else env[fm].browse()
                fuel_n = len(recs)
                for r in recs:
                    for fld in ('amount', 'total', 'cost', 'value'):
                        if fld in r._fields and r[fld]:
                            fuel_total += r[fld]; break
                break

        # -- petty cash --
        petty_total = petty_spent = 0.0
        if 'care.pms.petty.cash' in env:
            for pc in env['care.pms.petty.cash'].sudo().search([('project_id', '=', p.id)]):
                petty_total += pc.amount if 'amount' in pc._fields else 0
                petty_spent += pc.spent if 'spent' in pc._fields else 0

        target = round(p.x_kuwait_target, 3) if 'x_kuwait_target' in p._fields and p.x_kuwait_target else None
        revenue = round(p.pms_revenue, 3) if 'pms_revenue' in p._fields else inv_total
        total_expenses = round(salaries + allowances + fuel_total + petty_spent, 3)
        achieve = round((revenue / target) * 100, 1) if target else None

        return _ok({
            'currency': cur,
            'contract': contract,
            'target': target,
            'revenue': round(revenue, 3),
            'achievement': achieve,
            'cards': [
                {'key': 'contract', 'label': 'قيمة العقد', 'value': contract['amount'] if contract else None, 'icon': 'contract', 'color': '#15213B'},
                {'key': 'target', 'label': 'الكويت تارجت', 'value': target, 'icon': 'target', 'color': '#7C3AED'},
                {'key': 'invoice_month', 'label': 'فاتورة الشهر', 'value': round(inv_month, 3), 'icon': 'invoice', 'color': '#2563EB'},
                {'key': 'invoice_total', 'label': 'إجمالي الفواتير', 'value': round(inv_total, 3), 'icon': 'invoices', 'color': '#0891B2'},
                {'key': 'salaries', 'label': 'الرواتب الشهرية', 'value': round(salaries, 3), 'icon': 'salary', 'color': '#16A34A'},
                {'key': 'allowances', 'label': 'البدلات', 'value': round(allowances, 3), 'icon': 'allowance', 'color': '#0D9488'},
                {'key': 'materials', 'label': 'المواد (كمية)', 'value': round(mat_total_qty, 1), 'icon': 'materials', 'color': '#B45309'},
                {'key': 'fuel', 'label': 'الوقود/الديزل', 'value': round(fuel_total, 3), 'icon': 'fuel', 'color': '#DC2626'},
                {'key': 'petty', 'label': 'العهدة المصروفة', 'value': round(petty_spent, 3), 'icon': 'petty', 'color': '#EA580C'},
                {'key': 'expenses', 'label': 'إجمالي المصاريف', 'value': total_expenses, 'icon': 'expenses', 'color': '#B91C1C'},
            ],
            'counts': {'invoices': inv_count, 'employees': emp_n, 'materials': mat_n, 'fuel': fuel_n},
        })

    @route(API + '/pms/project/<int:pid>/delivery/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_delivery_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('material_id'):
            return _err('اختر المادة', 422)
        try:
            note = env['care.pms.delivery.note'].sudo().create({
                'project_id': p.id, 'location': b.get('location') or '',
                'receiver_name': b.get('receiver_name') or ''})
            env['care.pms.delivery.note.line'].sudo().create({
                'note_id': note.id, 'material_id': int(b['material_id']),
                'qty': float(b.get('qty') or 0)})
            note.action_confirm()
        except Exception as e:
            # A balance/validation error is the model telling us the delivery
            # exceeds stock — surface it, don't swallow it.
            return _err(str(e) or 'تعذّر تسجيل التسليم', 422)
        return _ok({'id': note.id, 'name': note.display_name})

    @route(API + '/pms/project/<int:pid>/expense/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_expense_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        amt = float(b.get('amount') or 0)
        if amt <= 0:
            return _err('أدخل المبلغ', 422)
        try:
            if b.get('cash_id'):
                cash = env['care.pms.petty.cash'].sudo().browse(int(b['cash_id']))
            else:
                cash = env['care.pms.petty.cash'].sudo().create(
                    {'project_id': p.id, 'amount': float(b.get('cash_amount') or amt)})
            evals = {
                'cash_id': cash.id, 'name': b.get('name') or 'مصروف',
                'category': b.get('category') or 'misc',
                'amount': amt, 'foreign_amount': amt, 'rate': 1.0}
            if b.get('note'):
                evals['note'] = b['note']
            if b.get('invoice_number'):
                evals['invoice_number'] = b['invoice_number']
            if b.get('attachment') or b.get('image'):
                evals['attachment'] = b.get('attachment') or b.get('image')
                evals['attachment_name'] = b.get('filename') or 'receipt.jpg'
            env['care.pms.petty.cash.expense'].sudo().create(evals)
        except Exception as e:
            return _err(str(e) or 'تعذّر تسجيل المصروف (قد يتجاوز العهدة)', 422)
        return _ok({'id': cash.id})

    @route(API + '/pms/project/<int:pid>/timesheet/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_timesheet_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        if not self._dept(p):
            return _err('لا قسم مرتبط بهذا المشروع', 422)
        from .api import _body
        b = _body() or {}
        if not (b.get('date_from') and b.get('date_to')):
            return _err('حدّد الفترة', 422)
        try:
            ts = env['care.timesheet'].sudo().create({
                'department_id': self._dept(p),
                'date_from': b['date_from'], 'date_to': b['date_to']})
            # Generate present-days from biometric attendance, then leave it as a
            # DRAFT so the user can review/adjust the days before submitting.
            if hasattr(ts, 'button_generate_timesheet'):
                ts.button_generate_timesheet()
            # Custom timesheet for ONE worker — keep only that employee's line.
            if b.get('employee_id'):
                keep = ts.line_ids.filtered(lambda l: l.employee_id.id == int(b['employee_id']))
                (ts.line_ids - keep).unlink()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الكشف', 422)
        return _ok({'id': ts.id, 'name': ts.display_name,
                    'state': ts.state if 'state' in ts._fields else None})

    @route(API + '/pms/project/<int:pid>/docrequest/create', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def pms_docrequest_create(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        p = self._writable_project(env, pid)
        if not p:
            return _err('لا صلاحية على هذا المشروع', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('employee_id'):
            return _err('اختر الموظف', 422)
        try:
            r = env['care.pms.doc.request'].sudo().create({
                'employee_id': int(b['employee_id']), 'project_id': p.id,
                'doc_type': b.get('doc_type') or 'civil_id',
                'description': b.get('description') or ''})
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الطلب', 422)
        return _ok({'id': r.id, 'name': r.display_name})

    def _emp_in_scope(self, env, eid):
        """The employee if they belong to a department of a project this user
        manages — the portal's own guard (self._mgr_departments)."""
        emp = env['hr.employee'].sudo().browse(int(eid))
        if not emp.exists():
            return None
        # search([]) on the caller's env already applies the per-user project
        # record rules, so this is the departments of THIS manager's projects.
        my_depts = env['project.project'].search([]).mapped('pms_department_id')
        return emp if emp.department_id and emp.department_id.id in my_depts.ids else None

    @route(API + '/pms/employee/<int:eid>/file', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_employee_file(self, eid, **kw):
        """The employee file a PM sees on the portal: identity, contract wage,
        docs, loans, penalties, bonuses, recent attendance and compliance dates.
        Scoped to the manager's own project departments."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        emp = self._emp_in_scope(env, eid)
        _mgr_view = bool(emp)   # a manager viewing a worker (vs. self-view)
        # Everyone may open their OWN file (بياناتي) even when not a manager.
        if not emp:
            own = env.user.employee_id if 'employee_id' in env.user._fields else None
            if own and own.id == int(eid):
                emp = own.sudo()
        # HR / management / admins may open ANY employee's file (the back-office).
        if not emp and (env.user.has_group('hr.group_hr_user')
                        or env.user.has_group('base.group_erp_manager')
                        or env.user.has_group('base.group_system')):
            cand = env['hr.employee'].sudo().browse(int(eid)).exists()
            if cand:
                emp = cand
                _mgr_view = True
        if not emp:
            return _err('هذا الموظف ليس ضمن مشاريعك', 403)

        def _rows(model, extra=None):
            if model not in env:
                return []
            recs = env[model].sudo().search([('employee_id', '=', emp.id)], limit=30)
            out = []
            for r in recs:
                d = {'id': r.id, 'name': r.display_name}
                if 'state' in r._fields:
                    sel = dict(r._fields['state'].selection)
                    d['state'] = r.state
                    d['state_label'] = sel.get(r.state, r.state)
                for f in (extra or []):
                    if f in r._fields:
                        v = r[f]
                        d[f] = _d(v) if hasattr(v, 'strftime') else (round(v, 3) if isinstance(v, float) else v)
                out.append(d)
            return out

        from odoo import fields as of
        today = of.Date.today()
        compliance = []
        for fld, lbl in (('residency_end_date', 'الإقامة'), ('affairs_permit_end_date', 'إذن الشؤون'),
                         ('visa_expire', 'التأشيرة'), ('work_permit_expiration_date', 'تصريح العمل'),
                         ('passport_expiry_date', 'الجواز')):
            if fld in emp._fields and emp[fld]:
                compliance.append({'label': lbl, 'date': str(emp[fld]),
                                   'days': (emp[fld] - today).days})

        att = env['hr.attendance'].sudo().search(
            [('employee_id', '=', emp.id)], order='check_in desc', limit=30)
        # Live duty status from today's attendance.
        from odoo import fields as of2
        _t0 = of2.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        _today = env['hr.attendance'].sudo().search(
            [('employee_id', '=', emp.id), ('check_in', '>=', _t0)])
        if _today.filtered(lambda a: not a.check_out):
            _duty, _duty_lbl = 'on_site', 'بالموقع الآن'
        elif _today:
            _duty, _duty_lbl = 'attended', 'داوم اليوم'
        else:
            _duty, _duty_lbl = 'off', 'لم يداوم اليوم'

        # The full employee page — every readable field, grouped like Odoo.
        def _fv(name, label):
            if name not in emp._fields:
                return None
            f = emp._fields[name]
            try:
                v = emp[name]
            except Exception:
                return None
            if f.type == 'many2one':
                v = v.display_name if v else None
            elif f.type == 'selection':
                try:
                    v = dict(f._description_selection(env)).get(v, v)
                except Exception:
                    pass
            elif f.type in ('date', 'datetime'):
                v = str(v) if v else None
            elif f.type == 'boolean':
                v = 'نعم' if v else 'لا'
            elif f.type in ('float', 'monetary', 'integer'):
                v = v if v else None
            if v in (None, '', False):
                return None
            return {'label': label, 'value': str(v)}

        details = []

        def _grp(title, pairs):
            rows = [r for r in (_fv(n, l) for n, l in pairs) if r]
            if rows:
                details.append({'title': title, 'fields': rows})

        _grp('معلومات العمل', [
            ('job_title', 'المسمى الوظيفي'), ('department_id', 'الإدارة'),
            ('work_department', 'القسم'), ('employee_type', 'نوع التوظيف'),
            ('worker_status', 'حالة العامل'), ('parent_id', 'المدير المباشر'),
            ('coach_id', 'المشرف'), ('work_phone', 'هاتف العمل'),
            ('mobile_phone', 'الجوال'), ('work_email', 'البريد'),
            ('cafm_workorder_count', 'أوامر العمل')])
        _grp('الهوية والإقامة', [
            ('barcode', 'رقم البادج'), ('civil_code', 'الرقم المدني'),
            ('identification_id', 'رقم التعريف'),
            ('residency_type', 'نوع الإقامة'), ('residency_start_date', 'بداية الإقامة'),
            ('residency_end_date', 'نهاية الإقامة'), ('work_permit_name', 'تصريح العمل'),
            ('passport_no', 'رقم الجواز'), ('passport_type', 'نوع الجواز'),
            ('passport_status', 'حالة الجواز')])
        _grp('معلومات شخصية', [
            ('country_id', 'الجنسية'), ('gender', 'الجنس'),
            ('marital', 'الحالة الاجتماعية'), ('birthday', 'تاريخ الميلاد')])
        _grp('الإجازات', [
            ('remaining_leaves', 'رصيد الإجازات'), ('leaves_count', 'إجازات مأخوذة')])
        _grp('السكن', [
            ('is_company_accommodation', 'سكن الشركة'),
            ('housing_hostel_id', 'الهوستل'), ('hostel_id', 'المبنى'),
            ('housing_floor_id', 'الطابق'), ('room_id', 'الغرفة'),
            ('bed_id', 'السرير')])

        # ============ RICH PROFILE SECTIONS (all best-effort/guarded) ============
        # -- tags --
        tags = [{'name': t.name, 'color': getattr(t, 'color', 0)}
                for t in emp.category_ids] if 'category_ids' in emp._fields else []

        # -- status marks (worker status / on-leave / etc.) --
        marks = []
        wsel = dict(emp._fields['worker_status']._description_selection(env)) if 'worker_status' in emp._fields else {}
        ws = emp.worker_status if 'worker_status' in emp._fields else None
        on_leave = False
        if 'current_leave_state' in emp._fields and emp.current_leave_state in ('validate', 'validate1'):
            on_leave = True
            marks.append({'key': 'on_leave', 'label': 'في إجازة', 'icon': 'flight', 'color': '#2563EB'})
        if ws:
            wl = (wsel.get(ws) or ws)
            low = ('%s %s' % (ws, wl)).lower()
            color = '#6B7280'
            if 'abscond' in low or 'هروب' in low or 'هارب' in low:
                color = '#B91C1C'
            elif 'suspend' in low or 'موقوف' in low or 'stop' in low:
                color = '#D97706'
            elif 'active' in low or 'يعمل' in low or 'on_job' in low:
                color = '#16A34A'
            marks.append({'key': 'worker_status', 'label': wl, 'icon': 'badge', 'color': color})

        # -- leaves + return status --
        leaves = []
        if 'hr.leave' in env:
            for l in env['hr.leave'].sudo().search([('employee_id', '=', emp.id)], order='date_from desc', limit=40):
                ret = None
                if 'returned' in l._fields and l.returned:
                    ret = dict(l._fields['returned']._description_selection(env)).get(l.returned, l.returned)
                leaves.append({
                    'id': l.id, 'type': l.holiday_status_id.name if l.holiday_status_id else None,
                    'from': _d(l.date_from), 'to': _d(l.date_to),
                    'days': round(l.number_of_days or 0, 1),
                    'state': l.state, 'state_label': dict(l._fields['state']._description_selection(env)).get(l.state, l.state),
                    'returned': ret,
                    'return_count': l.leave_return_count if 'leave_return_count' in l._fields else None,
                })

        # -- transfers (employee.shift.request) --
        transfers = []
        if 'employee.shift.request' in env:
            for t in env['employee.shift.request'].sudo().search([('employee_id', '=', emp.id)], order='id desc', limit=30):
                sl = dict(t._fields['state']._description_selection(env)) if 'state' in t._fields else {}
                transfers.append({
                    'id': t.id, 'from': (t.current_department.name if getattr(t, 'current_department', False) else None),
                    'to': (t.new_department.name if getattr(t, 'new_department', False) else None),
                    'date': _d(t.date) if 'date' in t._fields else None,
                    'state': t.state if 'state' in t._fields else None,
                    'state_label': sl.get(t.state) if 'state' in t._fields else None,
                })

        # -- uniform --
        uniform = []
        if 'uniform.delivery' in env:
            recs = env['uniform.delivery'].sudo().search(
                ['|', ('employee_id', '=', emp.id), ('employee_ids', 'in', emp.id)], order='date desc', limit=30)
            for u in recs:
                uniform.append({'id': u.id, 'type': u.uniform_type_id.name if u.uniform_type_id else u.name,
                                'date': _d(u.date), 'signed': bool(getattr(u, 'signature', False))})

        # -- skills --
        skills = []
        if 'employee_skill_ids' in emp._fields:
            for s in emp.employee_skill_ids:
                skills.append({'name': s.skill_id.name if s.skill_id else None,
                               'level': s.skill_level_id.name if s.skill_level_id else None,
                               'progress': s.level_progress if 'level_progress' in s._fields else None})
        elif 'skill_ids' in emp._fields:
            skills = [{'name': s.name, 'level': None, 'progress': None} for s in emp.skill_ids]

        # -- appraisals --
        appraisals = []
        if 'hr.appraisal' in env:
            for a in env['hr.appraisal'].sudo().search([('employee_id', '=', emp.id)], order='id desc', limit=20):
                sl = dict(a._fields['state']._description_selection(env)) if 'state' in a._fields else {}
                appraisals.append({'id': a.id, 'date': _d(a.date_close) if 'date_close' in a._fields else None,
                                   'state': a.state if 'state' in a._fields else None,
                                   'state_label': sl.get(a.state) if 'state' in a._fields else None,
                                   'score': round(a.final_score, 1) if 'final_score' in a._fields and a.final_score else None})

        # -- vehicles (driver_id is a partner) --
        vehicles = []
        if 'fleet.vehicle' in env:
            pids = []
            for f in ('work_contact_id', 'address_home_id'):
                if f in emp._fields and emp[f]:
                    pids.append(emp[f].id)
            if emp.user_id and emp.user_id.partner_id:
                pids.append(emp.user_id.partner_id.id)
            if pids:
                for v in env['fleet.vehicle'].sudo().search([('driver_id', 'in', pids)], limit=20):
                    vehicles.append({'id': v.id, 'plate': v.license_plate,
                                     'model': v.model_id.name if v.model_id else v.name})

        # -- traffic violations (driver_id = employee) --
        violations = []
        if 'care.traffic.violation' in env:
            for tv in env['care.traffic.violation'].sudo().search([('driver_id', '=', emp.id)], order='date desc', limit=30):
                sl = dict(tv._fields['state']._description_selection(env)) if 'state' in tv._fields else {}
                violations.append({'id': tv.id, 'type': tv.violation_type_id.name if tv.violation_type_id else tv.name,
                                   'date': _d(tv.date) if 'date' in tv._fields else None,
                                   'amount': round(tv.amount, 3) if 'amount' in tv._fields else None,
                                   'vehicle': tv.vehicle_id.license_plate if tv.vehicle_id else None,
                                   'state': tv.state if 'state' in tv._fields else None,
                                   'state_label': sl.get(tv.state) if 'state' in tv._fields else None})

        # -- documents (hr.employee.document, with images + expiry) --
        documents = []
        if 'hr.employee.document' in env:
            for dc in env['hr.employee.document'].sudo().search([('employee_ref_id', '=', emp.id)], limit=40):
                imgs = [_abs('/api/v1/pms/emp-doc-file/%s' % a.id) for a in dc.doc_attachment_ids] if 'doc_attachment_ids' in dc._fields else []
                exp = dc.expiry_date if 'expiry_date' in dc._fields else None
                documents.append({
                    'id': dc.id, 'type': dc.document_type_id.name if dc.document_type_id else None,
                    'number': dc.name or None,
                    'issue': _d(dc.issue_date) if 'issue_date' in dc._fields else None,
                    'expiry': str(exp) if exp else None,
                    'days': (exp - today).days if exp else None,
                    'images': imgs,
                })

        # -- payslips (monthly) --
        payslips = []
        if 'hr.payslip' in env:
            for ps in env['hr.payslip'].sudo().search([('employee_id', '=', emp.id)], order='date_from desc', limit=24):
                sl = dict(ps._fields['state']._description_selection(env)) if 'state' in ps._fields else {}
                payslips.append({'id': ps.id, 'name': ps.name or ps.number,
                                 'from': _d(ps.date_from), 'to': _d(ps.date_to),
                                 'net': round(ps.net_wage, 3) if 'net_wage' in ps._fields else None,
                                 'state': ps.state if 'state' in ps._fields else None,
                                 'state_label': sl.get(ps.state) if 'state' in ps._fields else None})

        # -- fingerprint devices --
        devices = []
        if 'attendance.device.user' in env:
            for du in env['attendance.device.user'].sudo().search([('employee_id', '=', emp.id)], limit=20):
                devices.append({'id': du.id,
                                'device': du.device_id.name if du.device_id else None,
                                'uid': du.uid if 'uid' in du._fields else None,
                                'templates': du.total_finger_template_records if 'total_finger_template_records' in du._fields else None})

        # -- legal cases (hr.lawsuit) --
        legal = []
        if 'hr.lawsuit' in env:
            L = env['hr.lawsuit'].sudo()
            lsel = dict(L._fields['state']._description_selection(env)) if 'state' in L._fields else {}
            for lc in L.search([('employee_id', '=', emp.id)], order='id desc', limit=40):
                st = lc.state if 'state' in lc._fields else None
                legal.append({
                    'id': lc.id, 'name': lc.name or (lc.ref_no if 'ref_no' in lc._fields else None),
                    'ref': lc.ref_no if 'ref_no' in lc._fields else None,
                    'court': lc.court_name if 'court_name' in lc._fields else None,
                    'hearing': _d(lc.hearing_date) if 'hearing_date' in lc._fields and lc.hearing_date else None,
                    'next': _d(lc.next_appointment) if 'next_appointment' in lc._fields and lc.next_appointment else None,
                    'details': (lc.case_details or None) if 'case_details' in lc._fields else None,
                    'state': st, 'state_label': lsel.get(st, st),
                })
            if any(x['state'] in ('running', 'delay') for x in legal):
                marks.append({'key': 'legal', 'label': 'قضية جارية', 'icon': 'gavel', 'color': '#B91C1C'})

        # -- work-suspension requests for this worker --
        _suspension_block = {'available': False, 'can_create': False, 'rows': []}
        if 'care.suspension.request' in env:
            SR = env['care.suspension.request'].sudo()
            rsel = dict(SR._fields['reason'].selection)
            ssel = dict(SR._fields['state'].selection)
            srows = []
            for s in SR.search([('employee_id', '=', emp.id)], order='id desc', limit=30):
                srows.append({
                    'id': s.id, 'name': s.name,
                    'reason': rsel.get(s.reason, s.reason),
                    'date': _d(s.date), 'state': s.state,
                    'state_label': ssel.get(s.state, s.state),
                    'has_allowance': s.has_allowance,
                    'open': 'suspension',
                })
            _suspension_block = {'available': True, 'can_create': _mgr_view, 'rows': srows}

        return _ok({
            'employee': {
                'id': emp.id, 'name': emp.name, 'job': emp.job_title or None,
                'department': emp.department_id.name or None,
                'manager': emp.parent_id.name or None,
                'badge': emp.barcode or None,
                # "المدني" is the dedicated Civil Code field, not Identification No.
                'civil': (emp.civil_code if 'civil_code' in emp._fields and emp.civil_code
                          else (emp.identification_id if 'identification_id' in emp._fields else None)),
                'residency_end': str(emp.residency_end_date) if 'residency_end_date' in emp._fields and emp.residency_end_date else None,
                'phone': emp.work_phone or emp.mobile_phone or None,
                'mobile': emp.mobile_phone or None,
                'email': emp.work_email or None,
                'nationality': emp.country_id.name or None,
                'photo': _abs('/api/v1/pms/employee/%s/photo' % emp.id),
                'duty': _duty, 'duty_label': _duty_lbl,
                'wage': round(emp.contract_id.wage, 3) if emp.contract_id else None,
                'tags': tags, 'marks': marks, 'on_leave': on_leave,
            },
            'details': details,
            'compliance': sorted(compliance, key=lambda c: c['days']),
            'docs': _rows('care.pms.doc.request'),
            'loans': _rows('hr.loan', ['loan_amount', 'balance_amount', 'total_amount']) + _rows('care.loan', ['amount']),
            'penalties': _rows('penalty.request', ['amount']),
            'bonuses': _rows('bonus.request', ['amount']),
            'allowances': _rows('care.allowance', ['amount', 'date']),
            'eos': _rows('care.eos', ['last_working_day']),
            'permissions': _rows('permission.request', ['permission_hours']),
            'custody': _rows('care.custody', ['issue_date']),
            'attendance': [{
                'id': a.id, 'date': str(a.check_in)[:10] if a.check_in else None,
                'check_in': _d(a.check_in), 'check_out': _d(a.check_out),
                'hours': round(a.worked_hours or 0.0, 1),
                'open': not a.check_out,
            } for a in att],
            # rich sections
            'leaves': leaves, 'transfers': transfers, 'uniform': uniform,
            'skills': skills, 'appraisals': appraisals, 'vehicles': vehicles,
            'violations': violations, 'documents': documents,
            'payslips': payslips, 'devices': devices, 'legal': legal,
            'suspension': _suspension_block,
        })

    @route(API + '/pms/vehicle/<int:vid>/file', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_vehicle_file(self, vid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'fleet.vehicle' not in env:
            return _err('غير متاح', 404)
        veh = env['fleet.vehicle'].sudo().browse(int(vid))
        if not veh.exists():
            return _err('غير موجود', 404)
        my_depts = env['project.project'].search([]).mapped('pms_department_id')
        if 'department_id' in veh._fields and veh.department_id and veh.department_id.id not in my_depts.ids:
            return _err('هذه المركبة ليست ضمن مشاريعك', 403)
        uses = []
        if 'petrol.tank.use' in env:
            U = env['petrol.tank.use'].sudo()
            for u in U.search([('vehicle_id', '=', veh.id)], order='id desc', limit=60):
                qty = (u.use_quantity if 'use_quantity' in U._fields else
                       (u.quantity if 'quantity' in U._fields else 0.0)) or 0.0
                uses.append({'id': u.id, 'date': _d(u.datetime) if 'datetime' in U._fields else None,
                             'liters': round(qty, 1),
                             'odometer': int(u.odometer_value) if 'odometer_value' in U._fields and u.odometer_value else None})
        # Full vehicle sheet — grouped like the fleet page.
        def _vv(name, label):
            if name not in veh._fields:
                return None
            f = veh._fields[name]
            try:
                v = veh[name]
            except Exception:
                return None
            if f.type == 'many2one':
                v = v.display_name if v else None
            elif f.type == 'selection':
                try:
                    v = dict(f._description_selection(env)).get(v, v)
                except Exception:
                    pass
            elif f.type in ('date', 'datetime'):
                v = str(v) if v else None
            elif f.type in ('float', 'integer', 'monetary'):
                v = v if v else None
            if v in (None, '', False):
                return None
            return {'label': label, 'value': str(v)}

        vdetails = []

        def _vgrp(title, pairs):
            rows = [r for r in (_vv(n, l) for n, l in pairs) if r]
            if rows:
                vdetails.append({'title': title, 'fields': rows})

        _vgrp('بيانات المركبة', [
            ('brand_id', 'الماركة'), ('model_id', 'الطراز'), ('model_year', 'سنة الصنع'),
            ('vehicle_type', 'النوع'), ('category_id', 'الفئة'), ('color', 'اللون'),
            ('fuel_type', 'نوع الوقود')])
        _vgrp('التشغيل', [
            ('odometer', 'العدّاد'), ('driver_id', 'السائق'), ('manager_id', 'المسؤول'),
            ('department_id', 'الإدارة'), ('location', 'الموقع'), ('state_id', 'الحالة')])
        _vgrp('السجل', [
            ('license_plate', 'رقم اللوحة'), ('acquisition_date', 'تاريخ الاقتناء'),
            ('first_contract_date', 'أول عقد'), ('service_count', 'عدد الخدمات')])

        return _ok({
            'vehicle': {
                'id': veh.id, 'name': veh.display_name,
                'plate': veh.license_plate or None,
                'model': (veh.model_id.name if veh.model_id else None),
                'brand': (veh.brand_id.name if veh.brand_id else None),
                'driver': (veh.driver_id.name if veh.driver_id else None),
                'department': (veh.department_id.name if 'department_id' in veh._fields and veh.department_id else None),
                'odometer': int(veh.odometer) if 'odometer' in veh._fields and veh.odometer else None,
                'fuel_type': dict(veh._fields['fuel_type']._description_selection(env)).get(veh.fuel_type) if 'fuel_type' in veh._fields and veh.fuel_type else None,
            },
            'details': vdetails,
            'fuel': uses,
            'fuel_total': round(sum(u['liters'] for u in uses), 1),
        })

    @route(API + '/pms/employee/<int:eid>/photo', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_emp_photo(self, eid, **kw):
        import base64
        e = request.env['hr.employee'].sudo().browse(int(eid)).exists()
        data = (e.image_256 or e.image_1920) if e else None
        if not data:
            data = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        raw = base64.b64decode(data)
        return request.make_response(raw, headers=[
            ('Content-Type', 'image/png'), ('Content-Length', str(len(raw))),
            ('Cache-Control', 'private, max-age=3600')])

    @route(API + '/pms/task-photo/<int:aid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_task_photo(self, aid, **kw):
        """Serve a task's image attachment (token-free, but strictly limited to
        image attachments that live on a project.task)."""
        import base64
        a = request.env['ir.attachment'].sudo().browse(int(aid)).exists()
        raw = None
        if a and a.res_model == 'project.task' and (a.mimetype or '').startswith('image/') and a.datas:
            try:
                raw = base64.b64decode(a.datas)
            except Exception:
                raw = None
        if raw is None:
            raw = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
            ctype = 'image/png'
        else:
            ctype = a.mimetype
        return request.make_response(raw, headers=[
            ('Content-Type', ctype), ('Content-Length', str(len(raw))),
            ('Cache-Control', 'private, max-age=3600')])
