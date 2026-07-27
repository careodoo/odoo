# -*- coding: utf-8 -*-
"""الأوامر الدائمة / تعليمات الموقع (Post Orders / SOP) — معيار مهني في الحراسة:
تعليمات ثابتة لكل موقع (بوابة/دوريات/طوارئ/إبلاغ) يقرؤها الحرّاس ويُقرّون بالاطلاع."""
from odoo import models, fields, api


class SecurityPostOrder(models.Model):
    _name = 'care.security.post.order'
    _description = 'أمر دائم / تعليمات موقع'
    _order = 'sequence, priority desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='العنوان', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='الموقع', tracking=True, index=True)
    category = fields.Selection([
        ('general', 'عام'), ('access', 'الدخول والبوابة'), ('patrol', 'الدوريات'),
        ('emergency', 'الطوارئ'), ('reporting', 'الإبلاغ'), ('safety', 'السلامة'),
    ], string='التصنيف', default='general', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'عادي'), ('1', 'مهم'), ('2', 'حرِج'),
    ], string='الأهمية', default='0', tracking=True)
    body = fields.Html(string='التعليمات')
    sequence = fields.Integer(string='الترتيب', default=10)
    active = fields.Boolean(default=True)
    effective_date = fields.Date(string='ساري من', default=fields.Date.context_today)
    ack_user_ids = fields.Many2many('res.users', 'security_post_order_ack_rel',
                                    'order_id', 'user_id', string='أقرّوا بالاطلاع')
    ack_count = fields.Integer(compute='_compute_ack', string='عدد المُقرّين')

    def _compute_ack(self):
        for r in self:
            r.ack_count = len(r.ack_user_ids)

    def action_acknowledge(self, user=None):
        """تسجيل إقرار الحارس بالاطلاع على الأمر الدائم."""
        u = user or self.env.user
        for r in self:
            if u.id not in r.ack_user_ids.ids:
                r.sudo().ack_user_ids = [(4, u.id)]
        return True
