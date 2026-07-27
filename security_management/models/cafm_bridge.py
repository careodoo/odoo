# -*- coding: utf-8 -*-
"""Bridge between the standalone *Security Manager* (security_management) module
and the CAFM platform (care_cafm).

No security models are re-implemented here — the real, rich Security Manager IS
the Security service inside CAFM. This module only *links* the two so a CAFM
facility knows its security premises, and the CAFM app can open Security Manager.
security_management keeps working perfectly on its own (independent)."""

from odoo import api, fields, models, _


class SecurityPremise(models.Model):
    _inherit = 'security.premise'

    # Ties a Security Manager premise to a CAFM facility (the same physical site).
    cafm_facility_id = fields.Many2one(
        'care.cafm.facility', string='مرفق CAFM', tracking=True,
        help='المرفق المقابل في نظام إدارة المرافق CAFM — يوحّد الأمن مع باقي الخدمات على نفس الموقع.')

    def action_sync_to_cafm(self):
        """Create/link a matching CAFM facility, then mirror this premise's floors
        and patrol checkpoints as CAFM locations (each gets its own QR). Idempotent:
        already-linked records are skipped, so it's safe to re-run."""
        Facility = self.env['care.cafm.facility']
        Location = self.env['care.cafm.location']
        created_loc = 0
        for prem in self:
            fac = prem.cafm_facility_id
            if not fac:
                fac = Facility.create({'name': prem.name})
                prem.cafm_facility_id = fac.id
            for fl in prem.floor_ids:
                if not fl.cafm_location_id:
                    fl.cafm_location_id = Location.create({
                        'name': fl.name, 'facility_id': fac.id, 'location_type': 'other',
                    }).id
                    created_loc += 1
            for pt in prem.patrol_point_ids:
                if not pt.cafm_location_id:
                    pt.cafm_location_id = Location.create({
                        'name': pt.name, 'facility_id': fac.id,
                        'location_type': 'other', 'is_checkpoint': True,
                    }).id
                    created_loc += 1
        if len(self) == 1 and self.cafm_facility_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('مرفق CAFM'),
                'res_model': 'care.cafm.facility',
                'res_id': self.cafm_facility_id.id,
                'view_mode': 'form',
            }
        return True


class SecurityFloor(models.Model):
    _inherit = 'security.floor'

    cafm_location_id = fields.Many2one(
        'care.cafm.location', string='موقع CAFM', tracking=True,
        help='الموقع المقابل في CAFM (لتوحيد الشجرة الجغرافية ورمز QR).')


class SecurityPatrolPoint(models.Model):
    _inherit = 'security.patrol.point'

    # A patrol checkpoint can point at the CAFM location whose QR the guard scans —
    # one QR per physical spot, shared by all services (unified scanning).
    cafm_location_id = fields.Many2one(
        'care.cafm.location', string='موقع CAFM', tracking=True,
        help='موقع CAFM الذي يمسح الحارس رمز QR الخاص به عند نقطة التفتيش هذه.')


class CafmFacility(models.Model):
    _inherit = 'care.cafm.facility'

    security_premise_ids = fields.One2many(
        'security.premise', 'cafm_facility_id', string='مواقع الأمن')
    security_premise_count = fields.Integer(compute='_compute_security_premise_count')

    def _compute_security_premise_count(self):
        Premise = self.env['security.premise']
        for rec in self:
            rec.security_premise_count = Premise.search_count([('cafm_facility_id', '=', rec.id)])

    def action_view_security_premises(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مواقع الأمن'),
            'res_model': 'security.premise',
            'view_mode': 'tree,form',
            'domain': [('cafm_facility_id', '=', self.id)],
            'context': {'default_cafm_facility_id': self.id},
        }
