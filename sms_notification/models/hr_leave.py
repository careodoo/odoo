from odoo import fields, models, api


class Leave(models.Model):
    _inherit = 'hr.leave'

    partner_id = fields.Many2one('res.partner')

    def action_approve(self):
        res = super(Leave, self).action_approve()
        for rec in self:
            if rec.employee_ids:
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'time_off'), ('globally_access', '=', False)])
                for sms_template_obj in sms_template_objs:
                    for partner in set(self.employee_ids.mapped('user_partner_id')):
                        if not partner.disable_notification:
                            rec.partner_id = partner.id
                            mobile = sms_template_obj._get_partner_mobile(partner)
                            if mobile:
                                sms_template_obj.send_sms_using_template(
                                    mobile, sms_template_obj, obj=rec)
        return res
