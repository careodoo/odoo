from odoo import fields, models, api, _


class Department(models.Model):
    _inherit = 'hr.department'

    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    logo = fields.Binary()
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    allowed_user_ids = fields.Many2many('res.users', compute='compute_allowed_user_ids', store=True)
    has_higher_manager = fields.Boolean(compute='compute_has_higher_manager', store=True)
    higher_manager_access = fields.Boolean()
    is_modifier = fields.Boolean(compute='compute_is_modifier')
    # project
    project_id = fields.Many2one('project.project')
    project_start_date = fields.Date()
    project_end_date = fields.Date()
    project_amount = fields.Float()
    project_social_file = fields.Many2one('hr.social.contracts')
    project_period = fields.Float()
    project_estimated_months = fields.Float(compute='compute_project_estimated_months', store=True)
    # counts
    employee_count = fields.Integer(compute='compute_employee_count')
    vehicle_count = fields.Integer(compute='compute_vehicle_count')
    task_count = fields.Integer(compute='compute_task_count')
    purchase_order_count = fields.Integer(compute='compute_purchase_order_count')
    sale_order_count = fields.Integer(compute='compute_sale_order_count')
    attendance_count = fields.Integer(compute='compute_attendance_count')
    letter_count = fields.Integer(compute='compute_letter_count')
    leave_count = fields.Integer(compute='compute_leave_count')
    shift_count = fields.Integer(compute='compute_shift_count')
    applicant_count = fields.Integer(compute='compute_applicant_count')
    # options
    show_employees = fields.Boolean(default=True)
    show_vehicles = fields.Boolean(default=True)
    show_tasks = fields.Boolean(default=True)
    show_purchase_orders = fields.Boolean(default=True)
    show_sale_orders = fields.Boolean(default=True)
    show_attendances = fields.Boolean(default=True)
    show_letters = fields.Boolean(default=True)
    show_leaves = fields.Boolean(default=True, string='Show Time Off')
    show_shifts = fields.Boolean(default=True)
    show_applicants = fields.Boolean(default=True)

    def compute_is_modifier(self):
        for rec in self:
            rec.is_modifier = False
            if self.env.user.has_group('base.group_erp_manager') or self.env.user.has_group('base.group_system'):
                rec.is_modifier = True

    @api.depends('manager_id')
    def compute_has_higher_manager(self):
        for rec in self:
            rec.has_higher_manager = bool(rec.manager_id.parent_id)

    @api.depends('manager_id', 'higher_manager_access')
    def compute_allowed_user_ids(self):
        for rec in self:
            allowed_users = []
            for user in self.env.ref('base.group_erp_manager').users:
                allowed_users.append(user.id)
            for user in self.env.ref('base.group_system').users:
                allowed_users.append(user.id)
            if rec.manager_id and rec.manager_id.user_id:
                allowed_users.append(rec.manager_id.user_id.id)
            if rec.higher_manager_access and rec.manager_id.parent_id.user_id:
                allowed_users.append(rec.manager_id.parent_id.user_id.id)
            rec.allowed_user_ids = [(6, 0, allowed_users)]

    @api.depends('project_start_date', 'project_end_date')
    def compute_project_estimated_months(self):
        for rec in self:
            rec.project_estimated_months = 0
            if rec.project_start_date and rec.project_end_date:
                rec.project_estimated_months = (rec.project_end_date.year - rec.project_start_date.year) * 12 + rec.project_end_date.month - rec.project_start_date.month

    def compute_employee_count(self):
        for rec in self:
            rec.employee_count = self.env['hr.employee'].search_count([('department_id', '=', rec.id)])

    def button_show_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employees'),
            'res_model': 'hr.employee',
            'view_mode': 'kanban,tree',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_vehicle_count(self):
        for rec in self:
            rec.vehicle_count = self.env['fleet.vehicle'].search_count([('department_id', '=', rec.id)])

    def button_show_vehicles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vehicles'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'kanban,tree',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_task_count(self):
        for rec in self:
            rec.task_count = self.env['project.task'].search_count([('project_id', '=', rec.project_id.id)])

    def button_show_tasks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks'),
            'res_model': 'project.task',
            'view_mode': 'kanban,tree',
            'domain': [('project_id', '=', self.project_id.id)],
        }

    def compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = self.env['purchase.order'].search_count([('department_id', '=', rec.id)])

    def button_show_purchase_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,kanban',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = self.env['sale.order'].search_count([('department_id', '=', rec.id)])

    def button_show_sale_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = self.env['hr.attendance'].search_count([('department_id', '=', rec.id)])

    def button_show_attendances(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendances'),
            'res_model': 'hr.attendance',
            'view_mode': 'tree',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_letter_count(self):
        for rec in self:
            rec.letter_count = self.env['letter.file'].search_count([('department_id', '=', rec.id)])

    def button_show_letters(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Letters'),
            'res_model': 'letter.file',
            'view_mode': 'kanban,tree',
            'domain': [('department_id', '=', self.id)],
        }

    def compute_leave_count(self):
        for rec in self:
            rec.leave_count = self.env['hr.leave'].search_count([('employee_id.department_id', '=', rec.id)])

    def button_show_leaves(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Leaves'),
            'res_model': 'hr.leave',
            'view_mode': 'tree',
            'domain': [('employee_id.department_id', '=', self.id)],
        }

    def compute_shift_count(self):
        for rec in self:
            rec.shift_count = self.env['employee.shift.request'].search_count([
                '|', ('current_department', '=', rec.id), ('new_department', '=', rec.id)
            ])

    def button_show_shifts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shifts'),
            'res_model': 'employee.shift.request',
            'view_mode': 'tree',
            'domain': [
                '|', ('current_department', '=', self.id), ('new_department', '=', self.id)
            ],
        }

    def compute_applicant_count(self):
        for rec in self:
            rec.applicant_count = self.env['hr.applicant'].search_count([('department_id', '=', rec.id)])

    def button_show_applicants(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Applicants'),
            'res_model': 'hr.applicant',
            'view_mode': 'tree',
            'domain': [('department_id', '=', self.id)],
        }
