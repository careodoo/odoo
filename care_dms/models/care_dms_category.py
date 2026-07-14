# -*- coding: utf-8 -*-
from odoo import fields, models, api


class CareDmsCategory(models.Model):
    """Document classification + retention policy (mockup 90).
    Each category defines how long its documents are kept, who may access
    them, and whether disposal is currently under review."""
    _name = 'care.dms.category'
    _description = 'DMS Category / Retention Policy'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='التصنيف', required=True, translate=True)
    retention_rule = fields.Char(
        string='مدة الاحتفاظ', translate=True,
        help='وصف سياسة الاحتفاظ كما تُعرض (مثال: طوال الخدمة + 5 سنوات).')
    retention_years = fields.Integer(
        string='سنوات الاحتفاظ (للحساب الآلي)', default=0,
        help='عدد السنوات من تاريخ الوثيقة حتى استحقاق الإتلاف. 0 = يدوي/حسب الجهة.')
    access_scope = fields.Char(string='صلاحية الوصول', translate=True)
    state = fields.Selection([
        ('active', 'فعّال'),
        ('review_disposal', 'مراجعة إتلاف'),
    ], string='الحالة', default='active', required=True)
    document_count = fields.Integer(string='العدد', compute='_compute_document_count')
    legal_note = fields.Text(string='الأساس القانوني')

    def _compute_document_count(self):
        Doc = self.env['care.dms.document']
        data = Doc.read_group([('category_id', 'in', self.ids), ('disposed', '=', False)],
                              ['category_id'], ['category_id'])
        counts = {d['category_id'][0]: d['category_id_count'] for d in data}
        for rec in self:
            rec.document_count = counts.get(rec.id, 0)

    def action_open_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': self.name,
            'res_model': 'care.dms.document', 'view_mode': 'kanban,tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
