# -*- coding: utf-8 -*-
"""Waste Transfer & Treatment — a self-contained CAFM service.

A client requests a waste pickup from their premises; we dispatch a crew + truck
to collect it, then transport it for treatment and finally to the government
incinerator, giving the client full reports at every stage.

This is a ground-up, smarter re-architecture of the legacy ``service_order``
module, living **inside** the CAFM ecosystem on its own tables — but every
data-bearing field keeps the *same name* as in ``service_order`` so records can
be migrated across 1:1 later. The state machine is driven from the order itself
(the trip follows), roles + proof live on the order, and a single
``dashboard_stats`` feeds both the portal and the app.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

STATES = [
    ('draft', 'مسودة'),
    ('scheduled', 'مجدول'),
    ('pickuped', 'تم الالتقاط'),
    ('arrived', 'وصل للمعالجة'),
    ('processing', 'قيد المعالجة'),
    ('delivered', 'سُلّم للمحرقة'),
    ('completed', 'مكتمل'),
    ('cancelled', 'ملغى'),
]
OPEN_STATES = ('draft', 'scheduled', 'pickuped', 'arrived', 'processing')
FLOW = ['draft', 'scheduled', 'pickuped', 'arrived', 'processing', 'delivered', 'completed']


class WasteType(models.Model):
    _name = 'cafm.waste.type'
    _description = 'نوع طلب النفايات'
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)


class WasteCenter(models.Model):
    _name = 'cafm.waste.center'
    _description = 'مركز المعالجة / المحرقة'
    name = fields.Char(required=True, translate=True)
    is_incinerator = fields.Boolean(string='محرقة حكومية')
    address = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)


class WasteItem(models.Model):
    _name = 'cafm.waste.item'
    _description = 'صنف نفايات'
    _inherit = ['mail.thread']
    name = fields.Char(required=True, translate=True)
    image = fields.Binary(string='صورة')
    type_id = fields.Many2one('cafm.waste.type', string='النوع')
    notes = fields.Html()
    width = fields.Float(string='العرض')
    height = fields.Float(string='الارتفاع')
    weight = fields.Float(string='الوزن (كجم)')
    active = fields.Boolean(default=True)


class WastePickupLocation(models.Model):
    _name = 'cafm.waste.pickup.location'
    _description = 'موقع التقاط'
    name = fields.Char(required=True)
    address = fields.Char(string='العنوان')
    project_id = fields.Many2one('cafm.waste.project', string='المشروع')
    active = fields.Boolean(default=True)


class WasteTeam(models.Model):
    _name = 'cafm.waste.team'
    _description = 'فريق رفع النفايات'
    name = fields.Char(required=True)
    project_id = fields.Many2one('cafm.waste.project', string='المشروع')
    employee_ids = fields.Many2many('hr.employee', string='الأعضاء')
    member_count = fields.Integer(compute='_compute_member_count')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    def _compute_member_count(self):
        for t in self:
            t.member_count = len(t.employee_ids)


class WasteProject(models.Model):
    _name = 'cafm.waste.project'
    _description = 'مشروع نفايات (عقد عميل)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Char(string='الرقم التسلسلي', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    contact_id = fields.Many2one('res.partner', string='جهة العميل', tracking=True)
    cafm_client_id = fields.Many2one('care.cafm.client', string='عميل المرافق', tracking=True)
    start_date = fields.Date(string='تاريخ البداية')
    end_date = fields.Date(string='تاريخ النهاية')
    image = fields.Binary()
    notes = fields.Html()
    pickup_location_ids = fields.One2many('cafm.waste.pickup.location', 'project_id', string='مواقع الالتقاط')
    team_ids = fields.One2many('cafm.waste.team', 'project_id', string='الفرق')
    order_ids = fields.One2many('cafm.waste.order', 'project_id', string='الطلبات')
    trip_ids = fields.One2many('cafm.waste.trip', 'project_id', string='الرحلات')
    order_count = fields.Integer(compute='_compute_counts')
    trip_count = fields.Integer(compute='_compute_counts')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_counts(self):
        for p in self:
            p.order_count = len(p.order_ids)
            p.trip_count = len(p.trip_ids)

    @api.onchange('cafm_client_id')
    def _onchange_client(self):
        if self.cafm_client_id and self.cafm_client_id.partner_id:
            self.contact_id = self.cafm_client_id.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('sequence'):
                v['sequence'] = self.env['ir.sequence'].next_by_code('cafm.waste.project') or '/'
        return super().create(vals_list)


class WasteOrderLine(models.Model):
    _name = 'cafm.waste.order.line'
    _description = 'سطر طلب نفايات'
    order_id = fields.Many2one('cafm.waste.order', string='الطلب', ondelete='cascade')
    item_id = fields.Many2one('cafm.waste.item', string='الصنف', required=True)
    width = fields.Float(related='item_id.width', string='العرض')
    height = fields.Float(related='item_id.height', string='الارتفاع')
    weight = fields.Float(related='item_id.weight', string='الوزن')
    quantity = fields.Float(string='الكمية', default=1.0)
    active = fields.Boolean(default=True)


class WasteTripLine(models.Model):
    _name = 'cafm.waste.trip.line'
    _description = 'سطر رحلة نفايات'
    trip_id = fields.Many2one('cafm.waste.trip', string='الرحلة', ondelete='cascade')
    order_id = fields.Many2one('cafm.waste.order', string='الطلب')
    item_id = fields.Many2one('cafm.waste.item', string='الصنف', required=True)
    width = fields.Float(related='item_id.width', string='العرض')
    height = fields.Float(related='item_id.height', string='الارتفاع')
    weight = fields.Float(related='item_id.weight', string='الوزن')
    quantity = fields.Float(string='الكمية', default=1.0)
    active = fields.Boolean(default=True)


class WasteTrip(models.Model):
    _name = 'cafm.waste.trip'
    _description = 'رحلة نقل نفايات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence desc, id desc'
    _rec_name = 'sequence'

    sequence = fields.Char(string='الرقم التسلسلي', readonly=True, copy=False)
    reference = fields.Char(string='المرجع', compute='_compute_reference', store=True)
    pickup_location_id = fields.Many2one('cafm.waste.pickup.location', string='موقع الالتقاط', tracking=True)
    center_id = fields.Many2one('cafm.waste.center', string='مركز المعالجة', tracking=True)
    type_id = fields.Many2one('cafm.waste.type', string='النوع', tracking=True)
    company_id = fields.Many2one('res.company', string='الشركة', default=lambda s: s.env.company)
    project_id = fields.Many2one('cafm.waste.project', string='المشروع', tracking=True)
    pickuped_datetime = fields.Datetime(string='وقت الالتقاط', tracking=True)
    contact_id = fields.Many2one('res.partner', string='جهة العميل', tracking=True)
    trip_date = fields.Date(string='تاريخ الرحلة', tracking=True)
    trip_line_ids = fields.One2many('cafm.waste.trip.line', 'trip_id', string='الأصناف')
    states = fields.Selection(STATES, string='الحالة', default='draft', tracking=True)
    team_id = fields.Many2one('cafm.waste.team', string='الفريق', tracking=True)
    order_id = fields.Many2one('cafm.waste.order', string='الطلب')
    media_ids = fields.Many2many('ir.attachment', 'cafm_waste_trip_media_rel', 'trip_id', 'attachment_id',
                                 string='صور وفيديوهات الرحلة')
    # live driver GPS tracking
    driver_id = fields.Many2one('res.users', string='السائق', tracking=True)
    driver_lat = fields.Float(string='خط العرض', digits=(10, 7))
    driver_lng = fields.Float(string='خط الطول', digits=(10, 7))
    driver_loc_time = fields.Datetime(string='آخر تحديث للموقع')
    total_weight = fields.Float(compute='_compute_totals', string='مجموع أوزان الأصناف')
    total_quantity = fields.Float(compute='_compute_totals', string='إجمالي الكمية')
    total_qty_weight = fields.Float(compute='_compute_totals', string='الوزن الكلي')
    active = fields.Boolean(default=True)

    @api.depends('trip_line_ids.quantity', 'trip_line_ids.weight')
    def _compute_totals(self):
        for t in self:
            t.total_weight = round(sum(t.trip_line_ids.mapped('weight')), 1)
            t.total_quantity = round(sum(t.trip_line_ids.mapped('quantity')), 1)
            t.total_qty_weight = round(sum(l.quantity * l.weight for l in t.trip_line_ids), 1)

    @api.depends('sequence', 'project_id.sequence')
    def _compute_reference(self):
        for t in self:
            t.reference = '%s - %s' % (t.sequence or '', t.project_id.sequence or '')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('sequence'):
                v['sequence'] = self.env['ir.sequence'].next_by_code('cafm.waste.trip') or '/'
        return super().create(vals_list)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.reference or self.sequence)


class WasteOrder(models.Model):
    _name = 'cafm.waste.order'
    _description = 'طلب نقل ومعالجة نفايات'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'serial desc, id desc'
    _rec_name = 'serial'

    serial = fields.Char(string='الرقم التسلسلي', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one('cafm.waste.project', string='المشروع', tracking=True)
    contact_id = fields.Many2one(related='project_id.contact_id', store=True, string='جهة العميل')
    type_id = fields.Many2one('cafm.waste.type', string='النوع', tracking=True)
    pickup_location_id = fields.Many2one('cafm.waste.pickup.location', string='موقع الالتقاط', tracking=True)
    order_datetime = fields.Datetime(string='وقت الالتقاط', tracking=True)
    request_datetime = fields.Datetime(string='وقت الطلب', default=fields.Datetime.now)
    notes = fields.Html(string='ملاحظات')
    states = fields.Selection(STATES, string='الحالة', default='draft', copy=False, tracking=True)
    order_line_ids = fields.One2many('cafm.waste.order.line', 'order_id', string='الأصناف')
    trip_id = fields.Many2one('cafm.waste.trip', string='الرحلة', tracking=True)
    trip_line_ids = fields.One2many(related='trip_id.trip_line_ids', string='أصناف الرحلة')

    # operation roles + proof (live on the order — smarter than the legacy split)
    ops_manager_id = fields.Many2one('res.users', string='مسؤول العمليات', tracking=True)
    driver_id = fields.Many2one('res.users', string='السائق', tracking=True)
    receiver_id = fields.Many2one('res.users', string='مستلم الكميات', tracking=True)
    proof_image = fields.Image(string='صورة إثبات', max_width=1920, max_height=1920)
    media_ids = fields.Many2many('ir.attachment', 'cafm_waste_order_media_rel', 'order_id', 'attachment_id',
                                 string='صور وفيديوهات الإثبات',
                                 help='صور وفيديوهات إضافية دالة على تنفيذ الرفع والمعالجة.')
    final_weight = fields.Float(string='الوزن النهائي المستلم')
    final_note = fields.Char(string='ملاحظة الاستلام')

    total_quantity = fields.Float(compute='_compute_totals', string='إجمالي الكمية')
    total_weight = fields.Float(compute='_compute_totals', string='الوزن الكلي')
    qr_url = fields.Char(compute='_compute_qr_url', string='QR')

    def effective_lines(self):
        """Items to display for the order: its own lines, or the trip's lines
        (legacy data kept the items on the trip, not the order)."""
        self.ensure_one()
        return self.order_line_ids or (self.trip_id.trip_line_ids if self.trip_id else self.order_line_ids)

    @api.depends('order_line_ids.quantity', 'order_line_ids.weight',
                 'trip_id.trip_line_ids.quantity', 'trip_id.trip_line_ids.weight')
    def _compute_totals(self):
        for o in self:
            lines = o.effective_lines()
            o.total_quantity = round(sum(lines.mapped('quantity')), 1)
            o.total_weight = round(sum(l.quantity * l.weight for l in lines), 1)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('serial'):
                v['serial'] = self.env['ir.sequence'].next_by_code('cafm.waste.order') or '/'
        orders = super().create(vals_list)
        for o in orders:
            o._notify_roles()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if {'ops_manager_id', 'driver_id', 'receiver_id'} & set(vals):
            for o in self:
                o._notify_roles()
        return res

    # ---- state machine (order drives; trip follows) ----------------------
    def _sync_trip(self, state):
        for o in self:
            if o.trip_id:
                o.trip_id.states = state

    def _ensure_trip(self):
        self.ensure_one()
        if self.trip_id:
            return self.trip_id
        trip = self.env['cafm.waste.trip'].create({
            'project_id': self.project_id.id,
            'type_id': self.type_id.id,
            'pickup_location_id': self.pickup_location_id.id,
            'contact_id': self.contact_id.id,
            'pickuped_datetime': self.order_datetime,
            'trip_date': fields.Date.context_today(self),
            'states': 'scheduled',
            'order_id': self.id,
            'trip_line_ids': [(0, 0, {'item_id': l.item_id.id, 'quantity': l.quantity,
                                      'order_id': self.id}) for l in self.order_line_ids],
        })
        self.trip_id = trip.id
        return trip

    def _advance(self, state, client_msg=True):
        for o in self:
            o.states = state
            o._sync_trip(state)
            if client_msg:
                o._notify_client(state)

    def action_to_schedule(self):
        for o in self:
            o._ensure_trip()
            o._advance('scheduled')

    def action_to_pickuped(self):
        self._advance('pickuped')

    def action_to_arrived(self):
        self._advance('arrived')

    def action_to_processing(self):
        self._advance('processing')

    def action_to_delivered(self):
        self._advance('delivered')

    def action_to_completed(self):
        self._advance('completed')

    def action_to_cancelled(self):
        self._advance('cancelled')

    def action_to_draft(self):
        self._advance('draft', client_msg=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for o in self:
            o.access_url = '/waste/order/%s' % o.id

    def _compute_qr_url(self):
        for o in self:
            o.qr_url = o.get_base_url() + (o.access_url or '')

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.serial or 'waste-order'

    # ---- notifications ---------------------------------------------------
    _CLIENT_MSG = {
        'scheduled': ('📅 تم جدولة طلبكم', 'تم جدولة طلب رفع النفايات %s وسيصل الفريق قريبًا.'),
        'pickuped': ('🚛 تم الالتقاط', 'تم رفع النفايات من موقعكم للطلب %s.'),
        'arrived': ('🏭 وصلت للمعالجة', 'وصلت شحنة الطلب %s إلى مركز المعالجة.'),
        'processing': ('♻️ جارٍ المعالجة', 'جارٍ معالجة نفايات الطلب %s.'),
        'delivered': ('🔥 سُلّمت للمحرقة', 'تم تسليم نفايات الطلب %s إلى المحرقة الحكومية.'),
        'completed': ('✅ اكتمل الطلب', 'اكتمل طلب رفع ومعالجة النفايات %s. شكرًا لكم.'),
        'cancelled': ('✖ تم إلغاء الطلب', 'تم إلغاء طلب النفايات %s.'),
    }

    def _client_users(self):
        self.ensure_one()
        users = self.env['res.users'].sudo()
        p = self.contact_id
        if p:
            users |= self.env['res.users'].sudo().search([('partner_id', '=', p.id)])
            if 'care.cafm.client' in self.env:
                users |= self.env['care.cafm.client'].sudo().search(
                    [('partner_id', '=', p.id)]).mapped('user_ids')
        return users

    def _notify_client(self, state):
        self.ensure_one()
        msg = self._CLIENT_MSG.get(state)
        if not msg or 'care.cafm.notification' not in self.env:
            return
        users = self._client_users()
        if users:
            title, tpl = msg
            try:
                self.env['care.cafm.notification'].sudo().push(
                    users, title, tpl % (self.serial or ''), ntype='info',
                    action_url='/waste/order/%s' % self.id)
            except Exception:
                pass

    def _notify_roles(self):
        self.ensure_one()
        if 'care.cafm.notification' not in self.env:
            return
        for user, label in [(self.ops_manager_id, 'مسؤول العمليات'),
                            (self.driver_id, 'السائق'), (self.receiver_id, 'مستلم الكميات')]:
            if user:
                try:
                    self.env['care.cafm.notification'].sudo().push(
                        user, _('طلب نفايات %s') % (self.serial or ''),
                        _('أُسند إليك دور «%s» في الطلب %s') % (label, self.serial or ''),
                        ntype='task', action_url='/waste/order/%s' % self.id)
                except Exception:
                    pass

    # ---- dashboard stats (feeds portal + app) ----------------------------
    @api.model
    def dashboard_stats(self, domain=None, date_from=None, date_to=None):
        dom = list(domain or [])
        if date_from:
            dom.append(('request_datetime', '>=', '%s 00:00:00' % date_from))
        if date_to:
            dom.append(('request_datetime', '<=', '%s 23:59:59' % date_to))
        recs = self.sudo().search(dom)
        by_state, by_item, by_month = {}, {}, {}
        tw = tq = completed = 0.0
        for o in recs:
            by_state[o.states] = by_state.get(o.states, 0) + 1
            if o.states in ('completed', 'delivered'):
                completed += 1
            fw = o.final_weight or 0.0
            tw += fw
            dt = o.request_datetime
            mk = dt.strftime('%Y-%m') if dt else '—'
            m = by_month.setdefault(mk, {'orders': 0, 'weight': 0.0, 'qty': 0.0})
            m['orders'] += 1
            m['weight'] += fw
            for l in o.effective_lines():
                tq += l.quantity or 0
                m['qty'] += l.quantity or 0
                it = by_item.setdefault(l.item_id.name or '—',
                                        {'qty': 0.0, 'orders': 0, 'item_id': l.item_id.id})
                it['qty'] += l.quantity or 0
                it['orders'] += 1
        months = sorted(by_month.items())
        maxm = max([v['orders'] for _, v in months], default=1) or 1
        top = sorted(by_item.items(), key=lambda x: -x[1]['qty'])[:8]
        return {
            'total_orders': len(recs),
            'open': sum(v for k, v in by_state.items() if k in OPEN_STATES),
            'completed': int(completed),
            'cancelled': by_state.get('cancelled', 0),
            'total_weight': round(tw, 1),
            'total_quantity': round(tq, 1),
            'by_month': [{'month': k, 'orders': v['orders'], 'weight': round(v['weight'], 1),
                          'qty': round(v['qty'], 1), 'pct': max(3, int(v['orders'] * 100 / maxm))}
                         for k, v in months],
            'by_item': [{'name': k, 'qty': v['qty'], 'orders': v['orders'], 'item_id': v['item_id']}
                        for k, v in top],
        }
