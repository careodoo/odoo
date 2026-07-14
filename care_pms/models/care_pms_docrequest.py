# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, models, _


class CarePmsDocRequest(models.Model):
    _name = 'care.pms.doc.request'
    _description = 'Employee Document Update Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    doc_type = fields.Selection(
        [('civil_id', 'Civil ID'), ('passport', 'Passport'), ('photo', 'Photo'),
         ('work_permit', 'Work Permit'), ('residence', 'Residence (Iqama)'),
         ('medical', 'Medical'), ('other', 'Other')],
        string='Document Type', required=True, default='civil_id', tracking=True)
    attachment = fields.Binary(string='Document Image')
    attachment_name = fields.Char(string='File Name')
    description = fields.Text(string='Notes')
    requested_by = fields.Many2one('res.users', string='Requested By',
                                   default=lambda s: s.env.user, tracking=True)
    approver_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.pms.doc.request') or '/'
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for req in self:
            # attach the document to the employee record (updates the file)
            if req.attachment:
                self.env['ir.attachment'].create({
                    'name': req.attachment_name or ('%s - %s' % (req.employee_id.name, req.doc_type)),
                    'datas': req.attachment,
                    'res_model': 'hr.employee',
                    'res_id': req.employee_id.id,
                })
                req.employee_id.message_post(
                    body=_('تم تحديث مستند «%s» عبر طلب %s.')
                    % (dict(req._fields['doc_type'].selection).get(req.doc_type, req.doc_type), req.name),
                    attachment_ids=[])
            req.write({'state': 'approved', 'approver_id': self.env.uid})
        return True

    def action_reject(self):
        self.write({'state': 'rejected', 'approver_id': self.env.uid})
