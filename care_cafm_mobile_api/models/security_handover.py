# -*- coding: utf-8 -*-
"""تسليم/استلام الوردية (Shift Handover) — معيار مهني: عند تغيّر الوردية يسلّم
الحارس المنصرف للحارس المستلِم تقريراً بالوضع العام والمهام المعلّقة والعهدة."""
from odoo import models, fields, api


class SecurityHandover(models.Model):
    _name = 'care.security.handover'
    _description = 'تسليم وردية أمنية'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='المرجع', default='/', readonly=True, copy=False)
    from_user_id = fields.Many2one('res.users', string='المسلِّم', tracking=True,
                                   default=lambda s: s.env.user)
    to_user_id = fields.Many2one('res.users', string='المستلِم', tracking=True)
    premise_id = fields.Many2one('security.premise', string='الموقع', tracking=True, index=True)
    date = fields.Datetime(string='وقت التسليم', default=fields.Datetime.now)
    situation = fields.Text(string='الوضع العام')
    pending = fields.Text(string='مهام معلّقة')
    keys_note = fields.Char(string='العهدة/المفاتيح')
    incidents_note = fields.Text(string='ملاحظات وبلاغات')
    state = fields.Selection([('submitted', 'مُرسَل'), ('acknowledged', 'مُستلَم')],
                             default='submitted', tracking=True)
    ack_date = fields.Datetime(string='وقت الاستلام', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('name') or v['name'] == '/':
                v['name'] = 'HO-%s' % fields.Datetime.now().strftime('%Y%m%d-%H%M%S')
        return super().create(vals_list)

    def action_acknowledge(self, user=None):
        u = user or self.env.user
        self.sudo().write({'state': 'acknowledged', 'to_user_id': u.id,
                           'ack_date': fields.Datetime.now()})
        return True
