# -*- coding: utf-8 -*-
"""Apply Arabic (ar_001) translations for the Letters module, keeping English source."""
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

AR = 'ar_001'

FIELDS = {
    'letter.file': {
        'direction': 'الاتجاه', 'letter_state': 'الحالة', 'classification_id': 'التصنيف',
        'is_confidential': 'سرّي', 'requester_id': 'مُقدّم الطلب', 'signed_by': 'وقّعه',
        'signed_date': 'تاريخ التوقيع', 'delegate_id': 'المندوب', 'delivery_mode': 'نوع التسليم',
        'delegate_handover_date': 'سُلّم للمندوب', 'delivered_date': 'تاريخ التوصيل',
        'receiver_name': 'اسم المستلم', 'receiver_signature': 'توقيع المستلم',
        'receipt_scan': 'صورة الاستلام', 'days_with_delegate': 'أيام مع المندوب',
        'is_overdue': 'متأخّر التسليم', 'response_deadline': 'موعد الرد النهائي',
        'deadline_state': 'حالة المهلة', 'reply_to_id': 'رد على', 'reply_ids': 'الردود',
        'reply_count': 'عدد الردود', 'employee_id': 'الموظف المرتبط', 'gov_file': 'الملف الحكومي',
        'ocr_text': 'نص المسح (OCR)', 'ocr_state': 'حالة القراءة',
        'archive_building': 'مبنى الأرشيف', 'archive_cabinet': 'الخزانة',
        'archive_file': 'الملف الورقي', 'archive_shelf': 'الرف',
        'fee_ids': 'الرسوم الحكومية', 'fee_total': 'إجمالي الرسوم', 'fee_unpaid': 'رسوم غير مدفوعة',
        'name': 'الاسم', 'ref': 'المرجع', 'partner_id': 'الجهة', 'department_id': 'القسم',
        'issue_date': 'تاريخ الإصدار', 'deli_date': 'تاريخ التسليم', 'letter_contain': 'المحتوى',
        'tag_id': 'الوسوم', 'image_letter': 'الصورة الممسوحة',
    },
    'letter.classification': {'name': 'التصنيف', 'code': 'الرمز', 'sequence': 'التسلسل',
                              'color': 'اللون', 'active': 'نشط', 'letter_count': 'عدد الكتب',
                              'default_delivery_mode': 'نوع التسليم الافتراضي'},
    'letter.fee': {'letter_id': 'الكتاب', 'name': 'البيان', 'amount': 'المبلغ (د.ك)',
                   'state': 'الحالة', 'receipt': 'الإيصال', 'paid_date': 'تاريخ الدفع'},
    'letter.template': {'name': 'اسم القالب', 'direction': 'الاتجاه', 'subject': 'الموضوع',
                        'body': 'النص', 'classification_id': 'التصنيف'},
}

SELECTIONS = {
    'letter.file': {
        'direction': {'outgoing': 'صادر', 'incoming': 'وارد'},
        'letter_state': {'draft': 'مسودة', 'to_sign': 'بانتظار التوقيع', 'signed': 'موقّع',
                         'scanned': 'ممسوح', 'with_delegate': 'مع المندوب', 'delivered': 'مُسلَّم',
                         'acknowledged': 'مُستلَم', 'archived': 'مؤرشف'},
        'deadline_state': {'none': 'لا يوجد', 'ok': 'ضمن المهلة', 'due_soon': 'يستحق قريباً',
                           'overdue': 'متأخّر'},
        'ocr_state': {'none': 'بلا مسح', 'pending': 'قيد المعالجة', 'done': 'مفهرس', 'failed': 'فشل'},
        'delivery_mode': {'ack_required': 'يتطلب إقرار استلام', 'no_ack': 'بلا إقرار — أرشفة مباشرة'},
    },
    'letter.classification': {
        'default_delivery_mode': {'ack_required': 'يتطلب إقرار استلام', 'no_ack': 'بلا إقرار — أرشفة مباشرة'},
    },
    'letter.fee': {'state': {'unpaid': 'غير مدفوع', 'paid': 'مدفوع'}},
    'letter.template': {'direction': {'outgoing': 'صادر', 'incoming': 'وارد'}},
}


class LetterI18n(models.AbstractModel):
    _name = 'letter.i18n'
    _description = 'Letters Arabic i18n applier'

    @api.model
    def apply_ar(self):
        # ensure ar_001 active
        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', AR)], limit=1)
        if lang and not lang.active:
            lang.active = True

        Fields = self.env['ir.model.fields']
        for model, fmap in FIELDS.items():
            for fname, label in fmap.items():
                rec = Fields.search([('model', '=', model), ('name', '=', fname)], limit=1)
                if rec:
                    try:
                        rec.with_context(lang=AR).field_description = label
                    except Exception as e:
                        _logger.debug('i18n field %s.%s: %s', model, fname, e)

        for model, smap in SELECTIONS.items():
            for fname, values in smap.items():
                field = Fields.search([('model', '=', model), ('name', '=', fname)], limit=1)
                if not field:
                    continue
                for value, label in values.items():
                    sel = self.env['ir.model.fields.selection'].search(
                        [('field_id', '=', field.id), ('value', '=', value)], limit=1)
                    if sel:
                        try:
                            sel.with_context(lang=AR).name = label
                        except Exception as e:
                            _logger.debug('i18n sel %s.%s.%s: %s', model, fname, value, e)
        # Force-rename the (vendor) Letters app root to Arabic in every language
        menu = self.env.ref('sp_letter_v15.letter_file_parent', raise_if_not_found=False)
        if menu:
            for lng in ('en_US', AR):
                try:
                    menu.with_context(lang=lng).name = 'المراسلات'
                except Exception as e:
                    _logger.debug('menu rename %s: %s', lng, e)

        _logger.info('care_letter: Arabic translations applied')
        return True
