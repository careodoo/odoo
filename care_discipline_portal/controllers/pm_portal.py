# -*- coding: utf-8 -*-
# بند «الشكاوى التأديبية» داخل قائمة المشروع في بوابة مدير المشروع:
# يقدّم شكوى ضد أحد عمّال مشروعه ويتابع مسارها (مرآة للباك إند).
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.care_pms.controllers.pm_portal import PMManagerPortal

# الحالات «الحيّة» (قيد المعالجة)
_OPEN = ('draft', 'submitted', 'manager_approved', 'hr_review', 'legal_review', 'penalty_decided')


class DisciplinePMPortal(PMManagerPortal):

    # إضافة البند لقائمة المشروع
    def _menu_project(self, project, active):
        items = super()._menu_project(project, active)
        _ = self._t
        cnt = 0
        if project.pms_department_id:
            cnt = request.env['care.complaint'].sudo().search_count([
                ('complainant_id', '=', request.env.uid),
                ('employee_id.department_id', 'child_of', project.pms_department_id.id),
                ('state', 'in', _OPEN)])
        items.append({
            'label': _('الشكاوى التأديبية', 'Disciplinary Complaints'),
            'url': '/my/pm/p/%s/discipline' % project.id,
            'icon': 'fa-gavel', 'active': active == 'discipline',
            'badge': cnt or '',
        })
        return items

    # عمّال المشروع (ضمن نطاق مدير المشروع)
    def _disc_workers(self, project):
        env = request.env
        if not project.pms_department_id:
            return env['hr.employee'].sudo().browse()
        return env['hr.employee'].sudo().search(
            [('department_id', 'child_of', project.pms_department_id.id)], order='name')

    def _disc_rows(self, project):
        env = request.env
        dom = [('complainant_id', '=', env.uid)]
        if project.pms_department_id:
            dom += [('employee_id.department_id', 'child_of', project.pms_department_id.id)]
        recs = env['care.complaint'].sudo().search(dom, order='create_date desc', limit=200)
        C = env['care.complaint']
        sl = dict(C._fields['state']._description_selection(env))
        sev = dict(C._fields['severity']._description_selection(env))
        pl = dict(C._fields['penalty_type']._description_selection(env))
        rows = []
        for r in recs:
            rows.append({
                'id': r.id, 'name': r.name, 'employee': r.employee_id.name,
                'category': r.category_id.name, 'severity': sev.get(r.severity, ''),
                'sev_key': r.severity, 'date': r.incident_date,
                'state': r.state, 'state_label': sl.get(r.state, r.state),
                'penalty': pl.get(r.penalty_type, '') if r.penalty_type else '',
            })
        return rows

    # ---------- قائمة + نموذج التقديم ----------
    @http.route(['/my/pm/p/<int:project_id>/discipline'], type='http', auth='user', website=True)
    def pm_discipline(self, project_id=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        return request.render('care_discipline_portal.disc_pm_list', self._base(
            self._menu_project(p, 'discipline'), p.name, project=p,
            rows=self._disc_rows(p),
            workers=self._disc_workers(p),
            categories=env['care.complaint.category'].sudo().search([('active', '=', True)]),
            today_iso=fields.Date.today().isoformat(),
            ok=kw.get('ok'), err=kw.get('err')))

    @http.route(['/my/pm/p/<int:project_id>/discipline/submit'], type='http',
                auth='user', website=True, methods=['POST'])
    def pm_discipline_submit(self, project_id=None, **post):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        try:
            emp = int(post.get('employee_id') or 0)
            cat = int(post.get('category_id') or 0)
            desc = (post.get('description') or '').strip()
            if not (emp and cat and desc):
                return request.redirect('/my/pm/p/%s/discipline?err=missing' % p.id)
            if emp not in self._disc_workers(p).ids:
                return request.redirect('/my/pm/p/%s/discipline?err=scope' % p.id)
            vals = {
                'employee_id': emp, 'category_id': cat, 'description': desc,
                'severity': post.get('severity') or 'medium',
                'incident_date': post.get('incident_date') or fields.Date.context_today(env['care.complaint']),
                'witnesses': (post.get('witnesses') or '').strip() or False,
                'complainant_ack': bool(post.get('ack')),
            }
            # يُنشأ باسم مدير المشروع (ليكون هو مُقدّم الشكوى)، ثم يُقدَّم
            c = env['care.complaint'].create(vals)
            c.action_submit()
            return request.redirect('/my/pm/p/%s/discipline?ok=1' % p.id)
        except Exception as e:
            msg = 'ack' if 'الإقرار' in str(e) else ('presc' if 'التقادم' in str(e) else '1')
            return request.redirect('/my/pm/p/%s/discipline?err=%s' % (p.id, msg))

    # ---------- تفاصيل شكوى ----------
    @http.route(['/my/pm/p/<int:project_id>/discipline/<int:cid>'], type='http',
                auth='user', website=True)
    def pm_discipline_detail(self, project_id=None, cid=None, **kw):
        p, red = self._proj_or_redirect(project_id)
        if red:
            return red
        env = request.env
        c = env['care.complaint'].sudo().browse(int(cid))
        # يرى مدير المشروع شكاواه فقط
        if not c.exists() or c.complainant_id.id != env.uid:
            return request.redirect('/my/pm/p/%s/discipline' % p.id)
        C = env['care.complaint']
        steps = [
            ('submitted', self._t('بانتظار المدير المباشر', 'Pending direct manager')),
            ('manager_approved', self._t('بانتظار الموارد البشرية', 'Pending HR')),
            ('hr_review', self._t('تحقيق الموارد البشرية', 'HR investigation')),
            ('legal_review', self._t('بانتظار الإدارة القانونية', 'Pending Legal')),
            ('penalty_decided', self._t('بانتظار تطبيق الجزاء', 'Pending penalty execution')),
            ('applied', self._t('طُبّق الجزاء', 'Penalty applied')),
        ]
        order = [s[0] for s in steps]
        cur_idx = order.index(c.state) if c.state in order else (len(order) if c.state == 'closed' else -1)
        pl = dict(C._fields['penalty_type']._description_selection(env))
        sl = dict(C._fields['state']._description_selection(env))
        info = {
            'id': c.id, 'name': c.name, 'employee': c.employee_id.name,
            'category': c.category_id.name,
            'severity': dict(C._fields['severity']._description_selection(env)).get(c.severity, ''),
            'date': c.incident_date, 'description': c.description,
            'state': c.state, 'state_label': sl.get(c.state, c.state),
            'penalty': pl.get(c.penalty_type, '') if c.penalty_type else '',
            'law_article': c.law_article_id.display_name or '',
            'reject_reason': c.reject_reason or '',
            'rejected': c.state == 'rejected',
        }
        return request.render('care_discipline_portal.disc_pm_detail', self._base(
            self._menu_project(p, 'discipline'), p.name, project=p,
            c=info, steps=steps, cur_idx=cur_idx))
