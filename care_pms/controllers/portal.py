# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError


class PMSPortal(CustomerPortal):

    def _pms_project_domain(self):
        return [('portal_user_ids', 'in', request.env.user.ids)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'pms_project_count' in counters:
            values['pms_project_count'] = request.env['project.project'].search_count(
                self._pms_project_domain())
        return values

    @http.route(['/my/pms', '/my/pms/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_pms_projects(self, page=1, **kw):
        # rule-scoped search as the portal user, then sudo for safe display
        projects = request.env['project.project'].search(self._pms_project_domain())
        values = {
            'projects': projects.sudo(),
            'page_name': 'pms_project',
        }
        return request.render('care_pms.portal_my_pms_projects', values)

    @http.route(['/my/pms/<int:project_id>'], type='http', auth='user', website=True)
    def portal_pms_project(self, project_id=None, **kw):
        try:
            project = self._document_check_access('project.project', project_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        project_su = project.sudo()
        tasks = request.env['project.task'].sudo().search([('project_id', '=', project.id)], limit=200)
        materials = request.env['care.pms.material'].sudo().search([('project_id', '=', project.id)])
        deliveries = request.env['care.pms.delivery.note'].sudo().search(
            [('project_id', '=', project.id)], limit=50)
        values = {
            'project': project_su,
            'tasks': tasks,
            'materials': materials,
            'deliveries': deliveries,
            'page_name': 'pms_project',
        }
        return request.render('care_pms.portal_pms_project_page', values)

    @http.route(['/my/pms/<int:project_id>/note'], type='http', auth='user', website=True, methods=['POST'])
    def portal_pms_project_note(self, project_id=None, **kw):
        try:
            project = self._document_check_access('project.project', project_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        subject = kw.get('subject') or _('ملاحظة/طلب من البورتال')
        body = kw.get('note') or ''
        kind = kw.get('kind') or 'note'
        if body:
            label = {'complaint': '🔴 شكوى', 'request': '📥 طلب', 'note': '📝 ملاحظة'}.get(kind, '📝 ملاحظة')
            project.sudo().message_post(
                body='<b>%s — %s</b><br/>%s' % (label, subject, body),
                subject=subject)
        return request.redirect('/my/pms/%s?submitted=1' % project.id)

    @http.route(['/my/pms/task/<int:task_id>/note'], type='http', auth='user', website=True, methods=['POST'])
    def portal_pms_task_note(self, task_id=None, **kw):
        try:
            task = self._document_check_access('project.task', task_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        note = kw.get('note')
        pid = task.sudo().project_id.id
        if note:
            task.sudo().message_post(body=_('ملاحظة من البورتال: %s') % note)
        return request.redirect('/my/pms/%s' % pid)
