# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "SMS Notification",
  "summary"              :  """Send SMS to customers. Send SMS notifications on Customer mobile with the module. Integrate SMS gateways with Odoo.""",
  "category"             :  "Marketing",
  "version"              :  "1.3.2",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-SMS-Notification.html",
  "description"          :  """Send Text Messages to mobile
Integrate SMS Gateways with Odoo
Bulk SMS send
Send Bulk SMS
SMS Gateway
Odoo SMS Notification
Odoo SMS alert
Notify with Odoo SMS 
Mobile message send
Send Mobile messages
Mobile notifications to customers
Mobile Notifications to Users
How to get SMS notification in Odoo
module to get SMS notification in Odoo
SMS Notification app in Odoo
Notify SMS in Odoo
Add SMS notification feature to your Odoo
Mobile SMS feature
How Odoo can help to get SMS notification,
Odoo SMS OTP Authentication,
Marketplace SMS
Plivo SMS Gateway
Twilio SMS Gateway
Clicksend SMS Gateway
Skebby SMS Gateway
Mobily SMS Gateway
MSG91 SMS Gateway
Netelip SMS Gateway""",
  "live_test_url"        :  "https://www.youtube.com/watch?v=wYCwiTkdGGE&feature=youtu.be",
  "depends"              :  [
                             'sale_management', 'stock', 'purchase', 'crm', 'purchase_tender', 'hr_holidays', 'hr_recruitment', 'project', 'fleet','sms'
                            ],
  "data"                 :  [
                             'security/ir_rule.xml',
                             'security/ir.model.access.csv',
                             'data/activity_type.xml',
                             'wizard/sms_template_preview_view.xml',
                             'edi/general_messages.xml',
                             'edi/sms_template_mail_compose.xml',
                             'edi/sms_template_purchase_mail_compose.xml',
                             'edi/sms_template_crm.xml',
                             'edi/sms_template_project.xml',
                             'edi/sms_template_time_off.xml',
                             'edi/sms_template_tender.xml',
                             'edi/sms_template_invoice_send.xml',
                             'edi/sms_template_for_order_creation.xml',
                             'edi/sms_template_for_order_confirm.xml',
                             'edi/sms_template_for_invoice_validate.xml',
                             'edi/sms_template_for_delivery_done.xml',
                             'edi/sms_template_for_invoice_payment_register.xml',
                             'edi/sms_template_birthday.xml',
                             'edi/sms_template_hr_recruitment.xml',
                             'edi/sms_template_fleet_contract.xml',
                             'views/configure_gateway_view.xml',
                             'views/sms_sms_view.xml',
                             'views/sms_group_view.xml',
                             'views/res_config_view.xml',
                             'views/sms_report_view.xml',
                             'views/sms_cron_view.xml',
                             'views/sms_template_view.xml',
                             'views/res_partner.xml',
                             'views/hr_employee.xml',
                             'data/birthday_cron.xml',
                             'data/project_cron.xml',
                             'data/fleet_contract.xml',
  ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  49,
  "currency"             :  "USD",
  # 'assets': {
  #       'web.assets_backend': [
  #           'sms_notification/static/src/js/field_phone_widget.js',
  #       ],
  #   },
}