# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EsignVerify(models.TransientModel):
    """شاشة التحقّق: أدخل سيريالًا فتظهر تفاصيل التوقيع (من/متى/أي مستند)."""
    _name = 'care.esign.verify'
    _description = 'Verify Electronic Signature'

    serial = fields.Char(string='السيريال', required=True)
    result_id = fields.Many2one('care.esignature', string='نتيجة', compute='_compute_result')
    found = fields.Boolean(compute='_compute_result')
    info = fields.Html(compute='_compute_result', string='التفاصيل')

    @api.depends('serial')
    def _compute_result(self):
        for w in self:
            rec = False
            if w.serial:
                rec = self.env['care.esignature'].sudo().search(
                    [('name', '=', (w.serial or '').strip().upper())], limit=1)
            w.result_id = rec.id if rec else False
            w.found = bool(rec)
            if rec:
                w.info = (
                    '<div style="padding:8px;border:1px solid #1c854f;border-radius:8px;background:#e4f4ea">'
                    '<b style="color:#1c854f">✅ توقيع صحيح وموثّق</b><br/>'
                    '<b>الموقِّع:</b> %s — %s<br/>'
                    '<b>التاريخ والوقت:</b> %s<br/>'
                    '<b>الموديول:</b> %s (%s)<br/>'
                    '<b>السجل:</b> %s<br/>'
                    '<b>الحالة:</b> %s</div>'
                ) % (rec.signer_name or '', rec.signer_role or '', rec.sign_date or '',
                     rec.res_model_name or rec.model, rec.model, rec.res_ref or rec.res_id,
                     dict(rec._fields['state'].selection).get(rec.state))
            elif w.serial:
                w.info = ('<div style="padding:8px;border:1px solid #c0392b;border-radius:8px;background:#fbe8ec">'
                          '<b style="color:#c0392b">⚠️ لا يوجد توقيع بهذا السيريال</b> — قد يكون غير صحيح أو مُزوَّرًا.</div>')
            else:
                w.info = False
