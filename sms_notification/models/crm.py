from odoo import fields, models, api


class Lead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        leads = super(Lead, self).create(vals_list)
        for vals in vals_list:
            if vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if not partner.disable_notification:
                    sms_template_objs = self.env["wk.sms.template"].sudo().search(
                        [('condition', '=', 'crm'), ('globally_access', '=', False)])
                    for sms_template_obj in sms_template_objs:
                        mobile = sms_template_obj._get_partner_mobile(partner)
                        if mobile:
                            sms_template_obj.send_sms_using_template(
                                mobile, sms_template_obj, obj=leads)
        return leads
