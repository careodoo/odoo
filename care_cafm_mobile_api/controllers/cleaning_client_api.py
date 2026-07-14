# -*- coding: utf-8 -*-
"""Client-facing CLEANING endpoints — surfaces the care_cafm_cleaning module's
quality audits, schedule compliance, cleaning rounds and consumables ledger,
hard-scoped to the caller's facilities. Read with sudo() so a client only ever
sees hygiene ops for their own sites, and can acknowledge/dispute audits."""
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


def _sel(Model, field):
    try:
        return dict(Model.fields_get([field])[field].get('selection') or [])
    except Exception:
        return {}


def _d(v):
    return v and str(v) or None


class CleaningClientApi(Controller):

    def _facilities(self, env):
        if env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system'):
            return env['care.cafm.facility'].sudo().search([])
        p = env.user.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        return env['care.cafm.facility'].sudo().search([('partner_id', 'in', list(pids))])

    def _fac_ids(self, env):
        facs = self._facilities(env)
        fid = request.httprequest.args.get('facility_id')
        if fid and fid.isdigit() and int(fid) in facs.ids:
            return [int(fid)]
        return facs.ids

    def _guard(self, env):
        if 'care.cafm.clean.audit' not in env:
            return _err('خدمة النظافة غير مفعّلة', 404)
        return None

    # ---- summary ----------------------------------------------------------
    @route(API + '/client/clean/summary', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def clean_summary(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.clean.audit' not in env:
            return _ok({'available': False})
        fids = self._fac_ids(env)
        Audit = env['care.cafm.clean.audit'].sudo()
        Sched = env['care.cafm.clean.schedule'].sudo()
        Round = env['care.cafm.clean.round'].sudo()
        audits = Audit.search([('facility_id', 'in', fids), ('state', '=', 'done')])
        scores = audits.mapped('score')
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        scheds = Sched.search([('facility_id', 'in', fids)])
        cons = env['care.cafm.clean.consumable'].sudo().search([('facility_id', 'in', fids)]) if 'care.cafm.clean.consumable' in env else Round.browse()
        from odoo import fields as F
        today = F.Date.context_today(Round)
        return _ok({
            'available': True,
            'audits': len(audits),
            'avg_score': avg,
            'audits_pending_ack': Audit.search_count([('facility_id', 'in', fids), ('state', '=', 'done'), ('client_ack', '=', 'pending')]),
            'schedules': len(scheds),
            'schedules_due': len(scheds.filtered('is_due')),
            'rounds_today': Round.search_count([('facility_id', 'in', fids), ('scan_in_time', '>=', str(today))]) if fids else 0,
            'consumables': len(cons),
            'low_stock': len(cons.filtered('low_stock')) if cons else 0,
        })

    # ---- quality audits ---------------------------------------------------
    @route(API + '/client/clean/audits', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def clean_audits(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.clean.audit'].sudo()
        rt, ack = _sel(M, 'rating'), _sel(M, 'client_ack')
        recs = M.search([('facility_id', 'in', self._fac_ids(env)), ('state', '=', 'done')], order='audit_date desc', limit=200)
        return _ok([{
            'id': a.id, 'name': a.name, 'facility': a.facility_id.name or None,
            'location': a.location_id.name or None, 'date': _d(a.audit_date),
            'auditor': a.auditor_id.name or None,
            'score': round(a.score, 1), 'rating': rt.get(a.rating, a.rating or ''), 'rating_raw': a.rating,
            'fail_count': a.fail_count,
            'ack': a.client_ack, 'ack_label': ack.get(a.client_ack, a.client_ack or ''),
            'ack_comment': a.client_ack_comment or None,
            'items': [{'name': l.name, 'result': l.result, 'note': l.note or None} for l in a.line_ids],
        } for a in recs])

    @route(API + '/client/clean/audit/<int:aid>/<string:decision>', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def clean_audit_ack(self, aid, decision, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        if decision not in ('accept', 'dispute'):
            return _err('إجراء غير صالح', 422)
        a = env['care.cafm.clean.audit'].sudo().browse(int(aid)).exists()
        if not a or a.facility_id.id not in self._fac_ids(env):
            return _err('غير موجود', 404)
        state = 'accepted' if decision == 'accept' else 'disputed'
        comment = (_body().get('comment') or '').strip()
        a.write({'client_ack': state, 'client_ack_comment': comment or a.client_ack_comment})
        a.message_post(body='العميل %s تدقيق الجودة%s' % (
            'قبِل' if state == 'accepted' else 'اعترض على',
            (' — %s' % comment) if comment else ''))
        return _ok({'id': a.id, 'ack': a.client_ack})

    # ---- schedule compliance ---------------------------------------------
    @route(API + '/client/clean/schedules', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def clean_schedules(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.clean.schedule'].sudo()
        fr = _sel(M, 'frequency')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='facility_id, location_id')
        return _ok([{
            'id': s.id, 'location': s.location_id.name or None, 'facility': s.facility_id.name or None,
            'frequency': fr.get(s.frequency, s.frequency or ''), 'demand_based': s.demand_based,
            'last_done': _d(s.last_done), 'next_due': _d(s.next_due), 'is_due': s.is_due,
        } for s in recs])

    # ---- cleaning rounds --------------------------------------------------
    @route(API + '/client/clean/rounds', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def clean_rounds(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        g = self._guard(env)
        if g:
            return g
        M = env['care.cafm.clean.round'].sudo()
        st = _sel(M, 'state')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='id desc', limit=200)
        return _ok([{
            'id': r.id, 'name': r.name, 'worker': r.worker_id.name or None,
            'location': r.location_id.name or None, 'facility': r.facility_id.name or None,
            'scan_in': _d(r.scan_in_time), 'scan_out': _d(r.scan_out_time),
            'duration_min': round(r.duration_minutes, 1),
            'state': r.state, 'state_label': st.get(r.state, r.state or ''),
        } for r in recs])

    # ---- consumables ------------------------------------------------------
    @route(API + '/client/clean/consumables', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def clean_consumables(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'care.cafm.clean.consumable' not in env:
            return _ok([])
        M = env['care.cafm.clean.consumable'].sudo()
        cat = _sel(M, 'category')
        recs = M.search([('facility_id', 'in', self._fac_ids(env))], order='facility_id, name')
        return _ok([{
            'id': c.id, 'name': c.name, 'facility': c.facility_id.name or None,
            'category': cat.get(c.category, c.category or ''), 'category_raw': c.category,
            'on_hand': c.on_hand, 'unit': c.unit or None, 'min_qty': c.min_qty,
            'low_stock': c.low_stock, 'last_supply_date': _d(c.last_supply_date),
        } for c in recs])
