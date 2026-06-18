from odoo import models, fields, api, _

class SecurityTaskChecklistItem(models.Model):
    _name = 'security.task.checklist.item'
    _description = 'Task Checklist Item'
    _order = 'sequence, id'
    
    name = fields.Char(string='Item', required=True)
    task_id = fields.Many2one('security.task', string='Task', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    is_completed = fields.Boolean(string='Completed', default=False)
    completed_by = fields.Many2one('res.users', string='Completed By', readonly=True)
    completion_date = fields.Datetime(string='Completion Date', readonly=True)
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals_list):
        if not isinstance(vals_tree, list):
            vals_list = [vals_list]
            
        for vals in vals_list:
            # Set sequence based on existing items if not provided
            if not vals.get('sequence') and vals.get('task_id'):
                task = self.env['security.task'].browse(vals['task_id'])
                if task.checklist_item_ids:
                    max_sequence = max(task.checklist_item_ids.mapped('sequence') or [0])
                    vals['sequence'] = max_sequence + 10
                    
        return super(SecurityTaskChecklistItem, self).create(vals_list)
    
    def action_mark_completed(self):
        """Mark checklist item as completed"""
        self.ensure_one()
        if not self.is_completed:
            self.write({
                'is_completed': True,
                'completed_by': self.env.user.id,
                'completion_date': fields.Datetime.now(),
            })
            
            # Update task progress
            self._update_task_progress()
        return True
    
    def action_mark_incomplete(self):
        """Mark checklist item as incomplete"""
        self.ensure_one()
        if self.is_completed:
            self.write({
                'is_completed': False,
                'completed_by': False,
                'completion_date': False,
            })
            
            # Update task progress
            self._update_task_progress()
        return True
    
    def _update_task_progress(self):
        """Update the progress of the parent task based on checklist items"""
        task = self.task_id
        if task and task.checklist_item_ids:
            total_items = len(task.checklist_item_ids)
            completed_items = len(task.checklist_item_ids.filtered(lambda x: x.is_completed))
            
            if total_items > 0:
                progress = int((completed_items / total_items) * 100)
                task.write({'progress': progress})
