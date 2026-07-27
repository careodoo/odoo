# -*- coding: utf-8 -*-
"""بورتال الويب للتصاريح — تكافؤ التطبيق↔البورتال: المُصدِر (عميل/مدير مشروع/مشرف)
يُصدر ويتابع التصاريح، والحارس يسجّل دخول/خروج الأشخاص من المتصفّح. يعيد استخدام
منطق النطاق والتسلسل نفسه من PermitsApi (عبر request.env بدل توكن التطبيق)."""
import datetime
from odoo import fields
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

from .permits_api import PermitsApi


class PermitsPortal(PermitsApi, CustomerPortal):

    def _portal_scope(self, env):
        """(dom الأساسي, can_issue, is_guard, issuer_premises)."""
        is_mgr = self._is_manager(env)
        issuer_prem = self._premises_of(env, self._issuer_facilities(env))
        guard_prem = self._guard_premises(env)
        is_guard = bool(guard_prem)
        can_issue = is_mgr or bool(issuer_prem)
        if is_mgr:
            dom = []
        elif can_issue:
            dom = ['|', ('create_uid', '=', env.uid), ('premise_id', 'in', issuer_prem.ids if issuer_prem else [])]
        elif is_guard:
            dom = [('premise_id', 'in', guard_prem.ids)]
        else:
            dom = [('id', '=', 0)]
        return dom, can_issue, is_guard, issuer_prem

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'permits_count' in counters:
            env = request.env
            cnt = 0
            if 'security.gate.pass' in env:
                dom, can_issue, is_guard, _p = self._portal_scope(env)
                if can_issue or is_guard:
                    cnt = env['security.gate.pass'].sudo().search_count(dom)
            values['permits_count'] = cnt
        return values

    @route(['/my/permits'], type='http', auth='user', website=True)
    def portal_permits(self, state=None, **kw):
        env = request.env
        if 'security.gate.pass' not in env:
            return request.render('care_cafm_mobile_api.portal_permits', {
                'items': [], 'stats': {}, 'can_issue': False, 'is_guard': False, 'premises': [], 'state': 'all'})
        GP = env['security.gate.pass'].sudo()
        dom, can_issue, is_guard, issuer_prem = self._portal_scope(env)
        fdom = list(dom)
        if state and state != 'all':
            fdom = fdom + [('state', '=', state)]
        recs = GP.search(fdom, order='create_date desc', limit=200)
        return request.render('care_cafm_mobile_api.portal_permits', {
            'items': [self._dict(env, g) for g in recs],
            'stats': self._stats(env, GP, dom),
            'can_issue': can_issue, 'is_guard': is_guard,
            'premises': [{'id': p.id, 'name': p.name} for p in (issuer_prem or [])],
            'state': state or 'all',
        })

    @route(['/my/permits/new'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_permit_new(self, **post):
        env = request.env
        if 'security.gate.pass' not in env:
            return request.redirect('/my/permits')
        prem = self._premises_of(env, self._issuer_facilities(env))
        if not self._is_manager(env) and not prem:
            return request.redirect('/my/permits')
        try:
            pid = int(post.get('premise_id'))
        except (TypeError, ValueError):
            return request.redirect('/my/permits')
        if not self._is_manager(env) and pid not in (prem.ids if prem else []):
            return request.redirect('/my/permits')
        premise = env['security.premise'].sudo().browse(pid).exists()
        name = (post.get('visitor') or '').strip()
        if not premise or not name:
            return request.redirect('/my/permits')
        Partner = env['res.partner'].sudo()
        visitor = Partner.search([('name', '=', name)], limit=1) or Partner.create({'name': name, 'phone': post.get('phone') or False})
        try:
            days = max(1, int(post.get('days') or 1))
        except (TypeError, ValueError):
            days = 1
        now = fields.Datetime.now()
        gp = env['security.gate.pass'].sudo().create({
            'visitor_id': visitor.id, 'client_id': premise.client_id.id if premise.client_id else False,
            'premise_id': premise.id, 'purpose': post.get('purpose') or '-',
            'valid_from': now, 'valid_until': now + datetime.timedelta(days=days),
            'pass_type': post.get('pass_type') if post.get('pass_type') in ('personal', 'vehicle') else 'personal',
            'is_multi_entry': bool(post.get('is_multi_entry')),
        })
        gp.write({'state': 'approved', 'approved_by': env.uid, 'approved_date': now})
        try:
            gp.action_generate_qr_code()
        except Exception:
            pass
        self._notify(env, self._premise_guard_users(env, premise), '🚪 تصريح جديد',
                     '%s — %s' % (name, premise.name), url='/permits/%s' % gp.id)
        return request.redirect('/my/permits/%s' % gp.id)

    @route(['/my/permits/<int:pid>'], type='http', auth='user', website=True)
    def portal_permit_detail(self, pid, **kw):
        env = request.env
        gp = env['security.gate.pass'].sudo().browse(pid).exists() if 'security.gate.pass' in env else None
        if not gp:
            return request.redirect('/my/permits')
        d = self._dict(env, gp, full=True)
        d['_is_guard'] = bool(self._guard_premises(env))
        d['_active'] = gp.state in ('approved', 'valid')
        return request.render('care_cafm_mobile_api.portal_permit_detail', {'p': d})

    @route(['/my/permits/<int:pid>/pdf'], type='http', auth='user', website=True)
    def portal_permit_pdf(self, pid, **kw):
        env = request.env
        gp = env['security.gate.pass'].sudo().browse(pid).exists() if 'security.gate.pass' in env else None
        if not gp:
            return request.redirect('/my/permits')
        pdf, _ct = env['ir.actions.report'].sudo()._render_qweb_pdf(
            'care_cafm_mobile_api.report_permit_card', [gp.id])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename=permit-%s.pdf' % gp.id),
        ])

    @route(['/my/permits/<int:pid>/visit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_permit_visit(self, pid, **post):
        env = request.env
        gp = env['security.gate.pass'].sudo().browse(pid).exists() if 'security.gate.pass' in env else None
        if gp:
            direction = post.get('direction')
            try:
                gp.api_record_visit(direction, person=post.get('person'))
                if gp.create_uid and gp.create_uid.id != env.uid:
                    lbl = 'دخل' if direction == 'in' else 'خرج'
                    self._notify(env, gp.create_uid, '🚪 حركة تصريح',
                                 '%s %s %s' % (post.get('person') or 'زائر', lbl, gp.premise_id.name or ''),
                                 url='/permits/%s' % gp.id)
            except Exception:
                pass
        return request.redirect('/my/permits/%s' % pid)
