# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseOrderPms(models.Model):
    _inherit = 'purchase.order'

    pms_project_id = fields.Many2one(
        'project.project', string='مشروع الصرف',
        help='المشروع الذي تُرسَل إليه أصناف هذا الطلب وتُسجَّل في سجله.')
    pms_supply_count = fields.Integer(compute='_compute_pms_supply_count')

    def _compute_pms_supply_count(self):
        Supply = self.env['care.pms.supply']
        for order in self:
            order.pms_supply_count = Supply.search_count([('po_id', '=', order.id)])

    def action_pms_send_to_project(self):
        """Send this PO's items to the project manager and record them in the
        project's material log (as an incoming supply, in transit)."""
        Supply = self.env['care.pms.supply']
        created = Supply.browse()
        for order in self:
            if not order.pms_project_id:
                raise UserError(_('اختر «مشروع الصرف» أولاً قبل الإرسال.'))
            line_cmds = []
            for ol in order.order_line:
                if ol.display_type or not ol.product_id:
                    continue
                line_cmds.append((0, 0, {
                    'product_id': ol.product_id.id,
                    'name': ol.product_id.display_name or ol.name,
                    'qty': ol.product_qty,
                    'uom_name': ol.product_uom.name if ol.product_uom else 'وحدة',
                }))
            if not line_cmds:
                raise UserError(_('لا توجد أصناف قابلة للإرسال في هذا الطلب.'))
            created |= Supply.create({
                'project_id': order.pms_project_id.id,
                'source': order.name,
                'po_id': order.id,
                'state': 'sent',
                'line_ids': line_cmds,
            })
        created._notify_project_manager()
        return _pms_open_supply_action(self, created)

    def action_pms_open_supplies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('واردات المشروع'),
            'res_model': 'care.pms.supply', 'view_mode': 'tree,form',
            'domain': [('po_id', '=', self.id)],
        }


class SaleOrderPms(models.Model):
    _inherit = 'sale.order'

    pms_project_id = fields.Many2one(
        'project.project', string='مشروع الصرف',
        help='المشروع الذي تُرسَل إليه أصناف هذا الطلب وتُسجَّل في سجله.')
    pms_supply_count = fields.Integer(compute='_compute_pms_supply_count')

    def _compute_pms_supply_count(self):
        Supply = self.env['care.pms.supply']
        for order in self:
            order.pms_supply_count = Supply.search_count([('so_id', '=', order.id)])

    def action_pms_send_to_project(self):
        Supply = self.env['care.pms.supply']
        created = Supply.browse()
        for order in self:
            if not order.pms_project_id:
                raise UserError(_('اختر «مشروع الصرف» أولاً قبل الإرسال.'))
            line_cmds = []
            for ol in order.order_line:
                if ol.display_type or not ol.product_id:
                    continue
                line_cmds.append((0, 0, {
                    'product_id': ol.product_id.id,
                    'name': ol.product_id.display_name or ol.name,
                    'qty': ol.product_uom_qty,
                    'uom_name': ol.product_uom.name if ol.product_uom else 'وحدة',
                }))
            if not line_cmds:
                raise UserError(_('لا توجد أصناف قابلة للإرسال في هذا الطلب.'))
            created |= Supply.create({
                'project_id': order.pms_project_id.id,
                'source': order.name,
                'so_id': order.id,
                'state': 'sent',
                'line_ids': line_cmds,
            })
        created._notify_project_manager()
        return _pms_open_supply_action(self, created)

    def action_pms_open_supplies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('واردات المشروع'),
            'res_model': 'care.pms.supply', 'view_mode': 'tree,form',
            'domain': [('so_id', '=', self.id)],
        }


def _pms_open_supply_action(env_holder, created):
    if not created:
        return True
    return {
        'type': 'ir.actions.act_window',
        'name': _('واردات المشروع'),
        'res_model': 'care.pms.supply',
        'view_mode': 'form' if len(created) == 1 else 'tree,form',
        'res_id': created.id if len(created) == 1 else False,
        'domain': [('id', 'in', created.ids)],
    }
