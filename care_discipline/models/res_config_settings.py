# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ===== أفكار المنظومة كخيارات تُفعَّل / تُعطَّل =====
    disc_esign = fields.Boolean(
        string='توقيع إلكتروني لكل مرحلة', default=True,
        help='توقيع المُقدّم/المدير/الموارد البشرية/القانونية إلكترونيًّا على كل خطوة.')
    disc_false_guard = fields.Boolean(
        string='حماية من الشكوى الكيدية (إقرار إلزامي)', default=True,
        help='يلزم مُقدّم الشكوى بالإقرار بصحّة البيانات قبل التقديم.')
    disc_prescription = fields.Boolean(
        string='تطبيق مدّة التقادم', default=True,
        help='لا يجوز الجزاء على واقعة مضى عليها أكثر من المدّة المحدّدة.')
    disc_prescription_days = fields.Integer(string='مدّة التقادم (أيام)', default=90)
    disc_require_defense = fields.Boolean(
        string='حق الدفاع إلزامي', default=True,
        help='يجب تدوين أقوال العامل قبل التحويل للإدارة القانونية.')
    disc_require_law_article = fields.Boolean(
        string='السند القانوني إلزامي', default=True,
        help='يجب ربط القرار بمادة من قانون العمل الكويتي.')
    disc_auto_integration = fields.Boolean(
        string='إنشاء الخصم/الإيقاف تلقائيًّا', default=True,
        help='عند التطبيق يُنشَأ سجل الخصم أو الإيقاف في الموديول المناسب.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    disc_esign = fields.Boolean(related='company_id.disc_esign', readonly=False)
    disc_false_guard = fields.Boolean(related='company_id.disc_false_guard', readonly=False)
    disc_prescription = fields.Boolean(related='company_id.disc_prescription', readonly=False)
    disc_prescription_days = fields.Integer(related='company_id.disc_prescription_days', readonly=False)
    disc_require_defense = fields.Boolean(related='company_id.disc_require_defense', readonly=False)
    disc_require_law_article = fields.Boolean(related='company_id.disc_require_law_article', readonly=False)
    disc_auto_integration = fields.Boolean(related='company_id.disc_auto_integration', readonly=False)
