# -*- coding: utf-8 -*-
"""لوحة خدمات إدارة المرافق: بطاقات أيقونات لكل خدمة متخصّصة (صف السيارات،
مكافحة الحشرات، المسابح، خزّانات المياه، التعقيم، الضيافة، مناولة المواد …)
تفتح فعل الخدمة عند الضغط. تُخزَّن مرجعية الفعل كنصّ (action_xmlid) وتُحلّ وقت
التشغيل، فلا حاجة لاعتماد care_cafm على وحدات الخدمات (عكس اتجاه الاعتماد)."""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CafmServiceLauncher(models.Model):
    _name = 'cafm.service.launcher'
    _description = 'CAFM Service Launcher'
    _order = 'sequence, id'

    name = fields.Char(string='الخدمة', required=True, translate=True)
    subtitle = fields.Char(string='الوصف', translate=True)
    icon = fields.Char(string='الأيقونة', default='fa-th-large',
                       help='صنف FontAwesome، مثل fa-car')
    color = fields.Char(string='اللون', default='#C0392B')
    sequence = fields.Integer(default=10)
    action_xmlid = fields.Char(string='مرجع الفعل (XML ID)')
    active = fields.Boolean(default=True)
    installed = fields.Boolean(string='مثبّتة', compute='_compute_meta')
    count = fields.Integer(string='عدد السجلات', compute='_compute_meta')

    def _resolve(self):
        self.ensure_one()
        if not self.action_xmlid:
            return None
        return self.env.ref(self.action_xmlid, raise_if_not_found=False)

    @api.depends('action_xmlid')
    def _compute_meta(self):
        for r in self:
            act = r._resolve()
            r.installed = bool(act)
            r.count = 0
            try:
                if act and act._name == 'ir.actions.act_window' and act.res_model and act.res_model in self.env:
                    r.count = self.env[act.res_model].sudo().search_count([])
            except Exception:
                r.count = 0

    def open_service(self):
        """يفتح فعل الخدمة المرتبط (يُحلّ الـ xmlid وقت التشغيل)."""
        self.ensure_one()
        act = self._resolve()
        if not act:
            raise UserError(_('هذه الخدمة غير مثبّتة على النظام حالياً.'))
        return self.env['ir.actions.act_window']._for_xml_id(self.action_xmlid)
