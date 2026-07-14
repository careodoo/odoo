# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

LIFECYCLE = [
    ('draft', 'Draft'),
    ('to_sign', 'To Sign'),
    ('signed', 'Signed'),
    ('scanned', 'Scanned'),
    ('with_delegate', 'With Delegate'),
    ('delivered', 'Delivered'),
    ('acknowledged', 'Acknowledged'),
    ('archived', 'Archived'),
]


class LetterFile(models.Model):
    _inherit = 'letter.file'

    # ----- direction / numbering -----
    direction = fields.Selection(
        [('outgoing', 'Outgoing'), ('incoming', 'Incoming')],
        string='Direction', default='outgoing', required=True, tracking=True, index=True)

    # ----- lifecycle -----
    letter_state = fields.Selection(
        LIFECYCLE, string='Status', default='draft', tracking=True, index=True,
        group_expand='_expand_states')

    classification_id = fields.Many2one('letter.classification', string='Classification', tracking=True)
    is_confidential = fields.Boolean(string='Confidential', tracking=True)

    # ----- people -----
    requester_id = fields.Many2one('res.users', string='Requested By',
                                   default=lambda s: s.env.user, tracking=True, index=True)
    signed_by = fields.Many2one('res.users', string='Signed By', readonly=True, tracking=True)
    signed_date = fields.Datetime(string='Signed On', readonly=True)
    # Replacements for former Odoo-Studio fields (data migrated in post_init, studio fields dropped)
    follow_up_person_id = fields.Many2one('hr.employee', string='Follow-up Person', tracking=True)
    notes = fields.Text(string='Notes')

    # ----- delivery tracking -----
    delivery_mode = fields.Selection(
        [('ack_required', 'Acknowledgement Required'), ('no_ack', 'No Acknowledgement — Auto Archive')],
        string='Delivery Mode', default='ack_required', required=True, tracking=True, index=True,
        help='No Acknowledgement: letters the receiving party does not sign back for — '
             'archived automatically upon delivery, and never chased for a receipt.')
    delegate_id = fields.Many2one('hr.employee', string='Delegate', tracking=True, index=True)
    delegate_handover_date = fields.Date(string='Handed to Delegate', tracking=True)
    delivered_date = fields.Date(string='Delivered On', tracking=True)
    receiver_name = fields.Char(string='Received By', tracking=True)
    receiver_signature = fields.Binary(string='Receiver Signature')
    receipt_scan = fields.Binary(string='Acknowledgement Scan')
    days_with_delegate = fields.Integer(string='Days With Delegate', compute='_compute_delivery', store=True)
    is_overdue = fields.Boolean(string='Delivery Overdue', compute='_compute_delivery', store=True, index=True)

    # ----- deadlines / threading -----
    response_deadline = fields.Date(string='Response Deadline', tracking=True)
    deadline_state = fields.Selection(
        [('none', 'None'), ('ok', 'On Track'), ('due_soon', 'Due Soon'), ('overdue', 'Overdue')],
        string='Deadline', compute='_compute_deadline_state', store=True)
    reply_to_id = fields.Many2one('letter.file', string='In Reply To', index=True)
    reply_ids = fields.One2many('letter.file', 'reply_to_id', string='Replies')
    reply_count = fields.Integer(compute='_compute_reply_count')

    # ----- cross-module links -----
    employee_id = fields.Many2one('hr.employee', string='Related Employee', index=True)
    gov_file = fields.Char(string='Government File')

    # ----- OCR / archive -----
    ocr_text = fields.Text(string='Scanned Text (OCR)', readonly=True)
    ocr_state = fields.Selection(
        [('none', 'No Scan'), ('pending', 'Pending'), ('done', 'Indexed'), ('failed', 'Failed')],
        string='OCR', default='none', readonly=True, index=True)
    archive_building = fields.Char(string='Archive Building')
    archive_cabinet = fields.Char(string='Cabinet')
    archive_file = fields.Char(string='Physical File')
    archive_shelf = fields.Char(string='Shelf')

    # ----- fees -----
    fee_ids = fields.One2many('letter.fee', 'letter_id', string='Government Fees')
    fee_total = fields.Float(string='Total Fees', compute='_compute_fees', store=True)
    fee_unpaid = fields.Float(string='Unpaid Fees', compute='_compute_fees', store=True)

    # ================= computes =================
    @api.model
    def _expand_states(self, states, domain, order=None):
        return [k for k, _v in LIFECYCLE]

    @api.depends('letter_state', 'delegate_handover_date', 'delivered_date',
                 'receipt_scan', 'receiver_name', 'delivery_mode')
    def _compute_delivery(self):
        threshold = self._overdue_days()
        today = date.today()
        for rec in self:
            days = 0
            if rec.delegate_handover_date and rec.letter_state in ('with_delegate', 'delivered'):
                end = rec.delivered_date or today
                days = (end - rec.delegate_handover_date).days
            rec.days_with_delegate = days
            rec.is_overdue = bool(
                rec.delivery_mode == 'ack_required'
                and rec.letter_state == 'with_delegate'
                and rec.delegate_handover_date
                and (today - rec.delegate_handover_date).days > threshold
            )

    @api.depends('response_deadline', 'letter_state')
    def _compute_deadline_state(self):
        today = date.today()
        for rec in self:
            if not rec.response_deadline or rec.letter_state in ('acknowledged', 'archived'):
                rec.deadline_state = 'none'
            else:
                delta = (rec.response_deadline - today).days
                if delta < 0:
                    rec.deadline_state = 'overdue'
                elif delta <= 3:
                    rec.deadline_state = 'due_soon'
                else:
                    rec.deadline_state = 'ok'

    @api.depends('reply_ids')
    def _compute_reply_count(self):
        for rec in self:
            rec.reply_count = len(rec.reply_ids)

    @api.depends('fee_ids.amount', 'fee_ids.state')
    def _compute_fees(self):
        for rec in self:
            rec.fee_total = sum(rec.fee_ids.mapped('amount'))
            rec.fee_unpaid = sum(f.amount for f in rec.fee_ids if f.state == 'unpaid')

    # ================= helpers =================
    @api.model
    def _overdue_days(self):
        val = self.env['ir.config_parameter'].sudo().get_param('care_letter.overdue_days', '7')
        try:
            return int(val)
        except (TypeError, ValueError):
            return 7

    def _make_incoming_ref(self):
        self.ensure_one()
        today = date.today()
        seq = self.env['ir.sequence'].next_by_code('letter.file.incoming') or str(self.id)
        return 'In/%s/%s/%s' % (today.year, today.month, seq)

    # ================= create =================
    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if not vals.get('requester_id'):
                vals['requester_id'] = self.env.uid
            # inherit delivery mode from the chosen classification when not set explicitly
            if not vals.get('delivery_mode') and vals.get('classification_id'):
                cls = self.env['letter.classification'].browse(vals['classification_id'])
                if cls.default_delivery_mode:
                    vals['delivery_mode'] = cls.default_delivery_mode
            # super() (sp_letter) expects a single dict and sets the Care/ ref via id
            rec = super(LetterFile, self).create(vals)
            records |= rec
        for rec in records:
            if rec.direction == 'incoming':
                rec.ref = rec._make_incoming_ref()
            if rec.image_letter and rec.ocr_state == 'none':
                rec.ocr_state = 'pending'
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'image_letter' in vals:
            for rec in self:
                if rec.image_letter and rec.ocr_state in ('none', 'failed'):
                    rec.ocr_state = 'pending'
        return res

    # ================= workflow buttons =================
    def action_send_to_sign(self):
        for rec in self:
            rec.letter_state = 'to_sign'
            signer = rec._signer_partners()
            rec._notify(signer, _('Letter awaiting your signature'),
                        _('كتاب بانتظار توقيعك'),
                        _('الكتاب التالي جاهز ويحتاج إلى توقيعك المعتمد قبل المتابعة إلى مرحلة المسح والتسليم.'),
                        accent='#e08a00')
        return True

    def action_sign(self):
        for rec in self:
            rec.write({'letter_state': 'signed', 'signed_by': self.env.uid,
                       'signed_date': fields.Datetime.now()})
        return True

    def action_scan(self):
        for rec in self:
            state = {'letter_state': 'scanned'}
            if rec.image_letter and rec.ocr_state in ('none', 'failed'):
                state['ocr_state'] = 'pending'
            rec.write(state)
            # notify the requester the letter is signed & ready
            if rec.requester_id and rec.requester_id.partner_id:
                rec._notify(rec.requester_id.partner_id,
                            _('Your letter is ready for pickup'),
                            _('كتابك جاهز للاستلام ✅'),
                            _('تم توقيع كتابك ومسحه ضوئياً، وهو الآن جاهز للاستلام من إدارة المراسلات.'),
                            accent='#1a9f6d')
        return True

    def action_handover_delegate(self):
        for rec in self:
            if not rec.delegate_id:
                continue
            rec.write({'letter_state': 'with_delegate',
                       'delegate_handover_date': fields.Date.today()})
            if rec.delegate_id.user_id and rec.delegate_id.user_id.partner_id:
                rec._notify(rec.delegate_id.user_id.partner_id,
                            _('A letter was handed to you for delivery'),
                            _('كتاب سُلّم إليك للتوصيل 🚚'),
                            _('استلمت الكتاب التالي لتوصيله إلى الجهة المعنية. يرجى توصيله وإرجاع '
                              'نسخة الاستلام (توقيع/ختم الجهة) في أقرب وقت.'),
                            accent='#2f6df6')
        return True

    def action_confirm_delivery(self):
        for rec in self:
            vals = {'letter_state': 'delivered',
                    'delivered_date': rec.delivered_date or fields.Date.today(),
                    'deli_date': rec.deli_date or fields.Date.today()}
            rec.write(vals)
            # letters that need no receipt back are archived straight away
            if rec.delivery_mode == 'no_ack':
                rec.letter_state = 'archived'
                rec.message_post(
                    body=_('تم التسليم وأُرشف الكتاب مباشرة (نوع بلا إقرار استلام).'),
                    subtype_xmlid='mail.mt_note')
        return True

    @api.onchange('classification_id')
    def _onchange_classification_delivery_mode(self):
        if self.classification_id and self.classification_id.default_delivery_mode:
            self.delivery_mode = self.classification_id.default_delivery_mode

    def action_acknowledge(self):
        for rec in self:
            rec.letter_state = 'acknowledged'
            if rec.requester_id and rec.requester_id.partner_id:
                rec._notify(rec.requester_id.partner_id,
                            _('Your letter has been delivered and acknowledged'),
                            _('تم تسليم كتابك واستلامه رسمياً ✅'),
                            _('تم توصيل كتابك إلى الجهة واستلامه رسمياً. تجد أدناه تفاصيل الإقرار.'),
                            accent='#1a9f6d')
        return True

    def action_archive_letter(self):
        for rec in self:
            rec.letter_state = 'archived'
        return True

    def action_open_replies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Replies'),
            'res_model': 'letter.file',
            'view_mode': 'tree,form',
            'domain': [('reply_to_id', '=', self.id)],
            'context': {'default_reply_to_id': self.id,
                        'default_partner_id': self.partner_id.id},
        }

    def action_print_label(self):
        return self.env.ref('care_letter.action_report_letter_label').report_action(self)

    def action_print_ref_label(self):
        """Print the legacy small label (Date + REF) from the old system."""
        return self.env.ref('sp_letter_v15.outgoing_report').report_action(self)

    def action_print_official(self):
        """Print the full letter on the official CARE letterhead."""
        return self.env.ref('care_letter.action_report_letter_official').report_action(self)

    # ================= notifications =================
    def _signer_partners(self):
        group = self.env.ref('care_letter.group_letter_signer', raise_if_not_found=False)
        if not group:
            return self.env['res.partner']
        return group.users.mapped('partner_id')

    def _fmt(self, value):
        return value if value else '—'

    def _letter_email_html(self, title, intro, accent='#2f6df6'):
        """Build a professional, information-rich CARE-branded HTML email body."""
        self.ensure_one()
        base = self.get_base_url()
        url = '%s/web#id=%s&model=letter.file&view_type=form' % (base, self.id)
        direction = dict(self._fields['direction'].selection).get(self.direction, '')
        state = dict(self._fields['letter_state'].selection).get(self.letter_state, '')

        rows = [
            ('المرجع', self.ref),
            ('الموضوع', self.name),
            ('الاتجاه', direction),
            ('الحالة', state),
            ('الجهة', self.partner_id.name if self.partner_id else None),
            ('التصنيف', self.classification_id.name if self.classification_id else None),
            ('القسم', self.department_id.name if self.department_id else None),
            ('تاريخ الإصدار', self.issue_date),
            ('المندوب', self.delegate_id.name if self.delegate_id else None),
            ('سُلّم للمندوب', self.delegate_handover_date),
            ('تاريخ التوصيل', self.delivered_date),
            ('المستلم', self.receiver_name),
            ('أيام مع المندوب', self.days_with_delegate if self.delegate_handover_date else None),
            ('موعد الرد النهائي', self.response_deadline),
            ('مسؤول المتابعة', self.follow_up_person_id.name if self.follow_up_person_id else None),
            ('مُقدّم الطلب', self.requester_id.name if self.requester_id else None),
            ('رسوم غير مدفوعة', ('%.3f د.ك' % self.fee_unpaid) if self.fee_unpaid else None),
        ]
        tr = ''
        for label, val in rows:
            if val in (None, False, '', 0):
                continue
            tr += (
                '<tr>'
                '<td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#8a93a8;'
                'font-weight:bold;font-size:12px;width:38%%;">%s</td>'
                '<td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#1d2433;'
                'font-weight:bold;font-size:13px;">%s</td>'
                '</tr>' % (label, val)
            )

        overdue_banner = ''
        if self.is_overdue:
            overdue_banner = (
                '<div style="background:#fff4f2;border:1px solid #ffd4cc;color:#c0392b;'
                'border-radius:8px;padding:10px 14px;font-weight:bold;font-size:13px;margin:0 0 14px;">'
                '🚨 هذا الكتاب متأخّر مع المندوب منذ %s يوماً — يلزم متابعة عاجلة.</div>'
                % self.days_with_delegate
            )

        return (
            '<div style="max-width:620px;margin:auto;font-family:Tahoma,Arial,sans-serif;'
            'direction:rtl;border:1px solid #e4e8f0;border-radius:14px;overflow:hidden;'
            'background:#ffffff;">'
            '<div style="background:#1e2a44;padding:16px 22px;">'
            '<span style="color:#e8564e;font-weight:bold;font-size:20px;">CARE</span>'
            '<span style="color:#aeb8cc;font-size:12px;font-weight:bold;"> · إدارة المراسلات</span>'
            '</div>'
            '<div style="background:%s;height:6px;"></div>'
            '<div style="padding:22px;">'
            '%s'
            '<h2 style="margin:0 0 6px;color:#1e2a44;font-size:19px;">%s</h2>'
            '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 14px;">%s</p>'
            '<table style="width:100%%;border-collapse:collapse;border:1px solid #eef1f6;'
            'border-radius:8px;overflow:hidden;">%s</table>'
            '<div style="text-align:center;margin-top:20px;">'
            '<a href="%s" style="display:inline-block;background:#2f6df6;color:#fff;'
            'padding:11px 26px;border-radius:8px;text-decoration:none;font-weight:bold;'
            'font-size:14px;">فتح الكتاب في النظام ←</a></div>'
            '</div>'
            '<div style="background:#f6f8fc;padding:13px 22px;color:#8a93a8;font-size:11px;'
            'text-align:center;">رسالة آلية من نظام إدارة المراسلات · CARE — '
            'يرجى عدم الرد على هذا البريد</div>'
            '</div>'
        ) % (accent, overdue_banner, title, intro, tr, url)

    def _notify(self, partners, subject, title, intro, accent='#2f6df6'):
        self.ensure_one()
        partners = partners.exists() if partners else partners
        if not partners:
            return
        self.message_post(
            body=self._letter_email_html(title, intro, accent),
            subject=subject,
            partner_ids=partners.ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light',
        )

    # ================= dashboard data =================
    @api.model
    def get_dashboard_data(self):
        def count(dom):
            return self.search_count(dom)

        kpi = {
            'total': count([]),
            'outgoing': count([('direction', '=', 'outgoing')]),
            'incoming': count([('direction', '=', 'incoming')]),
            'to_sign': count([('letter_state', '=', 'to_sign')]),
            'to_scan': count([('letter_state', '=', 'signed')]),
            'with_delegate': count([('letter_state', '=', 'with_delegate')]),
            'overdue': count([('is_overdue', '=', True)]),
            'done': count([('letter_state', 'in', ['delivered', 'acknowledged', 'archived'])]),
            'no_delivery': count([('deli_date', '=', False)]),
            'no_scan': count([('image_letter', '=', False)]),
            'confidential': count([('is_confidential', '=', True)]),
            'deadline_over': count([('deadline_state', '=', 'overdue')]),
        }

        state_labels = dict(self._fields['letter_state'].selection)
        status_dist = []
        for g in self.read_group([], ['letter_state'], ['letter_state']):
            k = g['letter_state']
            if not k:
                continue
            status_dist.append({'key': k, 'label': state_labels.get(k, k), 'value': g['letter_state_count']})

        dir_labels = dict(self._fields['direction'].selection)
        direction_dist = []
        for g in self.read_group([], ['direction'], ['direction']):
            k = g['direction']
            direction_dist.append({'key': k or 'none', 'label': dir_labels.get(k, k or '—'),
                                   'value': g['direction_count']})

        by_class = []
        for g in self.read_group([('classification_id', '!=', False)], ['classification_id'], ['classification_id']):
            by_class.append({'id': g['classification_id'][0], 'label': g['classification_id'][1],
                             'value': g['classification_id_count']})

        ocr_labels = dict(self._fields['ocr_state'].selection)
        ocr_dist = []
        for g in self.read_group([], ['ocr_state'], ['ocr_state']):
            k = g['ocr_state'] or 'none'
            ocr_dist.append({'key': k, 'label': ocr_labels.get(k, k), 'value': g['ocr_state_count']})

        top_partners = []
        for g in self.read_group([('partner_id', '!=', False)], ['partner_id'], ['partner_id'],
                                 orderby='partner_id_count desc', limit=8):
            top_partners.append({'id': g['partner_id'][0], 'name': g['partner_id'][1],
                                 'value': g['partner_id_count']})

        deleg = {}
        for g in self.read_group([('delegate_id', '!=', False)], ['delegate_id'], ['delegate_id'],
                                 orderby='delegate_id_count desc', limit=8):
            did = g['delegate_id'][0]
            deleg[did] = {'id': did, 'name': g['delegate_id'][1], 'total': g['delegate_id_count'], 'overdue': 0}
        if deleg:
            for g in self.read_group([('delegate_id', 'in', list(deleg)), ('is_overdue', '=', True)],
                                     ['delegate_id'], ['delegate_id']):
                deleg[g['delegate_id'][0]]['overdue'] = g['delegate_id_count']
        top_delegates = list(deleg.values())

        trend_labels, trend_values = [], []
        tg = self.read_group([('issue_date', '!=', False)], ['issue_date'], ['issue_date:month'],
                             orderby='issue_date:month')
        for g in tg[-12:]:
            trend_labels.append(g['issue_date:month'])
            trend_values.append(g['issue_date_count'])

        return {
            'kpi': kpi,
            'status_dist': status_dist,
            'direction_dist': direction_dist,
            'by_class': by_class,
            'ocr_dist': ocr_dist,
            'top_partners': top_partners,
            'top_delegates': top_delegates,
            'trend': {'labels': trend_labels, 'values': trend_values},
        }

    # ================= crons =================
    @api.model
    def cron_delivery_reminders(self):
        threshold = self._overdue_days()
        limit_date = date.today() - timedelta(days=threshold)
        overdue = self.search([
            ('letter_state', '=', 'with_delegate'),
            ('delivery_mode', '=', 'ack_required'),
            ('delegate_handover_date', '<', fields.Date.to_string(limit_date)),
        ])
        for rec in overdue:
            # remind the delegate
            if rec.delegate_id.user_id and rec.delegate_id.user_id.partner_id:
                rec._notify(rec.delegate_id.user_id.partner_id,
                            _('Reminder: acknowledgement not returned'),
                            _('تذكير: لم تُرجِع نسخة الاستلام ⏰'),
                            _('الكتاب التالي سُلّم إليك ولم تُرجِع نسخة الاستلام من الجهة. '
                              'يرجى المتابعة ورفع إثبات الاستلام في أقرب وقت.'),
                            accent='#c0392b')
            # escalate to follow-up person / requester
            escal = self.env['res.partner']
            if rec.follow_up_person_id and rec.follow_up_person_id.user_id:
                escal = rec.follow_up_person_id.user_id.partner_id
            elif rec.requester_id:
                escal = rec.requester_id.partner_id
            if escal:
                rec._notify(escal, _('Overdue letter with delegate'),
                            _('تصعيد: كتاب متأخّر مع المندوب 🚨'),
                            _('الكتاب التالي تجاوز المدة المسموحة مع المندوب دون إرجاع إثبات '
                              'الاستلام. يُرجى التدخّل والمتابعة.'),
                            accent='#c0392b')
        _logger.info('care_letter: sent %s delivery reminders', len(overdue))
        return True

    @api.model
    def cron_run_ocr(self, limit=30):
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except Exception:
            _logger.warning('care_letter OCR: pytesseract/PIL not available, skipping')
            return False
        import base64
        import io
        from PIL import Image
        import pytesseract
        recs = self.search([('ocr_state', '=', 'pending'), ('image_letter', '!=', False)], limit=limit)
        done = 0
        for rec in recs:
            try:
                raw = base64.b64decode(rec.image_letter)
                img = Image.open(io.BytesIO(raw))
                text = pytesseract.image_to_string(img, lang='ara+eng')
                rec.write({'ocr_text': (text or '').strip(), 'ocr_state': 'done'})
                done += 1
            except Exception as e:
                _logger.warning('care_letter OCR failed for %s: %s', rec.ref, e)
                rec.ocr_state = 'failed'
        _logger.info('care_letter OCR: processed %s letters', done)
        return True
