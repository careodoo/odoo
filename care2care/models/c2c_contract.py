# -*- coding: utf-8 -*-
"""CARE 2 CARE long-term / contract requests: a customer requests an ongoing
service, we send a price quote, and on approval we convert them into a CAFM
facilities-management client — bridging the storefront to CAFM."""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class C2CContractRequest(models.Model):
    _name = 'c2c.contract.request'
    _description = 'CARE 2 CARE Contract Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'c2c.team.notify.mixin']
    _order = 'create_date desc, id desc'
    _notify_setting_field = 'contract_notify_user_ids'
    _notify_action_prefix = 'c2c/contract'

    name = fields.Char(string='رقم الطلب', default='/', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل',
                                 default=lambda s: s.env.user.partner_id if not s.env.user._is_public() else False)
    customer_name = fields.Char(string='الاسم', required=True)
    phone = fields.Char(string='الهاتف', required=True)
    email = fields.Char(string='البريد')
    category_id = fields.Many2one('c2c.category', string='مجال الخدمة')
    service_id = fields.Many2one('c2c.service', string='الخدمة')
    title = fields.Char(string='عنوان الطلب', required=True)
    description = fields.Text(string='وصف الاحتياج')
    audience = fields.Selection([('home', 'منزل'), ('company', 'شركة/منشأة')], string='الجهة', default='company')
    site_address = fields.Char(string='الموقع/العنوان')
    duration_months = fields.Integer(string='المدة (أشهر)', default=12)
    sector = fields.Char(string='القطاع/النشاط')
    budget_range = fields.Char(string='الميزانية التقديرية')
    preferred_time = fields.Char(string='الوقت المفضّل للتواصل')
    option_ids = fields.Many2many('c2c.rfq.option', string='الخيارات المطلوبة')
    # quote
    quote_amount = fields.Float(string='قيمة العرض')
    quote_period = fields.Selection([('once', 'إجمالي'), ('monthly', 'شهري'), ('yearly', 'سنوي')],
                                    string='دورية العرض', default='monthly')
    quote_note = fields.Text(string='تفاصيل العرض')
    state = fields.Selection([
        ('new', 'جديد'), ('reviewing', 'قيد الدراسة'), ('quoted', 'أُرسل عرض السعر'),
        ('approved', 'موافَق عليه'), ('converted', 'محوّل لعميل CAFM'), ('rejected', 'مرفوض'),
    ], string='الحالة', default='new', required=True, tracking=True)
    cafm_client_id = fields.Integer(string='معرّف عميل CAFM', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', '/') == '/':
                v['name'] = self.env['ir.sequence'].next_by_code('c2c.contract.request') or _('طلب تعاقد')
        recs = super().create(vals_list)
        # a sales lead just landed — it must reach someone, so raise a To-Do too
        for r in recs:
            r._notify_team(_('📄 طلب تعاقد جديد'),
                           _('طلب تعاقد جديد %s: %s من %s (%s)%s') % (
                               r.name or '', r.title or '', r.customer_name or '',
                               r.phone or '', (' — %s' % r.category_id.name) if r.category_id else ''),
                           activity=True)
        return recs

    def action_send_quote(self):
        for r in self:
            if not r.quote_amount:
                raise UserError(_('أدخل قيمة العرض أولاً.'))
            r.state = 'quoted'
            r.message_post(body=_('📄 أُرسل عرض سعر: %.2f (%s)') % (r.quote_amount, dict(r._fields['quote_period'].selection).get(r.quote_period)))

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_convert_to_cafm(self):
        """On approval, turn the requester into a CAFM client."""
        for r in self:
            if r.state not in ('approved', 'quoted'):
                raise UserError(_('يُحوَّل الطلب بعد الموافقة على العرض.'))
            partner = r.partner_id
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': r.customer_name, 'phone': r.phone, 'email': r.email or False,
                    'company_type': 'company' if r.audience == 'company' else 'person',
                })
                r.partner_id = partner.id
            # flag as CAFM client + create the CAFM client record if the model exists
            if 'is_cafm_client' in partner._fields:
                partner.sudo().is_cafm_client = True
            if 'care.cafm.client' in self.env:
                existing = self.env['care.cafm.client'].sudo().search([('partner_id', '=', partner.id)], limit=1)
                client = existing or self.env['care.cafm.client'].sudo().create({
                    'name': partner.name, 'partner_id': partner.id,
                })
                r.cafm_client_id = client.id
            r.state = 'converted'
            r.message_post(body=_('✅ تم تحويل العميل إلى نظام إدارة المرافق (CAFM).'))
        return True


class C2CRfqOption(models.Model):
    """Admin-addable options that appear in the app's "request a quote" form —
    the client picks which extras/services their quote should cover."""
    _name = 'c2c.rfq.option'
    _description = 'CARE 2 CARE RFQ Option'
    _order = 'sequence, id'

    name = fields.Char(string='الخيار', required=True, translate=True)
    description = fields.Char(string='وصف مختصر', translate=True)
    icon = fields.Char(string='أيقونة', default='✅')
    category_id = fields.Many2one('c2c.category', string='ضمن مجال (اختياري)')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
