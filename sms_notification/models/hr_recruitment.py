from odoo import fields, models, api, _


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    sms_notified = fields.Boolean()
    next_meeting_date = fields.Datetime()

    @api.model
    def create(self, vals):
        res = super(Applicant, self).create(vals)
        if not vals.get('user_id'):
            sms_template_objs = self.env["wk.sms.template"].sudo().search(
                [('condition', '=', 'job_submit'), ('globally_access', '=', False)])
            for sms_template_obj in sms_template_objs:
                company_country_calling_code = self.env.user.company_id.country_id.phone_code
                mobile = vals.get('partner_phone')
                emp_mobile = "+{code}{mobile}".format(code=company_country_calling_code, mobile=mobile)
                if emp_mobile:
                    sms_template_obj.send_birthday_sms_using_template(
                        emp_mobile, sms_template_obj, obj=res)
        return res

    def write(self, vals):
        if 'stage_id' in vals:
            stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            if stage.name == 'Second Interview':
                sms_template_objs = self.env["wk.sms.template"].sudo().search(
                    [('condition', '=', 'job_meet2'), ('globally_access', '=', False)])
                for sms_template_obj in sms_template_objs:
                    company_country_calling_code = self.env.user.company_id.country_id.phone_code
                    mobile = self.partner_phone or self.partner_mobile
                    emp_mobile = "+{code}{mobile}".format(code=company_country_calling_code, mobile=mobile)
                    if emp_mobile:
                        sms_template_obj.send_birthday_sms_using_template(
                            emp_mobile, sms_template_obj, obj=self)
                res = super(Applicant, self).write(vals)
            else:
                res = super(Applicant, self).write(vals)
        else:
            res = super(Applicant, self).write(vals)
        return res


    @api.depends_context('lang')
    @api.depends('meeting_ids', 'meeting_ids.start')
    def _compute_meeting_display(self):
        applicant_with_meetings = self.filtered('meeting_ids')
        (self - applicant_with_meetings).write({
            'meeting_display_text': _('No Meeting'),
            'meeting_display_date': ''
        })
        today = fields.Date.today()
        for applicant in applicant_with_meetings:
            count = len(applicant.meeting_ids)
            dates = applicant.meeting_ids.mapped('start')
            min_date, max_date = min(dates), max(dates)
            if min_date.date() >= today:
                applicant.meeting_display_date = min_date
                applicant.next_meeting_date = min_date
            else:
                applicant.meeting_display_date = max_date
                applicant.next_meeting_date = max_date
            if count == 1:
                applicant.meeting_display_text = _('1 Meeting')
                if not applicant.sms_notified:
                    sms_template_objs = self.env["wk.sms.template"].sudo().search(
                        [('condition', '=', 'job_meet'), ('globally_access', '=', False)])
                    for sms_template_obj in sms_template_objs:
                        company_country_calling_code = self.env.user.company_id.country_id.phone_code
                        mobile = applicant.partner_phone or applicant.partner_mobile
                        emp_mobile = "+{code}{mobile}".format(code=company_country_calling_code, mobile=mobile)
                        if emp_mobile:
                            sms_template_obj.send_birthday_sms_using_template(
                                emp_mobile, sms_template_obj, obj=applicant)
                            applicant.sms_notified = True
            elif applicant.meeting_display_date >= today:
                applicant.meeting_display_text = _('Next Meeting')
            else:
                applicant.meeting_display_text = _('Last Meeting')
