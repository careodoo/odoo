# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    esign_signature = fields.Binary(string='التوقيع الإلكتروني', attachment=True,
                                    help='نموذج توقيعك — يُختَم تلقائيًا على اعتماداتك في التقارير.')
    esign_signature_set = fields.Boolean(string='التوقيع مُعرَّف', compute='_compute_esign_signature_set')
    # حوكمة: عند التعطيل لا يستطيع النظام استخدام توقيع هذا المستخدم في الاعتمادات.
    # يُضبط من سجلّ «اعتماد التوقيع الإلكتروني» (care.esign.enrollment).
    esign_disabled = fields.Boolean(string='التوقيع الإلكتروني معطّل', default=False,
                                    help='عند التفعيل: يُمنع ختم توقيع هذا المستخدم على الاعتمادات.')

    @api.depends('esign_signature')
    def _compute_esign_signature_set(self):
        for u in self:
            u.esign_signature_set = bool(u.esign_signature)

    # السماح لكل مستخدم بقراءة/تعيين توقيعه الخاص من تفضيلاته
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['esign_signature', 'esign_signature_set']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        # التوقيع الإلكتروني لا يُعدّله أو يحذفه الموظف من ملفه —
        # الصلاحية حصراً لمدير منظومة التواقيع (group_esign_manager).
        return super().SELF_WRITEABLE_FIELDS
