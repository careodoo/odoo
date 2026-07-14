# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CareAutomationRule(models.Model):
    _name = 'care.automation.rule'
    _description = 'HR Automation Rule (No-Code)'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Rule', required=True, translate=True)
    category = fields.Selection([
        ('gov', 'حكومي'), ('payroll', 'رواتب'), ('discipline', 'انضباط'),
        ('deploy', 'تشغيل/نشر'), ('welfare', 'رفاهية'), ('other', 'أخرى'),
    ], string='التصنيف', default='other', required=True)
    trigger = fields.Char(string='لقّا (متى)', translate=True)
    condition = fields.Char(string='إذا (الشرط)', translate=True)
    action_desc = fields.Char(string='بقّد (الإجراء)', translate=True)
    enabled = fields.Boolean(string='مفعّلة', default=True)
    cron_id = fields.Many2one('ir.cron', string='الأتمتة الحقيقية',
                              help='الكرون/الإجراء الذي ينفّذ القاعدة فعلياً — تفعيل/إيقاف القاعدة يتحكّم فيه.')
    is_live = fields.Boolean(string='حيّة', compute='_compute_is_live', store=True)
    note = fields.Text(string='ملاحظات')

    @api.depends('cron_id')
    def _compute_is_live(self):
        for r in self:
            r.is_live = bool(r.cron_id)

    def write(self, vals):
        res = super().write(vals)
        if 'enabled' in vals:
            for r in self.filtered('cron_id'):
                if r.cron_id.active != r.enabled:
                    r.cron_id.sudo().active = r.enabled
        return res

    def action_toggle(self):
        for r in self:
            r.enabled = not r.enabled
