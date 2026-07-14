# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cafm_facility_ids = fields.One2many('care.cafm.facility', 'partner_id', string='مرافق CAFM')
    cafm_facility_count = fields.Integer(compute='_compute_cafm_facility_count', string='المرافق')
    is_cafm_client = fields.Boolean(string='عميل CAFM', index=True, tracking=True,
                                    help='يظهر في قائمة العملاء حتى قبل إضافة أي مرفق.')
    cafm_can_add_workers = fields.Boolean(string='يُسمح للعميل بإضافة عمّال', tracking=True,
                                          help='عند التفعيل يستطيع مستخدمو هذا العميل إضافة عمّال بأنفسهم من التطبيق.')
    cafm_favorite_product_ids = fields.Many2many(
        'product.product', 'cafm_partner_fav_product_rel', 'partner_id', 'product_id',
        string='المنتجات المفضّلة', help='قائمة منتجات يطلبها العميل بشكل متكرر.')
    cafm_shop_product_ids = fields.Many2many(
        'product.product', 'cafm_partner_shop_product_rel', 'partner_id', 'product_id',
        string='منتجات المتجر', help='المنتجات المتاحة في متجر هذا العميل. اتركها فارغة لعرض كل المنتجات.')

    def _compute_cafm_facility_count(self):
        Fac = self.env['care.cafm.facility']
        for p in self:
            p.cafm_facility_count = Fac.search_count([('partner_id', '=', p.id)])

    def action_view_cafm_facilities(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مرافق %s') % self.name,
            'res_model': 'care.cafm.facility',
            'view_mode': 'kanban,tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }


class CafmClientPick(models.TransientModel):
    """Pick an EXISTING contact and register it as a CAFM client, instead of
    re-typing a customer that already lives in Contacts."""
    _name = 'care.cafm.client.pick'
    _description = 'اختيار عميل من جهات الاتصال'

    partner_id = fields.Many2one('res.partner', string='العميل (من جهات الاتصال)', required=True,
                                 help='اختر جهة اتصال موجودة لتسجيلها كعميل.')
    create_facility = fields.Boolean(string='إنشاء مرفق مبدئي', default=False)
    facility_name = fields.Char(string='اسم المرفق')

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id and not self.facility_name:
            self.facility_name = _('مرفق %s') % self.partner_id.name

    def action_confirm(self):
        self.ensure_one()
        self.partner_id.is_cafm_client = True
        if self.create_facility:
            self.env['care.cafm.facility'].create({
                'name': self.facility_name or (_('مرفق %s') % self.partner_id.name),
                'partner_id': self.partner_id.id,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': self.partner_id.name,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
