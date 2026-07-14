# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api

# nationality (country code) -> (label, is_rtl, sentence template with {job}/{date})
NATIVE = {
    'NP': ('नेपाली · Nepali', False,
           "कृपया CARE कम्पनीबाट काम छोड्ने मेरो निवेदन स्वीकार गर्नुहोस्। पद: {job}। "
           "मेरो कामको अन्तिम दिन {date} हुनेछ, व्यक्तिगत कारणले।"),
    'BD': ('বাংলা · Bengali', False,
           "অনুগ্রহ করে CARE কোম্পানি থেকে আমার পদত্যাগ গ্রহণ করুন। পদ: {job}। "
           "আমার শেষ কর্মদিবস {date}, ব্যক্তিগত কারণে।"),
    'IN': ('हिन्दी · Hindi', False,
           "कृपया CARE कंपनी से मेरा इस्तीफ़ा स्वीकार करें। पद: {job}। "
           "मेरा अंतिम कार्य दिवस {date} होगा, व्यक्तिगत कारणों से।"),
    'PH': ('Filipino', False,
           "Pakitanggap po ang aking pagbibitiw sa CARE company. Posisyon: {job}. "
           "Ang huli kong araw ng trabaho ay {date}, dahil sa personal na dahilan."),
    'PK': ('اردو · Urdu', True,
           "براہ کرم CARE کمپنی سے میرا استعفیٰ قبول کریں۔ عہدہ: {job}۔ "
           "میرا آخری کام کا دن {date} ہوگا، ذاتی وجوہات کی بنا پر۔"),
    'AF': ('پښتو · Pashto', True,
           "مهرباني وکړئ زما استعفا د CARE له شرکت څخه ومنئ. دنده: {job}. "
           "زما د کار وروستۍ ورځ به {date} وي، د شخصي دلایلو له امله."),
    'KE': ('Kiswahili · Swahili', False,
           "Tafadhali kubali kujiuzulu kwangu kutoka kampuni ya CARE. Cheo: {job}. "
           "Siku yangu ya mwisho ya kazi itakuwa {date}, kwa sababu binafsi."),
}


class HrEmployeeResignation(models.Model):
    _inherit = 'hr.employee.resignation'

    rep_job = fields.Char(compute='_compute_report_data')
    rep_date = fields.Char(compute='_compute_report_data')
    rep_reason_ar = fields.Char(compute='_compute_report_data')
    rep_reason_en = fields.Char(compute='_compute_report_data')
    rep_nationality = fields.Char(compute='_compute_report_data')
    native_label = fields.Char(compute='_compute_report_data')
    native_text = fields.Char(compute='_compute_report_data')
    native_rtl = fields.Boolean(compute='_compute_report_data')
    barcode_src = fields.Char(compute='_compute_codes')
    qr_src = fields.Char(compute='_compute_codes')

    @api.depends('employee_id', 'leave_date', 'reason')
    def _compute_report_data(self):
        for rec in self:
            job = (rec.employee_id.job_id.name or '—')
            d = rec.leave_date.strftime('%d/%m/%Y') if rec.leave_date else '—'
            reason = (rec.reason or '').strip()
            rec.rep_job = job
            rec.rep_date = d
            # keep the current wording when no reason is given
            rec.rep_reason_ar = reason or 'لأسباب خاصة'
            rec.rep_reason_en = reason or 'personal reasons'
            rec.rep_nationality = rec.employee_id.country_id.name or '—'
            code = (rec.employee_id.country_id.code or '').upper()
            data = NATIVE.get(code)
            if data:
                rec.native_label = data[0]
                rec.native_rtl = data[1]
                rec.native_text = data[2].format(job=job, date=d)
            else:
                rec.native_label = False
                rec.native_rtl = False
                rec.native_text = False

    @api.depends('name')
    def _compute_codes(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        IR = self.env['ir.actions.report']
        for rec in self:
            try:
                bc = IR.barcode('Code128', rec.name or 'NEW', width=600, height=110, humanreadable=1)
                rec.barcode_src = 'data:image/png;base64,' + base64.b64encode(bc).decode()
            except Exception:
                rec.barcode_src = False
            url = "%s/web#id=%s&model=hr.employee.resignation&view_type=form" % (base, rec.id)
            try:
                qrimg = IR.barcode('QR', url, width=150, height=150)
                rec.qr_src = 'data:image/png;base64,' + base64.b64encode(qrimg).decode()
            except Exception:
                rec.qr_src = False
