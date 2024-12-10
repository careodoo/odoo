from odoo import fields, models, api
from .qr_generator import generateQrCode
from odoo.http import request
from datetime import datetime


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    barcode = fields.Char()
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    category_id = fields.Many2one('account.asset.category')
    purchase_order_id = fields.Many2one('purchase.order')
    department_id = fields.Many2one('hr.department', tracking=True)
    transfer_ids = fields.One2many('asset.transfer', 'asset_id', string='Transfers')
    image = fields.Binary()

    def validate(self):
        res = super().validate()
        self.barcode = str(int(datetime.now().timestamp()))
        return res

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('care_asset.care_action_account_asset_model_form').id
            menu_id = self.env.ref('care_asset.care_asset_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'account.asset', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    def transfer_asset(self):
        return {
            'name': 'Transfer Asset',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'asset.transfer',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_old_department_id': self.department_id.id,
            }
        }

    def button_print_label(self):
        wizard = self.env['account.asset.report'].create({
            'line_ids': [(0, 0, {
                'asset_id': self.id,
            })]
        })
        xml_id, data = wizard._prepare_report_data()
        report_action = self.env.ref(xml_id).report_action(None, data=data)
        report_action.update({'close_on_report_download': True})
        return report_action

