# -*- coding: utf-8 -*-
"""Hospitality (خدمة الضيافة) — office catering as a CAFM service.

The shape of the problem: staff order a drink from their desk, a kitchen crew
prepares it against a clock, and the client wants to know who consumed what and
to cap it. So the model is a small ordering system with three distinct audiences
— the requester, the kitchen station, and the client's finance/admin — and each
gets the data in the form it actually needs.

Ordering is per-line rather than per-order at the kitchen: one order can hold a
coffee and a tea that different stations prepare and bump independently.
"""
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HospCategory(models.Model):
    _name = 'care.hosp.category'
    _description = 'قسم الضيافة'
    _order = 'sequence, name'

    name = fields.Char(string='القسم', required=True, translate=True)
    code = fields.Char(string='الرمز')
    icon = fields.Char(string='الأيقونة', default='☕')
    color = fields.Char(string='اللون', default='#8a6d3b',
                        help='لون القسم في البورتال وشاشة المطبخ.')
    sequence = fields.Integer(default=10)
    description = fields.Text(string='الوصف', translate=True)
    item_ids = fields.One2many('care.hosp.item', 'category_id', string='الأصناف')
    item_count = fields.Integer(compute='_compute_item_count', string='عدد الأصناف')
    active = fields.Boolean(default=True)

    def _compute_item_count(self):
        data = self.env['care.hosp.item']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        counts = {c.id: n for c, n in data}
        for r in self:
            r.item_count = counts.get(r.id, 0)


class HospOptionGroup(models.Model):
    """A question asked about an item — "كم سكر؟", "الحجم؟". Reusable across
    items so "السكر" is defined once and attached to every hot drink."""
    _name = 'care.hosp.option.group'
    _description = 'مجموعة خيارات'
    _order = 'sequence, name'

    name = fields.Char(string='المجموعة', required=True, translate=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean(string='إلزامي', default=True,
                              help='يجب على الطالب الاختيار قبل إتمام الطلب.')
    multi = fields.Boolean(string='اختيار متعدد',
                           help='مثل الإضافات: يمكن اختيار أكثر من خيار.')
    max_select = fields.Integer(string='أقصى عدد اختيارات', default=1)
    option_ids = fields.One2many('care.hosp.option', 'group_id', string='الخيارات')
    active = fields.Boolean(default=True)


class HospOption(models.Model):
    _name = 'care.hosp.option'
    _description = 'خيار'
    _order = 'sequence, name'

    name = fields.Char(string='الخيار', required=True, translate=True)
    group_id = fields.Many2one('care.hosp.option.group', string='المجموعة',
                               required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    is_default = fields.Boolean(string='الافتراضي')
    extra_cost = fields.Float(string='تكلفة إضافية', default=0.0)
    active = fields.Boolean(default=True)


class HospStation(models.Model):
    """Where an item is actually made. Splitting the kitchen into stations keeps
    the barista's screen free of sandwich orders."""
    _name = 'care.hosp.station'
    _description = 'محطة تحضير'
    _order = 'name'

    name = fields.Char(string='المحطة', required=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    icon = fields.Char(string='الأيقونة', default='🍳')
    member_ids = fields.Many2many('hr.employee', string='طاقم المحطة')
    open_from = fields.Float(string='يبدأ العمل', default=7.0)
    open_to = fields.Float(string='ينتهي العمل', default=17.0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class HospItem(models.Model):
    _name = 'care.hosp.item'
    _description = 'صنف ضيافة'
    _order = 'sequence, name'

    name = fields.Char(string='الصنف', required=True, translate=True)
    code = fields.Char(string='الرمز')
    category_id = fields.Many2one('care.hosp.category', string='القسم', required=True)
    station_id = fields.Many2one('care.hosp.station', string='محطة التحضير')
    sequence = fields.Integer(default=10)
    icon = fields.Char(string='الأيقونة', default='☕')
    image = fields.Image(string='الصورة', max_width=512, max_height=512)
    description = fields.Text(string='الوصف', translate=True)
    option_group_ids = fields.Many2many('care.hosp.option.group', string='مجموعات الخيارات')
    prep_minutes = fields.Integer(string='زمن التحضير (دقيقة)', default=5,
                                  help='يُستخدم كمستهدف على شاشة المطبخ.')
    unit_cost = fields.Float(string='تكلفة الوحدة',
                             help='للاحتساب الداخلي وتقارير الاستهلاك — لا يُحصَّل من الموظف.')
    facility_ids = fields.Many2many('care.cafm.facility', string='متاح في المرافق',
                                    help='اتركه فارغًا ليكون متاحًا في كل المرافق.')
    available = fields.Boolean(string='متاح', default=True)
    unavailable_note = fields.Char(string='سبب عدم التوفر')
    serve_from = fields.Float(string='يُقدَّم من الساعة', default=0.0)
    serve_to = fields.Float(string='حتى الساعة', default=24.0)
    is_hot = fields.Boolean(string='مشروب ساخن')
    order_count = fields.Integer(compute='_compute_stats', string='مرات الطلب')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_stats(self):
        data = self.env['care.hosp.order.line']._read_group(
            [('item_id', 'in', self.ids)], ['item_id'], ['quantity:sum'])
        counts = {i.id: q for i, q in data}
        for r in self:
            r.order_count = int(counts.get(r.id, 0))

    def is_servable_now(self):
        """Availability is a time window as well as a flag — breakfast items
        should stop being orderable at 11, not just be marked unavailable."""
        self.ensure_one()
        if not self.available:
            return False
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        h = now.hour + now.minute / 60.0
        if self.serve_from or self.serve_to != 24.0:
            return self.serve_from <= h <= self.serve_to
        return True


class HospOrder(models.Model):
    _name = 'care.hosp.order'
    _description = 'طلب ضيافة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='رقم الطلب', default='/', copy=False, readonly=True, index=True)
    requester_id = fields.Many2one('res.users', string='الطالب', required=True,
                                   default=lambda s: s.env.user, tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='الجهة', related='requester_id.partner_id',
                                 store=True, index=True)
    department_id = fields.Many2one('hr.department', string='الإدارة', tracking=True, index=True,
                                    help='لتحميل الاستهلاك على مركز التكلفة.')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع/المكتب')
    room_label = fields.Char(string='المكتب/القاعة',
                             help='نص حر حين لا يكون الموقع مسجّلًا كمكان في النظام.')

    line_ids = fields.One2many('care.hosp.order.line', 'order_id', string='الأصناف')
    note = fields.Text(string='ملاحظات')

    # guests / meetings — a very different order from "قهوتي الصباحية"
    order_type = fields.Selection([
        ('self', 'طلب شخصي'), ('meeting', 'اجتماع'), ('guest', 'ضيافة زوّار'),
    ], string='نوع الطلب', default='self', required=True, tracking=True)
    guest_count = fields.Integer(string='عدد الحضور', default=1)
    guest_name = fields.Char(string='اسم الضيف/الجهة')
    is_vip = fields.Boolean(string='ضيافة VIP', tracking=True)

    scheduled_at = fields.Datetime(string='موعد التقديم',
                                   help='اتركه فارغًا للتحضير فورًا.')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('await_approval', 'بانتظار الموافقة'),
        ('placed', 'مُرسَل'),
        ('accepted', 'مقبول'),
        ('preparing', 'قيد التحضير'),
        ('ready', 'جاهز'),
        ('delivered', 'تم التقديم'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True, index=True)

    placed_at = fields.Datetime(string='وقت الإرسال', readonly=True, index=True)
    accepted_at = fields.Datetime(string='وقت القبول', readonly=True)
    ready_at = fields.Datetime(string='وقت الجهوزية', readonly=True)
    delivered_at = fields.Datetime(string='وقت التقديم', readonly=True, index=True)
    prep_target = fields.Integer(string='المستهدف (دقيقة)', compute='_compute_target', store=True)
    prep_minutes = fields.Float(string='زمن التحضير الفعلي', compute='_compute_times', store=True)
    wait_minutes = fields.Float(string='زمن الانتظار الكلي', compute='_compute_times', store=True)
    is_late = fields.Boolean(string='متأخر', compute='_compute_times', store=True, index=True)

    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_totals', store=True)
    total_cost = fields.Float(string='التكلفة', compute='_compute_totals', store=True)

    rating = fields.Selection([('1', '★'), ('2', '★★'), ('3', '★★★'),
                               ('4', '★★★★'), ('5', '★★★★★')], string='التقييم')
    rating_note = fields.Char(string='ملاحظة التقييم')

    prepared_by = fields.Many2one('hr.employee', string='حضّرها', tracking=True)
    delivered_by = fields.Many2one('hr.employee', string='قدّمها')
    reject_reason = fields.Char(string='سبب الرفض')
    approver_id = fields.Many2one('res.users', string='المعتمِد')
    limit_note = fields.Char(string='ملاحظة الحد', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- computes ----
    @api.depends('line_ids.item_id.prep_minutes')
    def _compute_target(self):
        for o in self:
            # the order is ready when its slowest item is — they are made in parallel
            o.prep_target = max(o.line_ids.mapped('item_id.prep_minutes') or [5])

    @api.depends('placed_at', 'accepted_at', 'ready_at', 'delivered_at', 'state', 'prep_target')
    def _compute_times(self):
        now = fields.Datetime.now()
        for o in self:
            start = o.accepted_at or o.placed_at
            end = o.ready_at or (now if o.state in ('accepted', 'preparing') else False)
            o.prep_minutes = (end - start).total_seconds() / 60.0 if (start and end) else 0.0
            fin = o.delivered_at or (now if o.state not in ('delivered', 'cancelled', 'rejected') else False)
            o.wait_minutes = (fin - o.placed_at).total_seconds() / 60.0 if (o.placed_at and fin) else 0.0
            o.is_late = bool(o.state in ('placed', 'accepted', 'preparing')
                             and o.wait_minutes > (o.prep_target or 5))

    @api.depends('line_ids.quantity', 'line_ids.line_cost')
    def _compute_totals(self):
        for o in self:
            o.item_count = int(sum(o.line_ids.mapped('quantity')))
            o.total_cost = sum(o.line_ids.mapped('line_cost'))

    # ---- lifecycle ----
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.hosp.order') or '/'
        return super().create(vals_list)

    def action_place(self):
        """Submit to the kitchen — unless the requester is over their cap, in
        which case the order waits for a human instead of being thrown away."""
        for o in self:
            if not o.line_ids:
                raise UserError(_('أضف صنفًا واحدًا على الأقل.'))
            o._check_options()
            verdict = self.env['care.hosp.limit'].check_order(o)
            if verdict.get('blocked'):
                raise UserError(verdict['message'])
            if verdict.get('needs_approval'):
                o.write({'state': 'await_approval', 'limit_note': verdict['message']})
                o._notify_approvers(verdict['message'])
                continue
            o.write({'state': 'placed', 'placed_at': fields.Datetime.now()})
            o._notify_station()
        return True

    def action_approve(self):
        for o in self.filtered(lambda x: x.state == 'await_approval'):
            o.write({'state': 'placed', 'placed_at': fields.Datetime.now(),
                     'approver_id': self.env.user.id})
            o._notify_station()
            o._notify_requester(_('✅ اعتُمد طلب الضيافة'), o.name)
        return True

    def action_accept(self):
        emp = self.env.user.employee_id
        for o in self.filtered(lambda x: x.state == 'placed'):
            o.write({'state': 'accepted', 'accepted_at': fields.Datetime.now(),
                     'prepared_by': emp.id if emp else False})
            o._notify_requester(_('👨‍🍳 طلبك قيد التحضير'), o.name)
        return True

    def action_preparing(self):
        self.filtered(lambda x: x.state in ('placed', 'accepted')).write({'state': 'preparing'})
        return True

    def action_ready(self):
        for o in self.filtered(lambda x: x.state in ('placed', 'accepted', 'preparing')):
            o.write({'state': 'ready', 'ready_at': fields.Datetime.now()})
            o.line_ids.write({'state': 'ready'})
            o._notify_requester(_('🔔 طلبك جاهز'), o.name)
        return True

    def action_deliver(self):
        emp = self.env.user.employee_id
        for o in self.filtered(lambda x: x.state in ('ready', 'preparing', 'accepted')):
            o.write({'state': 'delivered', 'delivered_at': fields.Datetime.now(),
                     'delivered_by': emp.id if emp else o.delivered_by.id})
            o.line_ids.write({'state': 'served'})
        return True

    def action_reject(self, reason=None):
        for o in self:
            o.write({'state': 'rejected', 'reject_reason': reason or o.reject_reason})
            o._notify_requester(_('⛔ تعذّر تنفيذ طلبك'),
                                o.reject_reason or o.name)
        return True

    def action_cancel(self):
        self.filtered(lambda x: x.state not in ('delivered',)).write({'state': 'cancelled'})
        return True

    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    def _check_options(self):
        """A required option group left unanswered means the kitchen has to
        guess — reject it at the door instead."""
        for o in self:
            for line in o.line_ids:
                for grp in line.item_id.option_group_ids.filtered('required'):
                    if not (line.option_ids & grp.option_ids):
                        raise UserError(_('اختر "%s" للصنف "%s".') % (grp.name, line.item_id.name))

    # ---- notifications ----
    def _push(self, users, title, body):
        users = users.filtered('active')
        if not users or 'care.cafm.notification' not in self.env:
            return
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, body, ntype='task', action_url='/hosp/order/%s' % self.id)
        except Exception:
            pass

    def _notify_requester(self, title, body):
        self._push(self.requester_id, title, body)

    def _notify_station(self):
        """Whoever mans the stations this order touches gets told at once."""
        emps = self.line_ids.mapped('item_id.station_id.member_ids')
        users = emps.mapped('user_id')
        self._push(users, _('🆕 طلب ضيافة جديد'),
                   '%s — %s' % (self.name, self.room_label or self.location_id.name or ''))

    def _notify_approvers(self, message):
        approvers = self.env['care.hosp.limit'].approvers_for(self)
        self._push(approvers, _('🔐 طلب ضيافة يحتاج اعتمادك'),
                   '%s — %s' % (self.requester_id.name, message))


class HospOrderLine(models.Model):
    _name = 'care.hosp.order.line'
    _description = 'سطر طلب ضيافة'
    _order = 'id'

    order_id = fields.Many2one('care.hosp.order', string='الطلب', required=True,
                               ondelete='cascade', index=True)
    item_id = fields.Many2one('care.hosp.item', string='الصنف', required=True)
    category_id = fields.Many2one(related='item_id.category_id', store=True, string='القسم')
    station_id = fields.Many2one(related='item_id.station_id', store=True, string='المحطة', index=True)
    quantity = fields.Float(string='الكمية', default=1.0, required=True)
    option_ids = fields.Many2many('care.hosp.option', string='الخيارات')
    option_label = fields.Char(string='المواصفات', compute='_compute_label', store=True)
    note = fields.Char(string='ملاحظة', help='مثال: بدون رغوة، كوب ورقي.')
    line_cost = fields.Float(string='التكلفة', compute='_compute_cost', store=True)
    state = fields.Selection([('queued', 'في الطابور'), ('ready', 'جاهز'), ('served', 'قُدِّم')],
                             string='حالة السطر', default='queued')
    # denormalised for the analytics screens — they group by these constantly
    requester_id = fields.Many2one(related='order_id.requester_id', store=True, index=True)
    department_id = fields.Many2one(related='order_id.department_id', store=True, index=True)
    facility_id = fields.Many2one(related='order_id.facility_id', store=True, index=True)
    order_state = fields.Selection(related='order_id.state', store=True, index=True)
    delivered_at = fields.Datetime(related='order_id.delivered_at', store=True, index=True)

    @api.depends('option_ids')
    def _compute_label(self):
        for l in self:
            l.option_label = ' · '.join(l.option_ids.mapped('name'))

    @api.depends('quantity', 'item_id.unit_cost', 'option_ids.extra_cost')
    def _compute_cost(self):
        for l in self:
            extra = sum(l.option_ids.mapped('extra_cost'))
            l.line_cost = (l.item_id.unit_cost + extra) * (l.quantity or 0)

    @api.constrains('quantity')
    def _check_qty(self):
        for l in self:
            if l.quantity <= 0:
                raise ValidationError(_('الكمية يجب أن تكون أكبر من صفر.'))


class HospLimit(models.Model):
    """Consumption caps, set by the client. A cap can block outright or route
    the order to an approver — most clients want the second, because refusing a
    guest a coffee is worse than asking a manager."""
    _name = 'care.hosp.limit'
    _description = 'حد استهلاك الضيافة'
    _order = 'sequence, id'

    name = fields.Char(string='السياسة', required=True, translate=True)
    sequence = fields.Integer(default=10)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق',
                                  help='اتركه فارغًا لتطبيقها على كل المرافق.')
    scope = fields.Selection([
        ('user', 'مستخدم محدّد'), ('department', 'إدارة'), ('all', 'الجميع'),
    ], string='النطاق', default='all', required=True)
    user_ids = fields.Many2many('res.users', string='المستخدمون')
    department_ids = fields.Many2many('hr.department', string='الإدارات')
    category_id = fields.Many2one('care.hosp.category', string='مقصور على قسم',
                                  help='اتركه فارغًا ليشمل كل الأقسام.')
    period = fields.Selection([('day', 'يومي'), ('week', 'أسبوعي'), ('month', 'شهري')],
                              string='الفترة', default='day', required=True)
    max_items = fields.Integer(string='أقصى عدد أصناف', default=0,
                               help='صفر = بلا حد.')
    max_orders = fields.Integer(string='أقصى عدد طلبات', default=0)
    max_cost = fields.Float(string='أقصى تكلفة', default=0.0)
    on_exceed = fields.Selection([
        ('approve', 'يحتاج موافقة'), ('block', 'منع الطلب'), ('warn', 'تنبيه فقط'),
    ], string='عند التجاوز', default='approve', required=True)
    approver_ids = fields.Many2many('res.users', 'hosp_limit_approver_rel', 'limit_id', 'user_id',
                                    string='المعتمِدون')
    exempt_vip = fields.Boolean(string='استثناء ضيافة VIP والاجتماعات', default=True,
                                help='طلبات الاجتماعات والزوّار لا تُحتسب على حد الموظف.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- evaluation ----
    def _period_start(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.period == 'day':
            start = today
        elif self.period == 'week':
            start = today - timedelta(days=today.weekday())
        else:
            start = today.replace(day=1)
        return fields.Datetime.to_datetime(start)

    @api.model
    def _matching(self, order):
        """Policies that apply to this order, most specific first."""
        dom = ['|', ('facility_id', '=', False), ('facility_id', '=', order.facility_id.id)]
        pols = self.sudo().search(dom)
        out = self.browse()
        for p in pols:
            if p.category_id and p.category_id not in order.line_ids.mapped('category_id'):
                continue
            if p.scope == 'user' and order.requester_id not in p.user_ids:
                continue
            if p.scope == 'department' and order.department_id not in p.department_ids:
                continue
            out |= p
        return out

    @api.model
    def check_order(self, order):
        """Returns {'blocked'|'needs_approval'|'ok', 'message'} for one order."""
        pols = self._matching(order)
        if not pols:
            return {'ok': True}
        Line = self.env['care.hosp.order.line'].sudo()
        worst = {'ok': True}
        for p in pols:
            if p.exempt_vip and (order.is_vip or order.order_type in ('meeting', 'guest')):
                continue
            start = p._period_start()
            dom = [('requester_id', '=', order.requester_id.id),
                   ('order_id.placed_at', '>=', start),
                   ('order_state', 'not in', ('cancelled', 'rejected', 'draft'))]
            if p.category_id:
                dom.append(('category_id', '=', p.category_id.id))
            if p.facility_id:
                dom.append(('facility_id', '=', p.facility_id.id))
            used = Line.search(dom)
            used_items = sum(used.mapped('quantity'))
            used_cost = sum(used.mapped('line_cost'))
            used_orders = len(set(used.mapped('order_id').ids))
            new_items = sum(order.line_ids.mapped('quantity'))
            new_cost = sum(order.line_ids.mapped('line_cost'))

            hit = None
            if p.max_items and used_items + new_items > p.max_items:
                hit = _('تجاوز حد الأصناف (%(m)s %(per)s) — المستهلك %(u)s.') % {
                    'm': p.max_items, 'per': dict(p._fields['period'].selection)[p.period],
                    'u': int(used_items)}
            elif p.max_orders and used_orders + 1 > p.max_orders:
                hit = _('تجاوز حد الطلبات (%(m)s %(per)s).') % {
                    'm': p.max_orders, 'per': dict(p._fields['period'].selection)[p.period]}
            elif p.max_cost and used_cost + new_cost > p.max_cost:
                hit = _('تجاوز حد التكلفة (%(m)s).') % {'m': p.max_cost}
            if not hit:
                continue
            msg = '%s — %s' % (p.name, hit)
            if p.on_exceed == 'block':
                return {'blocked': True, 'message': msg}
            if p.on_exceed == 'approve':
                worst = {'needs_approval': True, 'message': msg}
            elif worst.get('ok'):
                worst = {'ok': True, 'warning': msg}
        return worst

    @api.model
    def approvers_for(self, order):
        users = self.env['res.users']
        for p in self._matching(order):
            users |= p.approver_ids
        if not users:
            users = self.env.ref('base.user_admin', raise_if_not_found=False) or users
        return users

    @api.model
    def usage_for(self, user, facility=None):
        """What this person has consumed against every policy that binds them —
        drives the "المتبقّي لك اليوم" line in the portal."""
        Line = self.env['care.hosp.order.line'].sudo()
        out = []
        for p in self.sudo().search([]):
            if p.scope == 'user' and user not in p.user_ids:
                continue
            if facility and p.facility_id and p.facility_id != facility:
                continue
            ldom = [('requester_id', '=', user.id),
                    ('order_id.placed_at', '>=', p._period_start()),
                    ('order_state', 'not in', ('cancelled', 'rejected', 'draft'))]
            if p.category_id:
                ldom.append(('category_id', '=', p.category_id.id))
            used = Line.search(ldom)
            out.append({
                'policy': p.name, 'period': p.period,
                'max_items': p.max_items, 'used_items': int(sum(used.mapped('quantity'))),
                'max_cost': p.max_cost, 'used_cost': sum(used.mapped('line_cost')),
                'on_exceed': p.on_exceed,
            })
        return out


class HospFavorite(models.Model):
    """"طلبي المعتاد" — the whole point of a hospitality app is that the third
    coffee of the week takes one tap, not six."""
    _name = 'care.hosp.favorite'
    _description = 'المفضّلة'
    _order = 'sequence, id'

    name = fields.Char(string='الاسم', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              default=lambda s: s.env.user, ondelete='cascade', index=True)
    item_id = fields.Many2one('care.hosp.item', string='الصنف', required=True)
    option_ids = fields.Many2many('care.hosp.option', string='الخيارات')
    quantity = fields.Float(string='الكمية', default=1.0)
    note = fields.Char(string='ملاحظة')
    sequence = fields.Integer(default=10)
    times_used = fields.Integer(string='مرات الاستخدام', default=0)


class HospStanding(models.Model):
    """A standing order — "قهوتي كل يوم عمل الساعة ٨". The cron places it, so
    the kitchen sees the morning rush before it walks in."""
    _name = 'care.hosp.standing'
    _description = 'طلب دائم'
    _order = 'time_of_day'

    name = fields.Char(string='الاسم', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              default=lambda s: s.env.user, ondelete='cascade')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع')
    room_label = fields.Char(string='المكتب')
    item_id = fields.Many2one('care.hosp.item', string='الصنف', required=True)
    option_ids = fields.Many2many('care.hosp.option', string='الخيارات')
    quantity = fields.Float(string='الكمية', default=1.0)
    time_of_day = fields.Float(string='الساعة', default=8.0, required=True)
    weekdays_only = fields.Boolean(string='أيام العمل فقط', default=True)
    last_run = fields.Date(string='آخر تنفيذ', readonly=True)
    active = fields.Boolean(default=True)

    @api.model
    def _cron_place_standing(self):
        """Places any standing order whose time has come today. Runs often; the
        last_run date makes it idempotent so a re-run never double-orders."""
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        today = now.date()
        h = now.hour + now.minute / 60.0
        for s in self.search([('last_run', '!=', today)]):
            if s.weekdays_only and today.weekday() in (4, 5):  # Fri/Sat weekend
                continue
            if h < s.time_of_day:
                continue
            order = self.env['care.hosp.order'].with_user(s.user_id).create({
                'requester_id': s.user_id.id, 'facility_id': s.facility_id.id,
                'location_id': s.location_id.id or False, 'room_label': s.room_label,
                'note': _('طلب دائم: %s') % s.name,
                'line_ids': [(0, 0, {'item_id': s.item_id.id, 'quantity': s.quantity,
                                     'option_ids': [(6, 0, s.option_ids.ids)]})],
            })
            try:
                order.action_place()
            except Exception:
                order.action_cancel()
            s.last_run = today
        return True
