from odoo import fields, models, api


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        res = super(MailComposer, self).action_send_mail()
        # Code to send sms to customer of the order.
        context = self.env.context
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')
        obj = self.env[active_model].browse(active_ids)
        if obj:
            if active_model == 'sale.order':
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'sale_mail'), ('globally_access', '=', False)])
            elif active_model == 'purchase.order':
                if obj.state in ['draft', 'sent']:
                    sms_template_objs = self.env["wk.sms.template"].sudo().search(
                        [('condition', '=', 'rfq_mail'), ('globally_access', '=', False)])
                else:
                    sms_template_objs = self.env["wk.sms.template"].sudo().search(
                        [('condition', '=', 'purchase_mail'), ('globally_access', '=', False)])
            else:
                return res
            for sms_template_obj in sms_template_objs:
                for partner in self.partner_ids:
                    mobile = sms_template_obj._get_partner_mobile(partner)
                    if mobile:
                        sms_template_obj.send_sms_using_template(
                            mobile, sms_template_obj, obj=obj)
        return res
