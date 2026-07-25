# -*- coding: utf-8 -*-
"""Dashboard delegation.

A project manager hands one of their supervisors the follow-up of a specific
dashboard section (icon) — team, custody, fuel, compliance… — optionally for a
limited time. The supervisor sees what was delegated to them and is notified.
"""
from odoo import api, fields, models


class PmsDelegation(models.Model):
    _name = 'care.pms.delegation'
    _description = 'تفويض متابعة لوحة المشروع'
    _inherit = ['mail.thread']
    _order = 'id desc'

    project_id = fields.Many2one('project.project', string='المشروع', required=True,
                                 index=True, ondelete='cascade', tracking=True)
    section_code = fields.Char(string='القسم (الأيقونة)', required=True, tracking=True)
    section_label = fields.Char(string='اسم القسم')
    delegate_id = fields.Many2one('res.users', string='المشرف المفوَّض', required=True,
                                  index=True, tracking=True)
    granted_by = fields.Many2one('res.users', string='فوّضه', default=lambda s: s.env.user,
                                 tracking=True)
    date_until = fields.Date(string='حتى تاريخ')
    note = fields.Char(string='ملاحظة')
    active = fields.Boolean(default=True)

    # The delegate accepts or declines the follow-up assignment.
    state = fields.Selection([
        ('pending', 'بانتظار القبول'),
        ('accepted', 'مقبول'),
        ('rejected', 'مرفوض'),
    ], string='حالة التفويض', default='pending', tracking=True, index=True)
    response_note = fields.Char(string='رد المفوَّض')
    response_date = fields.Datetime(string='تاريخ الرد', readonly=True)

    def action_accept(self):
        self.write({'state': 'accepted', 'response_date': fields.Datetime.now()})
        for rec in self:
            rec.message_post(body='✅ قَبِل %s تفويض متابعة «%s».'
                             % (rec.delegate_id.name, rec.section_label or rec.section_code))

    def action_reject(self):
        self.write({'state': 'rejected', 'response_date': fields.Datetime.now()})
        for rec in self:
            rec.message_post(body='❌ رَفَض %s تفويض متابعة «%s».'
                             % (rec.delegate_id.name, rec.section_label or rec.section_code))

    @api.model
    def is_active(self, rec):
        if not rec.active:
            return False
        if rec.date_until and rec.date_until < fields.Date.today():
            return False
        return True
