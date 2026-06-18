from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SecurityTaskCategory(models.Model):
    _name = 'security.task.category'
    _description = 'Task Category'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index')

    task_ids = fields.One2many('security.task', 'category_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count', string='Task Count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for category in self:
            category.task_count = len(category.task_ids)


class SecurityTask(models.Model):
    _name = 'security.task'
    _description = 'Security Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, deadline, id desc'



    name = fields.Char(string='Task Title', required=True, tracking=True)
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes')

    # Classification fields
    category_id = fields.Many2one('security.task.category', string='Category', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical')
    ], string='Priority', default='1', tracking=True)

    # Time fields
    start_date = fields.Datetime(string='Start Date', tracking=True)
    end_date = fields.Datetime(string='End Date', tracking=True)
    deadline = fields.Datetime(string='Deadline', tracking=True)
    progress = fields.Float(string='Progress', tracking=True)
    # Assignment fields
    assigned_to = fields.Many2one('security.guard', string='Assigned To', tracking=True, index=True)
    assigned_team_id = fields.Many2one('security.team', string='Assigned Team', tracking=True)

    # Client fields
    client_id = fields.Many2one('security.client', string='Client', required=True, tracking=True)
    premise_id = fields.Many2one('security.premise', string='Premise', tracking=True,
                                domain="[('client_id', '=', client_id or False)]")
    location_id = fields.Many2one('security.location', string='Location', tracking=True)
    contact_id = fields.Many2one('security.contact', string='Contact Person', tracking=True,
                                domain="[('client_id', '=', client_id or False)]")

    # Time fields
    date_created = fields.Datetime(string='Created On', default=fields.Datetime.now, readonly=True)
    deadline = fields.Datetime(string='Deadline', tracking=True)
    date_completed = fields.Datetime(string='Completed On', readonly=True)

    # Status fields
    state = fields.Selection([
        ('new', 'New'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('refused', 'Refused'),
        ('forwarded', 'Forwarded')
    ], string='Status', default='new', tracking=True)

    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')
    ], string='Kanban State', default='normal', tracking=True,
        help="A task's kanban state indicates special situations affecting it:\n"
             " * Grey: Normal state, ready to be started\n"
             " * Green: Task is ready to be completed\n"
             " * Red: Task is blocked or has issues")

    # Additional fields for task management
    delegated_to = fields.Many2one('hr.employee', string='Delegated To', tracking=True)
    refuse_reason = fields.Text(string='Refusal Reason')
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string='Kanban State', default='normal', tracking=True)

    notes = fields.Text(string='Notes')
    color = fields.Integer(string='Color Index')
    subtask_ids = fields.One2many('security.task', 'parent_id', string='Subtasks')
    subtask_count = fields.Integer(compute='_compute_subtask_count', string='Subtasks count')
    parent_id = fields.Many2one('security.task', string='Parent Task')
    task_type_id = fields.Many2one('security.task.type', string='Task Type', tracking=True)
    team_id = fields.Many2one('security.team', string='Team', tracking=True,
                                domain="[('client_id', '=', client_id or False)]")
    planned_date = fields.Datetime(string='Planned Date', tracking=True)
    completion_date = fields.Datetime(string='Completion Date', tracking=True)
    duration = fields.Float(string='Duration', tracking=True)
    checklist_item_ids = fields.One2many('security.task.checklist.item', 'task_id', string='Checklist Items')
    inspection_id = fields.Many2one('security.inspection', string='Inspection', tracking=True)
    
    @api.depends('subtask_ids')
    def _compute_subtask_count(self):
        for task in self:
            task.subtask_count = len(task.subtask_ids)


    @api.onchange('premise_id')
    def _onchange_premise(self):
        if self.premise_id and self.premise_id.client_id != self.client_id:
            self.premise_id = False
            return {'warning': {'title': _('Warning'), 'message': _('Selected premise does not belong to the selected client.')}}

    @api.onchange('client_id')
    def _onchange_client(self):
        if self.client_id and self.premise_id and self.premise_id.client_id != self.client_id:
            self.premise_id = False

    def action_accept(self):
        """Accept the task"""
        self.ensure_one()
        if not self.assigned_to:
            raise UserError(_("Cannot accept a task that is not assigned to an employee"))

        if self.state != 'new':
            raise UserError(_("Only new tasks can be accepted"))

        self.write({
            'state': 'accepted',
            'kanban_state': 'normal',
        })

        # Add activity record
        self.activity_schedule(
            'security_management.mail_activity_task_progress',
            summary=_('Task Progress Update'),
            note=_('Task has been accepted. Please update progress regularly.'),
            deadline=self.deadline.date() if self.deadline else fields.Date.today(),
            user_id=self.assigned_to.user_id.id if self.assigned_to.user_id else self.env.user.id
        )

        return True

    def action_start_progress(self):
        """Mark task as in progress"""
        self.ensure_one()
        if self.state != 'accepted':
            raise UserError(_('Only accepted tasks can be started'))

        self.write({
            'state': 'in_progress',
            'kanban_state': 'normal'
        })
        return True

    def action_complete(self):
        """Complete the task"""
        self.ensure_one()
        if self.state not in ['accepted', 'in_progress']:
            raise UserError(_("Only accepted or in progress tasks can be completed"))

        self.write({
            'state': 'completed',
            'date_completed': fields.Datetime.now(),
            'kanban_state': 'done',
        })

        # Close any activities
        self.activity_feedback(
            ['security_manager.mail_activity_task_progress'],
            feedback=_('Task completed successfully')
        )

        return True

    def action_refuse(self):
        """Open wizard to refuse the task"""
        self.ensure_one()
        if self.state not in ['new']:
            raise UserError(_("Only new tasks can be refused"))

        return {
            'name': _('Refuse Task'),
            'view_mode': 'form',
            'res_model': 'security.task.refuse.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_forward(self):
        """Open wizard to forward the task"""
        self.ensure_one()
        if self.state in ['completed', 'refused']:
            raise UserError(_("Completed or refused tasks cannot be forwarded"))

        return {
            'name': _('Forward Task'),
            'view_mode': 'form',
            'res_model': 'security.task.forward.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_reset_to_new(self):
        """Reset task to new state"""
        self.ensure_one()
        if self.state not in ['refused', 'forwarded']:
            raise UserError(_("Only refused or forwarded tasks can be reset"))

        self.write({
            'state': 'new',
            'delegated_to': False,
            'refuse_reason': False,
            'kanban_state': 'normal',
        })
        return True
    def action_cancel(self):
        """Cancel the task"""
        self.ensure_one()
        if self.state not in ['new', 'accepted', 'in_progress']:
            raise UserError(_("Only new, accepted, or in progress tasks can be cancelled"))

        self.write({
            'state': 'cancelled',
        })
        return True

    def action_view_subtasks(self):
        self.ensure_one()
        return {
            'name': _('Subtasks'),
            'view_mode': 'tree,form',
            'res_model': 'security.task',
            'type': 'ir.actions.act_window',
            'domain': [('parent_id', '=', self.id)],
            'context': {'create': False},
            'target': 'new',
        }

    def action_view_parent(self):
        self.ensure_one()
        return {
            'name': _('Parent Task'),
            'view_mode': 'form',
            'res_model': 'security.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
