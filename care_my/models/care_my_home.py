# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CareMyHome(models.TransientModel):
    _name = 'care.my.home'
    _description = 'My Home Dashboard'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_name = fields.Char(related='employee_id.name')
    image_1920 = fields.Image(related='employee_id.image_1920')
    job_title = fields.Char(related='employee_id.job_title')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    barcode = fields.Char(related='employee_id.barcode')
    worker_status = fields.Selection(related='employee_id.worker_status')

    leaves_count = fields.Integer(compute='_compute_counts')
    permissions_count = fields.Integer(compute='_compute_counts')
    loans_count = fields.Integer(compute='_compute_counts')
    custody_count = fields.Integer(compute='_compute_counts')
    attendance_days = fields.Integer(compute='_compute_counts')
    bonus_total = fields.Monetary(compute='_compute_counts', currency_field='currency_id')
    penalty_total = fields.Monetary(compute='_compute_counts', currency_field='currency_id')
    perf_score_ytd = fields.Float(compute='_compute_counts', string='الأداء (السنة)')
    my_tasks_count = fields.Integer(compute='_compute_counts', string='مهامي المفتوحة')
    doc_expiry_next = fields.Date(compute='_compute_counts', string='أقرب انتهاء مستند')
    doc_expiry_days = fields.Integer(compute='_compute_counts', string='أيام حتى الانتهاء')
    currency_id = fields.Many2one('res.currency', compute='_compute_counts')

    @api.depends('employee_id')
    def _compute_counts(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        for rec in self:
            eid = rec.employee_id.id
            env = rec.env
            rec.currency_id = rec.env.company.currency_id
            if not eid:
                rec.leaves_count = rec.permissions_count = rec.loans_count = 0
                rec.custody_count = rec.attendance_days = 0
                rec.bonus_total = rec.penalty_total = 0.0
                rec.perf_score_ytd = 0.0
                rec.doc_expiry_next = False
                rec.doc_expiry_days = 0
                rec.my_tasks_count = 0
                continue
            uid = rec.employee_id.user_id.id
            rec.my_tasks_count = env['project.task'].sudo().search_count(
                [('user_ids', 'in', [uid]), ('stage_id.fold', '=', False)]) if uid else 0
            year_start = today.replace(month=1, day=1)
            rec.perf_score_ytd = sum(env['care.performance.log'].sudo().search(
                [('employee_id', '=', eid), ('date', '>=', year_start)]).mapped('points'))
            emp = rec.employee_id
            exp = [d for d in [emp.residency_end_date, emp.affairs_permit_end_date,
                               emp.work_permit_expiration_date, emp.visa_expire] if d]
            rec.doc_expiry_next = min(exp) if exp else False
            rec.doc_expiry_days = (rec.doc_expiry_next - today).days if rec.doc_expiry_next else 0
            rec.leaves_count = env['hr.leave'].sudo().search_count([('employee_id', '=', eid)])
            rec.permissions_count = env['permission.request'].sudo().search_count([('employee_id', '=', eid)])
            rec.loans_count = env['hr.loan'].sudo().search_count([('employee_id', '=', eid)])
            rec.custody_count = env['care.custody'].sudo().search_count(
                [('employee_id', '=', eid), ('state', '!=', 'returned')])
            rec.attendance_days = env['hr.attendance'].sudo().search_count(
                [('employee_id', '=', eid), ('check_in', '>=', month_start)])
            rec.bonus_total = sum(env['care.bonus'].sudo().search([('employee_id', '=', eid)]).mapped('amount'))
            rec.penalty_total = sum(env['care.penalty'].sudo().search([('employee_id', '=', eid)]).mapped('amount'))

    @api.model
    def open_my_home(self):
        emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not emp:
            raise UserError(_('لا يوجد ملف موظف مرتبط بحسابك. برجاء التواصل مع الموارد البشرية.'))
        rec = self.create({'employee_id': emp.id})
        return {
            'type': 'ir.actions.act_window',
            'name': _('لوحتي'),
            'res_model': 'care.my.home',
            'res_id': rec.id,
            'view_mode': 'form',
            'views': [(self.env.ref('care_my.view_my_home_form').id, 'form')],
            'target': 'current',
        }
