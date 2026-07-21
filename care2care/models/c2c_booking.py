# -*- coding: utf-8 -*-
"""CARE 2 CARE booking: a customer books a service, picks a visit date/time,
address and pays. Lifecycle: draft → confirmed → assigned → in_progress →
done → (rated) / cancelled."""
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class C2CBooking(models.Model):
    _name = 'c2c.booking'
    _description = 'CARE 2 CARE Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'c2c.team.notify.mixin']
    _order = 'visit_datetime desc, id desc'
    _notify_setting_field = 'booking_notify_user_ids'
    _notify_action_prefix = 'c2c/booking'

    name = fields.Char(string='رقم الحجز', default='/', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل', required=True, tracking=True,
                                 default=lambda s: s.env.user.partner_id)
    service_id = fields.Many2one('c2c.service', string='الخدمة', required=True, tracking=True)
    package_id = fields.Many2one('c2c.service.package', string='الباقة',
                                 domain="[('service_id','=',service_id)]")
    category_id = fields.Many2one(related='service_id.category_id', store=True, string='الفئة')
    # scheduling
    visit_datetime = fields.Datetime(string='موعد الزيارة', required=True, tracking=True,
                                     default=lambda s: fields.Datetime.now() + timedelta(days=1))
    duration_min = fields.Integer(string='المدة (دقيقة)')
    end_datetime = fields.Datetime(string='وقت الانتهاء المتوقّع', compute='_compute_end', store=True)
    # location
    address = fields.Char(string='العنوان', tracking=True)
    area = fields.Char(string='المنطقة')
    gps = fields.Char(string='الإحداثيات (GPS)')
    phone = fields.Char(string='هاتف التواصل')
    notes = fields.Text(string='ملاحظات العميل')
    # assignment — either a single provider, or a whole crew (team leader).
    # A team assignment is visible to every member of that crew.
    provider_id = fields.Many2one('c2c.provider', string='مقدّم الخدمة', tracking=True)
    team_leader_id = fields.Many2one('c2c.provider', string='الفريق المُسنَد', tracking=True,
                                     domain="[('role','in',('team_leader','supervisor'))]",
                                     help='عند الإسناد لفريق يرى الطلبَ كل أعضاء الفريق.')
    team_driver_id = fields.Many2one('c2c.provider', related='team_leader_id.driver_id',
                                     string='سائق الفريق', store=True, readonly=True)
    # pricing & payment
    amount = fields.Float(string='المبلغ', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    payment_method = fields.Selection([
        ('cash', 'نقدًا عند الزيارة'), ('knet', 'كي نت'), ('card', 'بطاقة'), ('wallet', 'المحفظة'),
    ], string='طريقة الدفع', default='cash', tracking=True)
    payment_state = fields.Selection([
        ('unpaid', 'غير مدفوع'), ('paid', 'مدفوع'), ('refunded', 'مُسترجع'),
    ], string='حالة الدفع', default='unpaid', tracking=True)
    # Upayments track id of the last hosted charge for THIS record; the payment
    # callbacks verify this id server-side against the gateway before marking paid.
    upay_track_id = fields.Char(string='مرجع بوابة الدفع', copy=False, index=True)
    discount_code = fields.Char(string='كود الخصم')
    discount_amount = fields.Float(string='قيمة الخصم')
    state = fields.Selection([
        ('draft', 'مسودة'), ('confirmed', 'مؤكّد'), ('assigned', 'مُسند'),
        ('in_progress', 'قيد التنفيذ'), ('review', 'بانتظار اعتماد المشرف'),
        ('done', 'منجز'), ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True)
    rating = fields.Selection([
        ('1', '★'), ('2', '★★'), ('3', '★★★'), ('4', '★★★★'), ('5', '★★★★★'),
    ], string='التقييم', tracking=True)
    feedback = fields.Text(string='ملاحظات التقييم')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- field-execution (filled by the crew from the app) ----------------
    started_at = fields.Datetime(string='بدء التنفيذ', readonly=True, copy=False)
    finished_at = fields.Datetime(string='انتهاء التنفيذ', readonly=True, copy=False)
    staff_note = fields.Text(string='ملاحظة الفريق')
    proof_before = fields.Image(string='صورة قبل', max_width=1280, max_height=1280)
    proof_after = fields.Image(string='صورة بعد', max_width=1280, max_height=1280)
    # as many before/after photos & videos as the job needs
    media_ids = fields.One2many('c2c.booking.media', 'booking_id', string='وسائط التنفيذ')
    before_count = fields.Integer(compute='_compute_media_counts', string='صور قبل')
    after_count = fields.Integer(compute='_compute_media_counts', string='صور بعد')
    quality_ok = fields.Boolean(string='اعتماد الجودة', tracking=True)
    quality_by = fields.Many2one('c2c.provider', string='اعتمد الجودة', readonly=True, copy=False)
    submitted_by = fields.Many2one('c2c.provider', string='أرسله للاعتماد', readonly=True, copy=False)
    review_note = fields.Char(string='ملاحظة الاعتماد/الرفض')

    @api.depends('media_ids.kind')
    def _compute_media_counts(self):
        for b in self:
            b.before_count = len(b.media_ids.filtered(lambda m: m.kind == 'before'))
            b.after_count = len(b.media_ids.filtered(lambda m: m.kind == 'after'))

    @api.depends('visit_datetime', 'duration_min')
    def _compute_end(self):
        for b in self:
            b.end_datetime = (b.visit_datetime + timedelta(minutes=b.duration_min or 0)) if b.visit_datetime else False

    @api.onchange('service_id', 'package_id')
    def _onchange_service(self):
        if self.package_id:
            self.amount = self.package_id.price
            self.duration_min = self.package_id.duration_min
        elif self.service_id:
            self.amount = self.service_id.base_price
            self.duration_min = self.service_id.duration_min

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('c2c.booking') or _('حجز جديد')
            # default amount from service/package if not set
            if not v.get('amount'):
                pkg = self.env['c2c.service.package'].browse(v['package_id']) if v.get('package_id') else None
                svc = self.env['c2c.service'].browse(v['service_id']) if v.get('service_id') else None
                v['amount'] = (pkg.price if pkg else 0.0) or (svc.base_price if svc else 0.0)
            if not v.get('duration_min'):
                pkg = self.env['c2c.service.package'].browse(v['package_id']) if v.get('package_id') else None
                svc = self.env['c2c.service'].browse(v['service_id']) if v.get('service_id') else None
                v['duration_min'] = (pkg.duration_min if pkg else 0) or (svc.duration_min if svc else 60)
        recs = super().create(vals_list)
        # a customer just booked — make sure the back-office actually hears about it
        for b in recs:
            b._notify_team(_('📅 حجز خدمة جديد'),
                           _('حجز جديد %s: %s من %s لموعد %s') % (
                               b.name or '', b.service_id.name or '',
                               b.partner_id.display_name or '', b.visit_datetime or ''))
        return recs

    # friendly customer-facing message per booking state (app notification)
    _CUST_MSG = {
        'confirmed': ('✅ تم تأكيد حجزك', 'تم تأكيد حجز خدمة %s لموعد %s.'),
        'assigned': ('👷 تم تعيين الفني', 'تم تعيين فني لخدمة %s. سيصل في الموعد المحدد.'),
        'in_progress': ('🔧 بدأ التنفيذ', 'بدأ تنفيذ خدمة %s الآن.'),
        'done': ('🎉 اكتملت الخدمة', 'اكتملت خدمة %s. نتمنى أن تكون راضيًا — قيّم تجربتك.'),
        'cancelled': ('✖ تم إلغاء الحجز', 'تم إلغاء حجز خدمة %s.'),
    }

    def _notify_customer(self, state):
        self.ensure_one()
        msg = self._CUST_MSG.get(state)
        if not msg or 'care.cafm.notification' not in self.env or not self.partner_id:
            return
        users = self.env['res.users'].sudo().search([('partner_id', '=', self.partner_id.id)])
        if not users:
            return
        title, tpl = msg
        svc = self.service_id.name or ''
        body = tpl % (svc, self.visit_datetime or '') if state == 'confirmed' else tpl % svc
        try:
            self.env['care.cafm.notification'].sudo().push(
                users, title, body, ntype='info', action_url='c2c/booking/%s' % self.id)
        except Exception:
            pass
        # a branded email in step with the in-app notification
        self._email_customer(state, title, body)

    # colour + emoji per state, to theme the email header
    _STATE_STYLE = {
        'confirmed': ('#16A34A', '✅'), 'assigned': ('#2980B9', '👷'),
        'in_progress': ('#F39C12', '🔧'), 'done': ('#16A34A', '🎉'),
        'cancelled': ('#C0392B', '✖'),
    }

    def _email_customer(self, state, title, body):
        """Send the customer a professional, branded HTML email for a booking
        event. Silent no-op when there is no email on file."""
        self.ensure_one()
        email = self.partner_id.email
        if not email:
            return
        accent, emoji = self._STATE_STYLE.get(state, ('#C0392B', '📅'))
        cur = self.currency_id.name if 'currency_id' in self._fields and self.currency_id else 'KWD'
        rows = []
        def row(label, value):
            if not value:
                return
            rows.append(
                '<tr><td style="padding:7px 0;color:#8a94a6;font-size:13px">%s</td>'
                '<td style="padding:7px 0;text-align:left;font-weight:700;color:#1e293b;font-size:13px">%s</td></tr>'
                % (label, value))
        row('الخدمة', self.service_id.name or '')
        row('رقم الحجز', self.name or '')
        row('الموعد', self.visit_datetime and str(self.visit_datetime) or '')
        row('العنوان', ' '.join([x for x in [self.area or '', self.address or ''] if x]))
        if self.amount:
            row('المبلغ', '%s %s' % (round(self.amount, 3), cur))
        details = ''.join(rows)
        name = self.partner_id.name or 'عميلنا الكريم'
        html = """<div dir="rtl" style="margin:0;background:#f4f5f8;padding:22px 0;font-family:'Segoe UI',Tahoma,Arial,sans-serif">
  <table align="center" width="600" style="max-width:600px;margin:auto;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 8px 24px -12px rgba(0,0,0,.25)">
    <tr><td style="background:linear-gradient(135deg,#E24A3B,#C0392B,#8E241B);padding:26px 28px">
      <div style="color:#fff;font-size:22px;font-weight:900;letter-spacing:1px">CARE 2 CARE</div>
      <div style="color:#ffffffcc;font-size:12px;margin-top:2px">خدمات منزلية عند بابك · لأننا نهتم</div>
    </td></tr>
    <tr><td style="padding:26px 28px 8px">
      <div style="display:inline-block;background:%s18;color:%s;font-weight:800;font-size:13px;padding:6px 14px;border-radius:999px">%s %s</div>
      <h2 style="margin:14px 0 4px;color:#1e293b;font-size:19px">مرحبًا %s،</h2>
      <p style="margin:0;color:#55607a;font-size:14px;line-height:1.9">%s</p>
    </td></tr>
    <tr><td style="padding:14px 28px 0">
      <table width="100%%" style="background:#f8f9fc;border-radius:14px;padding:6px 16px;border:1px solid #edf0f5">%s</table>
    </td></tr>
    <tr><td style="padding:22px 28px">
      <a href="https://ecare.care-kw.com" style="display:block;text-align:center;background:%s;color:#fff;text-decoration:none;font-weight:800;font-size:15px;padding:14px;border-radius:12px">عرض التفاصيل في التطبيق</a>
    </td></tr>
    <tr><td style="padding:6px 28px 26px;border-top:1px solid #eef1f6;text-align:center;color:#9aa4b6;font-size:11px">
      شكرًا لاختيارك CARE 2 CARE · للاستفسار تواصل معنا في أي وقت.
    </td></tr>
  </table>
</div>""" % (accent, accent, emoji, title.replace('✅','').replace('👷','').replace('🔧','').replace('🎉','').replace('✖','').strip(),
             name, body, details, accent)
        try:
            self.env['mail.mail'].sudo().create({
                'subject': '%s %s — %s' % (emoji, title.replace(emoji,'').strip(), self.service_id.name or ''),
                'email_to': email,
                'email_from': (self.company_id.email or self.env.company.email or 'no-reply@care-kw.com'),
                'body_html': html,
                'auto_delete': True,
            }).send()
        except Exception:
            pass

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for b in self:
            b.message_post(body=_('✅ تم تأكيد الحجز لموعد %s') % (b.visit_datetime or ''))
            b._notify_customer('confirmed')

    def action_assign(self, provider=None):
        for b in self:
            if provider:
                b.provider_id = provider
            if not b.provider_id:
                raise UserError(_('اختر مقدّم خدمة أولاً.'))
            b.state = 'assigned'
            b._notify_customer('assigned')

    def action_assign_team(self, leader):
        """Hand the job to a whole crew: every member — and the crew's driver —
        sees it and is notified."""
        Provider = self.env['c2c.provider']
        leader = Provider.browse(int(leader)) if not isinstance(leader, models.BaseModel) else leader
        if not leader.exists():
            raise UserError(_('الفريق غير موجود.'))
        for b in self:
            b.team_leader_id = leader.id
            # the leader carries the job unless a specific member is already set
            if not b.provider_id:
                b.provider_id = leader.id
            if b.state in ('draft', 'confirmed'):
                b.state = 'assigned'
            crew = (leader | leader.team_member_ids | leader.driver_id)
            b.message_post(body=_('👥 أُسند الطلب إلى فريق %s (%d عضو).') % (leader.name, len(crew)))
            b._notify_crew(crew, _('🆕 طلب جديد لفريقك'),
                           '%s — %s' % (b.service_id.name or '', b.area or b.address or ''))
            b._notify_customer('assigned')
        return True

    def _notify_crew(self, crew, title, body):
        """Push an in-app notification to every crew member with an app user."""
        if 'care.cafm.notification' not in self.env:
            return
        Notif = self.env['care.cafm.notification'].sudo()
        for p in crew:
            if p.user_id:
                try:
                    Notif.push(p.user_id, title, body, ntype='task',
                               action_url='/c2c/booking/%s' % self.id)
                except Exception:
                    pass

    def action_start(self):
        for b in self:
            b.write({'state': 'in_progress', 'started_at': b.started_at or fields.Datetime.now()})
            b._notify_customer('in_progress')

    def action_done(self):
        for b in self:
            b.write({'state': 'done', 'finished_at': fields.Datetime.now()})
            b._notify_customer('done')

    def action_submit_review(self, by=None):
        """The crew says "we're finished" — the job goes to the supervisor for
        review instead of closing itself."""
        for b in self:
            if not b.media_ids.filtered(lambda m: m.kind == 'after'):
                raise UserError(_('أضف صورة/فيديو "بعد" قبل إرسال العمل للاعتماد.'))
            b.write({'state': 'review', 'finished_at': fields.Datetime.now(),
                     'submitted_by': by.id if by else b.provider_id.id})
            # ping whoever supervises this crew
            sups = b.provider_id.supervisor_id | b.team_leader_id.supervisor_id
            if not sups:
                sups = self.env['c2c.provider'].sudo().search(
                    [('role', 'in', ('supervisor', 'ops_manager'))], limit=5)
            b._notify_crew(sups, _('🔍 عمل بانتظار اعتمادك'),
                           '%s — %s' % (b.name or '', b.service_id.name or ''))
            b.message_post(body=_('📤 أرسل الفريق العمل للاعتماد (%d قبل / %d بعد).')
                           % (b.before_count, b.after_count))

    def action_approve_completion(self, by=None, note=None):
        """Supervisor reviewed the before/after evidence and signs the job off."""
        for b in self:
            b.write({'state': 'done', 'quality_ok': True,
                     'quality_by': by.id if by else False,
                     'review_note': note or b.review_note,
                     'finished_at': b.finished_at or fields.Datetime.now()})
            b.message_post(body=_('✅ اعتمد المشرف إنجاز العمل.%s')
                           % ((' — %s' % note) if note else ''))
            if b.provider_id:
                b._notify_crew(b.provider_id, _('✅ تم اعتماد عملك'), b.name or '')
            b._notify_customer('done')

    def action_reject_completion(self, by=None, note=None):
        """Send it back to the crew with a reason."""
        for b in self:
            b.write({'state': 'in_progress', 'review_note': note or ''})
            b.message_post(body=_('↩️ أعاد المشرف العمل للتنفيذ.%s')
                           % ((' — %s' % note) if note else ''))
            crew = b.provider_id | b.team_leader_id | b.team_leader_id.team_member_ids
            b._notify_crew(crew, _('↩️ العمل يحتاج استكمال'),
                           note or (b.name or ''))

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        for b in self:
            b._notify_customer('cancelled')

    def request_cancel(self, reason=None):
        """Customer-initiated cancellation (app/portal) — unlike action_cancel
        (used by staff) this alerts the back-office, since a crew may already
        be scheduled."""
        self.ensure_one()
        if self.state in ('done', 'cancelled'):
            return False
        # crew already committed → needs a human to unwind the assignment
        needs_review = self.state in ('assigned', 'in_progress')
        self.action_cancel()
        self.message_post(body=_('ألغى العميل الحجز%s') % ((': %s' % reason) if reason else ''))
        self._notify_team(_('✖ ألغى عميل حجزه'),
                          _('ألغى %s الحجز %s (%s) لموعد %s%s') % (
                              self.partner_id.display_name or '', self.name or '',
                              self.service_id.name or '', self.visit_datetime or '',
                              (' — %s' % reason) if reason else ''),
                          activity=needs_review)
        return True

    def action_pay(self):
        self.write({'payment_state': 'paid'})
        for b in self:
            b.message_post(body=_('💳 تم استلام الدفع: %.2f') % b.amount)

    def action_rate(self, stars, feedback=None):
        self.ensure_one()
        self.write({'rating': str(stars), 'feedback': feedback or self.feedback})
        self.service_id._compute_rating()


class C2CBookingMedia(models.Model):
    """Before/after evidence captured by the crew — as many photos and videos as
    the job needs, instead of a single before/after image."""
    _name = 'c2c.booking.media'
    _description = 'وسائط تنفيذ الحجز'
    _order = 'kind, id'

    booking_id = fields.Many2one('c2c.booking', string='الحجز', required=True,
                                 ondelete='cascade', index=True)
    kind = fields.Selection([('before', 'قبل'), ('after', 'بعد')],
                            string='النوع', required=True, default='after')
    media_type = fields.Selection([('photo', 'صورة'), ('video', 'فيديو')],
                                  string='الوسيط', default='photo')
    name = fields.Char(string='الاسم')
    file = fields.Binary(string='الملف', attachment=True)
    provider_id = fields.Many2one('c2c.provider', string='التقطها')
    note = fields.Char(string='ملاحظة')
