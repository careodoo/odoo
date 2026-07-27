# -*- coding: utf-8 -*-
"""تطوير التصاريح فوق security.gate.pass: تمييز «متعدد الدخول» عن «الفردي»، عدّاد
الموجودين بالداخل الآن، وتسجيل الحارس لدخول/خروج الأشخاص (سجلّ زيارات متكرر)."""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SecurityGatePassPermit(models.Model):
    _inherit = 'security.gate.pass'

    is_multi_entry = fields.Boolean(
        string='متعدد الدخول', default=False, tracking=True,
        help='يسمح بعدّة دخول/خروج خلال مدة الصلاحية. التصريح الفردي يُسمح فيه بدخول واحد.')
    current_inside = fields.Integer(string='بالداخل الآن', compute='_compute_current_inside')
    entries_count = fields.Integer(string='مرات الدخول', compute='_compute_current_inside')

    def _compute_current_inside(self):
        Log = self.env['security.visit.log'].sudo()
        for r in self:
            ins = Log.search_count([('gate_pass_id', '=', r.id), ('event_type', '=', 'check_in')])
            outs = Log.search_count([('gate_pass_id', '=', r.id), ('event_type', '=', 'check_out')])
            r.entries_count = ins
            r.current_inside = max(0, ins - outs)

    def api_record_visit(self, direction, person=None, id_number=None, lat=None, lng=None, note=None):
        """يسجّل دخول/خروج شخص على التصريح. متعدد الدخول: متكرر؛ فردي: مرّة واحدة."""
        self.ensure_one()
        if self.state not in ('approved', 'valid'):
            raise UserError(_('التصريح غير معتمد/ساري — لا يمكن تسجيل الدخول/الخروج.'))
        Log = self.env['security.visit.log'].sudo()
        ev = 'check_in' if direction == 'in' else 'check_out'
        if ev == 'check_in' and not self.is_multi_entry:
            if Log.search_count([('gate_pass_id', '=', self.id), ('event_type', '=', 'check_in')]):
                raise UserError(_('هذا تصريح فردي وسبق تسجيل الدخول عليه.'))
        body = ' | '.join([x for x in [person, id_number, note] if x])
        Log.create({
            'gate_pass_id': self.id, 'event_type': ev,
            'event_time': fields.Datetime.now(), 'recorded_by': self.env.uid,
            'location_latitude': float(lat or 0), 'location_longitude': float(lng or 0),
            'note': body or False,
        })
        vals = {}
        if ev == 'check_in' and 'checked_in' in self._fields:
            vals['checked_in'] = True
            if 'check_in_time' in self._fields and not self.check_in_time:
                vals['check_in_time'] = fields.Datetime.now()
        if ev == 'check_out' and 'checked_out' in self._fields and not self.is_multi_entry:
            vals['checked_out'] = True
            if 'check_out_time' in self._fields:
                vals['check_out_time'] = fields.Datetime.now()
        if vals:
            self.write(vals)
        return True
