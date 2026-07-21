# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup, escape
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TASK_KINDS = [
    ('task', 'Task'),
    ('memo', 'Memo'),
    ('internal_letter', 'Internal Letter'),
    ('internal_request', 'Internal Request'),
    ('correspondence', 'Correspondence'),
]


class ProjectTask(models.Model):
    _inherit = 'project.task'

    task_kind = fields.Selection(TASK_KINDS, string='Kind', default='task', tracking=True, index=True)
    pms_stage_name = fields.Char(related='stage_id.name', store=True, string='الحالة', index=True)
    pms_category_id = fields.Many2one('care.task.category', string='Category', tracking=True, index=True)
    pms_department_id = fields.Many2one('hr.department', string='Department', tracking=True, index=True)
    task_group_id = fields.Many2one('care.task.group', string='Task Group', index=True)

    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True, index=True)

    # ----- forwarding -----
    forward_to_id = fields.Many2one('res.users', string='Forward To')
    forward_from_id = fields.Many2one('res.users', string='Forwarded By', readonly=True)
    forward_state = fields.Selection(
        [('none', 'None'), ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        string='Forward Status', default='none', tracking=True, index=True)
    forward_reason = fields.Text(string='Forward Reason')
    forward_ids = fields.One2many('care.task.forward', 'task_id', string='Forward History')
    forward_count = fields.Integer(compute='_compute_forward_count')
    is_forward_recipient = fields.Boolean(compute='_compute_is_forward_recipient')

    def _compute_is_forward_recipient(self):
        uid = self.env.uid
        for t in self:
            t.is_forward_recipient = bool(t.forward_to_id and t.forward_to_id.id == uid)

    @api.depends('date_deadline', 'stage_id', 'stage_id.fold')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for t in self:
            done = bool(t.stage_id and t.stage_id.fold)
            t.is_overdue = bool(t.date_deadline and t.date_deadline < now and not done)

    @api.depends('forward_ids')
    def _compute_forward_count(self):
        for t in self:
            t.forward_count = len(t.forward_ids)

    # ----- forwarding workflow -----
    def action_request_forward(self):
        for task in self:
            if not task.forward_to_id:
                raise UserError(_('اختر المستخدم الذي تريد الإحالة إليه أولاً.'))
            fwd = self.env['care.task.forward'].create({
                'task_id': task.id,
                'from_user_id': self.env.uid,
                'to_user_id': task.forward_to_id.id,
                'reason': task.forward_reason or '',
                'state': 'pending',
            })
            task.write({'forward_state': 'pending', 'forward_from_id': self.env.uid})
            task._pms_notify(
                task.forward_to_id.partner_id,
                _('طلب إحالة تاسك إليك'),
                _('طلب إحالة تاسك إليك ➡️'),
                _('أحال إليك <b>%s</b> التاسك التالي ويطلب قبولك أو رفضك. تجد كامل التفاصيل أدناه.')
                % self.env.user.name,
                accent='#2f6df6')
        return True

    def action_accept_forward(self):
        for task in self:
            fwd = self.env['care.task.forward'].search(
                [('task_id', '=', task.id), ('state', '=', 'pending')], limit=1)
            if fwd:
                fwd.write({'state': 'accepted', 'response_date': fields.Datetime.now()})
            new_user = task.forward_to_id or (fwd.to_user_id if fwd else False)
            vals = {'forward_state': 'accepted'}
            if new_user:
                vals['user_ids'] = [(6, 0, new_user.ids)]
            task.write(vals)
            if task.forward_from_id:
                task._pms_notify(
                    task.forward_from_id.partner_id,
                    _('تم قبول الإحالة'),
                    _('تم قبول الإحالة ✅'),
                    _('قَبِل <b>%s</b> إحالة التاسك وانتقلت ملكيته إليه.') % self.env.user.name,
                    accent='#1a9f6d')
        return True

    def action_reject_forward(self):
        for task in self:
            fwd = self.env['care.task.forward'].search(
                [('task_id', '=', task.id), ('state', '=', 'pending')], limit=1)
            if fwd:
                fwd.write({'state': 'rejected', 'response_date': fields.Datetime.now(),
                           'response_reason': task.forward_reason or ''})
            task.write({'forward_state': 'rejected'})
            if task.forward_from_id:
                task._pms_notify(
                    task.forward_from_id.partner_id,
                    _('تم رفض الإحالة'),
                    _('تم رفض الإحالة ✖'),
                    _('رفض <b>%s</b> إحالة التاسك. يبقى مسنداً إليك — راجع السبب أدناه.') % self.env.user.name,
                    accent='#e2513f')
        return True

    def action_open_forwards(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('سجل الإحالات'),
            'res_model': 'care.task.forward',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
        }

    def _pms_email_html(self, title, intro, accent='#2f6df6'):
        """Professional, information-rich CARE-branded HTML for task notifications."""
        self.ensure_one()
        base = self.get_base_url()
        url = '%s/web#id=%s&model=project.task&view_type=form' % (base, self.id)
        kind = dict(self._fields['task_kind'].selection).get(self.task_kind, '')
        fwd = dict(self._fields['forward_state'].selection).get(self.forward_state, '')
        prio = 'عالية' if self.priority == '1' else 'عادية'
        assignees = ', '.join(self.user_ids.mapped('name')) if self.user_ids else '—'
        rows = [
            ('التاسك', self.name),
            ('المشروع', self.project_id.name if self.project_id else None),
            ('الإدارة', self.pms_department_id.name if self.pms_department_id else None),
            ('النوع', kind),
            ('البند/الفئة', self.pms_category_id.name if self.pms_category_id else None),
            ('المرحلة', self.stage_id.name if self.stage_id else None),
            ('المسند إليه', assignees),
            ('الأولوية', prio),
            ('تاريخ الاستحقاق', self.date_deadline),
            ('حالة الإحالة', fwd if self.forward_state and self.forward_state != 'none' else None),
            ('أحالها', self.forward_from_id.name if self.forward_from_id else None),
            ('إحالة إلى', self.forward_to_id.name if self.forward_to_id else None),
            ('سبب الإحالة', self.forward_reason),
        ]
        tr = ''
        for label, val in rows:
            if val in (None, False, ''):
                continue
            tr += (
                '<tr><td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#8a93a8;'
                'font-weight:bold;font-size:12px;width:38%%;">%s</td>'
                '<td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#1d2433;'
                'font-weight:bold;font-size:13px;">%s</td></tr>' % (escape(label), escape(val)))
        overdue = ''
        if self.is_overdue:
            overdue = ('<div style="background:#fff4f2;border:1px solid #ffd4cc;color:#c0392b;'
                       'border-radius:8px;padding:10px 14px;font-weight:bold;font-size:13px;margin:0 0 14px;">'
                       '🚨 هذا التاسك تجاوز موعد استحقاقه.</div>')
        return Markup((
            '<div style="max-width:620px;margin:auto;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
            'border:1px solid #e4e8f0;border-radius:14px;overflow:hidden;background:#fff;">'
            '<div style="background:#15213b;padding:16px 22px;">'
            '<span style="color:#f0663c;font-weight:bold;font-size:20px;">CARE</span>'
            '<span style="color:#aeb8cc;font-size:12px;font-weight:bold;"> · إدارة المشاريع والتاسكات</span></div>'
            '<div style="background:%s;height:6px;"></div>'
            '<div style="padding:22px;">%s'
            '<h2 style="margin:0 0 6px;color:#15213b;font-size:19px;">%s</h2>'
            '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 14px;">%s</p>'
            '<table style="width:100%%;border-collapse:collapse;border:1px solid #eef1f6;'
            'border-radius:8px;overflow:hidden;">%s</table>'
            '<div style="text-align:center;margin-top:20px;">'
            '<a href="%s" style="display:inline-block;background:#2f6df6;color:#fff;padding:11px 26px;'
            'border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">فتح التاسك في النظام ←</a></div>'
            '</div>'
            '<div style="background:#f6f8fc;padding:13px 22px;color:#8a93a8;font-size:11px;text-align:center;">'
            'رسالة آلية من نظام إدارة المشاريع · CARE — يرجى عدم الرد على هذا البريد</div>'
            '</div>') % (accent, overdue, title, intro, tr, url))

    def _pms_notify(self, partners, subject, title, intro, accent='#2f6df6'):
        self.ensure_one()
        if not partners:
            return
        try:
            self.with_context(mail_notify_force_send=False).message_post(
                body=self._pms_email_html(title, intro, accent), subject=subject,
                partner_ids=partners.ids, message_type='notification',
                subtype_xmlid='mail.mt_comment', email_layout_xmlid='mail.mail_notification_light')
        except Exception as e:
            _logger.warning('care_pms notify failed (non-fatal): %s', e)

    # ----- crons -----
    def _pms_digest_rows(self, tasks, base_url, days=True):
        """One HTML table row per task, with a per-task open link."""
        now = fields.Datetime.now()
        out = ''
        for t in tasks.sorted(lambda x: (x.priority != '1', x.date_deadline or now)):
            url = '%s/web#id=%s&model=project.task&view_type=form' % (base_url, t.id)
            late_txt = ''
            if days and t.date_deadline:
                d = (now.date() - t.date_deadline).days if hasattr(t.date_deadline, 'day') else 0
                late_txt = ('<span style="color:#c0392b;font-weight:bold;">%s يوم</span>' % d) if d > 0 else '—'
            prio = '🔴' if t.priority == '1' else ''
            out += (
                '<tr>'
                '<td style="padding:8px 12px;border-bottom:1px solid #eef1f6;font-size:13px;color:#1d2433;font-weight:bold;">%s %s</td>'
                '<td style="padding:8px 12px;border-bottom:1px solid #eef1f6;font-size:12px;color:#5b6577;">%s</td>'
                '<td style="padding:8px 12px;border-bottom:1px solid #eef1f6;font-size:12px;color:#5b6577;white-space:nowrap;">%s</td>'
                '<td style="padding:8px 12px;border-bottom:1px solid #eef1f6;font-size:12px;text-align:center;">%s</td>'
                '<td style="padding:8px 12px;border-bottom:1px solid #eef1f6;text-align:center;">'
                '<a href="%s" style="color:#2f6df6;font-weight:bold;font-size:12px;text-decoration:none;">فتح ←</a></td>'
                '</tr>') % (prio, escape(t.name or ''), escape(t.project_id.name or '—'),
                           escape(str(t.date_deadline or '—')), late_txt or '—', url)
        return out

    def _pms_digest_html(self, recipient_name, overdue, pending, base_url):
        """One professional CARE-branded digest listing ALL of a person's
        overdue tasks + pending forwards — sent once a day, not per task."""
        sections = ''
        if overdue:
            sections += (
                '<div style="background:#fff4f2;border:1px solid #ffd4cc;color:#c0392b;border-radius:8px;'
                'padding:10px 14px;font-weight:bold;font-size:13px;margin:0 0 14px;">'
                '🚨 لديك <b>%d</b> تاسك متجاوز موعد استحقاقه.</div>'
                '<table style="width:100%%;border-collapse:collapse;border:1px solid #eef1f6;border-radius:8px;overflow:hidden;">'
                '<tr style="background:#f6f8fc;"><th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">التاسك</th>'
                '<th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">المشروع</th>'
                '<th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">الاستحقاق</th>'
                '<th style="padding:8px 12px;text-align:center;font-size:11px;color:#8a93a8;">التأخّر</th>'
                '<th style="padding:8px 12px;text-align:center;font-size:11px;color:#8a93a8;"></th></tr>'
                '%s</table>') % (len(overdue), self._pms_digest_rows(overdue, base_url))
        if pending:
            sections += (
                '<div style="background:#fff8ec;border:1px solid #ffe1ac;color:#a86400;border-radius:8px;'
                'padding:10px 14px;font-weight:bold;font-size:13px;margin:18px 0 14px;">'
                '⏰ لديك <b>%d</b> طلب إحالة بانتظار قبولك أو رفضك.</div>'
                '<table style="width:100%%;border-collapse:collapse;border:1px solid #eef1f6;border-radius:8px;overflow:hidden;">'
                '<tr style="background:#f6f8fc;"><th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">التاسك</th>'
                '<th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">المشروع</th>'
                '<th style="padding:8px 12px;text-align:right;font-size:11px;color:#8a93a8;">الاستحقاق</th>'
                '<th style="padding:8px 12px;text-align:center;font-size:11px;color:#8a93a8;">التأخّر</th>'
                '<th style="padding:8px 12px;text-align:center;font-size:11px;color:#8a93a8;"></th></tr>'
                '%s</table>') % (len(pending), self._pms_digest_rows(pending, base_url, days=False))
        return Markup((
            '<div style="max-width:640px;margin:auto;font-family:Tahoma,Arial,sans-serif;direction:rtl;'
            'border:1px solid #e4e8f0;border-radius:14px;overflow:hidden;background:#fff;">'
            '<div style="background:#15213b;padding:16px 22px;">'
            '<span style="color:#f0663c;font-weight:bold;font-size:20px;">CARE</span>'
            '<span style="color:#aeb8cc;font-size:12px;font-weight:bold;"> · الملخّص اليومي للتاسكات</span></div>'
            '<div style="background:#e2513f;height:6px;"></div>'
            '<div style="padding:22px;">'
            '<h2 style="margin:0 0 6px;color:#15213b;font-size:19px;">صباح الخير %s</h2>'
            '<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 16px;">هذا ملخّص واحد بكل ما يحتاج انتباهك اليوم — بدل رسالة لكل تاسك.</p>'
            '%s'
            '<div style="text-align:center;margin-top:22px;">'
            '<a href="%s/web#action=&model=project.task&view_type=list" style="display:inline-block;background:#2f6df6;'
            'color:#fff;padding:11px 26px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">فتح كل التاسكات ←</a></div>'
            '</div>'
            '<div style="background:#f6f8fc;padding:13px 22px;color:#8a93a8;font-size:11px;text-align:center;">'
            'ملخّص يومي آلي من نظام إدارة المشاريع · CARE — يُرسل مرة واحدة يوميًا</div>'
            '</div>') % (escape(recipient_name or ''), sections, base_url))

    @api.model
    def cron_pms_escalate_overdue(self):
        """Daily: send ONE consolidated digest per recipient instead of a
        separate email per task (per-task email spam was the pain point)."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        # group overdue tasks by the manager who must act on them
        buckets = {}   # partner -> {'overdue': tasks, 'pending': tasks}
        for task in self.search([('is_overdue', '=', True)]):
            mgr = task.project_id.user_id.partner_id if task.project_id.user_id else False
            if mgr and mgr.email:
                buckets.setdefault(mgr, {'overdue': self.browse(), 'pending': self.browse()})
                buckets[mgr]['overdue'] |= task
        # pending forwards go to the person they wait on
        for task in self.search([('forward_state', '=', 'pending')]):
            p = task.forward_to_id.partner_id if task.forward_to_id else False
            if p and p.email:
                buckets.setdefault(p, {'overdue': self.browse(), 'pending': self.browse()})
                buckets[p]['pending'] |= task
        Mail = self.env['mail.mail'].sudo()
        for partner, data in buckets.items():
            n = len(data['overdue']) + len(data['pending'])
            if not n:
                continue
            subject = _('ملخّصك اليومي: %s بند بحاجة انتباهك') % n
            try:
                Mail.create({
                    'subject': subject,
                    'body_html': self._pms_digest_html(partner.name, data['overdue'], data['pending'], base_url),
                    'email_to': partner.email,
                    'auto_delete': True,
                }).send()
            except Exception as e:
                _logger.warning('care_pms daily digest failed for %s (non-fatal): %s', partner.email, e)
        return True
