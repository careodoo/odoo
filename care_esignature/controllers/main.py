# -*- coding: utf-8 -*-
"""صفحة تحقّق عامة من التوقيع الإلكتروني: يفتحها الـQR عند المسح.
تعرض أن هذا السيريال توقيع صحيح يخصّ هذا المستند تحديدًا (اسم النموذج + رقم المرجع
+ تاريخ المستند + تاريخ التوقيع + الموقّع والصفة + الحالة)."""
from odoo import http, fields
from odoo.http import request


class EsignVerifyController(http.Controller):

    @http.route(['/esign/verify/<string:serial>'], type='http', auth='public',
                website=False, sitemap=False, csrf=False)
    def esign_verify(self, serial, **kw):
        serial = (serial or '').strip().upper()
        Sig = request.env['care.esignature'].sudo()
        rec = Sig.search([('name', '=', serial)], limit=1)
        # تاريخ المستند الموقَّع (إن وُجد حقل تاريخ شائع عليه) — لعرضه ضمن بيانات التأكيد
        doc_date = ''
        if rec and rec.model in request.env and rec.res_id:
            try:
                doc = request.env[rec.model].sudo().browse(rec.res_id)
                if doc.exists():
                    for f in ('date', 'request_date', 'create_date', 'date_request',
                              'effective_date', 'date_start', 'approval_date'):
                        if f in doc._fields and doc[f]:
                            doc_date = fields.Date.to_string(doc[f]) if doc._fields[f].type == 'date' \
                                else str(doc[f])[:16]
                            break
            except Exception:
                doc_date = ''
        # صورة التوقيع كـdata-URI بخلفية شفافة (صفحة عامة؛ لا نعتمد على /web/image الذي يحجبه ACL العام)
        img_src = rec.transparent_datauri(rec.signature) if rec else ''
        values = {
            'rec': rec,
            'serial': serial,
            'doc_date': doc_date,
            'img_src': img_src,
            'now': fields.Datetime.now(),
        }
        return request.render('care_esignature.verify_page', values)
