from odoo import models, fields, api
from datetime import datetime
from odoo.http import request
from .qr_generator import generateQrCode


class OvertimeRequest(models.Model):
    _name = 'overtime.request'
    _description = 'Overtime Request'

    def get_default_approvers(self):
        return [
            (0, 0, {'sequence': rec.sequence, 'user_id': rec.user_id.id}) for rec in self.env['overtime.approver'].search([])
        ]

    @api.model
    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    project_id = fields.Many2one('project.project', required=True)
    project_manager_id = fields.Many2one('res.users', related='project_id.user_id', required=True)
    request_date = fields.Date('Date', required=True)
    request_line_ids = fields.One2many('overtime.request.line', 'request_id', 'Request Lines')
    state = fields.Selection(selection=[
        ('draft', 'New'), ('submit', 'Submitted'), ('waiting', 'Waiting Approval'),
        ('approve', 'Approved'), ('reject', 'Rejected'), ('cancel', 'Cancel'),
    ], default='draft', tracking=True)
    user_confirmed = fields.Boolean(compute='compute_user_confirmed')
    approval_ids = fields.One2many('overtime.request.approval', 'overtime_request_id', default=get_default_approvers)
    approver_users = fields.Many2many('res.users', compute='compute_approver_users', store=True)
    approver_users_str = fields.Char(compute='compute_approver_users_str', store=True)
    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')

    @api.depends('approver_users')
    def compute_approver_users_str(self):
        for rec in self:
            rec.approver_users_str = ''
            if rec.approver_users:
                rec.approver_users_str = ','.join(rec.approver_users.mapped('email'))

    def compute_user_confirmed(self):
        for rec in self:
            rec.user_confirmed = False
            if rec.approval_ids and rec.approver_users:
                if self.env.uid in rec.approver_users.ids:
                    if rec.approval_ids.filtered(lambda l: l.user_id.id == self.env.uid and l.approved):
                        rec.user_confirmed = True

    @api.depends('approval_ids', 'approval_ids.user_id')
    def compute_approver_users(self):
        for rec in self:
            rec.approver_users = False
            if rec.approval_ids:
                rec.approver_users = [(6, 0, [u.id for u in rec.approval_ids.mapped('user_id')])]

    def name_get(self):
        return [(rec.id, f'{rec.project_id.name}-{rec.request_date}',) for rec in self]

    def button_submit(self):
        self.state = 'submit'

    def button_approve(self):
        self.approval_ids.filtered(lambda l: l.user_id.id == self.env.uid).write({
            'approved': True,
            'date_approved': fields.Datetime.now(),
        })
        if self.approval_ids.filtered(lambda l: not l.approved):
            self.write({'state': 'waiting'})
            return
        self.write({
            'state': 'approve',
        })

    def button_reject(self):
        self.state = 'reject'

    def button_cancel(self):
        self.state = 'cancel'

    def button_draft(self):
        self.state = 'draft'
        self.approval_ids = [(5, 0, 0)]
        self.write({
            'approval_ids': self.get_default_approvers()
        })

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('hr_overtime_compensation.action_overtime_request').id
            menu_id = self.env.ref('hr_overtime_compensation.overtime_request_menu').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'overtime.request', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)


class OvertimeRequestLine(models.Model):
    _name = 'overtime.request.line'
    _description = 'Overtime Request Line'

    def get_default_employee_ids(self):
        manager = self.env.user.employee_id
        return self.env['hr.employee'].sudo().search([('parent_id', '=', manager.id)]).ids

    request_id = fields.Many2one('overtime.request', 'Overtime Request', )
    project_id = fields.Many2one('project.project', related='request_id.project_id')
    employee_ids = fields.Many2many('hr.employee', default=get_default_employee_ids)
    employee_id = fields.Many2one('hr.employee', domain="[('id', 'in', employee_ids)]", string='Name')
    job_title = fields.Char(related='employee_id.job_title', )
    barcode = fields.Char(related='employee_id.barcode', )
    num_hours = fields.Float('Number of Hours', )
    compensation_value = fields.Float('Compensation Value', )
    overtime_reason = fields.Text('Overtime Reason', )


class OvertimeRequestApproval(models.Model):
    _name = 'overtime.request.approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Overtime Request Approval'
    _order = 'sequence'

    overtime_request_id = fields.Many2one('overtime.request')
    sequence = fields.Integer(default=10)
    user_id = fields.Many2one('res.users')
    approved = fields.Boolean()
    date_approved = fields.Datetime(string='Approved Date')

    def send_approve_request(self):
        template = self.env.ref('hr_overtime_compensation.email_template_approve_request_approval')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True, notif_layout='mail.mail_notification_light')
        project = self.overtime_request_id.project_id.name
        self.sudo().activity_schedule(
            'hr_overtime_compensation.mail_act_overtime_request_approval',
            summary='Overtime{} Approve'.format(project),
            note='Overtime {} Approve'.format(project),
            user_id=self.user_id.id)

