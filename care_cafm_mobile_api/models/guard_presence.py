# -*- coding: utf-8 -*-
"""حالة نشاط الحارس لحظياً: نشط (حركة) / سكون (بلا حركة > 5 دقائق) / نائم (نبض
قلب منخفض + هاتف ساكن) / غير متصل. يُغذّى من نبضات heartbeat من الهاتف (وحقاً
من الساعة الذكية لاحقاً)، ويعرضه المشرف عن فريقه."""
from odoo import api, fields, models


class GuardPresence(models.Model):
    _name = 'care.guard.presence'
    _description = 'حالة نشاط الحارس'
    _order = 'last_seen desc'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='المستخدم', required=True, index=True, ondelete='cascade')
    guard_id = fields.Many2one('security.guard', string='الحارس', ondelete='set null')
    state = fields.Selection([
        ('active', 'نشط'),
        ('idle', 'سكون'),
        ('sleep', 'نائم'),
        ('offline', 'غير متصل'),
    ], string='الحالة', default='offline', index=True)
    last_seen = fields.Datetime(string='آخر ظهور')
    last_motion_at = fields.Datetime(string='آخر حركة')
    heart_rate = fields.Integer(string='نبض القلب')
    phone_still = fields.Boolean(string='الهاتف ساكن')
    battery = fields.Integer(string='البطارية %')

    _sql_constraints = [('user_uniq', 'unique(user_id)', 'حالة واحدة لكل مستخدم.')]

    # عتبات قابلة للضبط
    IDLE_SECONDS = 300     # 5 دقائق بلا حركة → سكون
    OFFLINE_SECONDS = 180  # 3 دقائق بلا نبضة → غير متصل
    SLEEP_HR = 50          # نبض أقل منه (مع سكون الهاتف) → نائم

    def _recompute_state(self):
        now = fields.Datetime.now()
        for r in self:
            if not r.last_seen or (now - r.last_seen).total_seconds() > self.OFFLINE_SECONDS:
                r.state = 'offline'
                continue
            # نائم: نبض منخفض متزامن مع سكون الهاتف
            if r.heart_rate and 0 < r.heart_rate < self.SLEEP_HR and r.phone_still:
                r.state = 'sleep'
                continue
            # سكون: مضى أكثر من 5 دقائق بلا حركة
            if r.last_motion_at and (now - r.last_motion_at).total_seconds() > self.IDLE_SECONDS:
                r.state = 'idle'
                continue
            r.state = 'active'

    @api.model
    def heartbeat(self, user, moving=None, heart_rate=None, still=None, battery=None):
        """نبضة من جهاز المستخدم — تحدّث الحالة وتعيد السجل."""
        now = fields.Datetime.now()
        rec = self.sudo().search([('user_id', '=', user.id)], limit=1)
        guard = self.env['security.guard'].sudo().search([('user_id', '=', user.id)], limit=1)
        vals = {'last_seen': now, 'guard_id': guard.id if guard else False}
        if moving:
            vals['last_motion_at'] = now
        if heart_rate is not None:
            vals['heart_rate'] = int(heart_rate)
        if still is not None:
            vals['phone_still'] = bool(still)
        if battery is not None:
            vals['battery'] = int(battery)
        if rec:
            rec.write(vals)
        else:
            rec = self.sudo().create({'user_id': user.id, **vals})
        rec._recompute_state()
        return rec
