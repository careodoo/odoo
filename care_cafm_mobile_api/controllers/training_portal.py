# -*- coding: utf-8 -*-
"""بورتال ويب لموديول التدريب (/my/training) — تكافؤ مع شاشة التطبيق:
إحصائيات + بطاقات طلبات التدريب ملوّنة بالمرحلة. يعيد استخدام منطق TrainingApi."""
from odoo.http import request, route

from .training_api import TrainingApi


class TrainingPortal(TrainingApi):

    @route(['/my/training'], type='http', auth='user', website=True)
    def portal_training(self, stage=None, **kw):
        env = request.env
        if not self._has(env):
            return request.render('care_cafm_mobile_api.portal_training', {'available': False})
        cids = self._cids(env)
        A = env['training.application'].sudo()
        dom = [('company_id', 'in', cids)]
        if stage:
            dom.append(('stage_id', '=', int(stage)))
        apps = A.search(dom, order='id desc', limit=200)
        all_apps = A.search([('company_id', 'in', cids)])
        stages = env['application.stage'].sudo().search([])
        return request.render('care_cafm_mobile_api.portal_training', {
            'available': True,
            'stats': {
                'applications': len(all_apps),
                'approved': len(all_apps.filtered('is_approved')),
                'completed': len(all_apps.filtered('is_completed')),
                'in_progress': len(all_apps.filtered(lambda x: not x.is_completed and not x.is_approved)),
                'tasks': sum(all_apps.mapped('task_count')),
            },
            'stages': [{'id': s.id, 'name': s.name, 'count': A.search_count([('company_id', 'in', cids), ('stage_id', '=', s.id)])} for s in stages],
            'current_stage': int(stage) if stage else 0,
            'apps': [self._app_dict(a) for a in apps],
        })
