# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CafmWorkorder(models.Model):
    """A work order (reactive / preventive / corrective). The worker scans the
    location QR to prove presence and START the repair timer; the duration is
    measured until 'done' — feeding MTTR/SLA."""
    _name = 'care.cafm.workorder'
    _description = 'CAFM Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, request_datetime desc, id desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    title = fields.Char(string='العنوان', required=True, tracking=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, tracking=True, index=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع (بمسح QR)', tracking=True,
                                  domain="[('facility_id','=',facility_id)]")
    service_id = fields.Many2one('care.cafm.service', string='الخدمة', required=True, tracking=True, index=True)
    service_type = fields.Selection(related='service_id.service_type', store=True)
    project_id = fields.Many2one(related='facility_id.project_id', store=True, string='المشروع')
    partner_id = fields.Many2one(related='facility_id.partner_id', store=True, string='العميل')

    wo_type = fields.Selection([
        ('reactive', 'تصحيحي (طارئ)'), ('preventive', 'وقائي (PPM)'),
        ('inspection', 'من جولة/ملاحظة'),
    ], string='النوع', default='reactive', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'عادية'), ('1', 'متوسطة'), ('2', 'عالية'), ('3', 'عاجلة'),
    ], string='الأولوية', default='1', tracking=True)
    description = fields.Text(string='الوصف')
    instructions = fields.Text(string='المطلوب تنفيذه',
                               help='التعليمات/المطلوب من العامل تنفيذه بدقة في هذه المهمة.')

    # ---- completion proof requirements (set by whoever assigns the task) ----
    proof_presence = fields.Boolean(string='يتطلب إثبات حضور (QR)', default=True,
                                    help='لا يمكن الإرسال للاعتماد إلا بعد مسح رمز QR المسجّل للموقع.')
    proof_photo = fields.Boolean(string='يتطلب صورة', default=True)
    proof_video = fields.Boolean(string='يتطلب فيديو', default=False)
    result_description = fields.Text(string='وصف النتيجة',
                                     help='ملخّص ما نفّذه العامل — يظهر في جدول النتيجة للمشرف.')
    presence_verified = fields.Boolean(string='أُثبت الحضور', compute='_compute_presence_verified')
    rejection_count = fields.Integer(string='مرات الإرجاع', default=0, copy=False, tracking=True,
                                     help='عدد مرات إرجاع النتيجة من المشرف — يؤثّر سلباً على تقييم العامل.')

    employee_id = fields.Many2one('hr.employee', string='المُسنَد إليه', tracking=True, index=True)
    supervisor_id = fields.Many2one('res.users', string='المشرف')

    request_datetime = fields.Datetime(string='وقت الطلب', default=fields.Datetime.now, tracking=True)
    sla_hours = fields.Float(string='SLA (ساعات)')
    deadline = fields.Datetime(string='الموعد النهائي', compute='_compute_deadline', store=True)
    expected_minutes = fields.Integer(string='المدة المحدّدة (دقيقة)', default=60,
                                      help='المدة التي يحدّدها المُسنِد — يبدأ منها العدّاد التنازلي عند بدء التنفيذ.')
    start_datetime = fields.Datetime(string='بداية التنفيذ (بمسح الحضور)', readonly=True, copy=False)
    done_datetime = fields.Datetime(string='وقت الإنجاز', readonly=True, copy=False)
    duration_minutes = fields.Float(string='مدة الإصلاح (دقيقة)', compute='_compute_duration', store=True)
    response_minutes = fields.Float(string='زمن الاستجابة (دقيقة)', compute='_compute_duration', store=True)
    is_overdue = fields.Boolean(compute='_compute_overdue', search='_search_overdue')

    state = fields.Selection([
        ('new', 'جديد'), ('assigned', 'مُسنَد'), ('in_progress', 'قيد التنفيذ'),
        ('hold', 'معلّق'), ('done', 'مُنجَز'), ('verified', 'مُعتمَد'), ('cancelled', 'ملغى'),
    ], default='new', tracking=True, index=True)

    asset_id = fields.Many2one('account.asset', string='الأصل المحاسبي')
    cafm_asset_id = fields.Many2one('care.cafm.asset', string='الأصل', tracking=True,
                                    domain="[('facility_id','=',facility_id)]")
    escalation_level = fields.Integer(string='مستوى التصعيد', default=0, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _escalate_to(self, user, level_label):
        self.ensure_one()
        if user:
            self.activity_schedule(
                'mail.mail_activity_data_warning' if self.env.ref('mail.mail_activity_data_warning', False)
                else 'mail.mail_activity_data_todo',
                summary=_('تصعيد SLA (%s): %s') % (level_label, self.title or self.name),
                date_deadline=fields.Date.today(), user_id=user.id)

    @api.model
    def _cron_sla_escalate(self):
        """Auto-escalate overdue work orders: L1→supervisor, L2→HR managers."""
        now = fields.Datetime.now()
        overdue = self.search([('deadline', '!=', False), ('deadline', '<', now),
                               ('state', 'not in', ('done', 'verified', 'cancelled'))])
        mgr_grp = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        for wo in overdue:
            over_h = (now - wo.deadline).total_seconds() / 3600.0
            if wo.escalation_level < 1:
                wo.escalation_level = 1
                sup = wo.supervisor_id or (wo.employee_id.parent_id.user_id
                                           if wo.employee_id.parent_id else False)
                wo._escalate_to(sup, _('المستوى 1 — المشرف'))
                wo._cafm_log(_('⏱ تجاوز SLA — تصعيد للمشرف (المستوى 1).'))
            elif wo.escalation_level == 1 and over_h >= 2.0:
                wo.escalation_level = 2
                mgr = mgr_grp.users[:1] if mgr_grp and mgr_grp.users else False
                wo._escalate_to(mgr, _('المستوى 2 — الإدارة'))
                wo._cafm_log(_('🔺 تأخّر متواصل (%.0f ساعة) — تصعيد للإدارة (المستوى 2).') % over_h)

    @api.onchange('service_id')
    def _onchange_service(self):
        if self.service_id and not self.sla_hours:
            self.sla_hours = self.service_id.default_sla_hours

    @api.depends('request_datetime', 'sla_hours')
    def _compute_deadline(self):
        for rec in self:
            if rec.request_datetime and rec.sla_hours:
                rec.deadline = rec.request_datetime + timedelta(hours=rec.sla_hours)
            else:
                rec.deadline = False

    @api.depends('start_datetime', 'done_datetime', 'request_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.done_datetime:
                rec.duration_minutes = (rec.done_datetime - rec.start_datetime).total_seconds() / 60.0
            else:
                rec.duration_minutes = 0.0
            if rec.request_datetime and rec.start_datetime:
                rec.response_minutes = (rec.start_datetime - rec.request_datetime).total_seconds() / 60.0
            else:
                rec.response_minutes = 0.0

    def _compute_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.deadline and rec.deadline < now
                                  and rec.state not in ('done', 'verified', 'cancelled'))

    def _search_overdue(self, operator, value):
        now = fields.Datetime.now()
        dom = [('deadline', '<', now), ('state', 'not in', ('done', 'verified', 'cancelled'))]
        recs = self.search(dom)
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', recs.ids)]
        return [('id', 'not in', recs.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        SLA = self.env['care.cafm.sla'].sudo() if 'care.cafm.sla' in self.env else None
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.workorder') or '/'
            if not vals.get('sla_hours'):
                # a matching SLA policy takes precedence over the service default
                hrs = None
                if SLA is not None and vals.get('facility_id'):
                    hrs = SLA.resolution_hours_for(
                        self.env['care.cafm.facility'].browse(vals['facility_id']),
                        self.env['care.cafm.service'].browse(vals['service_id']) if vals.get('service_id') else self.env['care.cafm.service'],
                        str(vals.get('priority') or '1'))
                if not hrs and vals.get('service_id'):
                    hrs = self.env['care.cafm.service'].browse(vals['service_id']).default_sla_hours
                if hrs:
                    vals['sla_hours'] = hrs
        return super().create(vals_list)

    def _push_assignment(self):
        """Tell the assignee's phone. Assignment was the one event workers
        actually wait on, and it pushed nothing at all — only an Odoo activity,
        which the mobile app never surfaces."""
        Notif = self.env.get('care.cafm.notification')
        if Notif is None:
            return
        for rec in self:
            user = rec.employee_id.user_id
            if not user or not user.active:
                continue
            try:
                self.env['care.cafm.notification'].sudo().push(
                    user, _('🆕 أمر عمل جديد مُسنَد إليك'),
                    ' — '.join(filter(None, [rec.title or rec.name,
                                             rec.facility_id.name or ''])),
                    ntype='task', action_url='/workorder/%s' % rec.id)
            except Exception:
                pass  # never let a push failure block the workflow

    def write(self, vals):
        """Assignment also happens by dropping an employee on the record (or via
        the API), not only through action_assign — push in both paths."""
        before = {r.id: r.employee_id.id for r in self} if 'employee_id' in vals else {}
        res = super().write(vals)
        if before:
            changed = self.filtered(
                lambda r: r.employee_id and r.employee_id.id != before.get(r.id))
            changed._push_assignment()
        return res

    # ---------- workflow ----------
    def action_assign(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError(_('اختر العامل المُسنَد إليه أولاً.'))
            rec.state = 'assigned'
            if rec.employee_id.user_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=_('أمر عمل: %s') % (rec.title or ''),
                                      user_id=rec.employee_id.user_id.id)
            rec._push_assignment()

    def _cafm_log(self, body):
        """message_post that never fails when the acting user has no email
        (field workers often don't) — supplies a company/noreply email_from."""
        email = self.env.user.email or self.env.company.email or 'noreply@ecare.care-kw.com'
        for rec in self:
            rec.message_post(body=body, email_from=email)

    def _compute_presence_verified(self):
        Scan = self.env['care.cafm.scan'].sudo()
        for rec in self:
            if not rec.proof_presence:
                rec.presence_verified = True
                continue
            if not rec.employee_id:
                rec.presence_verified = False
                continue
            # a QR scan by this worker, tied to this work order OR at its location
            rec.presence_verified = Scan.search_count([
                ('employee_id', '=', rec.employee_id.id),
                '|', ('workorder_id', '=', rec.id),
                ('location_id', '=', rec.location_id.id if rec.location_id else False),
            ]) > 0

    def _image_media(self):
        return self.media_ids.filtered(lambda m: m.media_type in ('photo', 'before', 'after'))

    def _video_media(self):
        return self.media_ids.filtered(lambda m: m.media_type == 'video')

    def proof_missing(self):
        """Return a list of human messages for unmet completion requirements."""
        self.ensure_one()
        missing = []
        if self.proof_presence and not self.presence_verified:
            missing.append(_('إثبات الحضور بمسح رمز QR الخاص بالموقع'))
        if self.proof_photo and not self._image_media():
            missing.append(_('صورة واحدة على الأقل'))
        if self.proof_video and not self._video_media():
            missing.append(_('مقطع فيديو واحد على الأقل'))
        return missing

    def action_scan_start(self, location=None):
        """Presence proof: worker scanned the location QR — start the timer."""
        for rec in self:
            rec.start_datetime = fields.Datetime.now()
            rec.state = 'in_progress'
            rec.env['care.cafm.scan'].create({
                'employee_id': rec.employee_id.id,
                'location_id': (location or rec.location_id).id if (location or rec.location_id) else False,
                'scan_type': 'start_task', 'workorder_id': rec.id})
            rec._cafm_log(_('▶️ بدأ التنفيذ بعد إثبات الحضور بالموقع — العدّاد يعمل.'))

    def action_hold(self):
        self.write({'state': 'hold'})

    def action_done(self):
        """Worker submits the result for approval — only if the required proof
        (presence QR + photo/video) is provided."""
        for rec in self:
            missing = rec.proof_missing()
            if missing:
                raise UserError(_('لا يمكن الإرسال للاعتماد قبل تقديم: %s') % ('، '.join(missing)))
            if not rec.start_datetime:
                rec.start_datetime = fields.Datetime.now()
            rec.write({'state': 'done', 'done_datetime': fields.Datetime.now()})
            rec._cafm_log(_('✔ أرسل العامل النتيجة للاعتماد — خلال %.0f دقيقة.') % rec.duration_minutes)

    def action_verify(self):
        self.write({'state': 'verified'})
        for rec in self:
            rec._cafm_log(_('✅ اعتُمدت النتيجة من المشرف.'))

    def action_reject(self, reason=None):
        """Supervisor returns the task to the worker (result not accepted).
        Repeated rejections hurt the worker's performance score."""
        for rec in self:
            rec.rejection_count += 1
            rec.write({'state': 'in_progress', 'done_datetime': False})
            body = _('↩️ أُرجعت المهمة للتنفيذ من جديد (النتيجة غير معتمدة).')
            if reason:
                body += _(' السبب: %s') % reason
            if rec.rejection_count > 1:
                body += _(' — تكرار الإرجاع (%d مرات) يؤثّر سلباً على التقييم.') % rec.rejection_count
            rec._cafm_log(body)
            rec._record_rejection_performance(reason)

    def _record_rejection_performance(self, reason=None):
        """Feed a negative signal into the performance ledger when a worker's
        result is returned unapproved more than once (best-effort, optional dep)."""
        self.ensure_one()
        if self.rejection_count <= 1 or not self.employee_id:
            return
        if 'care.performance.log' not in self.env:
            return
        Perf = self.env['care.performance.log']
        try:
            Perf.sudo().record_event(
                self.employee_id.id, -abs(self.rejection_count), 'workorder_rejected',
                _('إرجاع نتيجة أمر العمل %s (%d مرات)%s') % (
                    self.name, self.rejection_count, (': ' + reason) if reason else ''),
                res_model='care.cafm.workorder', res_id=self.id)
        except Exception:
            _logger.exception('perf record on WO rejection failed')

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'new'})


class CafmScan(models.Model):
    """Every QR scan: movement, task-start (presence), patrol, cleaning in/out.
    Feeds 'who is where now' and the task timer."""
    _name = 'care.cafm.scan'
    _description = 'CAFM QR Scan Log'
    _order = 'scan_datetime desc, id desc'

    employee_id = fields.Many2one('hr.employee', string='العضو', index=True)
    location_id = fields.Many2one('care.cafm.location', string='الموقع', index=True)
    facility_id = fields.Many2one(related='location_id.facility_id', store=True)
    scan_type = fields.Selection([
        ('move', 'تنقّل'), ('start_task', 'بدء مهمة (حضور)'), ('patrol', 'نقطة دورية'),
        ('clean_in', 'دخول تنظيف'), ('clean_out', 'خروج تنظيف'), ('report', 'بلاغ'),
    ], string='نوع المسح', default='move', required=True)
    workorder_id = fields.Many2one('care.cafm.workorder', string='أمر العمل', ondelete='set null')
    scan_datetime = fields.Datetime(string='الوقت', default=fields.Datetime.now, required=True, index=True)
    note = fields.Char()
