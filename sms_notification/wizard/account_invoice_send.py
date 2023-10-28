from odoo import fields, models, api


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    def send_and_print_action(self):
        res = super(AccountInvoiceSend, self).send_and_print_action()
        context = self.env.context
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')
        obj = self.env[active_model].browse(active_ids)
        if obj:
            sms_template_objs = self.env["wk.sms.template"].sudo().search(
                [('condition', '=', 'sale_invoice_mail'), ('globally_access', '=', False)])
            for sms_template_obj in sms_template_objs:
                for partner in self.partner_ids:
                    mobile = sms_template_obj._get_partner_mobile(partner)
                    if mobile:
                        sms_template_obj.send_sms_using_template(
                            mobile, sms_template_obj, obj=obj)

        return res
