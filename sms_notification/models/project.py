from odoo import fields, models, api
from datetime import datetime, date


class Task(models.Model):
    _inherit = 'project.task'

    task_partner_id = fields.Many2one('res.partner')
    sms_notified = fields.Boolean()

    @api.model
    def create(self, vals):
        tasks = super(Task, self).create(vals)
        if vals.get('user_ids'):
            sms_template_objs = self.env["wk.sms.template"].sudo().search(
                [('condition', '=', 'project'), ('globally_access', '=', False)])
            for sms_template_obj in sms_template_objs:
                for user_id in tasks.user_ids:
                    partner = user_id.partner_id
                    if not partner.disable_notification:
                        # send sms
                        tasks.task_partner_id = partner.id
                        mobile = sms_template_obj._get_partner_mobile(partner)
                        if mobile:
                            sms_template_obj.send_task_sms_using_template(
                                mobile, sms_template_obj, obj=tasks, partner=partner)
            for user_id in tasks.user_ids:
                note = "You are assigned to Task to do {}.".format(tasks.name)
                if tasks.date_deadline:
                    note = "You are assigned to Task to do {} Before the date {}.".format(tasks.name,
                                                                                          tasks.date_deadline)
                tasks.sudo().activity_schedule(
                    'sms_notification.mail_act_task_assign',
                    summary='New Task',
                    note=note,
                    user_id=user_id.id)

        return tasks

    @api.model
    def remind_task(self):
        tasks = self.env['project.task'].search([
            ('sms_notified', '=', False), ('is_closed', '=', False), ('date_deadline', '!=', False)
        ])
        for rec in tasks:
            if rec.date_deadline.day - date.today().day == 1:
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'project_cron'), ('globally_access', '=', False)])
                for sms_template_obj in sms_template_objs:
                    for user_id in rec.user_ids:
                        partner = user_id.partner_id
                        if not partner.disable_notification:
                            rec.task_partner_id = partner.id
                            mobile = sms_template_obj._get_partner_mobile(partner)
                            if mobile:
                                sms_template_obj.send_task_sms_using_template(
                                    mobile, sms_template_obj, obj=rec, partner=partner)
                                rec.sms_notified = True
                            rec.sudo().activity_schedule(
                                'sms_notification.mail_act_task_assign',
                                summary='Task Deadline Reminder',
                                note="We remind you to do the Task {} Before the date {}.".format(rec.name, rec.date_deadline),
                                user_id=user_id.id)
                for user_id in rec.user_ids:
                    rec.sudo().activity_schedule(
                        'sms_notification.mail_act_task_assign',
                        summary='Task Deadline Reminder',
                        note="We remind you to do the Task {} Before the date {}.".format(rec.name,
                                                                                          rec.date_deadline),
                        user_id=user_id.id)

    def write(self, values):
        """
        send notification for task assignee and task create uid
        """
        res = super(Task, self).write(values)
        if values.get('stage_id'):
            stage = self.env['project.task.type'].browse(values.get('stage_id'))
            if stage:
                followers = [uid for uid in self.user_ids.ids]
                followers.append(self.create_uid.id)
                if followers:
                    for follower in followers:
                        self.sudo().activity_schedule(
                            'sms_notification.mail_act_task_assign',
                            summary='Project Task',
                            note='Task state has been changed to {}'.format(stage.name),
                            user_id=follower)
        return res
