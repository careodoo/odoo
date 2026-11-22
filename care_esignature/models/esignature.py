# -*- coding: utf-8 -*-
import random
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# خريطة الموديولات ← رمز قصير يظهر داخل السيريال
MODULE_CODES = {
    'care.extra.work': 'XW',
    'care.allowance.payout': 'BD',
    'purchase.request': 'PR',
    'purchase.order': 'PO',
    'c2c.workshop': 'WS',
    'c2c.workshop.wage.request': 'WG',
    'care.penalty': 'PN',
    'care.bonus': 'BN',
    'hr.leave': 'LV',
    'care.eos.request': 'EO',
    'care.loan': 'LN',
    'care.item.request': 'IT',
    'care.gov.custody.request': 'GC',
    'care.suspension.request': 'SP',
    'care.leave.settlement': 'LS',
}


class CareESignature(models.Model):
    _name = 'care.esignature'
    _description = 'Electronic Signature Record'
    _inherit = ['mail.thread']
    _order = 'sign_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='السيريال', required=True, index=True, copy=False, readonly=True,
                       help='سيريال التوقيع الفريد — غير مكرّر.')
    user_id = fields.Many2one('res.users', string='الموقِّع (مستخدم)', required=True, readonly=True,
                              default=lambda s: s.env.user, index=True)
    employee_id = fields.Many2one('hr.employee', string='الموظّف', readonly=True)
    signature = fields.Binary(string='صورة التوقيع', readonly=True, attachment=True,
                              help='لقطة من توقيع المستخدم وقت الاعتماد.')
    signer_name = fields.Char(string='اسم الموقِّع', readonly=True)
    signer_role = fields.Char(string='الصفة', readonly=True, help='صفة الاعتماد: مدير المشروع / الموارد البشرية …')
    signer_role_en = fields.Char(string='الصفة (EN)', readonly=True)
    # التفويض (الإنابة): وقّع المفوَّض إليه بالنيابة عن مفوِّض
    delegated_by_id = fields.Many2one('res.users', string='مفوّض من قبل', readonly=True)
    delegated_by_name = fields.Char(string='اسم المفوِّض', readonly=True)

    model = fields.Char(string='الموديول', required=True, index=True, readonly=True)
    res_id = fields.Integer(string='رقم السجل', required=True, index=True, readonly=True)
    res_ref = fields.Char(string='مرجع السجل', readonly=True, help='اسم/رقم المستند الموقّع.')
    res_model_name = fields.Char(string='نوع المستند', readonly=True)
    module_code = fields.Char(string='رمز الموديول', readonly=True)

    sign_date = fields.Datetime(string='تاريخ ووقت التوقيع', required=True, readonly=True,
                                default=fields.Datetime.now, index=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True,
                                 default=lambda s: s.env.company)
    state = fields.Selection([('valid', 'صحيح'), ('void', 'مُلغى')], string='الحالة',
                             default='valid', tracking=True, readonly=True)

    # رابط التحقّق العام + مصدر صورة QR (QR يرمّز الرابط، فيفتح صفحة التحقّق عند المسح)
    verify_url = fields.Char(string='رابط التحقّق', compute='_compute_verify',
                             help='رابط عام يفتح صفحة التحقّق من هذا التوقيع.')
    qr_src = fields.Char(string='مصدر QR', compute='_compute_verify',
                         help='مصدر صورة الـQR — يرمّز رابط التحقّق العام لا نصّ السيريال.')

    _sql_constraints = [
        ('uniq_serial', 'unique(name)', 'سيريال التوقيع يجب أن يكون فريدًا.'),
    ]

    # ------- توليد السيريال -------
    @api.model
    def _module_code(self, model):
        if model in MODULE_CODES:
            return MODULE_CODES[model]
        parts = [p for p in (model or '').split('.') if p]
        return ((parts[-1][:2]) if parts else 'XX').upper()

    @api.model
    def _gen_serial(self, code, res_id, dt):
        h = ''.join(random.choice('0123456789ABCDEF') for _ in range(4))
        return 'SIG-%s-%s-%s-%05d-%s' % (
            dt.strftime('%Y%m%d'), dt.strftime('%H%M'), code or 'XX', int(res_id or 0), h)

    @api.model
    def _unique_serial(self, code, res_id, dt):
        for _try in range(8):
            serial = self._gen_serial(code, res_id, dt)
            if not self.sudo().search_count([('name', '=', serial)]):
                return serial
        # نادراً جداً: أضف لاحقة إضافية
        return serial + random.choice('0123456789ABCDEF')

    @api.depends('name')
    def _compute_verify(self):
        from werkzeug.urls import url_encode
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        for rec in self:
            url = ('%s/esign/verify/%s' % (base, rec.name)) if rec.name else ''
            rec.verify_url = url
            rec.qr_src = ('/report/barcode?' + url_encode({
                'barcode_type': 'QR', 'value': url, 'width': 120, 'height': 120})) if url else ''

    # ------- توقيع بخلفية شفافة (تفريغ البكسلات شبه البيضاء) -------
    signature_png = fields.Binary(string='توقيع شفاف', compute='_compute_sig_png', store=True,
                                  help='صورة التوقيع بخلفية شفافة (تُستخدم في التقارير بلا مستطيل أبيض).')

    @api.model
    def _transparent_b64(self, b64):
        """يحوّل أي صورة توقيع إلى PNG بخلفية شفافة (البكسلات شبه البيضاء → شفافة). يُرجع base64 أو False."""
        if not b64:
            return False
        import io
        import base64 as _b64
        try:
            from PIL import Image
            raw = _b64.b64decode(b64)
            im = Image.open(io.BytesIO(raw)).convert('RGBA')
            try:
                import numpy as np
                arr = np.array(im)
                white = (arr[:, :, 0] > 225) & (arr[:, :, 1] > 225) & (arr[:, :, 2] > 225)
                arr[white, 3] = 0
                im = Image.fromarray(arr, 'RGBA')
            except Exception:
                im.putdata([(r, g, bl, 0) if (r > 225 and g > 225 and bl > 225) else (r, g, bl, a)
                            for (r, g, bl, a) in im.getdata()])
            out = io.BytesIO()
            im.save(out, 'PNG')
            return _b64.b64encode(out.getvalue())
        except Exception:
            return b64 if isinstance(b64, bytes) else (b64 or '').encode()

    @api.depends('signature')
    def _compute_sig_png(self):
        for rec in self:
            rec.signature_png = rec._transparent_b64(rec.signature)

    @api.model
    def transparent_datauri(self, b64):
        """data-URI لصورة توقيع بخلفية شفافة (للـCEO/البورتال/أي صورة خام). يُرجع '' إن فارغة."""
        clean = self._transparent_b64(b64)
        if not clean:
            return ''
        return 'data:image/png;base64,' + (clean.decode() if isinstance(clean, bytes) else clean)

    @api.model
    def _short_name(self, emp, user=None):
        """الاسم المختصر للتوقيع من ملف الموظف: short_name إن وُجد،
        وإلا أول 3 أسماء من الاسم الكامل، وإلا اسم المستخدم (آخر ملاذ)."""
        if emp:
            sn = (getattr(emp, 'short_name', False) or '').strip()
            if sn:
                return sn
            full = (emp.name or '').strip()
            if full:
                return ' '.join(full.split()[:3])
        return (user and user.name) or ''

    # ------- مسح تواقيع مستند (عند الإلغاء / إعادة لمسودة) -------
    @api.model
    def clear_for(self, model, res_id, roles=None):
        """يحذف تواقيع الاعتماد المسجّلة لهذا المستند.
        يُستدعى عند إلغاء الطلب أو إرجاعه لمسودة — فلا تبقى تواقيع قديمة على نموذجٍ أُعيد فتحه.
        roles: قائمة صفات محدّدة للحذف، أو None لحذف الكلّ."""
        dom = [('model', '=', model), ('res_id', '=', int(res_id or 0))]
        if roles:
            dom.append(('signer_role', 'in', list(roles)))
        recs = self.sudo().search(dom)
        n = len(recs)
        if recs:
            # حذف داخلي مُصرَّح (إرجاع لمسودة/إلغاء) — يتجاوز حارس «سجل التدقيق» بسياق esign_internal
            recs.with_context(esign_internal=True).unlink()
        return n

    # ------- واجهة التوقيع (تُستدعى من الموافقات) -------
    @api.model
    def esign_sign(self, model, res_id, role='', role_en='', user=None):
        """يُنشئ سجل توقيع إلكتروني لمستخدم على مستند، ويعيد السجل.
        idempotent: لا يكرّر توقيع نفس المستخدم بنفس الصفة على نفس المستند."""
        self = self.sudo()
        user = user or self.env.user
        # حوكمة: إن كان التوقيع الإلكتروني معطّلًا لهذا المستخدم، لا نلتقط توقيعًا
        # (التدفّق لا يُفشَل — الصندوق في التقرير يبقى «بانتظار التوقيع»). الغياب الافتراضي = مسموح.
        try:
            if getattr(user, 'esign_disabled', False):
                return self.browse()
        except Exception:
            pass
        emp = user.employee_id
        existing = self.search([('model', '=', model), ('res_id', '=', res_id),
                                ('user_id', '=', user.id), ('signer_role', '=', role or '')], limit=1)
        if existing:
            return existing
        dt = fields.Datetime.now()
        code = self._module_code(model)
        serial = self._unique_serial(code, res_id, dt)
        ref, mname = '', model
        try:
            doc = self.env[model].browse(res_id)
            ref = doc.display_name or ''
            mname = self.env['ir.model']._get(model).name or model
        except Exception:
            pass
        sig_img = user.esign_signature or (emp and getattr(emp, 'esign_signature', False)) or False
        # اكتشاف الإنابة: هل يوقّع هذا المستخدم بالتفويض عن مفوِّض لهذا النوع؟
        delegated_by = False
        try:
            Deleg = self.env.get('care.user.delegation')
            AT = self.env.get('care.approval.type')
            if Deleg is not None and AT is not None:
                atype = AT.sudo().search([('model_name', '=', model)], limit=1)
                if atype:
                    for d in Deleg.sudo().search([('delegate_id', '=', user.id), ('active', '=', True)]):
                        if d.covers_type(atype):
                            delegated_by = d.delegator_id
                            break
        except Exception:
            delegated_by = False
        return self.create({
            'name': serial, 'user_id': user.id, 'employee_id': emp.id if emp else False,
            'signature': sig_img,
            'signer_name': self._short_name(emp, user),
            'signer_role': role or '', 'signer_role_en': role_en or '',
            'delegated_by_id': delegated_by.id if delegated_by else False,
            'delegated_by_name': delegated_by.name if delegated_by else False,
            'model': model, 'res_id': res_id, 'res_ref': ref, 'res_model_name': mname,
            'module_code': code, 'sign_date': dt,
        })

    def action_open_document(self):
        """فتح المستند الموقّع (السجل المصدر) من سجلّ التوقيع."""
        self.ensure_one()
        if not self.model or not self.res_id or self.model not in self.env:
            raise UserError(_('لا يوجد مستند مرتبط بهذا التوقيع.'))
        try:
            rec = self.env[self.model].browse(self.res_id)
            if not rec.exists():
                raise UserError(_('المستند المرتبط لم يعد موجودًا.'))
        except UserError:
            raise
        except Exception:
            raise UserError(_('تعذّر فتح المستند المرتبط.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
            'name': self.res_ref or self.res_model_name or self.model,
        }

    @api.model
    def for_document(self, model, res_id):
        """كل تواقيع مستند (تستخدمها التقارير)."""
        return self.sudo().search([('model', '=', model), ('res_id', '=', res_id), ('state', '=', 'valid')])

    @api.model
    def for_role(self, model, res_id, role):
        """التوقيع الصحيح لصفة معيّنة على مستند — للتقارير، بلا حاجة لتوريث esign.mixin على الموديل.
        يُستدعى من أي تقرير: o.env['care.esignature'].for_role(o._name, o.id, 'الصفة')."""
        if not (model and res_id):
            return self.browse()
        return self.sudo().search([
            ('model', '=', model), ('res_id', '=', res_id),
            ('signer_role', '=', role or ''), ('state', '=', 'valid'),
        ], limit=1)

    # ------- حماية: للقراءة فقط بعد الإنشاء -------
    _MAIL_FIELDS = {'message_follower_ids', 'message_ids', 'message_main_attachment_id',
                    'message_partner_ids', 'activity_ids', 'state'}

    def write(self, vals):
        if not self.env.context.get('esign_internal') and not self.env.su:
            bad = set(vals) - self._MAIL_FIELDS
            if bad:
                raise UserError(_('سجل التوقيع الإلكتروني للقراءة فقط ولا يمكن تعديله بعد إنشائه (%s).')
                                % ', '.join(sorted(bad)))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('esign_internal') and not self.env.user.has_group(
                'care_esignature.group_esign_manager'):
            raise UserError(_('لا يمكن حذف سجلات التوقيع الإلكتروني (سجل تدقيق).'))
        return super().unlink()

    def action_void(self):
        """إلغاء توقيع (لمدير المنظومة فقط) — لا يُحذف بل يُعلَّم."""
        self.sudo().with_context(esign_internal=True).write({'state': 'void'})
        for r in self:
            r.message_post(body=_('تم تعليم التوقيع كمُلغى بواسطة %s') % self.env.user.name)
