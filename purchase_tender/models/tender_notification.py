from odoo import _, api, fields, models

# Notification types that can have their own independent recipient list.
TENDER_NOTIFY_TYPES = [
    ('new', 'مناقصة جديدة'),
    ('status', 'تغيير الحالة'),
    ('date', 'تغيير التاريخ'),
    ('closing', 'قرب الإغلاق'),
    ('guarantee', 'الضمان البنكي'),
    ('digest', 'الملخص الدوري'),
    ('watchlist', 'قائمة المتابعة'),
    ('new_entrants', 'منافسون جدد'),
]


class TenderNotificationRecipient(models.Model):
    """Independent recipient list per notification type. When a row exists for
    a given type, ONLY its users receive that notification (overriding the
    group/follower based default); otherwise the legacy default is used."""

    _name = 'purchase.tender.notify.line'
    _description = 'Tender Notification Recipients (per type)'
    _inherit = ['mail.thread']
    _order = 'notify_type'
    _rec_name = 'notify_type'

    notify_type = fields.Selection(
        TENDER_NOTIFY_TYPES, string='نوع الإشعار', required=True, index=True, tracking=True)
    user_ids = fields.Many2many('res.users', string='المستخدمون', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, tracking=True)

    _sql_constraints = [
        ('uniq_type_company', 'unique(notify_type, company_id)',
         'لا يمكن تكرار نوع الإشعار لنفس الشركة.'),
    ]

    @api.depends('notify_type')
    def _compute_display_name(self):
        labels = dict(TENDER_NOTIFY_TYPES)
        for rec in self:
            rec.display_name = labels.get(rec.notify_type, rec.notify_type or '')
