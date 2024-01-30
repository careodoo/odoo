# -*- coding: utf-8 -*-
# Copyright 2019 Artem Shurshilov
# Odoo Proprietary License v1.0

# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps, or if you have received a written
# agreement from the authors of the Software (see the COPYRIGHT file).

# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).

# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.

# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettingsWebcam(models.TransientModel):
    _inherit = 'res.config.settings'

    face_recognition_pro_scale_recognition = fields.Integer(
        string='Scale of similafity face', help="0-100, 55 - standart value more 55 most stricter match",
        default=55)
    face_recognition_pro_scale_spoofing = fields.Integer(
        string='Scale of anti-spoofing', help="0-100, 100 - 100% person, 0 - disable, 70 - standart value",
        default=70)
    face_recognition_pro_photo_check = fields.Boolean(
        string='Enable face recognition check real person from photo/image',
        help="Check in/out user only if it live/real person not photo")
    face_recognition_pro_access = fields.Boolean(
        string='Enable face recognition access', help="Check in/out user only when face recognition do snapshot")
    face_recognition_pro_store = fields.Boolean(string='Store snapshots and descriptors employees?',
                                                help="Store snapshot and descriptor of employee when he check in/out in DB for visual control, takes up a lot of server space")
    face_recognition_pro_kiosk_auto = fields.Boolean(
        string='Face recognition kiosk auto check in/out', help="Check in/out click auto when users face finded")

    def set_values(self):
        res = super(ResConfigSettingsWebcam, self).set_values()
        config_parameters = self.env['ir.config_parameter']
        config_parameters.set_param(
            "hr_attendance_face_recognition_pro_access", self.face_recognition_pro_access)
        config_parameters.set_param(
            "hr_attendance_face_recognition_pro_store", self.face_recognition_pro_store)
        config_parameters.set_param(
            "hr_attendance_face_recognition_pro_kiosk_auto", self.face_recognition_pro_kiosk_auto)
        config_parameters.set_param(
            "face_recognition_pro_photo_check", self.face_recognition_pro_photo_check)
        if (self.face_recognition_pro_scale_recognition > 100 or self.face_recognition_pro_scale_spoofing > 100 or
        self.face_recognition_pro_scale_recognition < 0 or self.face_recognition_pro_scale_spoofing <0):
            raise ValidationError("Error! Please check scale field allow range 0-100")
        config_parameters.set_param(
            "face_recognition_pro_scale_spoofing", self.face_recognition_pro_scale_spoofing)
        config_parameters.set_param(
            "face_recognition_pro_scale_recognition", self.face_recognition_pro_scale_recognition)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsWebcam, self).get_values()
        res.update(face_recognition_pro_access=self.env['ir.config_parameter'].get_param(
            'hr_attendance_face_recognition_pro_access'))
        res.update(face_recognition_pro_store=self.env['ir.config_parameter'].get_param(
            'hr_attendance_face_recognition_pro_store'))
        res.update(face_recognition_pro_kiosk_auto=self.env['ir.config_parameter'].get_param(
            'hr_attendance_face_recognition_pro_kiosk_auto'))
        res.update(face_recognition_pro_photo_check=self.env['ir.config_parameter'].get_param(
            'face_recognition_pro_photo_check'))

        face_recognition_pro_scale_recognition=self.env['ir.config_parameter'].get_param(
            'face_recognition_pro_scale_recognition')
        if not face_recognition_pro_scale_recognition:
            face_recognition_pro_scale_recognition = 55
        res.update(face_recognition_pro_scale_recognition=face_recognition_pro_scale_recognition)

        face_recognition_pro_scale_spoofing=self.env['ir.config_parameter'].get_param(
            'face_recognition_pro_scale_spoofing')
        if (not face_recognition_pro_scale_spoofing):
            face_recognition_pro_scale_spoofing = 70
        res.update(face_recognition_pro_scale_spoofing=face_recognition_pro_scale_spoofing)
        return res
