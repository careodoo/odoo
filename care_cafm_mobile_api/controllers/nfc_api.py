# -*- coding: utf-8 -*-
"""NFC tag provisioning — program a physical tag for a location, verify it, and
manage its lifecycle (active / disabled / lost). Writing the location code onto
the tag AND registering the tag's hardware uid means even a write-protected tag
still resolves when a worker taps it."""
from odoo import fields
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _body, API


class NfcApi(Controller):

    def _may_manage(self, env):
        """Provisioning is a supervisor/manager job, not a field-worker one."""
        u = env.user
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return True
        cp = u.partner_id.commercial_partner_id or u.partner_id
        if cp and cp.sudo().cafm_can_add_workers:
            return True
        # a CAFM/security supervisor may also tag their own sites
        try:
            return u.has_group('security_management.group_security_manager')
        except Exception:
            return False

    def _my_facility_ids(self, env):
        """Facilities the caller may tag: their client's, or the ones they work on."""
        u = env.user
        Fac = env['care.cafm.facility'].sudo()
        if u.has_group('base.group_erp_manager') or u.has_group('base.group_system'):
            return Fac.search([]).ids
        p = u.partner_id
        pids = {p.id}
        if p.commercial_partner_id:
            pids.add(p.commercial_partner_id.id)
            pids.update(env['res.partner'].sudo().search(
                [('commercial_partner_id', '=', p.commercial_partner_id.id)]).ids)
        ids = Fac.search([('partner_id', 'in', list(pids))]).ids
        if not ids and u.employee_id:
            ids = env['care.cafm.workorder'].sudo().search(
                [('employee_id', '=', u.employee_id.id)]).mapped('facility_id').ids
        return ids

    def _loc_dict(self, l):
        return {
            'id': l.id, 'name': l.name, 'code': l.code,
            'facility': l.facility_id.name or None, 'facility_id': l.facility_id.id or None,
            'building': l.building_id.name or None, 'floor': l.floor_id.name or None,
            'checkpoint': l.is_checkpoint,
            'nfc_uid': l.nfc_uid or None,
            'nfc_state': l.nfc_state or 'none',
            'nfc_state_label': dict(l._fields['nfc_state'].selection).get(l.nfc_state or 'none'),
            'nfc_written_on': str(l.nfc_written_on)[:16] if l.nfc_written_on else None,
            'nfc_written_by': l.nfc_written_by.name or None,
            'nfc_note': l.nfc_note or None,
            # what the app should write onto the tag
            'payload': l.code or '',
        }

    # ---- the provisioning list -------------------------------------------
    @route(API + '/nfc/locations', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def nfc_locations(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        a = request.httprequest.args
        Loc = env['care.cafm.location'].sudo()
        dom = [('facility_id', 'in', self._my_facility_ids(env))]
        fid = a.get('facility_id')
        if fid and fid.isdigit():
            dom.append(('facility_id', '=', int(fid)))
        st = a.get('state')
        if st == 'programmed':
            dom.append(('nfc_state', '=', 'active'))
        elif st == 'unprogrammed':
            dom.append(('nfc_state', 'in', ('none', 'lost')))
        elif st == 'disabled':
            dom.append(('nfc_state', '=', 'disabled'))
        q = (a.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('code', 'ilike', q), ('nfc_uid', 'ilike', q)]
        locs = Loc.search(dom, order='facility_id, name', limit=500)
        allf = Loc.search([('facility_id', 'in', self._my_facility_ids(env))])
        return _ok({
            'can_manage': self._may_manage(env),
            'counts': {
                'total': len(allf),
                'programmed': len(allf.filtered(lambda l: l.nfc_state == 'active')),
                'unprogrammed': len(allf.filtered(lambda l: l.nfc_state in ('none', 'lost') or not l.nfc_state)),
                'disabled': len(allf.filtered(lambda l: l.nfc_state == 'disabled')),
            },
            'facilities': [{'id': f.id, 'name': f.name} for f in
                           env['care.cafm.facility'].sudo().browse(self._my_facility_ids(env))],
            'locations': [self._loc_dict(l) for l in locs],
        })

    # ---- program / pair a tag ---------------------------------------------
    @route(API + '/nfc/location/<int:lid>/provision', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def nfc_provision(self, lid, **kw):
        """Bind a physical tag (by its uid) to this location and mark it active.
        The app writes the location code onto the tag first; if the tag is
        locked, registering the uid alone is still enough to resolve it."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._may_manage(env):
            return _err('غير مسموح لك ببرمجة الشرائح', 403)
        loc = env['care.cafm.location'].sudo().browse(lid).exists()
        if not loc or loc.facility_id.id not in self._my_facility_ids(env):
            return _err('الموقع غير موجود', 404)
        b = _body()
        uid = (b.get('uid') or '').strip()
        if not uid:
            return _err('لم تُقرأ الشريحة', 422)
        # a uid must not serve two locations at once
        clash = env['care.cafm.location'].sudo().search(
            [('nfc_uid', '=', uid), ('id', '!=', loc.id)], limit=1)
        if clash and not b.get('force'):
            return _err('هذه الشريحة مرتبطة بالفعل بـ «%s». استخدم إعادة الربط لنقلها.'
                        % clash.name, 409)
        if clash:
            clash.write({'nfc_uid': False, 'nfc_state': 'lost',
                         'nfc_note': 'نُقلت الشريحة إلى %s' % loc.name})
        loc.write({
            'nfc_uid': uid, 'nfc_state': 'active',
            'nfc_written_on': fields.Datetime.now(),
            'nfc_written_by': env.user.id,
            'nfc_note': b.get('note') or ('كُتبت على الشريحة' if b.get('written') else 'رُبطت بالمعرّف فقط'),
        })
        return _ok(self._loc_dict(loc))

    @route(API + '/nfc/location/<int:lid>/<string:act>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def nfc_action(self, lid, act, **kw):
        """disable | enable | revoke a location's tag."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._may_manage(env):
            return _err('غير مسموح', 403)
        loc = env['care.cafm.location'].sudo().browse(lid).exists()
        if not loc or loc.facility_id.id not in self._my_facility_ids(env):
            return _err('الموقع غير موجود', 404)
        if act == 'disable':
            loc.action_nfc_disable()
        elif act == 'enable':
            if not loc.nfc_uid:
                return _err('لا توجد شريحة مرتبطة', 422)
            loc.write({'nfc_state': 'active'})
        elif act == 'revoke':
            loc.action_nfc_revoke()
        else:
            return _err('إجراء غير معروف', 400)
        return _ok(self._loc_dict(loc))

    # ---- verify a tag in the field ----------------------------------------
    @route(API + '/nfc/verify', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def nfc_verify(self, **kw):
        """Tap any tag and get told which location it belongs to — for auditing
        stickers without starting a task."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        val = (_body().get('value') or '').strip()
        if not val:
            return _err('لم تُقرأ الشريحة', 422)
        loc = env['care.cafm.location'].sudo().resolve_tag(val)
        if not loc:
            return _ok({'known': False, 'value': val})
        d = self._loc_dict(loc)
        d['known'] = True
        d['mine'] = loc.facility_id.id in self._my_facility_ids(env)
        return _ok(d)
