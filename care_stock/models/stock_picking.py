from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request


class Picking(models.Model):
    _inherit = 'stock.picking'

    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('stock.view_picking_form').id
            menu_id = self.env.ref('stock.menu_stock_root').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'stock.picking', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)
