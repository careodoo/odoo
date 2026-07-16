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
    return {'id': v.id, 'name': v.display_name} if v else None


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
                           'avatar': _abs('/web/image/res.users/%s/avatar_128' % u.id)}
                          for u in t.user_ids],
            'state': t.state if 'state' in t._fields else None,
            'done': (t.state in DONE_STATES) if 'state' in t._fields else False,
            'progress': round(t.progress or 0, 1) if 'progress' in t._fields else 0,
            'subtasks': len(t.child_ids) if 'child_ids' in t._fields else 0,
            'tags': [tg.name for tg in t.tag_ids] if 'tag_ids' in t._fields else [],
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
        out = []
        for p in recs:
            total = T.search_count([('project_id', '=', p.id)])
            done = T.search_count([('project_id', '=', p.id)] + DOM_DONE)
            out.append({
                'id': p.id, 'name': p.name,
                'partner': _m2o(p.partner_id),
                'manager': _m2o(p.user_id),
                'date_start': _d(p.date_start), 'date_end': _d(p.date),
                'tasks': total, 'done': done,
                'progress': round(done * 100.0 / total, 1) if total else 0.0,
                'open': total - done,
            })
        return _ok(out)

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
        return _ok({
            'id': p.id, 'name': p.name,
            'partner': _m2o(p.partner_id), 'manager': _m2o(p.user_id),
            'date_start': _d(p.date_start), 'date_end': _d(p.date),
            'description': p.description or None,
            'tasks': total, 'done': done, 'open': total - done,
            'progress': round(done * 100.0 / total, 1) if total else 0.0,
            'stages': stages,
        })

    # ---- tasks -----------------------------------------------------------
    @route(API + '/pms/tasks', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_tasks(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from odoo import fields as of
        T = env['project.task']
        dom = []
        if kw.get('project_id') and str(kw['project_id']).isdigit():
            dom.append(('project_id', '=', int(kw['project_id'])))
        if kw.get('stage_id') and str(kw['stage_id']).isdigit():
            dom.append(('stage_id', '=', int(kw['stage_id'])))
        f = kw.get('filter') or ''
        today = of.Date.context_today(T)
        now = of.Datetime.now()
        dl_is_dt = T._fields['date_deadline'].type == 'datetime'
        past = now if dl_is_dt else today
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
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', ('name', 'ilike', q), ('project_id.name', 'ilike', q)]
        try:
            limit = min(int(kw.get('limit') or 80), 200)
        except Exception:
            limit = 80
        recs = T.search(dom, order='priority desc, date_deadline asc, id desc', limit=limit)
        return _ok({'count': T.search_count(dom), 'rows': [self._task_row(t) for t in recs]})

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
            'children': [{'id': c.id, 'name': c.name, 'stage': c.stage_id.name,
                          'done': c.state in DONE_STATES} for c in t.child_ids] if 'child_ids' in t._fields else [],
            'can_write': can_write,
            'stages': [{'id': s.id, 'name': s.name, 'fold': s.fold}
                       for s in env['project.task.type'].search(
                           [('project_ids', 'in', [t.project_id.id])] if t.project_id else [])],
            'messages': [{'author': m.author_id.display_name or '—', 'date': _d(m.date),
                          'body': (m.body or '')[:600]}
                         for m in t.message_ids.filtered(lambda x: x.body)[:8]],
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
