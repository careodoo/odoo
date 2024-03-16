from odoo import fields, models, api, _
from datetime import datetime
from .qr_generator import generateQrCode
from odoo.http import request
from odoo.exceptions import ValidationError


class Leave(models.Model):
    _inherit = 'hr.leave'

    def generate_barcode(self):
        return str(int(datetime.now().timestamp()))

    barcode = fields.Char(default=generate_barcode)
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_url = fields.Char("QR Code", compute='_generate_qr_code')
    original_return_date = fields.Date()
    hr_department_id = fields.Many2one('hr.department', string='Department')
    hr_employee_id = fields.Many2one('hr.employee', string='Employee', domain="[('department_id', '=', hr_department_id)]")
    leave_return_ids = fields.One2many('hr.action.leave.return', 'last_leave_id')
    leave_return_count = fields.Integer(compute='compute_leave_return_count', store=True)
    returned = fields.Selection(selection=[('1', 'Returned'), ('0', 'Not Returned')], compute='has_returned', store=True)

    @api.depends('leave_return_ids.state')
    def has_returned(self):
        for rec in self:
            rec.returned = '0'
            if rec.leave_return_ids:
                if rec.leave_return_ids[0].state == 'approved':
                    rec.returned = '1'

    @api.depends('leave_return_ids')
    def compute_leave_return_count(self):
        for rec in self:
            rec.leave_return_count = len(rec.leave_return_ids or [])

    def action_view_leave_return(self):
        return {
            'name': _('Leave Return'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'hr.action.leave.return',
            'domain': [('last_leave_id', '=', self.id)],
            'target': 'current',
        }


    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        if self.env.context.get('leave_skip_state_check') or self.env.user.has_group('care_hr.group_hr_leave_return_approver'):
            return
        for holiday in self:
            if holiday.state in ['cancel', 'refuse', 'validate1', 'validate']:
                raise ValidationError(_("This modification is not allowed in the current state."))

    def _generate_qr_code(self):
        for rec in self:
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('hr_holidays.hr_leave_view_form_manager').id
            menu_id = self.env.ref('hr_holidays.menu_open_department_leave_approve').id
            qr_info += '/web#id=%s&action=%s&model=%s&view_type=form&cids=&menu_id=%s' % (rec.id, action_id, 'hr.leave', menu_id)
            rec.qr_url = qr_info
            rec.qr_image = generateQrCode.generate_qr_code(qr_info)

    @api.onchange('hr_employee_id')
    def onchange_hr_employee_id(self):
        self.employee_id = self.hr_employee_id.id
        self.employee_ids = [(6, 0, self.hr_employee_id.ids)]
