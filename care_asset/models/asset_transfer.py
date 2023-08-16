from odoo import fields, models, api
from odoo.exceptions import UserError


class AssetTransfer(models.Model):
    _name = 'asset.transfer'
    _description = 'Asset Transfer'

    def get_default_sign_lines(self):
        return [(0, 0, {'employee_id': rec.user_id.employee_id.id}) for rec in self.env['asset.transfer.approver'].search([])]

    asset_id = fields.Many2one('account.asset')
    old_department_id = fields.Many2one('hr.department')
    new_department_id = fields.Many2one('hr.department', domain="[('id', '!=', old_department_id)]")
    note = fields.Text()
    signature_lines = fields.One2many('purchase.sign', 'asset_transfer_id', default=get_default_sign_lines)
    signature_users = fields.Many2many('res.users', compute='compute_signature_users', store=True)
    user_confirmed = fields.Boolean(compute='compute_user_confirmed')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('sent', 'Sent'), ('confirm', 'Confirm')
    ], default='draft')

    def compute_user_confirmed(self):
        for rec in self:
            rec.user_confirmed = False
            if rec.signature_lines and rec.signature_users:
                if self.env.uid in rec.signature_users.ids:
                    employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
                    if rec.signature_lines.filtered(lambda l: l.employee_id.id == employee.id and l.confirm):
                        rec.user_confirmed = True

    @api.depends('signature_lines')
    def compute_signature_users(self):
        for rec in self:
            rec.signature_users = False
            if rec.signature_lines:
                rec.signature_users = [(6, 0, [u.id for u in rec.signature_lines.mapped('employee_id').mapped('user_id')])]

    def button_request_approval(self):
        if not self.signature_users:
            raise UserError("Ask your admin to configure asset transfer approvers!")
        template = self.env.ref('care_asset.purchase_sign_template_asset_transfer')
        for line in self.signature_lines:
            self.env['mail.template'].browse(template.id).send_mail(
                line.id, force_send=True, notif_layout='mail.mail_notification_light'
            )
            line.sudo().activity_schedule(
                'purchase_report.mail_act_purchase_sign_create',
                summary='Asset Transfer',
                note='Confirm Asset Transfer for {} from {} to {}]'.format(
                    self.asset_id.name, self.old_department_id.name, self.new_department_id.name,
                ),
                user_id=line.employee_id.user_id.id)
        self.write({'state': 'sent'})

    def button_confirm(self):
        self.signature_lines.filtered(lambda l: l.employee_id.user_id.id == self.env.uid).write({
            'confirm': True,
            'date_confirm': fields.Datetime.now(),
        })
        if self.signature_lines.filtered(lambda l: not l.confirm):
            return
        self.asset_id.department_id = self.new_department_id.id
        self.write({'state': 'confirm'})
