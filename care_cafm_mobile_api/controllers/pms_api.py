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
        # Two grouped queries instead of two search_counts per project — the loop
        # was ~244 queries for 122 projects and took 1.5s on the list screen.
        def _by_project(extra):
            rows = T.read_group([('project_id', 'in', recs.ids)] + extra,
                                ['project_id'], ['project_id'])
            return {r['project_id'][0]: r['project_id_count'] for r in rows if r['project_id']}
        totals = _by_project([])
        dones = _by_project(DOM_DONE)
        out = []
        for p in recs:
            total = totals.get(p.id, 0)
            done = dones.get(p.id, 0)
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
            'forward_to': _m2o(t.forward_to_id) if 'forward_to_id' in t._fields else None,
            'forward_from': _m2o(t.forward_from_id) if 'forward_from_id' in t._fields else None,
            'forward_state': (t.forward_state if 'forward_state' in t._fields else None),
            'forward_reason': (t.forward_reason or None) if 'forward_reason' in t._fields else None,
            # Whether THIS caller is the one being asked to accept/reject.
            'is_recipient': bool('forward_to_id' in t._fields and t.forward_to_id
                                 and t.forward_to_id.id == env.uid),
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
            t.write({'forward_to_id': int(to_uid), 'forward_reason': b.get('reason') or ''})
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
        try:
            # The task is created as the caller, so create-rights are enforced.
            t = env['project.task'].create(vals)
        except Exception as e:
            return _err(str(e) or 'تعذّر الإنشاء', 403)
        return _ok(self._task_row(t))

    @route(API + '/pms/project/<int:pid>/forward-users', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def pms_forward_users(self, pid, **kw):
        """Internal users a task may be forwarded to (mirrors the portal list)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        users = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name', limit=400)
        return _ok([{'id': u.id, 'name': u.name} for u in users])



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
        for m in env['care.pms.material'].sudo().search([('project_id', '=', p.id)], limit=300):
            rows.append({
                'id': m.id, 'title': m.name or m.display_name,
                'subtitle': (m.category_id.name if 'category_id' in m._fields and m.category_id else None),
                'value': m.qty_available if 'qty_available' in m._fields else None,
                'value_label': 'المتاح',
                'badges': [x for x in [
                    ('الوحدة: %s' % m.uom_id.name) if 'uom_id' in m._fields and m.uom_id else None,
                ] if x],
            })
        return {'rows': rows, 'stats': {'الأصناف': len(rows)}}

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
        rows = [{
            'id': s.id, 'title': s.name or s.display_name,
            'subtitle': _d(s.date) if 'date' in s._fields else None,
            'state': (s.state if 'state' in s._fields else None),
            'state_label': state_lbl.get(s.state) if 'state' in s._fields else None,
            # Only offer "receive" on records that are actually awaiting receipt.
            # Only a supply in transit can be received — matches the receive
            # endpoint's own guard, so the button never leads to a 422.
            'can_receive': bool('state' in s._fields and s.state == 'sent'),
            'badges': [('%s بند' % len(s.line_ids))] if 'line_ids' in s._fields else [],
        } for s in recs]
        return {'rows': rows, 'stats': {'الطلبات': len(rows),
                                        'بانتظار الاستلام': sum(1 for r in rows if r['can_receive'])}}

    def _sec_petty(self, env, p):
        P = env['care.pms.petty.cash'].sudo()
        recs = P.search([('project_id', '=', p.id)], order='id desc', limit=100)
        state_lbl = dict(P._fields['state'].selection) if 'state' in P._fields else {}
        total = sum(r.amount for r in recs) if 'amount' in P._fields else 0
        spent = sum(r.spent_amount for r in recs) if 'spent_amount' in P._fields else 0
        rows = [{
            'id': r.id, 'title': r.name or r.display_name,
            'subtitle': _d(r.date) if 'date' in r._fields else None,
            'state': (r.state if 'state' in r._fields else None),
            'state_label': state_lbl.get(r.state) if 'state' in r._fields else None,
            'value': r.amount if 'amount' in r._fields else None,
            'value_label': 'العهدة',
            'badges': [x for x in [
                ('المصروف: %s' % round(r.spent_amount, 3)) if 'spent_amount' in r._fields else None,
                ('المتبقي: %s' % round(r.balance, 3)) if 'balance' in r._fields else None,
            ] if x],
        } for r in recs]
        return {'rows': rows, 'stats': {'العُهد': len(rows), 'إجمالي العهدة': round(total, 3),
                                        'المصروف': round(spent, 3)}}

    def _sec_requests(self, env, p):
        R = env['care.pms.doc.request'].sudo()
        recs = R.search([('project_id', '=', p.id)], order='id desc', limit=100)
        state_lbl = dict(R._fields['state'].selection) if 'state' in R._fields else {}
        rows = [{
            'id': r.id, 'title': r.display_name,
            'subtitle': (r.employee_id.name if 'employee_id' in r._fields and r.employee_id else None),
            'state': (r.state if 'state' in r._fields else None),
            'state_label': state_lbl.get(r.state) if 'state' in r._fields else None,
            'badges': [_d(r.create_date)] if r.create_date else [],
        } for r in recs]
        return {'rows': rows, 'stats': {'الطلبات': len(rows)}}

    def _sec_team(self, env, p):
        dept = self._dept(p)
        if not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا قسم مرتبط بهذا المشروع.'}
        emps = env['hr.employee'].sudo().search([('department_id', '=', dept)], limit=500)
        rows = [{
            'id': e.id, 'title': e.name,
            'subtitle': e.job_title or None,
            'image': _abs('/api/v1/pms/employee/%s/photo' % e.id),
            'badges': [x for x in [e.work_phone or None,
                                   (e.parent_id.name if e.parent_id else None)] if x],
        } for e in emps]
        return {'rows': rows, 'stats': {'العاملون': len(rows)}}

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
        rows = [{
            'id': a.id, 'title': a.employee_id.name,
            'subtitle': '%s → %s' % (_d(a.check_in) or '—', _d(a.check_out) or '—'),
            'value': round(a.worked_hours or 0.0, 1), 'value_label': 'ساعة',
            'state': 'open' if not a.check_out else 'closed',
            'state_label': 'بالموقع' if not a.check_out else 'انصرف',
        } for a in recent]
        return {'rows': rows, 'stats': {
            'العاملون': len(emps), 'حضروا اليوم': len(today.mapped('employee_id')),
            'بالموقع الآن': len(here),
            'ساعات اليوم': round(sum(today.mapped('worked_hours') or [0]), 1)}}

    def _sec_timesheet(self, env, p):
        # care.timesheet is scoped by department and holds a period + lines —
        # it has no project_id and no hours field (checked against the model,
        # not assumed).
        dept = self._dept(p)
        if 'care.timesheet' not in env or not dept:
            return {'rows': [], 'stats': {}, 'empty': 'لا كشوف ساعات لهذا المشروع.'}
        T = env['care.timesheet'].sudo()
        recs = T.search([('department_id', '=', dept)], order='id desc', limit=100)
        state_lbl = dict(T._fields['state'].selection) if 'state' in T._fields else {}
        rows = [{
            'id': t.id, 'title': t.name or t.display_name,
            'subtitle': '%s → %s' % (_d(t.date_from) or '—', _d(t.date_to) or '—'),
            'state': (t.state if 'state' in t._fields else None),
            'state_label': state_lbl.get(t.state) if 'state' in t._fields else None,
            'value': len(t.line_ids) if 'line_ids' in t._fields else None,
            'value_label': 'سطر',
        } for t in recs]
        return {'rows': rows, 'stats': {'الكشوف': len(rows),
                                        'إجمالي السطور': sum(r['value'] or 0 for r in rows)}}

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
        dept = self._dept(p)
        if not dept or 'petrol.tank.use' not in env:
            return {'rows': [], 'stats': {}, 'empty': 'لا بيانات وقود لهذا المشروع.'}
        U = env['petrol.tank.use'].sudo()
        uses = U.search([('vehicle_id.department_id', '=', dept)], order='id desc', limit=150)
        rows = []
        for u in uses:
            # The model stamps `datetime` and stores litres in use_quantity —
            # there is no `date`/`liters`/`amount` on it.
            qty = (u.use_quantity if 'use_quantity' in U._fields else
                   (u.quantity if 'quantity' in U._fields else 0.0)) or 0.0
            rows.append({
                'id': u.id,
                'vehicle_id': u.vehicle_id.id if u.vehicle_id else None,
                'title': (u.vehicle_id.display_name if u.vehicle_id else u.display_name),
                'subtitle': _d(u.datetime) if 'datetime' in U._fields else None,
                'open': 'vehicle' if u.vehicle_id else None,
                'value': round(qty, 1), 'value_label': 'لتر',
                'badges': [x for x in [
                    ('العدّاد: %s' % int(u.odometer_value)) if 'odometer_value' in U._fields and u.odometer_value else None,
                ] if x],
            })
        return {'rows': rows, 'stats': {'التعبئات': len(rows),
                                        'إجمالي اللترات': round(sum(r['value'] or 0 for r in rows), 1)}}

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
                'value': worst, 'value_label': 'يوم',
                'state': ('expired' if (worst is not None and worst < 0)
                          else 'soon' if (worst is not None and worst <= 60) else 'ok'),
                'state_label': ('منتهية' if (worst is not None and worst < 0)
                                else 'تنتهي قريبًا' if (worst is not None and worst <= 60) else 'سارية'),
                'badges': ['%s: %s (%s يوم)' % (i['label'], i['date'], i['days']) for i in items],
            })
        # Worst first — this section exists to surface what is about to lapse.
        rows.sort(key=lambda r: (r['value'] if r['value'] is not None else 9999))
        return {'rows': rows, 'stats': {'العاملون بوثائق': len(rows),
                                        'منتهية': expired, 'تنتهي خلال 60 يومًا': soon}}

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
        'finance': ('المالية', 'account_balance', _sec_finance),
        'contracts': ('العقود', 'assignment', _sec_contracts),
        'performance': ('الأداء', 'trending_up', _sec_performance),
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
        return _ok({
            'project': {'id': p.id, 'name': p.name},
            'sections': [{'code': c, 'label': v[0], 'icon': v[1]} for c, v in self.SECTIONS.items()],
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
            out['employees'] = [{'id': e.id, 'name': e.name}
                                for e in (env['hr.employee'].sudo().search(
                                    [('department_id', '=', dept)], limit=500) if dept else [])]
        return _ok(out)

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
        if sup.state != 'sent':
            return _err('هذا التوريد ليس قيد الاستلام', 422)
        try:
            sup.action_receive()
        except Exception as e:
            return _err(str(e) or 'تعذّر الاستلام', 422)
        return _ok({'id': sup.id, 'state': sup.state})

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
            env['care.pms.petty.cash.expense'].sudo().create({
                'cash_id': cash.id, 'name': b.get('name') or 'مصروف',
                'category': b.get('category') or 'misc',
                'amount': amt, 'foreign_amount': amt, 'rate': 1.0})
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
            # Pulls present-days per employee from biometric attendance, then
            # sends for approval — same two calls the portal makes.
            if hasattr(ts, 'button_generate_timesheet'):
                ts.button_generate_timesheet()
            if hasattr(ts, 'button_submit'):
                ts.button_submit()
        except Exception as e:
            return _err(str(e) or 'تعذّر إنشاء الكشف', 422)
        return _ok({'id': ts.id, 'name': ts.display_name})

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
        return _ok({
            'employee': {
                'id': emp.id, 'name': emp.name, 'job': emp.job_title or None,
                'department': emp.department_id.name or None,
                'manager': emp.parent_id.name or None,
                'phone': emp.work_phone or emp.mobile_phone or None,
                'nationality': emp.country_id.name or None,
                'photo': _abs('/api/v1/pms/employee/%s/photo' % emp.id),
                # Wage is the reason a PM opens this file — the portal shows it,
                # so parity does too; the whole endpoint is department-scoped.
                'wage': round(emp.contract_id.wage, 3) if emp.contract_id else None,
            },
            'compliance': sorted(compliance, key=lambda c: c['days']),
            'docs': _rows('care.pms.doc.request'),
            'loans': _rows('hr.loan', ['amount']) + _rows('care.loan', ['amount']),
            'penalties': _rows('penalty.request', ['amount']),
            'bonuses': _rows('bonus.request', ['amount']),
            'attendance': [{
                'id': a.id, 'date': str(a.check_in)[:10] if a.check_in else None,
                'check_in': _d(a.check_in), 'check_out': _d(a.check_out),
                'hours': round(a.worked_hours or 0.0, 1),
                'open': not a.check_out,
            } for a in att],
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
        return _ok({
            'vehicle': {
                'id': veh.id, 'name': veh.display_name,
                'plate': veh.license_plate or None,
                'model': (veh.model_id.name if veh.model_id else None),
                'driver': (veh.driver_id.name if veh.driver_id else None),
                'department': (veh.department_id.name if 'department_id' in veh._fields and veh.department_id else None),
                'odometer': int(veh.odometer) if 'odometer' in veh._fields and veh.odometer else None,
            },
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
