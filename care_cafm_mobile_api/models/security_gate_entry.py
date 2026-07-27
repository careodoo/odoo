# -*- coding: utf-8 -*-
"""سجل البوابة الخفيف (Gate Register) — تسجيل سريع للحارس لأي زائر/مركبة/توصيل/
مقاول عند البوابة دون الحاجة لإنشاء تصريح ومُراسل مسبقاً (نماذج التصاريح ثقيلة).
دخول فوري (state=inside) ثم خروج بضغطة (out_time + state=left)."""
from odoo import models, fields, api


class SecurityGateEntry(models.Model):
    _name = 'care.security.gate.entry'
    _description = 'سجل البوابة'
    _order = 'in_time desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='المرجع', default='/', readonly=True, copy=False)
    guard_user_id = fields.Many2one('res.users', string='الحارس المُسجِّل',
                                    default=lambda s: s.env.user, tracking=True)
    premise_id = fields.Many2one('security.premise', string='الموقع', index=True, tracking=True)
    date = fields.Date(string='التاريخ', default=fields.Date.context_today, index=True)

    entry_type = fields.Selection([
        ('visitor', 'زائر'),
        ('vehicle', 'مركبة'),
        ('delivery', 'توصيل'),
        ('contractor', 'مقاول'),
    ], string='النوع', default='visitor', required=True, tracking=True)

    person_name = fields.Char(string='الاسم', tracking=True)
    id_number = fields.Char(string='رقم الهوية')
    phone = fields.Char(string='الهاتف')
    company = fields.Char(string='الجهة/الشركة')
    host_name = fields.Char(string='المُستضيف (لزيارة من؟)')
    purpose = fields.Char(string='الغرض')
    persons_count = fields.Integer(string='عدد الأشخاص', default=1)

    plate = fields.Char(string='رقم اللوحة')
    vehicle_desc = fields.Char(string='وصف المركبة')

    in_time = fields.Datetime(string='وقت الدخول', default=fields.Datetime.now, tracking=True)
    out_time = fields.Datetime(string='وقت الخروج', tracking=True)
    note = fields.Text(string='ملاحظات')
    state = fields.Selection([('inside', 'بالداخل'), ('left', 'غادر')],
                             default='inside', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not v.get('name') or v['name'] == '/':
                v['name'] = 'GE-%s' % fields.Datetime.now().strftime('%Y%m%d-%H%M%S')
        return super().create(vals_list)

    def action_mark_exit(self):
        for r in self:
            if r.state == 'inside':
                r.write({'out_time': fields.Datetime.now(), 'state': 'left'})
