# -*- coding: utf-8 -*-
"""The vehicle behind the plate.

A valet ticket is a single visit. But the same cars come back — a consultant's
car every Tuesday, a supplier's van every morning — and re-typing the make,
colour and owner each time is both slow and how a car ends up logged twice
under two spellings.

So the plate is the identity. Scan or type it and, if it has been here before,
everything already known about it is filled in and its history is one tap
away. What the camera reads is normalised before matching: Arabic-Indic digits
become Latin, separators and spacing are dropped, so ١٢٣٤٥/ب and 12345 B are
the same car.
"""
import re
from datetime import timedelta

from odoo import api, fields, models, _

# ٠١٢٣٤٥٦٧٨٩ and ۰۱۲۳۴۵۶۷۸۹ both appear on Gulf plates and in OCR output.
_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')


def normalise_plate(raw):
    """A comparable key for a plate: Latin digits, no separators, upper case.

    Matching on the raw string fails on exactly the differences that do not
    matter — a slash, a space, or Arabic numerals from the camera.
    """
    if not raw:
        return ''
    s = str(raw).translate(_DIGITS).upper()
    return re.sub(r'[^0-9A-Zء-ي]', '', s)


class ValetVehicle(models.Model):
    _name = 'care.valet.vehicle'
    _description = 'مركبة مسجّلة'
    _inherit = ['mail.thread']
    _order = 'last_seen desc, id desc'
    _rec_name = 'plate'

    plate = fields.Char(string='رقم اللوحة', required=True, tracking=True, index=True)
    plate_key = fields.Char(string='مفتاح المطابقة', compute='_compute_key', store=True,
                            index=True,
                            help='اللوحة بعد التوحيد — يُطابَق به ما تقرأه الكاميرا.')
    make = fields.Char(string='الماركة', tracking=True)
    model = fields.Char(string='الموديل', tracking=True)
    color = fields.Char(string='اللون', tracking=True)
    owner_name = fields.Char(string='اسم المالك', tracking=True)
    owner_phone = fields.Char(string='هاتف المالك', tracking=True)
    owner_type = fields.Selection([
        ('guest', 'زائر'), ('staff', 'موظف'), ('patient', 'مريض'),
        ('supplier', 'مورّد'), ('vip', 'كبار الشخصيات'),
    ], string='الصفة', default='guest', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف', tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', index=True,
                                  tracking=True)

    # ---- standing instructions that should survive between visits ----------
    vip = fields.Boolean(string='كبار الشخصيات', tracking=True,
                         help='يُنبَّه الطاقم فور تسجيل دخول المركبة.')
    blocked = fields.Boolean(string='ممنوعة', tracking=True)
    block_reason = fields.Char(string='سبب المنع', tracking=True)
    notes = fields.Text(string='ملاحظات دائمة',
                        help='مثل: مقبض الباب الأيسر متضرّر مسبقًا، أو ناقل حركة يدوي.')
    preferred_zone_id = fields.Many2one('care.valet.zone', string='الموقف المفضّل')

    ticket_ids = fields.One2many('care.valet.ticket', 'vehicle_id', string='الزيارات')
    visit_count = fields.Integer(string='عدد الزيارات', compute='_compute_stats',
                                 store=True)
    last_seen = fields.Datetime(string='آخر زيارة', compute='_compute_stats', store=True)
    first_seen = fields.Datetime(string='أول زيارة', compute='_compute_stats', store=True)
    avg_stay_minutes = fields.Float(string='متوسط مدة البقاء (دقيقة)',
                                    compute='_compute_stats', store=True)
    is_regular = fields.Boolean(string='زائر متكرّر', compute='_compute_stats', store=True,
                                help='ثلاث زيارات فأكثر خلال التسعين يومًا الماضية.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('plate_key_uniq', 'unique(plate_key, company_id)',
                         'هذه اللوحة مسجّلة بالفعل.')]

    @api.depends('plate')
    def _compute_key(self):
        for v in self:
            v.plate_key = normalise_plate(v.plate)

    @api.depends('ticket_ids.received_at', 'ticket_ids.state')
    def _compute_stats(self):
        cutoff = fields.Datetime.now() - timedelta(days=90)
        for v in self:
            visits = v.ticket_ids.sorted('received_at')
            v.visit_count = len(visits)
            v.first_seen = visits[:1].received_at if visits else False
            v.last_seen = visits[-1:].received_at if visits else False
            stays = [
                (t.delivered_at - t.received_at).total_seconds() / 60.0
                for t in visits if t.delivered_at and t.received_at]
            v.avg_stay_minutes = (sum(stays) / len(stays)) if stays else 0.0
            v.is_regular = len([t for t in visits
                                if t.received_at and t.received_at >= cutoff]) >= 3

    @api.model
    def find_by_plate(self, plate):
        """The lookup a camera scan performs. Returns an empty set, not None,
        so callers can treat 'unknown car' as an ordinary case."""
        key = normalise_plate(plate)
        return self.search([('plate_key', '=', key)], limit=1) if key else self.browse()

    @api.model
    def resolve(self, plate, vals=None):
        """Find this plate or register it, and keep what we learn.

        A visit often knows more than the record does — the guest gives a phone
        number, the crew notes the colour. Filling only the blanks means a
        later visit never overwrites something a person corrected by hand.
        """
        vehicle = self.find_by_plate(plate)
        vals = {k: v for k, v in (vals or {}).items() if v}
        if not vehicle:
            return self.create(dict(vals, plate=plate))
        fill = {k: v for k, v in vals.items()
                if k in self._fields and not vehicle[k]}
        if fill:
            vehicle.write(fill)
        return vehicle

    def action_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('زيارات %s') % self.plate,
            'res_model': 'care.valet.ticket', 'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_plate': self.plate},
        }


class ValetTicketVehicle(models.Model):
    """Tie every ticket to its vehicle, so a plate accumulates a history."""
    _inherit = 'care.valet.ticket'

    vehicle_id = fields.Many2one('care.valet.vehicle', string='المركبة', index=True,
                                 ondelete='set null', tracking=True)
    vehicle_known = fields.Boolean(string='مركبة معروفة', compute='_compute_known',
                                   store=True)
    visit_number = fields.Integer(string='رقم الزيارة', compute='_compute_known',
                                  store=True)

    @api.depends('vehicle_id', 'vehicle_id.visit_count')
    def _compute_known(self):
        for t in self:
            t.vehicle_known = bool(t.vehicle_id and t.vehicle_id.visit_count > 1)
            t.visit_number = t.vehicle_id.visit_count if t.vehicle_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for t in tickets:
            if t.plate and not t.vehicle_id:
                t.vehicle_id = self.env['care.valet.vehicle'].sudo().resolve(
                    t.plate, {
                        'make': t.car_make, 'model': t.car_model, 'color': t.car_color,
                        'owner_name': t.guest_name, 'owner_phone': t.guest_phone,
                        'facility_id': t.facility_id.id,
                    }).id
            v = t.vehicle_id
            if v and v.blocked:
                t.message_post(body=_('⛔ مركبة ممنوعة: %s') % (v.block_reason or ''))
            elif v and v.vip:
                t.message_post(body=_('⭐ مركبة كبار الشخصيات — أولوية في التسليم.'))
            elif v and v.notes:
                t.message_post(body=_('📌 ملاحظات دائمة على المركبة: %s') % v.notes)
        return tickets
