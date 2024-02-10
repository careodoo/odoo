from odoo import fields, models, api, _


class ProductUpdateRequest(models.Model):
    _name = 'product.update.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Product Update Request'

    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    line_ids = fields.One2many('product.update.request.line', 'request_id')
    notes = fields.Text()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='draft')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('product.update.request') or _('New')
        result = super(ProductUpdateRequest, self).create(vals)
        return result

    def button_submit(self):
        self.state = 'submitted'
        users = self.env.ref('care_stock.group_product_update_request_approver').users
        for user in users:
            self.sudo().activity_schedule(
                'care_stock.mail_act_product_update_request',
                summary='Product Update Request',
                note='Ask To Approve Product Update Request',
                user_id=user.id)

    def button_approve(self):
        for line in self.line_ids:
            line.product_id.standard_price = line.new_cost
        self.state = 'approved'
        self.sudo().activity_schedule(
            'care_stock.mail_act_product_update_request',
            summary='Product Update Request',
            note=f'Your Product Update Request {self.name} has been Approved',
            user_id=self.create_uid.id)

    def button_reject(self):
        self.state = 'rejected'
        self.sudo().activity_schedule(
            'care_stock.mail_act_product_update_request',
            summary='Product Update Request',
            note=f'Your Product Update Request {self.name} has been Rejected',
            user_id=self.create_uid.id)


class ProductUpdateRequestLine(models.Model):
    _name = 'product.update.request.line'
    _description = 'Product Update Request Line'

    request_id = fields.Many2one('product.update.request')
    product_id = fields.Many2one('product.template', required=True)
    cost = fields.Float()
    new_cost = fields.Float(required=True)
    notes = fields.Text()

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.cost = self.product_id.standard_price
