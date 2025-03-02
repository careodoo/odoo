from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime


class Experience(models.Model):
    _name = 'care.experience'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Experience'
    _order = 'id desc'

    name = fields.Char()
    line_ids = fields.One2many('care.experience.line', 'experience_id')
    partner_id = fields.Many2one('res.partner', string='Organization')
    contract_amount = fields.Float()
    period = fields.Integer(string='Period in Months')
    labor_quantity = fields.Integer()
    start_date = fields.Date()
    expire_date = fields.Date()
    contract_type = fields.Selection(selection=[
        ('government', 'Government'),
        ('commercials', 'Commercials'),
    ])
    kanban_state = fields.Selection(selection=[
        ('normal', 'Normal'),
        ('done', 'Done'),
        ('blocked', 'Blocked'),
    ])
    notes = fields.Text()
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submit', 'Submit'), ('valid', 'Valid'),
                   ('expired', 'Expired')],
        default="draft",
        tracking=True,
    )
    # proposal
    proposal_id = fields.Many2one('proposal.proposal')
    sequence = fields.Char()
    ref = fields.Char(
        compute='compute_ref',
        store=True,
        string='Contract ID',
    )
    contract_copy = fields.Many2many("ir.attachment")
    project_id = fields.Many2one('project.project', string='Project', store=True)
    department_id = fields.Many2one('hr.department', string='Department', store=True)

    @api.depends('contract_type', 'sequence')
    def compute_ref(self):
        for rec in self:
            name = 'CONT'
            if rec.contract_type:
                if rec.contract_type == 'government':
                    name += f'/G'
                else:
                    name += f'/C'
            name += '/' + str(datetime.now().year)
            if rec.sequence:
                name += '/' + rec.sequence
            rec.ref = name

    def button_submit(self):
        if not self.name:
            raise ValidationError("Please add contract name!")
        self.state = 'submit'

    def button_valid(self):
        if not self.name:
            raise ValidationError("Please add contract name!")
        if not self.contract_copy:
            raise ValidationError("Please add contract copy!")
        self.state = 'valid'

    def button_expired(self):
        if not self.name:
            raise ValidationError("Please add contract name!")
        if not self.contract_copy:
            raise ValidationError("Please add contract copy!")
        self.state = 'expired'

    def button_draft(self):
        self.state = 'draft'

    def check_experience_expiration(self):
        experience_ids = self.env['care.experience'].search([])
        for rec in experience_ids:
            if rec.expire_date and rec.expire_date < datetime.now().date():
                rec.state = 'expired'
