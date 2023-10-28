from odoo import fields, models, api
from datetime import date


class FleetContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    sms_notified = fields.Boolean()

    @api.model
    def remind_renew_contract(self):
        contracts = self.env['fleet.vehicle.log.contract'].search([
            ('expiration_date', '!=', False), ('insurer_id', '!=', False), ('sms_notified', '=', False), ('state', 'not in', ['expired', 'closed'])
        ])
        for rec in contracts:
            if not rec.insurer_id.disable_notification:
                if rec.expiration_date.day - date.today().day <= 10:
                    sms_template_objs = self.env["wk.sms.template"].sudo().search(
                        [('condition', '=', 'fleet'), ('globally_access', '=', False)])
                    for sms_template_obj in sms_template_objs:
                        mobile = sms_template_obj._get_partner_mobile(rec.insurer_id)
                        if mobile:
                            sms_template_obj.send_birthday_sms_using_template(
                                mobile, sms_template_obj, obj=rec)
                            rec.sms_notified = True

