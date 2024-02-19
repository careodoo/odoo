from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    reason_id = fields.Many2one('stock.scrap.reason')

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            menu_id = self.env.ref('stock.menu_stock_root').id
            qr_info += '/web#id=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, 'stock.scrap', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)


class StockScrapReason(models.Model):
    _name = 'stock.scrap.reason'

    name = fields.Char(required=True)
