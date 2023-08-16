# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    military_service_position = fields.Selection(string="", selection=[('not_applicable', 'not applicable'),
                                                                       ('Exempted', 'Exempted'),
                                                                       ('Completed', 'Completed'),
                                                                       ('Postponed', 'Postponed'), ], required=False, )

    postponed_date = fields.Date(string="", required=False, )

    graduation_date = fields.Date(string="", required=False, )

    insurance_start_date = fields.Date(string="", required=False, )

    insurance_type = fields.Selection(string="", selection=[('general_medical_insurance', 'General medical insurance'),
                                                            ('private_medical_insurance',
                                                             'Private medical insurance'), ], required=False, )

    insurance_status = fields.Selection(string="",
                                        selection=[('insured', 'Insured'),
                                                   ('external_insurance', 'External insurance'),
                                                   ('insurance_is_in_progress', 'Insurance is in progress'), ],
                                        required=False, )

    insurance_salary = fields.Float(string="", required=False, )

    pension = fields.Float(string="", required=False, )

    personal_id = fields.Integer(string="Personal ID", required=False, )


    personal_photo = fields.Many2many('ir.attachment', 'personal_photo_rel', 'personal_photo_ref', 'attach_ref', string="",)
    id_photo = fields.Many2many('ir.attachment', 'id_photo_rel', 'id_photo_ref', 'attach_ref1', string="")
    passport_attachment = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_attachment_ref', 'attach_ref2', string="")
    graduation_certificate = fields.Many2many('ir.attachment', 'graduation_certificate_rel', 'graduation_certificate_ref', 'attach_ref3', string="")
    military_service_certificate = fields.Many2many('ir.attachment', 'military_service_certificate_rel', 'military_service_certificate_ref', 'attach_ref4', string="")
    certificate_of_police_record = fields.Many2many('ir.attachment', 'certificate_of_police_record_rel', 'certificate_of_police_record_ref', 'attach_ref5', string="")


    @api.constrains('personal_id')
    def same_personal_id_constrains(self):
        if self.personal_id:
            same_personal_id_count = self.env['hr.employee'].search_count(
                [('personal_id', '=', self.personal_id)])
            if same_personal_id_count > 1:
                raise ValidationError(_('Personal ID must be unique'))

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    military_service_position = fields.Selection(string="", selection=[('not_applicable', 'not applicable'),
                                                                       ('Exempted', 'Exempted'),
                                                                       ('Completed', 'Completed'),
                                                                       ('Postponed', 'Postponed'), ], required=False, )
    postponed_date = fields.Date(string="", required=False, )

    graduation_date = fields.Date(string="", required=False, )

    insurance_start_date = fields.Date(string="", required=False, )

    insurance_type = fields.Selection(string="", selection=[('general_medical_insurance', 'General medical insurance'),
                                                            ('private_medical_insurance',
                                                             'Private medical insurance'), ], required=False, )

    insurance_status = fields.Selection(string="",
                                        selection=[('insured', 'Insured'),
                                                   ('external_insurance', 'External insurance'),
                                                   ('insurance_is_in_progress', 'Insurance is in progress'), ],
                                        required=False, )

    insurance_salary = fields.Float(string="", required=False, )

    pension = fields.Float(string="", required=False, )

    personal_id = fields.Integer(string="Personal ID", required=False, )

    personal_photo = fields.Many2many('ir.attachment', 'personal_photo_rel', 'personal_photo_ref', 'attach_ref', string="",)
    id_photo = fields.Many2many('ir.attachment', 'id_photo_rel', 'id_photo_ref', 'attach_ref1', string="")
    passport_attachment = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_attachment_ref', 'attach_ref2', string="")
    graduation_certificate = fields.Many2many('ir.attachment', 'graduation_certificate_rel', 'graduation_certificate_ref', 'attach_ref3', string="")
    military_service_certificate = fields.Many2many('ir.attachment', 'military_service_certificate_rel', 'military_service_certificate_ref', 'attach_ref4', string="")
    certificate_of_police_record = fields.Many2many('ir.attachment', 'certificate_of_police_record_rel', 'certificate_of_police_record_ref', 'attach_ref5', string="")
