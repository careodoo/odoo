# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import datetime

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    _order = 'id desc'

    custody_id    = fields.Many2one('custody', string="Custody", domain=[('is_active', '=', True)])
    total_cost    = fields.Float(string="Total Cost", compute="compute_expected_cost")
    type          = fields.Selection([('service', 'Service'), ('maintenance', 'Maintenance')], string="Type", required=True)
    is_attachment = fields.Boolean(string="Is Attachment", compute='compute_is_attachment')
    next_service_date = fields.Date(string="Next Service Date", required=True)
    is_fire_extinguisher = fields.Boolean(string="Fire Extinguisher")
    damage_line = fields.One2many('fleet.vehicle.log.services.damage', 'service_id', string="Damage Line")
    checks_line = fields.One2many('fleet.vehicle.log.services.checks', 'service_id', string="Checks Line")

    def action_notify_next_service_date(self):
        for record in self:
            if record.next_service_date:
                days = self.env['ir.config_parameter'].sudo().get_param('care.services_next_service_date_notify_reminder') or False
                user = self.env['res.users'].search([('id', '=', 2)])
                date = record.next_service_date - datetime.timedelta(days=int(days))
                today = datetime.date.today()

                if today <= date <= record.next_service_date:
                    record.action_send_notify_by_mails(user)

    def action_send_notify_by_mails(self, users):
        for user in users:
            template_id = self.env.ref('care.notify_next_service_date_template').id
            template = self.env['mail.template'].browse(template_id)
            template.subject = 'Notify Next Service Date For Services (%s)' %(self.name)
            template.email_from = self.env['res.users'].search([('id', '=', 1)]).employee_id.work_email
            template.email_to = user.employee_id.work_email
            template.body_html = """Dear %s,
                                    <br/>
                                    We would like to inform you that Next Service Date (%s) Is Near.
                                    <br/>
                                    <a href="${object.get_base_url()}/mail/view?model=fleet.vehicle.log.services&amp;res_id=%s">View Services (%s)</a>
                                    <br/>
                                    Accept it with the utmost respect. """ %(user.name, self.next_service_date, self.id, self.name)
            template.send_mail(self.id, force_send=True)

    def compute_expected_cost(self):
        for record in self:
            record.total_cost = 0
            for line in record.damage_line:
                record.total_cost += line.cost

    def compute_is_attachment(self):
        for record in self:
            attachments = self.env['ir.attachment'].search([('res_model', '=', 'fleet.vehicle.log.services'), ('res_id', '=', record.id)])
            if attachments:
                record.is_attachment = True
            else:
                record.is_attachment = False


    # @api.onchange('damage_line')
    # def create_activity_plan(self):
    #     activity = self.env['mail.activity.type'].search([('name', '=', 'To Do')]).id
    #     user = self.env.user.id
    #
    #     for line in self.damage_line:
    #         if line.source == 'purchase':
    #             note = 'Please Create Purchase Order For %s' %(line.name)
    #             mail = self.sudo().activity_schedule(str(activity), user_id=user, note=note)
