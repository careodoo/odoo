# -*- coding: utf-8 -*-
"""Lightweight 1:1 chat between people who share a facility or project — so a
cleaner, a supervisor and a project's crew can message each other in-app."""
from odoo import api, fields, models


class CareChatMessage(models.Model):
    _name = 'care.chat.message'
    _description = 'رسالة محادثة'
    _order = 'id desc'

    from_uid = fields.Many2one('res.users', string='من', required=True, index=True, ondelete='cascade')
    to_uid = fields.Many2one('res.users', string='إلى', required=True, index=True, ondelete='cascade')
    body = fields.Text(string='النص')
    # a message may carry a photo or a video instead of (or with) text
    file = fields.Binary(string='مرفق', attachment=True)
    file_name = fields.Char(string='اسم الملف')
    media_type = fields.Selection([('photo', 'صورة'), ('video', 'فيديو')], string='نوع المرفق')
    is_read = fields.Boolean(string='مقروءة', default=False, index=True)
    # a stable pair key so a conversation is easy to fetch regardless of direction
    pair_key = fields.Char(string='مفتاح المحادثة', index=True, compute='_compute_pair', store=True)

    @api.depends('from_uid', 'to_uid')
    def _compute_pair(self):
        for m in self:
            a, b = sorted([m.from_uid.id or 0, m.to_uid.id or 0])
            m.pair_key = '%d-%d' % (a, b)

    @api.model
    def pair_of(self, uid_a, uid_b):
        a, b = sorted([int(uid_a), int(uid_b)])
        return '%d-%d' % (a, b)
