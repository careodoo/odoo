# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CareAccessLearnWizard(models.TransientModel):
    """تعلّم مجموعات المسمّى من مستخدم مرجعي موثوق — بدل اختراع خريطة area→مجموعات.
    يبني خريطة المسمّى→المجموعات من الواقع القائم بنظافة."""
    _name = 'care.access.learn.wizard'
    _description = 'تعلّم مجموعات المسمّى من مستخدم مرجعي'

    role_id = fields.Many2one('care.job.role', string='المسمّى', required=True)
    reference_user_id = fields.Many2one(
        'res.users', string='المستخدم المرجعي', required=True,
        domain=[('share', '=', False)],
        help='مستخدم يؤدّي مهام هذا المسمّى بصلاحيات سليمة — تُنسَخ مجموعاته.')
    exclude_system = fields.Boolean(string='استبعاد مجموعات النظام/التقنية', default=True)
    preview_count = fields.Integer(string='عدد المجموعات المقترحة', compute='_compute_preview')

    def _groups(self):
        g = self.reference_user_id.groups_id
        if self.exclude_system:
            sysg = self.env.ref('base.group_system', raise_if_not_found=False)
            if sysg:
                g = g - sysg
        return g

    @api.depends('reference_user_id', 'exclude_system')
    def _compute_preview(self):
        for w in self:
            w.preview_count = len(w._groups()) if w.reference_user_id else 0

    def action_learn(self):
        self.ensure_one()
        g = self._groups()
        self.role_id.odoo_group_ids = [(6, 0, g.ids)]
        self.env['care.access.audit'].sudo().log(
            'learn', _('مجموعات «%s» تُعلّمت من %s (%s مجموعة)') % (
                self.role_id.name, self.reference_user_id.name, len(g)))
        return {'type': 'ir.actions.act_window', 'res_model': 'care.job.role',
                'res_id': self.role_id.id, 'view_mode': 'form', 'views': [(False, 'form')]}
