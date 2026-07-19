# -*- coding: utf-8 -*-
"""Valet parking for CARE CAFM.

The full kerb-to-kerb cycle: a guest hands over a car, the attendant issues a
numbered ticket, parks it in a numbered bay, and later retrieves it on request —
with timing, charges, damage notes and shift takings all recorded."""
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ValetZone(models.Model):
    """A parking area the service covers — a garage, a basement, a forecourt."""
    _name = 'care.valet.zone'
    _description = 'منطقة صف السيارات'
    _order = 'facility_id, name'

    name = fields.Char(string='المنطقة', required=True, translate=True)
    code = fields.Char(string='الرمز')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    capacity = fields.Integer(string='السعة (مواقف)', default=50)
    spot_ids = fields.One2many('care.valet.spot', 'zone_id', string='المواقف')
    occupied = fields.Integer(compute='_compute_stats', string='مشغولة')
    free = fields.Integer(compute='_compute_stats', string='متاحة')
    occupancy = fields.Float(compute='_compute_stats', string='الإشغال %')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('spot_ids.state', 'capacity')
    def _compute_stats(self):
        for z in self:
            busy = len(z.spot_ids.filtered(lambda s: s.state == 'occupied'))
            total = len(z.spot_ids) or z.capacity or 0
            z.occupied = busy
            z.free = max(0, total - busy)
            z.occupancy = round(100.0 * busy / total, 1) if total else 0.0


class ValetSpot(models.Model):
    """One numbered bay."""
    _name = 'care.valet.spot'
    _description = 'موقف'
    _order = 'zone_id, name'

    name = fields.Char(string='رقم الموقف', required=True)
    zone_id = fields.Many2one('care.valet.zone', string='المنطقة', required=True, ondelete='cascade')
    facility_id = fields.Many2one(related='zone_id.facility_id', store=True, string='المرفق')
    state = fields.Selection([
        ('free', 'متاح'), ('occupied', 'مشغول'), ('blocked', 'معطّل'),
    ], string='الحالة', default='free', required=True, index=True)
    ticket_id = fields.Many2one('care.valet.ticket', string='التذكرة الحالية', readonly=True)
    note = fields.Char(string='ملاحظة')
    active = fields.Boolean(default=True)


class ValetTicket(models.Model):
    """A guest's car, from hand-over to hand-back."""
    _name = 'care.valet.ticket'
    _description = 'تذكرة صف سيارة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_at desc, id desc'

    name = fields.Char(string='رقم التذكرة', default='/', copy=False, readonly=True, index=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True)
    zone_id = fields.Many2one('care.valet.zone', string='المنطقة', tracking=True,
                              domain="[('facility_id','=',facility_id)]")
    spot_id = fields.Many2one('care.valet.spot', string='الموقف', tracking=True,
                              domain="[('zone_id','=',zone_id)]")
    # the car
    plate = fields.Char(string='رقم اللوحة', required=True, tracking=True, index=True)
    car_make = fields.Char(string='الماركة')
    car_model = fields.Char(string='الموديل')
    car_color = fields.Char(string='اللون')
    # the guest
    guest_name = fields.Char(string='اسم الضيف')
    guest_phone = fields.Char(string='هاتف الضيف', index=True)
    # the crew
    received_by = fields.Many2one('hr.employee', string='استلمها', tracking=True)
    parked_by = fields.Many2one('hr.employee', string='صفّها')
    delivered_by = fields.Many2one('hr.employee', string='سلّمها', tracking=True)
    shift_id = fields.Many2one('care.valet.shift', string='الوردية', index=True)
    # timing
    received_at = fields.Datetime(string='وقت الاستلام', default=fields.Datetime.now, required=True, tracking=True)
    parked_at = fields.Datetime(string='وقت الصف', readonly=True)
    requested_at = fields.Datetime(string='وقت الطلب', readonly=True, tracking=True)
    delivered_at = fields.Datetime(string='وقت التسليم', readonly=True, tracking=True)
    park_minutes = fields.Float(string='مدة الوقوف (دقيقة)', compute='_compute_times', store=True)
    retrieval_minutes = fields.Float(string='زمن الإحضار (دقيقة)', compute='_compute_times', store=True)
    sla_minutes = fields.Integer(string='المستهدف للإحضار (دقيقة)', default=7)
    is_late = fields.Boolean(string='تأخر الإحضار', compute='_compute_times', store=True)
    # money
    fee = fields.Float(string='الرسوم', tracking=True)
    tip = fields.Float(string='الإكرامية')
    payment_method = fields.Selection([
        ('cash', 'نقدًا'), ('knet', 'كي نت'), ('card', 'بطاقة'), ('free', 'مجاني/ضيف'),
    ], string='طريقة الدفع', default='cash', tracking=True)
    paid = fields.Boolean(string='مدفوع', tracking=True)
    # condition
    damage_note = fields.Text(string='ملاحظات حالة المركبة')
    has_damage = fields.Boolean(string='بها ملاحظات ضرر', tracking=True)
    key_tag = fields.Char(string='رقم علاقة المفتاح')
    state = fields.Selection([
        ('received', 'مُستلَمة'), ('parked', 'مركونة'), ('requested', 'مطلوبة'),
        ('delivered', 'سُلِّمت'), ('cancelled', 'ملغاة'),
    ], string='الحالة', default='received', required=True, tracking=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('valet_name_uniq', 'unique(name)', 'رقم التذكرة يجب أن يكون فريدًا.')]

    @api.depends('received_at', 'delivered_at', 'requested_at', 'sla_minutes')
    def _compute_times(self):
        for t in self:
            t.park_minutes = ((t.delivered_at - t.received_at).total_seconds() / 60.0
                              if t.received_at and t.delivered_at else 0.0)
            t.retrieval_minutes = ((t.delivered_at - t.requested_at).total_seconds() / 60.0
                                   if t.requested_at and t.delivered_at else 0.0)
            t.is_late = bool(t.retrieval_minutes and t.sla_minutes
                             and t.retrieval_minutes > t.sla_minutes)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.valet.ticket') or '/'
            if v.get('damage_note'):
                v['has_damage'] = True
        return super().create(vals_list)

    # ---- the cycle -------------------------------------------------------
    def action_park(self, spot=None):
        """Attendant parked the car in a bay."""
        for t in self:
            if spot:
                t.spot_id = spot
            if not t.spot_id:
                raise UserError(_('اختر الموقف أولاً.'))
            if t.spot_id.state == 'occupied' and t.spot_id.ticket_id != t:
                raise UserError(_('الموقف %s مشغول بالفعل.') % t.spot_id.name)
            t.write({'state': 'parked', 'parked_at': fields.Datetime.now(),
                     'parked_by': t.parked_by.id or t.received_by.id})
            t.spot_id.write({'state': 'occupied', 'ticket_id': t.id})
            t.message_post(body=_('🅿️ رُكنت في الموقف %s.') % t.spot_id.name)

    def action_request(self):
        """Guest asked for the car back — starts the retrieval clock."""
        for t in self:
            t.write({'state': 'requested', 'requested_at': fields.Datetime.now()})
            t.message_post(body=_('🔔 طلب الضيف إحضار المركبة.'))

    def action_deliver(self, by=None, fee=None, tip=None, paid=None):
        for t in self:
            vals = {'state': 'delivered', 'delivered_at': fields.Datetime.now()}
            if by:
                vals['delivered_by'] = by
            if fee is not None:
                vals['fee'] = fee
            if tip is not None:
                vals['tip'] = tip
            if paid is not None:
                vals['paid'] = paid
            t.write(vals)
            if t.spot_id:
                t.spot_id.write({'state': 'free', 'ticket_id': False})
            t.message_post(body=_('✅ سُلّمت المركبة للضيف%s.')
                           % ((' خلال %d دقيقة' % t.retrieval_minutes) if t.retrieval_minutes else ''))

    def action_cancel(self):
        for t in self:
            if t.spot_id:
                t.spot_id.write({'state': 'free', 'ticket_id': False})
            t.write({'state': 'cancelled'})


class ValetShift(models.Model):
    """An attendant's shift — the takings and volume behind it."""
    _name = 'care.valet.shift'
    _description = 'وردية فاليه'
    _order = 'start_at desc'

    name = fields.Char(string='الوردية', default='/', copy=False, readonly=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف', required=True)
    start_at = fields.Datetime(string='البداية', default=fields.Datetime.now, required=True)
    end_at = fields.Datetime(string='النهاية')
    ticket_ids = fields.One2many('care.valet.ticket', 'shift_id', string='التذاكر')
    ticket_count = fields.Integer(compute='_compute_totals', store=True, string='عدد التذاكر')
    total_fees = fields.Float(compute='_compute_totals', store=True, string='إجمالي الرسوم')
    total_tips = fields.Float(compute='_compute_totals', store=True, string='إجمالي الإكراميات')
    cash_due = fields.Float(compute='_compute_totals', store=True, string='النقد المستحق للتسليم')
    state = fields.Selection([('open', 'مفتوحة'), ('closed', 'مغلقة')], default='open', required=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('ticket_ids.fee', 'ticket_ids.tip', 'ticket_ids.paid', 'ticket_ids.payment_method')
    def _compute_totals(self):
        for s in self:
            t = s.ticket_ids
            s.ticket_count = len(t)
            s.total_fees = sum(t.mapped('fee'))
            s.total_tips = sum(t.mapped('tip'))
            s.cash_due = sum(x.fee + x.tip for x in t if x.payment_method == 'cash' and x.paid)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('care.valet.shift') or '/'
        return super().create(vals_list)

    def action_close(self):
        self.write({'state': 'closed', 'end_at': fields.Datetime.now()})
