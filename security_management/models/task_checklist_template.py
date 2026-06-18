from odoo import models, fields, api, _

class SecurityTaskChecklistTemplate(models.Model):
    _name = 'security.task.checklist.template'
    _description = 'Task Checklist Template'
    _order = 'sequence, id'
    
    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    task_type_id = fields.Many2one('security.task.type', string='Task Type', 
                                  required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        groups='base.group_multi_company',
        help='Company this template belongs to'
    )
    item_ids = fields.One2many('security.task.checklist.template.item', 'template_id', string='Checklist Items')
    item_count = fields.Integer(string='Number of Items', compute='_compute_item_count')
    
    @api.depends('item_ids')
    def _compute_item_count(self):
        for template in self:
            template.item_count = len(template.item_ids)
    
    def create_checklist_items(self, task_id):
        """Create checklist items based on this template for the given task"""
        self.ensure_one()
        items = []
        for template_item in self.item_ids:
            items.append(template_item.create_checklist_item(task_id))
        return items


class SecurityTaskChecklistTemplateItem(models.Model):
    _name = 'security.task.checklist.template.item'
    _description = 'Task Checklist Template Item'
    _order = 'sequence, id'
    
    name = fields.Char(string='Item Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    template_id = fields.Many2one('security.task.checklist.template', string='Template', 
                                 required=True, ondelete='cascade')
    is_required = fields.Boolean(string='Required', default=False,
                               help='If checked, this item must be completed for the task to be considered done')
    
    def create_checklist_item(self, task_id):
        """Create a checklist item based on this template for the given task"""
        self.ensure_one()
        return self.env['security.task.checklist.item'].create({
            'name': self.name,
            'task_id': task_id,
            'sequence': self.sequence,
            'notes': self.description,
        })
