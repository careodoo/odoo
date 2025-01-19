from odoo import fields, models, api


class SaleSign(models.Model):
    _name = 'sale.sign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sale Sign'
    _rec_name = 'rec_name'
    _order = 'id desc'

    sale_order_id = fields.Many2one('sale.order')
    employee_id = fields.Many2one('hr.employee')
    employee_title = fields.Char(related='employee_id.job_title')
    signature = fields.Binary()
    confirm = fields.Boolean(string='Approved Online')
    date_confirm = fields.Datetime('Confirmation Date')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    rec_name = fields.Char(compute='compute_rec_name', store=True)

    @api.depends('sale_order_id')
    def compute_rec_name(self):
        for rec in self:
            rec.rec_name = ''
            if rec.sale_order_id:
                rec.rec_name = 'Ask to Sign Sale Order {}'.format(rec.sale_order_id.name)

    def send_sign_request(self):
        if self.sale_order_id:
            template = self.env.ref('care_sale.sale_sign_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True,
                                                                    email_layout_xmlid='mail.mail_notification_light')
            self.sudo().activity_schedule(
                'care_sale.mail_act_sale_sign_create',
                summary='Sale Order{} Sign'.format(self.sale_order_id.name),
                note='Sale Order {} Sign'.format(self.sale_order_id.name),
                user_id=self.employee_id.user_id.id)
