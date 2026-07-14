# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ExperienceRenewal(models.Model):
    """One renewal/extension cycle of a contract, tracking the full workflow:
    client request → our approval → notify senior management (email with the
    request + approval letter) → renew & send bank guarantee → sign the
    extension contract. Each step keeps its date, document and deadline."""
    _name = 'care.experience.renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contract Renewal / Extension'
    _order = 'id desc'

    name = fields.Char(string='المرجع', default='/', copy=False, readonly=True)
    experience_id = fields.Many2one('care.experience', string='العقد', required=True,
                                    ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one(related='experience_id.partner_id', string='الجهة', store=True)
    kind = fields.Selection([('renew', 'تجديد'), ('extend', 'تمديد')],
                            string='النوع', default='renew', tracking=True)
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('requested', 'طلب مُستلَم من الجهة'),
        ('approved', 'تمّت الموافقة'),
        ('senior_notified', 'أُشعرت الإدارة العليا'),
        ('guarantee', 'تجديد الكفالة وإرسالها'),
        ('signed', 'توقيع عقد التمديد'),
        ('cancelled', 'ملغى'),
    ], default='draft', tracking=True)

    # 1) client request
    request_date = fields.Date(string='تاريخ طلب الجهة', tracking=True)
    request_attachment = fields.Binary(string='طلب التمديد/التجديد (من الجهة)')
    request_filename = fields.Char()
    respond_deadline = fields.Date(string='الموعد النهائي للرد', tracking=True)

    # 2) our approval
    approval_date = fields.Date(string='تاريخ موافقتنا', tracking=True)
    approval_attachment = fields.Binary(string='كتاب الموافقة')
    approval_filename = fields.Char()

    # 3) senior management notification
    senior_notified_date = fields.Date(string='تاريخ إشعار الإدارة العليا', readonly=True)

    # 4) bank guarantee
    guarantee_id = fields.Many2one('care.bank.guarantee', string='الكفالة البنكية')
    guarantee_sent_date = fields.Date(string='تاريخ إرسال الكفالة', tracking=True)

    # 5) insurance + signed contract
    insurance_attachment = fields.Binary(string='وثيقة التأمين')
    insurance_filename = fields.Char()
    sign_deadline = fields.Date(string='الموعد النهائي للتوقيع', tracking=True)
    sign_date = fields.Date(string='تاريخ التوقيع', tracking=True)
    new_contract_attachment = fields.Binary(string='نسخة عقد التمديد الموقّع')
    new_contract_filename = fields.Char()

    # new terms after renewal
    new_start_date = fields.Date(string='بداية الفترة الجديدة')
    new_expire_date = fields.Date(string='نهاية الفترة الجديدة')
    new_value = fields.Float(string='قيمة العقد الجديدة')
    currency_id = fields.Many2one(related='experience_id.currency_id')

    notify_user_ids = fields.Many2many('res.users', string='المُشعَرون (الإدارة العليا/المعنيون)')
    note = fields.Text(string='ملاحظات')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                exp = self.env['care.experience'].browse(vals.get('experience_id'))
                seq = len(exp.renewal_ids) + 1
                vals['name'] = '%s/REN%s' % (exp.ref or 'CONT', seq)
        return super().create(vals_list)

    # ---------------- workflow ----------------
    def action_receive_request(self):
        for r in self:
            r.write({'state': 'requested',
                     'request_date': r.request_date or fields.Date.today()})

    def action_approve(self):
        for r in self:
            r.write({'state': 'approved',
                     'approval_date': r.approval_date or fields.Date.today()})

    def _senior_email_html(self):
        """Branded HTML card for the senior-management notification email.
        Markup wrapping is required so Odoo 15+ doesn't escape the HTML — see
        the message_post Markup gotcha."""
        self.ensure_one()
        exp = self.experience_id
        kind_label = dict(self._fields['kind'].selection).get(self.kind, self.kind)
        rows = [
            ('العقد', exp.name or exp.ref or '—'),
            ('الجهة المتعاقدة', self.partner_id.name or '—'),
            ('نوع الإجراء', kind_label),
            ('نوع العقد', 'حكومي' if exp.contract_type == 'government' else 'خاص/تجاري'),
            ('تاريخ الانتهاء الحالي', exp.expire_date and str(exp.expire_date) or '—'),
            ('الفترة الجديدة المقترحة', (self.new_start_date and self.new_expire_date)
                and ('%s ← %s' % (self.new_start_date, self.new_expire_date)) or '—'),
            ('القيمة الجديدة', self.new_value and ('%s %s' % ('{:,.3f}'.format(self.new_value),
                exp.currency_id.name or '')) or '—'),
        ]
        # Build rows as Markup so the final `%` interpolation keeps the <tr>
        # tags (markupsafe escapes plain-str values but preserves Markup ones);
        # k/v are still escaped inside each row via `Markup(tmpl) % (k, v)`.
        tr = Markup('').join(
            Markup(
                '<tr><td style="padding:7px 12px;color:#5a6472;font-size:13px;border-bottom:1px solid #eef1f5;white-space:nowrap;">%s</td>'
                '<td style="padding:7px 12px;color:#1a2330;font-size:13px;font-weight:600;border-bottom:1px solid #eef1f5;">%s</td></tr>'
            ) % (k, v) for k, v in rows)
        return Markup(
            '<div style="max-width:600px;margin:0 auto;font-family:Tajawal,Arial,sans-serif;direction:rtl;text-align:right;border:1px solid #e6e9ef;border-radius:12px;overflow:hidden;">'
            '<div style="background:linear-gradient(135deg,#1e5eff,#0b3ec9);padding:18px 20px;color:#fff;">'
            '<div style="font-size:12px;opacity:.85;letter-spacing:1px;">إشعار الإدارة العليا · اعتماد تجديد عقد</div>'
            '<div style="font-size:19px;font-weight:800;margin-top:3px;">%(title)s</div></div>'
            '<div style="padding:16px 20px;">'
            '<p style="color:#333;font-size:14px;margin:0 0 12px;">تحية طيبة،<br/>'
            'نرفع لسيادتكم طلب %(kind)s العقد أدناه للعلم والاعتماد. مرفق طيّه <b>طلب الجهة</b> و<b>كتاب موافقتنا</b>.</p>'
            '<table style="width:100%%;border-collapse:collapse;background:#fbfcfe;border:1px solid #eef1f5;border-radius:8px;">%(rows)s</table>'
            '<p style="color:#8a93a1;font-size:12px;margin:14px 0 0;">هذه رسالة آلية من نظام إدارة العقود — care. يُرجى اتخاذ اللازم قبل الموعد النهائي.</p>'
            '</div></div>'
        ) % {'title': exp.name or exp.ref or _('عقد'),
             'kind': kind_label, 'rows': tr}

    def action_notify_senior(self):
        """Email senior management with the client request + our approval attached."""
        for r in self:
            users = r.notify_user_ids or r.experience_id.notify_user_ids or r.experience_id.manager_id
            partners = users.mapped('partner_id').filtered('email')
            atts = self.env['ir.attachment']
            for binf, fnf, label in [
                (r.request_attachment, r.request_filename, 'client_request'),
                (r.approval_attachment, r.approval_filename, 'approval_letter')]:
                if binf:
                    atts |= self.env['ir.attachment'].create({
                        'name': fnf or (label + '.pdf'), 'type': 'binary', 'datas': binf,
                        'res_model': r._name, 'res_id': r.id})
            r.message_post(body=r._senior_email_html(), partner_ids=partners.ids,
                           attachment_ids=atts.ids, message_type='notification',
                           subtype_xmlid='mail.mt_comment',
                           subject=_('اعتماد تجديد عقد: %s') % (r.experience_id.name or ''))
            r.write({'state': 'senior_notified', 'senior_notified_date': fields.Date.today()})

    def action_renew_guarantee(self):
        for r in self:
            if not r.guarantee_id:
                raise UserError(_('اربط/أنشئ الكفالة البنكية أولاً.'))
            r.write({'state': 'guarantee',
                     'guarantee_sent_date': r.guarantee_sent_date or fields.Date.today()})

    def action_sign(self):
        """Sign the extension: update the parent contract's dates/value/state."""
        for r in self:
            if not r.new_expire_date:
                raise UserError(_('حدّد نهاية الفترة الجديدة قبل التوقيع.'))
            r.write({'state': 'signed', 'sign_date': r.sign_date or fields.Date.today()})
            exp = r.experience_id
            vals = {'state': 'valid', 'expire_date': r.new_expire_date}
            if r.new_start_date:
                vals['start_date'] = r.new_start_date
            if r.new_value:
                vals['contract_amount'] = r.new_value
            if r.new_contract_attachment:
                att = self.env['ir.attachment'].create({
                    'name': r.new_contract_filename or 'extension_contract.pdf',
                    'type': 'binary', 'datas': r.new_contract_attachment,
                    'res_model': 'care.experience', 'res_id': exp.id})
                vals['contract_copy'] = [(4, att.id)]
            exp.write(vals)
            exp.message_post(body=_('تم توقيع تمديد العقد حتى %s.') % r.new_expire_date)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_deadline_alerts(self):
        """Alert on approaching/overdue deadlines for response / signing."""
        today = fields.Date.today()
        soon = fields.Date.add(today, days=5)
        Act = self.env['mail.activity']  # noqa
        for r in self.search([('state', 'not in', ('signed', 'cancelled'))]):
            checks = [('respond_deadline', r.respond_deadline, 'الرد على طلب الجهة'),
                      ('sign_deadline', r.sign_deadline, 'توقيع عقد التمديد')]
            for _f, dl, label in checks:
                if dl and dl <= soon:
                    users = r.notify_user_ids or r.experience_id.manager_id
                    for u in users:
                        r.activity_schedule(
                            'mail.mail_activity_data_todo',
                            summary=_('موعد نهائي يقترب: %s (%s)') % (label, r.experience_id.name or ''),
                            date_deadline=dl, user_id=u.id)
