from odoo import fields, models, api


class Tender(models.Model):
    _inherit = 'purchase.tender'

    @api.model
    def create(self, vals):
        res = super(Tender, self).create(vals)
        if vals.get('organization'):
            partner = self.env['res.partner'].browse(vals['organization'])
            if not partner.disable_notification:
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'tender_create'), ('globally_access', '=', False)])
                for sms_template_obj in sms_template_objs:
                    mobile = sms_template_obj._get_partner_mobile(partner)
                    if mobile:
                        sms_template_obj.send_sms_using_template(
                            mobile, sms_template_obj, obj=res)
        return res

    def write(self, vals):
        result = super(Tender, self).write(vals)
        for res in self:
            if not res.partner_id.disable_notification:
                if res and vals.get("state", False) in ['cancelled', 'postponed']:
                    if vals['state'] == 'cancelled':
                        sms_template_objs = self.env["wk.sms.template"].sudo().search(
                            [('condition', '=', 'tender_cancel'),('globally_access','=',False)])
                    else:
                        sms_template_objs = self.env["wk.sms.template"].sudo().search(
                            [('condition', '=', 'tender_postponed'), ('globally_access', '=', False)])
                    for sms_template_obj in sms_template_objs:
                        mobile = sms_template_obj._get_partner_mobile(
                            res.partner_id)
                        if mobile:
                            sms_template_obj.send_sms_using_template(
                                mobile, sms_template_obj, obj=res)
        return result

