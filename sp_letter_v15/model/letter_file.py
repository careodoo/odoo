from odoo import api, fields, models, tools, _
from datetime import date


class LetterFile(models.Model):
    _name='letter.file'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name=fields.Char('Name')
    ref=fields.Char('Reference')
    tag_id=fields.Many2many('multi.tag',string='Tags')
    partner_id=fields.Many2one('res.partner',string='Contact')
    department_id=fields.Many2one('hr.department',string='Department')
    issue_date=fields.Date('issue Date')
    deli_date=fields.Date('Deliver Date')
    letter_contain=fields.Text('Letter Contain')
    out_going_stage=fields.Many2one('outgoing.stage',string='Stage')
    image_letter=fields.Binary('Image')
    kanban_state = fields.Selection([('normal', 'Normal'), ('done', 'Done'),('blocked', 'Blocked')])
    color = fields.Integer('Color')

    @api.model
    def create(self, vals):
        res=super(LetterFile,self).create(vals)
        todays_date = date.today()
        res.ref= 'Care' + '/' + str(todays_date.year) +'/' + str(todays_date.month) +'/' + str(res.id)
        return res

class MultiTag(models.Model):
    _name='multi.tag'

    name=fields.Char('Name')
    color=fields.Integer('Color')


class Outgoingstage(models.Model):
    _name='outgoing.stage'

    name=fields.Char('Stage Name')

