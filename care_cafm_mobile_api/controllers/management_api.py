# -*- coding: utf-8 -*-
"""Native MANAGEMENT API — the company's back-office systems in the app.

The management interface used to be a launcher of /web links, i.e. web pages
inside a WebView. These endpoints expose the same systems as real data so the
app can render them natively.

Security model: every read runs with the CALLER's env — never sudo — so Odoo's
own record rules and ACLs decide what each user may see. A system that raises
AccessError is simply reported as unavailable to that user.
"""
import re

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.http import request, Controller, route

from .api import _auth, _ok, _err, _abs, _bearer, API


# Never surface these, whatever Odoo would technically allow the caller to read.
SENSITIVE_RE = re.compile(
    r'salary|wage|bank|acc_number|iban|ssnid|sinid|passport|identification|'
    r'private|pin$|barcode|birthday|children|marital|gender|emergency|'
    r'km_home|permit|visa|study_|certificate|country_of_birth|place_of_birth|'
    r'password|token|secret', re.I)


def _d(v):
    return v and str(v) or None


# key -> spec. `fields` are what the list shows; `search` drives the query.
# Only whitelisted models are reachable — never a model name from the client.
REGISTRY = {
    'purchases': {
        'model': 'purchase.order', 'icon': '🛒', 'ar': 'المشتريات', 'en': 'Purchases',
        'order': 'date_order desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'date_order', 'state': 'state',
    },
    'sales': {
        'model': 'sale.order', 'icon': '💰', 'ar': 'المبيعات', 'en': 'Sales',
        'order': 'date_order desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'date_order', 'state': 'state',
    },
    'tenders': {
        'model': 'purchase.tender', 'icon': '📑', 'ar': 'المناقصات', 'en': 'Tenders',
        'order': 'close_sort_key, id desc',
        'search': ['name', 'tender_no', 'tender_name', 'organization.name', 'winner.name'],
        'title': 'name', 'subtitle': 'organization', 'amount': 'price',
        'date': 'closing_date', 'state': 'state',
    },
    'proposals': {
        'model': 'proposal.proposal', 'icon': '📊', 'ar': 'عروض الأسعار', 'en': 'Proposals',
        'order': 'id desc',
        'search': ['ref', 'name', 'partner_id.name', 'service_type_id.name',
                   'service_site', 'city'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'total_amount',
        'date': 'proposal_date', 'state': 'state',
    },
    'employees': {
        'model': 'hr.employee', 'icon': '👥', 'ar': 'الموظفون', 'en': 'Employees',
        'order': 'name',
        # search by name, badge (barcode), civil ID, passport, email, phone, job
        'search': ['name', 'barcode', 'identification_id', 'passport_id',
                   'work_email', 'mobile_phone', 'job_title'],
        'title': 'name', 'subtitle': 'job_title', 'amount': None,
        'date': None, 'state': None, 'image': 'avatar_128',
        # WORK data only. Never the private HR block (identification_id/civil ID,
        # birthday, marital, gender, permits, bank) — a directory in a phone app
        # has no business carrying it, even for users Odoo would let read it.
        'fields': ['name', 'job_title', 'department_id', 'parent_id', 'coach_id',
                   'work_phone', 'mobile_phone', 'work_email', 'work_location_id',
                   'company_id', 'resource_calendar_id', 'employee_type'],
        # Only safe work-contact fields are editable from a phone.
        'edit': ['job_title', 'work_phone', 'mobile_phone', 'work_email',
                 'work_location_id'],
    },
    'hr_allowances': {
        'model': 'care.allowance', 'icon': '💵', 'ar': 'البدلات', 'en': 'Allowances',
        'order': 'date desc, id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': 'amount', 'date': 'date', 'state': 'state',
    },
    'hr_bonuses': {
        'model': 'bonus.request', 'icon': '🎁', 'ar': 'المكافآت', 'en': 'Bonuses',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': None, 'date': 'request_date', 'state': 'state',
    },
    'hr_loans': {
        'model': 'care.loan', 'icon': '💰', 'ar': 'السُّلف', 'en': 'Loans',
        'order': 'date desc, id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': 'amount', 'date': 'date', 'state': 'state',
    },
    'hr_penalties': {
        'model': 'penalty.request', 'icon': '⚠️', 'ar': 'الجزاءات', 'en': 'Penalties',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': None, 'date': 'request_date', 'state': 'state',
    },
    'hr_eos': {
        'model': 'care.eos', 'icon': '🏁', 'ar': 'إنهاء الخدمة', 'en': 'End of service',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': 'net_amount', 'date': 'create_date', 'state': 'state',
    },
    'hr_custody': {
        'model': 'care.custody', 'icon': '🧰', 'ar': 'العهد', 'en': 'Custody',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': None, 'date': 'create_date', 'state': 'state',
    },
    'hr_permissions': {
        'model': 'permission.request', 'icon': '🕒', 'ar': 'الاستئذانات', 'en': 'Permissions',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': None, 'date': 'create_date', 'state': 'state',
    },
    'leaves': {
        'model': 'hr.leave', 'icon': '🌴', 'ar': 'الإجازات', 'en': 'Time off',
        'order': 'id desc', 'search': ['employee_id.name'],
        'title': 'display_name', 'subtitle': 'employee_id', 'amount': 'number_of_days',
        'date': 'date_from', 'state': 'state',
        'fields': ['employee_id', 'holiday_status_id', 'date_from', 'date_to',
                   'number_of_days', 'name', 'department_id', 'state'],
        'edit': ['holiday_status_id', 'date_from', 'date_to', 'name'],
    },
    'expenses': {
        'model': 'hr.expense.sheet', 'icon': '🧾', 'ar': 'مصروفات الموظفين',
        'en': 'Expense reports',
        'order': 'id desc', 'search': ['name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': 'total_amount',
        'date': 'create_date', 'state': 'state',
        'fields': ['name', 'employee_id', 'total_amount', 'payment_mode',
                   'accounting_date', 'department_id', 'state'],
        'edit': ['name'],
    },
    'documents': {
        'model': 'care.dms.document', 'icon': '📁', 'ar': 'المستندات', 'en': 'Documents',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': None, 'amount': None,
        'date': 'create_date', 'state': 'state',
        'edit': ['name'],
    },
    'experience': {
        'model': 'care.experience', 'icon': '🏆', 'ar': 'الخبرات', 'en': 'Experience',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': 'state',
    },
    'fleet': {
        'model': 'fleet.vehicle', 'icon': '🚗', 'ar': 'الأسطول', 'en': 'Fleet',
        'order': 'id desc', 'search': ['name', 'license_plate'],
        'title': 'name', 'subtitle': 'license_plate', 'amount': None,
        'date': None, 'state': 'state_id',
    },
    'crm': {
        'model': 'crm.lead', 'icon': '🎯', 'ar': 'الفرص', 'en': 'CRM',
        'order': 'id desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'expected_revenue',
        'date': 'create_date', 'state': 'stage_id',
        'edit': ['name', 'expected_revenue', 'email_from', 'phone', 'stage_id'],
    },
    'invoices': {
        'model': 'account.move', 'icon': '🧾', 'ar': 'الفواتير', 'en': 'Invoices',
        'order': 'invoice_date desc, id desc', 'search': ['name', 'partner_id.name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'invoice_date', 'state': 'state',
        'domain': [('move_type', 'in', ('out_invoice', 'in_invoice'))],
    },
    'attendance': {
        'model': 'hr.attendance', 'icon': '⏱️', 'ar': 'الحضور والانصراف', 'en': 'Attendance',
        'order': 'check_in desc, id desc', 'search': ['employee_id.name'],
        'title': 'employee_id', 'subtitle': 'department_id', 'amount': None,
        'date': 'check_in', 'state': None,
    },
    'bio_devices': {
        'model': 'attendance.device', 'icon': '🔌', 'ar': 'أجهزة البصمة', 'en': 'Biometric devices',
        'order': 'name', 'search': ['name', 'device_name', 'ip'],
        'title': 'name', 'subtitle': 'ip', 'amount': None,
        'date': None, 'state': 'state',
    },
    'uniform': {
        'model': 'uniform.delivery', 'icon': '👕', 'ar': 'تسليم اليونيفورم', 'en': 'Uniform delivery',
        'order': 'date desc, id desc',
        'search': ['name', 'employee_id.name', 'uniform_type_id.name'],
        'title': 'employee_id', 'subtitle': 'uniform_type_id', 'amount': None,
        'date': 'date', 'state': None,
    },
    'approvals': {
        'model': 'approval.request', 'icon': '✔️', 'ar': 'الموافقات', 'en': 'Approvals',
        'order': 'id desc', 'search': ['name', 'request_owner_id.name', 'category_id.name'],
        'title': 'name', 'subtitle': 'category_id', 'amount': None,
        'date': 'date', 'state': 'request_status',
    },
    'files': {
        'model': 'documents.document', 'icon': '🗂️', 'ar': 'الوثائق', 'en': 'Documents',
        'order': 'create_date desc, id desc',
        # multi-field search: name, folder, owner, contact, mime type
        'search': ['name', 'folder_id.name', 'owner_id.name', 'partner_id.name', 'mimetype'],
        'title': 'name', 'subtitle': 'folder_id', 'amount': None,
        'date': 'create_date', 'state': None,
    },
    'invoice_requests': {
        'model': 'request.invoice', 'icon': '📥', 'ar': 'طلبات الفواتير', 'en': 'Invoice requests',
        'order': 'id desc', 'sudo': True,
        'search': ['name', 'partner_id.name', 'x_studio_invoice_ref', 'x_studio_finance_ref'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': 'amount_total',
        'date': 'invoice_date', 'state': 'state',
    },
    'projects': {
        'model': 'project.project', 'icon': '🏗️', 'ar': 'المشاريع', 'en': 'Projects',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': 'partner_id', 'amount': None,
        'date': 'create_date', 'state': None,
        'edit': ['name'],
    },
    'correspondence': {
        'model': 'care.letter', 'icon': '✉️', 'ar': 'المراسلات', 'en': 'Correspondence',
        'order': 'date desc, id desc',
        'search': ['name', 'employee_id.name', 'body'],
        'title': 'name', 'subtitle': 'letter_type', 'amount': None,
        'date': 'date', 'state': 'state',
    },
    'recruitment': {
        'model': 'hr.applicant', 'icon': '🧑‍💼', 'ar': 'التوظيف', 'en': 'Recruitment',
        'order': 'id desc',
        'search': ['partner_name', 'email_from', 'partner_phone', 'job_id.name', 'stage_id.name'],
        'title': 'partner_name', 'subtitle': 'job_id', 'amount': None,
        'date': 'create_date', 'state': 'stage_id',
    },
    'passports': {
        'model': 'care.passport', 'icon': '🛂', 'ar': 'الجوازات', 'en': 'Passports',
        'order': 'expiry_date, id desc',
        'search': ['name', 'passport_no', 'employee_id.name', 'employee_id.barcode',
                   'employee_id.identification_id', 'country_id.name', 'holder_id.name'],
        'title': 'employee_id', 'subtitle': 'passport_no', 'amount': None,
        'date': 'expiry_date', 'state': 'state',
    },
    'legal': {
        'model': 'hr.lawsuit', 'icon': '⚖️', 'ar': 'القضايا القانونية', 'en': 'Legal cases',
        'order': 'id desc', 'search': ['name', 'ref_no', 'court_name', 'employee_id.name'],
        'title': 'name', 'subtitle': 'court_name', 'amount': None,
        'date': 'hearing_date', 'state': 'state',
        'edit': ['state', 'court_name', 'ref_no', 'hearing_date', 'next_appointment'],
    },
    'petrol': {
        'model': 'petrol.tank', 'icon': '⛽', 'ar': 'خزانات الوقود', 'en': 'Petrol tanks',
        'order': 'id desc', 'search': ['name'],
        'title': 'name', 'subtitle': None, 'amount': 'balance',
        'date': 'last_charge', 'state': 'stage_id',
    },
    'vehicle_service': {
        'model': 'fleet.vehicle.log.services', 'icon': '🔧', 'ar': 'صيانة المركبات', 'en': 'Vehicle service',
        'order': 'date desc, id desc',
        'search': ['name', 'vehicle_id.name', 'vehicle_id.license_plate', 'description'],
        'title': 'vehicle_id', 'subtitle': 'service_type_id', 'amount': 'amount',
        'date': 'date', 'state': 'state',
        'edit': ['state', 'amount', 'date', 'description', 'service_type_id', 'odometer'],
    },
    'payroll': {
        'model': 'hr.payslip.run', 'icon': '💵', 'ar': 'مسيّرات الرواتب', 'en': 'Payroll batches',
        'order': 'date_start desc, id desc', 'search': ['name'],
        'title': 'name', 'subtitle': None, 'amount': None,
        'date': 'date_start', 'state': 'state',
    },
    'payslips': {
        'model': 'hr.payslip', 'icon': '🧾', 'ar': 'قسائم الرواتب', 'en': 'Payslips',
        'order': 'date_from desc, id desc', 'search': ['number', 'name', 'employee_id.name'],
        'title': 'number', 'subtitle': 'employee_id', 'amount': 'net_wage',
        'date': 'date_from', 'state': 'state',
    },
    'hostels': {
        'model': 'hostel', 'icon': '🏠', 'ar': 'السكن', 'en': 'Housing',
        'order': 'name', 'search': ['name'],
        'title': 'name', 'subtitle': None, 'amount': None,
        'date': None, 'state': None,
        'fields': ['name', 'floor_count', 'flat_count', 'room_count', 'bed_count',
                   'total_capacity', 'company_id'],
    },
    'hostel_beds': {
        'model': 'hostel.bed', 'icon': '🛏️', 'ar': 'الأسرّة والإشغال', 'en': 'Beds & occupancy',
        'order': 'hostel_id, room_id, name', 'search': ['name', 'employee_id.name', 'room_id.name', 'hostel_id.name'],
        'title': 'name', 'subtitle': 'employee_id', 'amount': None,
        'date': None, 'state': None,
        'fields': ['name', 'hostel_id', 'floor_id', 'flat_id', 'room_id', 'employee_id',
                   'is_available', 'vacation'],
    },
}


# Whitelisted workflow actions per system. A client sends an action KEY, never a
# method name, and the method must appear here — arbitrary calls are impossible.
# `states` gates when the button shows; empty = always. Execution uses the
# caller's env, so Odoo still refuses if they lack write access.
ACTIONS = {
    'purchases': [
        {'key': 'confirm', 'method': 'button_confirm', 'ar': 'تأكيد الطلب', 'en': 'Confirm order',
         'states': ['draft', 'sent', 'to approve'], 'style': 'primary'},
        {'key': 'approve', 'method': 'button_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['to approve'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'button_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'sent', 'to approve', 'purchase'], 'style': 'danger', 'confirm': True},
        {'key': 'lock', 'method': 'button_done', 'ar': 'قفل الطلب', 'en': 'Lock',
         'states': ['purchase'], 'style': 'plain'},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel', 'sent'], 'style': 'plain'},
    ],
    'approvals': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'تقديم للاعتماد', 'en': 'Submit',
         'states': ['new'], 'style': 'primary'},
        {'key': 'approve', 'method': 'action_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['new', 'pending'], 'style': 'primary'},
        {'key': 'refuse', 'method': 'action_refuse', 'ar': 'رفض', 'en': 'Refuse',
         'states': ['new', 'pending', 'approved'], 'style': 'danger', 'confirm': True},
        {'key': 'cancel', 'method': 'action_withdraw', 'ar': 'سحب', 'en': 'Withdraw',
         'states': ['new', 'pending'], 'style': 'plain', 'confirm': True},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel', 'refused'], 'style': 'plain'},
    ],
    'legal': [
        {'key': 'process', 'method': 'process', 'ar': 'بدء النظر', 'en': 'Start / Running',
         'states': ['draft', 'delay'], 'style': 'primary'},
        {'key': 'delay', 'method': 'delay', 'ar': 'تأجيل', 'en': 'Postpone',
         'states': ['running'], 'style': 'plain'},
        {'key': 'won', 'method': 'won', 'ar': '🏆 كسب القضية', 'en': 'Won',
         'states': ['draft', 'running', 'delay'], 'style': 'primary'},
        {'key': 'loss', 'method': 'loss', 'ar': 'خسارة القضية', 'en': 'Lost',
         'states': ['draft', 'running', 'delay'], 'style': 'danger', 'confirm': True},
        {'key': 'cancel', 'method': 'cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'running', 'delay'], 'style': 'danger', 'confirm': True},
    ],
    'hr_allowances': [
        {'key': 'submit', 'method': 'action_submit', 'ar': 'تقديم', 'en': 'Submit', 'states': ['draft'], 'style': 'primary'},
        {'key': 'dept', 'method': 'action_dept_approve', 'ar': 'اعتماد القسم', 'en': 'Dept. approve', 'states': ['draft', 'submit', 'submitted'], 'style': 'primary'},
        {'key': 'senior', 'method': 'action_senior_approve', 'ar': 'اعتماد الإدارة', 'en': 'Senior approve', 'states': ['dept'], 'style': 'primary'},
        {'key': 'paid', 'method': 'action_mark_cash_paid', 'ar': 'تأكيد الصرف النقدي', 'en': 'Mark cash paid', 'states': ['approved'], 'style': 'primary'},
        {'key': 'refuse', 'method': 'action_refuse', 'ar': 'رفض', 'en': 'Refuse', 'states': ['draft', 'dept', 'approved'], 'style': 'danger', 'confirm': True},
        {'key': 'reset', 'method': 'action_reset', 'ar': 'إعادة لمسودة', 'en': 'Reset', 'states': ['dept', 'approved', 'refused'], 'style': 'plain'},
    ],
    'hr_bonuses': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'تقديم', 'en': 'Submit', 'states': ['draft'], 'style': 'primary'},
        {'key': 'dept', 'method': 'action_department_approve', 'ar': 'اعتماد القسم', 'en': 'Dept. approve', 'states': ['submitted'], 'style': 'primary'},
        {'key': 'manager', 'method': 'action_manager_approve', 'ar': 'اعتماد المدير', 'en': 'Manager approve', 'states': ['submitted', 'department'], 'style': 'primary'},
        {'key': 'reject', 'method': 'action_reject', 'ar': 'رفض', 'en': 'Reject', 'states': ['draft', 'submitted', 'department'], 'style': 'danger', 'confirm': True},
        {'key': 'reset', 'method': 'action_reset_to_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset', 'states': ['submitted', 'accounting'], 'style': 'plain'},
    ],
    'hr_loans': [
        {'key': 'submit', 'method': 'action_submit', 'ar': 'تقديم', 'en': 'Submit', 'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'action_approve', 'ar': 'اعتماد', 'en': 'Approve', 'states': ['submitted'], 'style': 'primary'},
        {'key': 'start', 'method': 'action_start', 'ar': 'بدء الخصم', 'en': 'Start deduction', 'states': ['approved'], 'style': 'primary'},
        {'key': 'refuse', 'method': 'action_refuse', 'ar': 'رفض', 'en': 'Refuse', 'states': ['draft', 'submitted', 'approved'], 'style': 'danger', 'confirm': True},
        {'key': 'reset', 'method': 'action_reset', 'ar': 'إعادة لمسودة', 'en': 'Reset', 'states': ['approved', 'refused'], 'style': 'plain'},
    ],
    'hr_eos': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'اعتماد', 'en': 'Confirm', 'states': ['draft'], 'style': 'primary'},
        {'key': 'paid', 'method': 'action_paid', 'ar': 'تأكيد الصرف', 'en': 'Mark paid', 'states': ['confirmed'], 'style': 'primary'},
    ],
    'hr_custody': [
        {'key': 'return', 'method': 'action_return', 'ar': 'استرجاع العهدة', 'en': 'Return', 'states': ['issued'], 'style': 'primary'},
        {'key': 'lost', 'method': 'action_lost', 'ar': 'فقدان', 'en': 'Lost', 'states': ['issued'], 'style': 'danger', 'confirm': True},
        {'key': 'damaged', 'method': 'action_damaged', 'ar': 'تلف', 'en': 'Damaged', 'states': ['issued'], 'style': 'danger', 'confirm': True},
        {'key': 'reset', 'method': 'action_reset', 'ar': 'إعادة للعهدة', 'en': 'Reset', 'states': ['returned', 'lost', 'damaged'], 'style': 'plain'},
    ],
    'hr_permissions': [
        {'key': 'submit', 'method': 'button_submit', 'ar': 'تقديم', 'en': 'Submit', 'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'button_approve', 'ar': 'اعتماد', 'en': 'Approve', 'states': ['submitted'], 'style': 'primary'},
        {'key': 'reject', 'method': 'button_reject', 'ar': 'رفض', 'en': 'Reject', 'states': ['draft', 'submitted'], 'style': 'danger', 'confirm': True},
    ],
    'bio_devices': [
        {'key': 'check', 'method': 'action_check_connection', 'ar': 'فحص الاتصال', 'en': 'Check connection',
         'states': [], 'style': 'primary'},
        {'key': 'fetch', 'method': 'action_fetch_attendance_data', 'ar': 'سحب البصمات', 'en': 'Fetch attendance',
         'states': [], 'style': 'primary'},
        {'key': 'info', 'method': 'action_device_information', 'ar': 'معلومات الجهاز', 'en': 'Device info',
         'states': [], 'style': 'plain'},
        {'key': 'restart', 'method': 'action_restart', 'ar': 'إعادة تشغيل', 'en': 'Restart',
         'states': [], 'style': 'plain', 'confirm': True},
        {'key': 'clear', 'method': 'action_clear_attendance_data', 'ar': 'مسح بيانات الجهاز', 'en': 'Clear device data',
         'states': [], 'style': 'danger', 'confirm': True},
    ],
    'invoice_requests': [
        {'key': 'submit', 'method': 'action_submit', 'ar': 'تقديم', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'invoice', 'method': 'action_convert_to_invoice', 'ar': 'تحويل لفاتورة', 'en': 'Convert to invoice',
         'states': ['submitted'], 'style': 'primary'},
        {'key': 'refuse', 'method': 'action_refuse', 'ar': 'رفض', 'en': 'Refuse',
         'states': ['draft', 'submitted'], 'style': 'danger', 'confirm': True},
        {'key': 'cancel', 'method': 'action_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'submitted'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel', 'rejected'], 'style': 'plain'},
    ],
    'sales': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'تأكيد', 'en': 'Confirm',
         'states': ['draft', 'sent'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'action_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'sent', 'sale'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel'], 'style': 'plain'},
    ],
    'invoices': [
        {'key': 'post', 'method': 'action_post', 'ar': 'ترحيل القيد', 'en': 'Post',
         'states': ['draft'], 'style': 'primary', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['posted', 'cancel'], 'style': 'plain'},
    ],
    'crm': [
        {'key': 'won', 'method': 'action_set_won_rainbowman', 'ar': 'كسبت', 'en': 'Mark won',
         'states': [], 'style': 'primary'},
        {'key': 'lost', 'method': 'action_set_lost', 'ar': 'خسرت', 'en': 'Mark lost',
         'states': [], 'style': 'danger', 'confirm': True},
    ],
    'proposals': [
        {'key': 'submit', 'method': 'button_submit', 'ar': 'تقديم', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'button_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['submit', 'waiting'], 'style': 'primary'},
        {'key': 'reject', 'method': 'button_reject', 'ar': 'رفض', 'en': 'Reject',
         'states': ['submit', 'waiting'], 'style': 'danger', 'confirm': True},
        {'key': 'won', 'method': 'button_won', 'ar': '🏆 فزنا', 'en': 'Won',
         'states': ['approve', 'submit'], 'style': 'primary'},
        {'key': 'cancel', 'method': 'button_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'submit', 'waiting', 'approve'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['cancel', 'reject'], 'style': 'plain'},
    ],
    'tenders': [
        {'key': 'under_study', 'method': 'action_set_under_study', 'ar': 'قيد الدراسة', 'en': 'Under study',
         'states': ['new'], 'style': 'primary'},
        {'key': 'interested', 'method': 'action_set_interested', 'ar': 'مهتمون', 'en': 'Interested',
         'states': ['new', 'under_study', 'docs_purchased'], 'style': 'primary'},
        {'key': 'preparing', 'method': 'action_set_preparing', 'ar': 'جارٍ التحضير', 'en': 'Preparing',
         'states': ['interested', 'docs_purchased', 'under_study'], 'style': 'primary'},
        {'key': 'participated', 'method': 'action_set_participated', 'ar': 'تم التقديم', 'en': 'Submitted',
         'states': ['preparing'], 'style': 'primary'},
        {'key': 'winner', 'method': 'action_set_winner', 'ar': '🏆 فزنا', 'en': 'Won',
         'states': ['participated'], 'style': 'primary'},
        {'key': 'lost', 'method': 'action_set_lost', 'ar': 'خسرنا', 'en': 'Lost',
         'states': ['participated'], 'style': 'danger', 'confirm': True},
        {'key': 'cancelled', 'method': 'action_set_cancelled', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': [], 'style': 'danger', 'confirm': True},
    ],
    'leaves': [
        {'key': 'confirm', 'method': 'action_confirm', 'ar': 'إرسال للاعتماد', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'action_approve', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['confirm', 'validate1'], 'style': 'primary'},
        {'key': 'refuse', 'method': 'action_refuse', 'ar': 'رفض', 'en': 'Refuse',
         'states': ['confirm', 'validate1', 'validate'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['confirm', 'refuse'], 'style': 'plain'},
    ],
    'expenses': [
        {'key': 'submit', 'method': 'action_submit_sheet', 'ar': 'إرسال للاعتماد', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'approve', 'method': 'approve_expense_sheets', 'ar': 'اعتماد', 'en': 'Approve',
         'states': ['submit'], 'style': 'primary'},
    ],
    'payslips': [
        {'key': 'compute', 'method': 'compute_sheet', 'ar': 'احتساب', 'en': 'Compute',
         'states': ['draft', 'verify'], 'style': 'primary'},
        {'key': 'done', 'method': 'action_payslip_done', 'ar': 'اعتماد', 'en': 'Confirm',
         'states': ['draft', 'verify'], 'style': 'primary'},
        {'key': 'draft', 'method': 'action_payslip_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['done', 'cancel', 'paid'], 'style': 'plain'},
        {'key': 'cancel', 'method': 'action_payslip_cancel', 'ar': 'إلغاء', 'en': 'Cancel',
         'states': ['draft', 'verify'], 'style': 'danger', 'confirm': True},
    ],
    'payroll': [
        {'key': 'open', 'method': 'action_open', 'ar': 'فتح المسيّر', 'en': 'Open batch',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'close', 'method': 'action_close', 'ar': 'إغلاق', 'en': 'Close',
         'states': ['verify'], 'style': 'primary'},
        {'key': 'draft', 'method': 'action_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['verify', 'close'], 'style': 'plain'},
    ],
    'experience': [
        {'key': 'submit', 'method': 'button_submit', 'ar': 'تقديم', 'en': 'Submit',
         'states': ['draft'], 'style': 'primary'},
        {'key': 'valid', 'method': 'button_valid', 'ar': 'اعتماد/تفعيل', 'en': 'Validate',
         'states': ['submit'], 'style': 'primary'},
        {'key': 'renew', 'method': 'action_start_renewal', 'ar': 'بدء التجديد', 'en': 'Start renewal',
         'states': ['valid'], 'style': 'primary'},
        {'key': 'expired', 'method': 'button_expired', 'ar': 'انتهى', 'en': 'Mark expired',
         'states': ['valid', 'under_renewal'], 'style': 'plain'},
        {'key': 'terminate', 'method': 'button_terminate', 'ar': 'إنهاء العقد', 'en': 'Terminate',
         'states': ['submit', 'valid', 'under_renewal'], 'style': 'danger', 'confirm': True},
        {'key': 'draft', 'method': 'button_draft', 'ar': 'إعادة لمسودة', 'en': 'Reset to draft',
         'states': ['submit', 'valid', 'expired', 'terminated'], 'style': 'plain'},
    ],
}


# Printable reports per system. Only those whose report action actually exists on
# this DB are surfaced. `type` drives the client (pdf → in-app viewer, xlsx →
# download). The report is rendered with the caller's env (ACLs still apply).
REPORTS = {
    'sales': [
        {'report': 'care_sale.report_saleorder_header', 'ar': 'عرض السعر (CARE)', 'en': 'Quotation (CARE)', 'type': 'pdf'},
        {'report': 'sale.report_saleorder', 'ar': 'أمر البيع', 'en': 'Sale order', 'type': 'pdf'},
        {'report': 'sale.report_saleorder_pro_forma', 'ar': 'فاتورة مبدئية', 'en': 'Pro-forma', 'type': 'pdf'},
    ],
    'purchases': [
        {'report': 'purchase_report.report_purchaseorder_header', 'ar': 'أمر الشراء (CARE)', 'en': 'PO (CARE)', 'type': 'pdf'},
        {'report': 'purchase.report_purchaseorder', 'ar': 'أمر الشراء', 'en': 'Purchase order', 'type': 'pdf'},
        {'report': 'purchase.report_purchasequotation', 'ar': 'طلب عرض سعر', 'en': 'RFQ', 'type': 'pdf'},
    ],
    'proposals': [
        {'report': 'care_proposal.customer_proposal_report', 'ar': 'عرض السعر للعميل', 'en': 'Customer proposal', 'type': 'pdf'},
        {'report': 'care_proposal.proposal_scope_xlsx_report', 'ar': 'نطاق العمل (Excel)', 'en': 'Scope (Excel)', 'type': 'xlsx'},
        {'report': 'care_proposal.proposal_manpower_xlsx_report', 'ar': 'القوى العاملة (Excel)', 'en': 'Manpower (Excel)', 'type': 'xlsx'},
        {'report': 'care_proposal.proposal_material_xlsx_report', 'ar': 'المواد (Excel)', 'en': 'Materials (Excel)', 'type': 'xlsx'},
        {'report': 'care_proposal.proposal_equipment_xlsx_report', 'ar': 'المعدات (Excel)', 'en': 'Equipment (Excel)', 'type': 'xlsx'},
    ],
    'tenders': [
        {'report': 'purchase_tender.purchase_tender_report', 'ar': 'ملف المناقصة', 'en': 'Tender file', 'type': 'pdf'},
        {'report': 'purchase_tender.tender_summary_report', 'ar': 'ملخص المناقصة', 'en': 'Tender summary', 'type': 'pdf'},
        {'report': 'purchase_tender.tender_requirements_report', 'ar': 'متطلبات المناقصة', 'en': 'Requirements', 'type': 'pdf'},
        {'report': 'purchase_tender.tender_bid_result_report', 'ar': 'نتيجة العطاء', 'en': 'Bid result', 'type': 'pdf'},
    ],
    'invoices': [
        {'report': 'account.report_invoice', 'ar': 'الفاتورة', 'en': 'Invoice', 'type': 'pdf'},
    ],
    'expenses': [
        {'report': 'hr_expense.report_expense_sheet', 'ar': 'تقرير المصروفات', 'en': 'Expense report', 'type': 'pdf'},
    ],
    'correspondence': [
        {'report': 'care_hr.report_letter', 'ar': 'الخطاب', 'en': 'Letter', 'type': 'pdf'},
    ],
    'experience': [
        {'report': 'care_experience.report_contract_dossier', 'ar': 'ملف العقد', 'en': 'Contract dossier', 'type': 'pdf'},
    ],
    'payslips': [
        {'report': 'hr_payroll.report_payslip_lang', 'ar': 'قسيمة الراتب', 'en': 'Payslip', 'type': 'pdf'},
    ],
}


# Sub-modules that hang off an employee — the rich employee file lists each one.
EMP_RELATED = [
    ('hr.contract', 'العقود', 'Contracts', '📄'),
    ('care.allowance', 'البدلات', 'Allowances', '💵'),
    ('hr.action.joining', 'مباشرة العمل', 'Work commencement', '🚀'),
    ('care.eos', 'إنهاء الخدمة', 'End of service', '🏁'),
    ('hr.action.leave.return', 'العودة من إجازة', 'Leave return', '↩️'),
    ('hr.leave', 'الإجازات', 'Time off', '🌴'),
    ('permission.request', 'الاستئذانات', 'Permissions', '🕒'),
    ('hr.loan', 'السُّلف', 'Loans', '💰'),
    ('care.loan', 'السُّلف', 'Loans', '💰'),
    ('penalty.request', 'الجزاءات', 'Penalties', '⚠️'),
    ('bonus.request', 'المكافآت', 'Bonuses', '🎁'),
    ('hr.payslip', 'كشوف الرواتب', 'Payslips', '🧾'),
    ('care.suspension.request', 'الإيقاف عن العمل', 'Suspensions', '⛔'),
    ('care.probation', 'فترة التجربة', 'Probation', '📋'),
    ('hr.employee.skill', 'المهارات', 'Skills', '🎓'),
    ('hr.appraisal', 'التقييمات', 'Appraisals', '⭐'),
    ('care.passport', 'الجوازات', 'Passports', '🛂'),
    ('hr.lawsuit', 'القضايا القانونية', 'Legal', '⚖️'),
    ('care.custody', 'العهد', 'Custody', '🧰'),
]

# Field grouping for the rich employee file — keyword → section.
EMP_GROUPS = [
    ('👤 معلومات شخصية', 'Personal', ['birthday', 'gender', 'marital', 'place_of_birth',
        'country_id', 'nationality', 'spouse', 'children', 'blood', 'religion', 'ssnid', 'lang', 'age']),
    ('🪪 الهوية والإقامة', 'Identity & residence', ['civil', 'identification', 'residency',
        'iqama', 'passport', 'visa', 'work_permit', 'permit', 'sponsor', 'border', 'muqeem', 'labor', 'kuwait']),
    ('💼 معلومات العمل', 'Work', ['job', 'department', 'parent_id', 'coach', 'manager',
        'employee_type', 'resource_calendar', 'work_location', 'joining', 'hire', 'date_start',
        'category', 'barcode', 'pin', 'company_id', 'active', 'worker_status', 'work_department']),
    ('📞 التواصل', 'Contact', ['work_phone', 'mobile', 'work_email', 'email', 'phone']),
    ('🏠 السكن', 'Housing', ['accommodation', 'hostel', 'housing', 'room', 'bed', 'floor']),
    ('💰 الراتب والبنك', 'Pay & bank', ['wage', 'salary', 'bank', 'iban', 'allowance', 'transport']),
]


# Config-driven "create new" for systems without a bespoke create form.
# many2one: 'search' → live search (relation whitelist); 'model' → inline options.
CREATE_SPECS = {
    'tenders': {'model': 'purchase.tender', 'ar': 'مناقصة جديدة', 'en': 'New tender', 'fields': [
        {'name': 'name', 'ar': 'اسم المناقصة', 'en': 'Tender name', 'type': 'char', 'required': True},
        {'name': 'organization', 'ar': 'الجهة', 'en': 'Organization', 'type': 'many2one', 'search': 'res.partner', 'required': True},
        {'name': 'tender_no', 'ar': 'رقم المناقصة', 'en': 'Tender no.', 'type': 'char'},
        {'name': 'issue_date', 'ar': 'تاريخ الطرح', 'en': 'Issue date', 'type': 'date'},
        {'name': 'closing_date', 'ar': 'تاريخ الإغلاق', 'en': 'Closing date', 'type': 'date'},
        {'name': 'price', 'ar': 'القيمة', 'en': 'Value', 'type': 'float'},
        {'name': 'guarantee', 'ar': 'الضمان', 'en': 'Guarantee', 'type': 'float'},
        {'name': 'bid_type', 'ar': 'نوع المناقصة', 'en': 'Bid type', 'type': 'many2one', 'model': 'bid.type'},
        {'name': 'classification_id', 'ar': 'التصنيف', 'en': 'Classification', 'type': 'many2one', 'model': 'purchase.tender.classification'},
    ]},
    'leaves': {'model': 'hr.leave', 'ar': 'طلب إجازة', 'en': 'New time off', 'defaults': {'holiday_type': 'employee'}, 'fields': [
        {'name': 'employee_id', 'ar': 'الموظف', 'en': 'Employee', 'type': 'many2one', 'search': 'hr.employee', 'required': True},
        {'name': 'holiday_status_id', 'ar': 'نوع الإجازة', 'en': 'Leave type', 'type': 'many2one', 'model': 'hr.leave.type', 'required': True},
        {'name': 'request_date_from', 'ar': 'من', 'en': 'From', 'type': 'date', 'required': True},
        {'name': 'request_date_to', 'ar': 'إلى', 'en': 'To', 'type': 'date', 'required': True},
        {'name': 'name', 'ar': 'السبب', 'en': 'Reason', 'type': 'text'},
    ]},
    'vehicle_service': {'model': 'fleet.vehicle.log.services', 'ar': 'طلب صيانة مركبة', 'en': 'New vehicle service', 'defaults': {'type': 'service'}, 'fields': [
        {'name': 'vehicle_id', 'ar': 'المركبة', 'en': 'Vehicle', 'type': 'many2one', 'search': 'fleet.vehicle', 'required': True},
        {'name': 'service_type_id', 'ar': 'نوع الخدمة', 'en': 'Service type', 'type': 'many2one', 'model': 'fleet.service.type', 'required': True},
        {'name': 'type', 'ar': 'التصنيف', 'en': 'Type', 'type': 'selection'},
        {'name': 'date', 'ar': 'التاريخ', 'en': 'Date', 'type': 'date'},
        {'name': 'next_service_date', 'ar': 'الخدمة القادمة', 'en': 'Next service', 'type': 'date'},
        {'name': 'amount', 'ar': 'التكلفة', 'en': 'Amount', 'type': 'float'},
        {'name': 'odometer', 'ar': 'قراءة العدّاد', 'en': 'Odometer', 'type': 'float'},
        {'name': 'vendor_id', 'ar': 'المورّد', 'en': 'Vendor', 'type': 'many2one', 'search': 'res.partner'},
        {'name': 'inv_ref', 'ar': 'مرجع المورّد', 'en': 'Vendor ref', 'type': 'char'},
        {'name': 'purchaser_id', 'ar': 'السائق', 'en': 'Driver', 'type': 'many2one', 'search': 'res.partner'},
        {'name': 'description', 'ar': 'الوصف', 'en': 'Description', 'type': 'text'},
        {'name': 'notes', 'ar': 'ملاحظات', 'en': 'Notes', 'type': 'text'},
    ]},
    'correspondence': {'model': 'care.letter', 'ar': 'خطاب جديد', 'en': 'New letter', 'fields': [
        {'name': 'employee_id', 'ar': 'الموظف', 'en': 'Employee', 'type': 'many2one', 'search': 'hr.employee', 'required': True},
        {'name': 'letter_type', 'ar': 'نوع الخطاب', 'en': 'Letter type', 'type': 'selection', 'required': True},
        {'name': 'addressed_to', 'ar': 'موجَّه إلى', 'en': 'Addressed to', 'type': 'char'},
        {'name': 'date', 'ar': 'التاريخ', 'en': 'Date', 'type': 'date', 'required': True},
        {'name': 'body', 'ar': 'نص الخطاب', 'en': 'Body', 'type': 'text'},
    ]},
    'experience': {'model': 'care.experience', 'ar': 'خبرة/عقد جديد', 'en': 'New experience', 'fields': [
        {'name': 'partner_id', 'ar': 'العميل', 'en': 'Customer', 'type': 'many2one', 'search': 'res.partner'},
        {'name': 'start_date', 'ar': 'تاريخ البدء', 'en': 'Start date', 'type': 'date'},
    ]},
    'invoice_requests': {'model': 'request.invoice', 'ar': 'طلب فاتورة جديد', 'en': 'New invoice request', 'fields': [
        {'name': 'partner_id', 'ar': 'العميل', 'en': 'Customer', 'type': 'many2one', 'search': 'res.partner', 'required': True},
        {'name': 'invoice_date', 'ar': 'تاريخ الفاتورة', 'en': 'Invoice date', 'type': 'date'},
        {'name': 'project_id', 'ar': 'المشروع', 'en': 'Project', 'type': 'many2one', 'search': 'project.project'},
        {'name': 'department_id', 'ar': 'القسم', 'en': 'Department', 'type': 'many2one', 'model': 'hr.department'},
    ]},
    'passports': {'model': 'care.passport', 'ar': 'تسجيل جواز', 'en': 'Register passport', 'fields': [
        {'name': 'employee_id', 'ar': 'الموظف', 'en': 'Employee', 'type': 'many2one', 'search': 'hr.employee', 'required': True},
        {'name': 'shelf_location', 'ar': 'الموقع/الرف', 'en': 'Shelf / location', 'type': 'char'},
    ]},
    'petrol': {'model': 'petrol.tank', 'ar': 'خزان وقود جديد', 'en': 'New fuel tank', 'fields': [
        {'name': 'name', 'ar': 'اسم الخزان', 'en': 'Tank name', 'type': 'char', 'required': True},
        {'name': 'capacity', 'ar': 'السعة (لتر)', 'en': 'Capacity (L)', 'type': 'float', 'required': True},
        {'name': 'stage_id', 'ar': 'المرحلة', 'en': 'Stage', 'type': 'many2one', 'model': 'petrol.tank.stage'},
    ]},
    'legal': {'model': 'hr.lawsuit', 'ar': 'قضية جديدة', 'en': 'New legal case', 'fields': [
        {'name': 'employee_id', 'ar': 'الموظف (الطرف الثاني)', 'en': 'Employee (Party 2)', 'type': 'many2one', 'search': 'hr.employee'},
        {'name': 'ref_no', 'ar': 'رقم المرجع', 'en': 'Reference no.', 'type': 'char'},
        {'name': 'court_name', 'ar': 'اسم المحكمة', 'en': 'Court name', 'type': 'char'},
        {'name': 'judge', 'ar': 'القاضي', 'en': 'Judge', 'type': 'char'},
        {'name': 'lawyer', 'ar': 'المحامي', 'en': 'Lawyer', 'type': 'many2one', 'search': 'res.partner'},
        {'name': 'requested_date', 'ar': 'تاريخ الرفع', 'en': 'Filing date', 'type': 'date'},
        {'name': 'hearing_date', 'ar': 'تاريخ الجلسة', 'en': 'Hearing date', 'type': 'date'},
        {'name': 'case_details', 'ar': 'تفاصيل القضية', 'en': 'Case details', 'type': 'text'},
    ]},
}

# Employee sub-module quick-create (employee_id injected from the file screen).
EMP_CREATE_SPECS = {
    'care.allowance': {'ar': 'بدل جديد', 'en': 'New allowance', 'fields': [
        {'name': 'payment_method', 'ar': 'طريقة الدفع', 'en': 'Payment method', 'type': 'selection', 'required': True},
        {'name': 'amount', 'ar': 'المبلغ', 'en': 'Amount', 'type': 'float', 'required': True},
        {'name': 'frequency', 'ar': 'التكرار', 'en': 'Frequency', 'type': 'selection', 'required': True},
        {'name': 'date', 'ar': 'التاريخ', 'en': 'Date', 'type': 'date', 'required': True},
    ]},
    'care.loan': {'ar': 'سلفة / قرض جديد', 'en': 'New loan / advance', 'fields': [
        {'name': 'loan_type', 'ar': 'النوع', 'en': 'Type', 'type': 'selection', 'required': True},
        {'name': 'amount', 'ar': 'المبلغ', 'en': 'Amount', 'type': 'float', 'required': True},
        {'name': 'installments', 'ar': 'عدد الأقساط', 'en': 'Installments', 'type': 'integer', 'required': True},
        {'name': 'date', 'ar': 'التاريخ', 'en': 'Date', 'type': 'date', 'required': True},
    ]},
    'permission.request': {'ar': 'استئذان جديد', 'en': 'New permission', 'fields': [
        {'name': 'type', 'ar': 'النوع', 'en': 'Type', 'type': 'selection', 'required': True},
        {'name': 'permission_from', 'ar': 'من', 'en': 'From', 'type': 'datetime', 'required': True},
        {'name': 'permission_hours', 'ar': 'عدد الساعات', 'en': 'Hours', 'type': 'integer', 'required': True},
        {'name': 'reason', 'ar': 'السبب', 'en': 'Reason', 'type': 'text', 'required': True},
    ]},
    'care.eos': {'ar': 'إنهاء خدمة', 'en': 'End of service', 'fields': [
        {'name': 'reason', 'ar': 'السبب', 'en': 'Reason', 'type': 'selection', 'required': True},
        {'name': 'last_working_day', 'ar': 'آخر يوم عمل', 'en': 'Last working day', 'type': 'date', 'required': True},
    ]},
    'care.custody': {'ar': 'عهدة جديدة', 'en': 'New custody', 'fields': [
        {'name': 'item_type', 'ar': 'نوع العهدة', 'en': 'Item type', 'type': 'selection', 'required': True},
        {'name': 'description', 'ar': 'الوصف', 'en': 'Description', 'type': 'char', 'required': True},
        {'name': 'issue_date', 'ar': 'تاريخ الإصدار', 'en': 'Issue date', 'type': 'date', 'required': True},
    ]},
    'bonus.request': {'ar': 'مكافأة جديدة', 'en': 'New bonus', 'fields': [
        {'name': 'bonus_type', 'ar': 'نوع المكافأة', 'en': 'Bonus type', 'type': 'selection', 'required': True},
        {'name': 'reason', 'ar': 'السبب', 'en': 'Reason', 'type': 'text', 'required': True},
    ]},
    'penalty.request': {'ar': 'جزاء جديد', 'en': 'New penalty', 'fields': [
        {'name': 'penalty_type', 'ar': 'نوع الجزاء', 'en': 'Penalty type', 'type': 'selection', 'required': True},
        {'name': 'reason', 'ar': 'السبب', 'en': 'Reason', 'type': 'text', 'required': True},
    ]},
}


# Models a generic m2o field may live-search (never an arbitrary model name).
RELATION_SEARCH = {
    'res.partner': ['name'], 'hr.employee': ['name', 'barcode', 'work_email'],
    'fleet.vehicle': ['name', 'license_plate'], 'product.product': ['name', 'default_code'],
    'res.users': ['name', 'login'], 'project.project': ['name'],
}


class ManagementApi(Controller):

    def _spec(self, key):
        return REGISTRY.get(key)

    def _raw_state(self, rec, spec):
        """The stored state value (not its label), for gating actions."""
        f = spec.get('state')
        if not f or f not in rec._fields:
            return None
        v = rec[f]
        return v.id if rec._fields[f].type == 'many2one' else v

    def _actions_for(self, env, rec, key, spec):
        """Actions available on THIS record for THIS user."""
        out = []
        defs = ACTIONS.get(key) or []
        if not defs:
            return out
        # no write access → offer nothing rather than fail on tap
        if not spec.get('sudo'):
            try:
                env[spec['model']].check_access_rights('write', raise_exception=True)
            except Exception:
                return out
        st = self._raw_state(rec, spec)
        for a in defs:
            if not hasattr(rec, a['method']):
                continue
            if a['states'] and st not in a['states']:
                continue
            out.append({'key': a['key'], 'ar': a['ar'], 'en': a['en'],
                        'style': a.get('style', 'plain'), 'confirm': bool(a.get('confirm'))})
        return out

    def _val(self, rec, fname):
        """Read a field for display, tolerating missing fields across versions."""
        if not fname or fname not in rec._fields:
            return None
        v = rec[fname]
        f = rec._fields[fname]
        if f.type == 'many2one':
            return v.display_name if v else None
        if f.type == 'selection':
            try:
                return dict(f._description_selection(rec.env)).get(v, v)
            except Exception:
                return v
        if f.type in ('date', 'datetime'):
            return _d(v)
        if f.type in ('float', 'monetary'):
            return round(v or 0, 2)
        return v if v not in (False, None) else None

    def _raw_edit_val(self, rec, fname):
        """The stored value for an editable field — an id for m2o, a string for
        dates — so the app pre-fills the form correctly."""
        f = rec._fields[fname]
        v = rec[fname]
        if f.type == 'many2one':
            return v.id or None
        if f.type in ('date', 'datetime'):
            return str(v) if v else None
        return v if v not in (False, None) else None

    def _m2o_options(self, rec, f):
        """Choices for a relation field the caller may pick from (their ACL)."""
        try:
            recs = rec.env[f.comodel_name].search([], limit=100)
            return [{'v': r.id, 'l': r.display_name} for r in recs]
        except Exception:
            return []

    def _can(self, env, spec):
        """Whether this user may read the model. Normally Odoo's ACL decides;
        for `sudo` systems (manager back-office over a group-restricted model)
        managers/admins are allowed and reads run with sudo."""
        model = spec['model']
        if model not in env:
            return False
        if spec.get('sudo'):
            u = env.user
            return u.has_group('base.group_erp_manager') or u.has_group('base.group_system')
        try:
            env[model].check_access_rights('read', raise_exception=True)
            return True
        except (AccessError, Exception):
            return False

    def _model(self, env, spec):
        """The model recordset for reads — sudo for `sudo` systems."""
        M = env[spec['model']]
        return M.sudo() if spec.get('sudo') else M

    # ---- Per-user Management access (show/hide systems, create/edit, details)
    _ACCESS_PARAM = 'care_mgmt.access'

    def _access_all(self, env):
        import json
        raw = env['ir.config_parameter'].sudo().get_param(self._ACCESS_PARAM)
        try:
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    def _user_access(self, env, uid=None):
        """Effective access overrides for a user (empty = full access)."""
        uid = uid or env.uid
        cfg = self._access_all(env).get(str(uid)) or {}
        return {
            'hidden': set(cfg.get('hidden') or []),
            'no_create': set(cfg.get('no_create') or []),
            'no_edit': set(cfg.get('no_edit') or []),
            'hide_attachments': bool(cfg.get('hide_attachments')),
            'hide_amounts': bool(cfg.get('hide_amounts')),
        }

    def _is_mgmt_admin(self, env):
        u = env.user
        return u.has_group('base.group_erp_manager') or u.has_group('base.group_system')

    def _create_blocked(self, env, key):
        acc = self._user_access(env)
        return key in acc['hidden'] or key in acc['no_create']

    # Records that "need attention" per system — drives the red badge on the home.
    _PENDING = {
        'proposals': [('state', 'in', ['submit', 'waiting'])],
        'tenders': [('state', 'in', ['new', 'under_study'])],
        'sales': [('state', 'in', ['draft', 'sent'])],
        'purchases': [('state', 'in', ['draft', 'sent', 'to approve'])],
        'invoices': [('state', '=', 'draft')],
        'leaves': [('state', 'in', ['confirm', 'validate1'])],
        'expenses': [('state', '=', 'submit')],
        'payslips': [('state', 'in', ['draft', 'verify'])],
        'payroll': [('state', 'in', ['draft', 'verify'])],
        'experience': [('state', 'in', ['submit', 'under_renewal'])],
        'vehicle_service': [('state', 'in', ['new', 'running'])],
        'correspondence': [('state', '=', 'draft')],
        'invoice_requests': [('state', 'in', ['draft', 'submitted'])],
        'approvals': [('request_status', 'in', ['new', 'pending'])],
    }

    # HR sub-systems that live INSIDE the Employees icon (the employee
    # module-icon row), so they are hidden from the top-level home grid to
    # avoid duplication. Still fully reachable via /management/<key>/list.
    _EMP_SUB = {
        'leaves', 'hr_allowances', 'hr_bonuses', 'hr_loans', 'hr_penalties',
        'hr_eos', 'hr_custody', 'hr_permissions', 'documents', 'correspondence',
        'passports', 'recruitment',
    }
    # Payroll sub-systems grouped under a single «الرواتب» parent tile.
    _PAYROLL_SUB = {'payslips', 'payroll'}

    # ---- which systems does THIS user actually have? ----------------------
    @route(API + '/management/apps', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_apps(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        access = self._user_access(env)
        out = []
        for key, spec in REGISTRY.items():
            if key in self._EMP_SUB:
                continue  # surfaced inside the Employees icon instead
            if key in self._PAYROLL_SUB:
                continue  # surfaced inside the «الرواتب» parent tile instead
            if key == 'bio_devices':
                continue  # surfaced inside the Attendance icon instead
            if key in access['hidden']:
                continue  # hidden for this user by a manager
            if not self._can(env, spec):
                continue
            try:
                Model = self._model(env, spec)
                dom = list(spec.get('domain') or [])
                count = Model.search_count(dom)
                pending = 0
                pdom = self._PENDING.get(key)
                if pdom:
                    try:
                        pending = Model.search_count(dom + list(pdom))
                    except Exception:
                        pending = 0
            except Exception:
                continue
            out.append({'key': key, 'icon': spec['icon'], 'ar': spec['ar'], 'en': spec['en'],
                        'count': count, 'pending': pending})
        # synthetic «الرواتب» parent tile (opens a hub of payslips + batches)
        if 'payslips' not in access['hidden'] and self._can(env, REGISTRY['payslips']):
            try:
                Slip = self._model(env, REGISTRY['payslips'])
                pcount = Slip.search_count([])
                ppend = Slip.search_count(list(self._PENDING.get('payslips') or []))
                out.append({'key': 'payroll_hub', 'icon': '💵', 'ar': 'الرواتب', 'en': 'Payroll',
                            'count': pcount, 'pending': ppend})
            except Exception:
                pass
        return _ok(out)

    # ---- counts for the Employees sub-module icon row (feeds red badges) ---
    @route(API + '/management/emp_modules', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_emp_modules(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        access = self._user_access(env)
        # the ordered keys shown under the Employees icon
        keys = ['attendance', 'leaves', 'hr_allowances', 'hr_loans', 'hr_bonuses',
                'hr_penalties', 'hr_eos', 'hr_permissions', 'hr_custody',
                'documents', 'correspondence', 'passports', 'recruitment']
        out = {}
        for key in keys:
            spec = REGISTRY.get(key)
            if not spec or key in access['hidden'] or not self._can(env, spec):
                continue
            try:
                Model = self._model(env, spec)
                dom = list(spec.get('domain') or [])
                count = Model.search_count(dom)
                pending = 0
                pdom = self._PENDING.get(key)
                if pdom:
                    try:
                        pending = Model.search_count(dom + list(pdom))
                    except Exception:
                        pending = 0
            except Exception:
                continue
            out[key] = {'count': count, 'pending': pending}
        return _ok(out)

    # ---- list ------------------------------------------------------------
    @route(API + '/management/<string:key>/list', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_list(self, key, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على هذا النظام', 403)
        access = self._user_access(env)
        if key in access['hidden']:
            return _err('لا تملك صلاحية على هذا النظام', 403)
        Model = self._model(env, spec)  # sudo for `sudo` systems, else caller's ACL
        dom = list(spec.get('domain') or [])
        q = (kw.get('q') or '').strip()
        if q and spec.get('search'):
            sub = []
            for f in spec['search']:
                root = f.split('.')[0]
                if root in Model._fields:
                    sub.append((f, 'ilike', q))
            if sub:
                dom += ['|'] * (len(sub) - 1) + sub
        # generic state filter (any system with a selection 'state'); a
        # comma-separated value matches any of the listed states.
        if kw.get('state') and spec.get('state') and spec['state'] in Model._fields:
            vals = [s for s in str(kw['state']).split(',') if s]
            if len(vals) > 1:
                dom.append((spec['state'], 'in', vals))
            elif vals:
                dom.append((spec['state'], '=', vals[0]))
        # attendance: department + period + open filters
        if key == 'attendance':
            if kw.get('dept'):
                try:
                    dom.append(('department_id', '=', int(kw['dept'])))
                except (TypeError, ValueError):
                    pass
            p = kw.get('period')
            if p in ('today', 'week', 'month'):
                from dateutil.relativedelta import relativedelta
                t = fields.Date.today()
                since = t if p == 'today' else (t - relativedelta(days=t.weekday()) if p == 'week' else t.replace(day=1))
                dom.append(('check_in', '>=', str(since) + ' 00:00:00'))
            if kw.get('open') == '1':
                dom.append(('check_out', '=', False))
        # documents: folder + type filters
        if key == 'files':
            if kw.get('folder'):
                try:
                    dom.append(('folder_id', '=', int(kw['folder'])))
                except (TypeError, ValueError):
                    pass
            if kw.get('ftype') == 'image':
                dom.append(('mimetype', 'ilike', 'image/'))
            elif kw.get('ftype') == 'pdf':
                dom.append(('mimetype', '=', 'application/pdf'))
        # employee-specific filters
        active_test = True
        if key == 'employees':
            if kw.get('dept'):
                try:
                    dom.append(('department_id', '=', int(kw['dept'])))
                except (TypeError, ValueError):
                    pass
            if kw.get('etype'):
                dom.append(('employee_type', '=', kw['etype']))
            st = kw.get('emp_status')
            if st == 'archived':
                dom.append(('active', '=', False))
                active_test = False
            elif st == 'all':
                active_test = False
        try:
            limit = min(int(kw.get('limit') or 60), 200)
        except Exception:
            limit = 60
        M2 = Model.with_context(active_test=active_test) if not active_test else Model
        try:
            recs = M2.search(dom, order=spec.get('order') or 'id desc', limit=limit)
        except Exception:
            recs = M2.search(dom, limit=limit)
        rows = []
        for r in recs:
            code = self._raw_state(r, spec)
            row = {
                'id': r.id,
                'title': self._val(r, spec['title']) or r.display_name,
                'subtitle': self._val(r, spec.get('subtitle')),
                'amount': self._val(r, spec.get('amount')),
                'date': self._val(r, spec.get('date')),
                'state': self._val(r, spec.get('state')),
                'state_code': code,
                'state_color': self._state_color(code) if code else None,
                'image': ('/web/image/%s/%s/%s' % (spec['model'], r.id, spec['image']))
                         if spec.get('image') and spec['image'] in r._fields and r[spec['image']] else None,
            }
            if key == 'proposals':
                try:
                    row['pr'] = self._proposal_row(r)
                except Exception:
                    pass
            elif key == 'tenders':
                try:
                    row['tn'] = self._tender_row(r)
                except Exception:
                    pass
            elif key == 'employees':
                try:
                    row['emp'] = self._employee_row(r)
                except Exception:
                    pass
            elif key in ('sales', 'purchases', 'invoices'):
                try:
                    row['ord'] = self._order_row(r)
                except Exception:
                    pass
            elif key == 'leaves':
                try:
                    row['lv'] = self._leave_row(r)
                except Exception:
                    pass
            elif key == 'crm':
                try:
                    row['crm'] = self._crm_row(r)
                    row['state_color'] = row['crm']['stage_color']  # colour by stage
                except Exception:
                    pass
            elif key == 'expenses':
                try:
                    row['exp'] = self._expense_row(r)
                except Exception:
                    pass
            elif key == 'experience':
                try:
                    row['xp'] = self._experience_row(r)
                except Exception:
                    pass
            elif key == 'vehicle_service':
                try:
                    row['vs'] = self._vs_row(r)
                except Exception:
                    pass
            elif key == 'correspondence':
                try:
                    row['lt'] = self._letter_row(r)
                except Exception:
                    pass
            elif key == 'invoice_requests':
                try:
                    row['ri'] = self._reqinv_row(r)
                except Exception:
                    pass
            elif key == 'files':
                try:
                    row['doc'] = self._doc_row(r)
                except Exception:
                    pass
            elif key == 'approvals':
                try:
                    row['appr'] = self._appr_row(r)
                except Exception:
                    pass
            elif key == 'attendance':
                try:
                    row['att'] = self._att_row(r)
                except Exception:
                    pass
            elif key == 'bio_devices':
                try:
                    row['dev'] = self._dev_row(r)
                except Exception:
                    pass
            elif key == 'fleet':
                try:
                    row['fl'] = self._fleet_row(r)
                    if row['fl'].get('state'):
                        row['state'] = row['fl']['state']
                        row['state_color'] = row['fl']['state_color']
                except Exception:
                    pass
            elif key == 'legal':
                try:
                    row['lg'] = self._legal_row(r)
                except Exception:
                    pass
            elif key == 'petrol':
                try:
                    row['pt'] = self._petrol_row(r)
                except Exception:
                    pass
            elif key == 'passports':
                try:
                    row['pp'] = self._passport_row(r)
                except Exception:
                    pass
            else:
                # every other system: a professional logo/avatar for the row
                try:
                    row['logo_b64'] = self._generic_logo(r)
                except Exception:
                    pass
            rows.append(row)
        out = {'key': key, 'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'],
               'count': M2.search_count(dom), 'rows': rows,
               'currency': self._currency(recs[:1]) if recs else None}
        try:
            if key == 'proposals':
                all_recs = Model.search(dom) if len(recs) >= limit else recs
                out['stats'] = self._proposal_stats(all_recs)
                out['can_create'] = Model.check_access_rights('create', raise_exception=False)
            elif key == 'tenders':
                all_recs = Model.search(dom) if len(recs) >= limit else recs
                out['stats'] = self._tender_stats(all_recs)
                out['can_create'] = Model.check_access_rights('create', raise_exception=False)
            elif key == 'sales':
                out['stats'] = self._agg_stats(Model, dom, key, confirmed_states=('sale', 'done'))
            elif key == 'purchases':
                out['stats'] = self._agg_stats(Model, dom, key, confirmed_states=('purchase', 'done'))
                out['can_create'] = Model.check_access_rights('create', raise_exception=False)
            elif key == 'invoices':
                out['stats'] = self._agg_stats(Model, dom, key, confirmed_states=('posted',))
            elif key == 'leaves':
                grp = Model.read_group(dom, ['number_of_days'], [])
                days = (grp[0].get('number_of_days') if grp else 0.0) or 0.0
                out['stats'] = self._agg_stats(
                    Model, dom, key, amount_field=None, confirmed_states=('validate',),
                    extra=[{'key': 'days', 'ar': 'إجمالي الأيام', 'en': 'Total days',
                            'value': round(days, 1), 'icon': '🌴'}])
            elif key == 'crm':
                out['stats'] = self._crm_stats(Model, dom)
                out['can_create'] = Model.check_access_rights('create', raise_exception=False)
            elif key == 'expenses':
                out['stats'] = self._agg_stats(
                    Model, dom, key, amount_field='total_amount',
                    confirmed_states=('approve', 'post', 'done'))
            elif key == 'fleet':
                out['stats'] = self._fleet_stats(Model, dom)
            elif key == 'employees':
                out['stats'] = self._employee_stats(env, Model, dom)
                out['filters'] = self._employee_filters(env)
            elif key == 'experience':
                out['stats'] = self._experience_stats(Model, dom)
            elif key == 'vehicle_service':
                out['stats'] = self._vs_stats(Model, dom)
            elif key == 'correspondence':
                out['stats'] = self._letter_stats(Model, dom)
            elif key == 'invoice_requests':
                out['stats'] = self._reqinv_stats(Model, dom)
            elif key == 'files':
                out['stats'] = self._doc_stats(env, Model, dom)
                out['filters'] = self._doc_filters(env)
            elif key == 'approvals':
                out['stats'] = self._appr_stats(Model, dom)
            elif key == 'attendance':
                out['stats'] = self._att_stats(env, Model, dom)
                out['filters'] = self._att_filters(env)
            elif key == 'bio_devices':
                out['stats'] = self._dev_stats(Model, dom)
            elif key == 'legal':
                out['stats'] = self._legal_stats(Model, dom)
            elif key == 'petrol':
                out['stats'] = self._petrol_stats(Model, dom)
            elif key == 'passports':
                out['stats'] = self._passport_stats(Model, dom)
        except Exception:
            pass
        # generic state-filter chips: any system whose `state` is a selection
        sf = spec.get('state')
        if sf and sf in Model._fields and Model._fields[sf].type == 'selection':
            try:
                out['state_filters'] = [{'v': k2, 'l': l2} for k2, l2 in
                                        Model._fields[sf]._description_selection(env)]
            except Exception:
                pass
        # generic create availability (systems without a bespoke create form)
        if key in CREATE_SPECS and not out.get('can_create'):
            try:
                out['can_create'] = Model.check_access_rights('create', raise_exception=False)
                out['create_kind'] = 'generic'
            except Exception:
                pass
        # ---- per-user access overrides ----
        if key in access['no_create']:
            out['can_create'] = False
        if access['hide_amounts']:
            out['hide_amounts'] = True
        return _ok(out)

    # ---- Excel export of a filtered list ---------------------------------
    def _export_columns(self, key, spec):
        """(ar, en, getter) columns per system; None → generic from spec."""
        def m2o(f):
            return lambda r: (r[f].display_name if f in r._fields and r[f] else '')

        def val(f):
            return lambda r: (r[f] if f in r._fields and r[f] not in (False, None) else '')

        def dat(f):
            return lambda r: (str(r[f]) if f in r._fields and r[f] else '')

        def sel(f):
            def g(r):
                if f not in r._fields or not r[f]:
                    return ''
                try:
                    return dict(r._fields[f]._description_selection(r.env)).get(r[f], r[f])
                except Exception:
                    return r[f]
            return g

        table = {
            'proposals': [('المرجع', 'Ref', val('ref')), ('العميل', 'Customer', m2o('partner_id')),
                          ('نوع الخدمة', 'Service', m2o('service_type_id')), ('التكلفة', 'Cost', val('total_pricing_cost')),
                          ('البيع', 'Sale', val('total_amount')), ('الربح', 'Profit', val('margin_amount')),
                          ('نسبة الربح %', 'Margin %', val('margin_percentage')), ('الحالة', 'State', sel('state')),
                          ('التاريخ', 'Date', dat('proposal_date'))],
            'tenders': [('رقم المناقصة', 'Tender no.', val('tender_no')), ('الجهة', 'Organization', m2o('organization')),
                        ('القيمة', 'Value', val('price')), ('الضمان', 'Guarantee', val('guarantee')),
                        ('احتمالية الفوز %', 'Win %', val('win_probability')), ('الإغلاق', 'Closing', dat('closing_date')),
                        ('الفائز', 'Winner', m2o('winner')), ('الحالة', 'State', sel('state'))],
            'employees': [('الاسم', 'Name', val('name')), ('الوظيفة', 'Job', val('job_title')),
                          ('القسم', 'Department', m2o('department_id')), ('نوع التوظيف', 'Type', sel('employee_type')),
                          ('الحضور', 'Attendance', sel('attendance_state')), ('الهاتف', 'Phone', val('work_phone'))],
            'leaves': [('الموظف', 'Employee', m2o('employee_id')), ('النوع', 'Type', m2o('holiday_status_id')),
                       ('الأيام', 'Days', val('number_of_days')), ('من', 'From', dat('date_from')),
                       ('إلى', 'To', dat('date_to')), ('الحالة', 'State', sel('state'))],
            'crm': [('العنوان', 'Title', val('name')), ('العميل', 'Customer', m2o('partner_id')),
                    ('الإيراد المتوقع', 'Expected', val('expected_revenue')), ('الاحتمالية %', 'Prob %', val('probability')),
                    ('المرحلة', 'Stage', m2o('stage_id')), ('المندوب', 'Owner', m2o('user_id'))],
            'invoices': [('الفاتورة', 'Invoice', val('name')), ('الطرف', 'Partner', m2o('partner_id')),
                         ('المبلغ', 'Amount', val('amount_total')), ('المتبقّي', 'Residual', val('amount_residual')),
                         ('السداد', 'Payment', sel('payment_state')), ('الحالة', 'State', sel('state')),
                         ('التاريخ', 'Date', dat('invoice_date'))],
            'fleet': [('المركبة', 'Vehicle', m2o('model_id')), ('اللوحة', 'Plate', val('license_plate')),
                      ('السائق', 'Driver', m2o('driver_id')), ('العدّاد', 'Odometer', val('odometer')),
                      ('الوقود', 'Fuel', sel('fuel_type')), ('السنة', 'Year', val('model_year'))],
        }
        order = [('المستند', 'Document', val('name')), ('الطرف', 'Partner', m2o('partner_id')),
                 ('المبلغ', 'Amount', val('amount_total')), ('الحالة', 'State', sel('state')),
                 ('التاريخ', 'Date', dat('date_order'))]
        if key in ('sales', 'purchases'):
            return order
        if key in table:
            return table[key]
        # generic fallback from the spec
        cols = [('العنوان', 'Title', lambda r: self._val(r, spec['title']) or r.display_name)]
        if spec.get('subtitle'):
            cols.append(('التفاصيل', 'Details', lambda r: self._val(r, spec['subtitle']) or ''))
        if spec.get('state'):
            cols.append(('الحالة', 'State', lambda r: self._val(r, spec['state']) or ''))
        if spec.get('amount'):
            cols.append(('القيمة', 'Amount', lambda r: self._val(r, spec['amount']) or 0))
        if spec.get('date'):
            cols.append(('التاريخ', 'Date', lambda r: self._val(r, spec['date']) or ''))
        return cols

    @route(API + '/management/<string:key>/export', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_export(self, key, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على هذا النظام', 403)
        Model = env[spec['model']]
        dom = list(spec.get('domain') or [])
        q = (kw.get('q') or '').strip()
        if q and spec.get('search'):
            sub = [(f, 'ilike', q) for f in spec['search'] if f.split('.')[0] in Model._fields]
            if sub:
                dom += ['|'] * (len(sub) - 1) + sub
        try:
            recs = Model.search(dom, order=spec.get('order') or 'id desc', limit=5000)
        except Exception:
            recs = Model.search(dom, limit=5000)
        cols = self._export_columns(key, spec)
        lang = 'en' if (kw.get('lang') == 'en') else 'ar'

        import io
        import xlsxwriter
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet((spec['en'] or key)[:31])
        if lang == 'ar':
            ws.right_to_left()
        title_fmt = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#B01C2E',
                                   'align': 'center', 'valign': 'vcenter', 'border': 1})
        cell = wb.add_format({'border': 1, 'valign': 'vcenter'})
        for c, (ar, en, _g) in enumerate(cols):
            ws.write(0, c, ar if lang == 'ar' else en, title_fmt)
            ws.set_column(c, c, 22)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(recs), len(cols) - 1)
        for i, r in enumerate(recs, start=1):
            for c, (_ar, _en, getter) in enumerate(cols):
                try:
                    v = getter(r)
                except Exception:
                    v = ''
                if isinstance(v, float):
                    v = round(v, 3)
                ws.write(i, c, v, cell)
        wb.close()
        data = buf.getvalue()
        buf.close()
        fname = '%s.xlsx' % key
        return request.make_response(data, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="%s"' % fname),
            ('Content-Length', str(len(data))),
        ])

    # ---- global search across ALL systems --------------------------------
    @route(API + '/management/search', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_search(self, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        q = (q or '').strip()
        if len(q) < 2:
            return _ok({'groups': [], 'total': 0})
        groups, total = [], 0
        for key, spec in REGISTRY.items():
            if not spec.get('search') or not self._can(env, spec):
                continue
            Model = env[spec['model']]
            dom = list(spec.get('domain') or [])
            sub = [(f, 'ilike', q) for f in spec['search'] if f.split('.')[0] in Model._fields]
            if not sub:
                continue
            dom += ['|'] * (len(sub) - 1) + sub
            try:
                recs = Model.search(dom, order=spec.get('order') or 'id desc', limit=6)
                cnt = Model.search_count(dom)
            except Exception:
                continue
            if not recs:
                continue
            total += cnt
            groups.append({
                'key': key, 'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'], 'count': cnt,
                'rows': [{
                    'id': r.id,
                    'title': self._val(r, spec['title']) or r.display_name,
                    'subtitle': self._val(r, spec.get('subtitle')),
                    'state': self._val(r, spec.get('state')),
                    'amount': self._val(r, spec.get('amount')),
                } for r in recs],
            })
        # systems with the most hits first
        groups.sort(key=lambda g: -g['count'])
        return _ok({'groups': groups, 'total': total})

    # ---- detail ----------------------------------------------------------
    @route(API + '/management/<string:key>/<int:rid>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def management_detail(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على هذا النظام', 403)
        try:
            rec = self._model(env, spec).browse(rid)
            if not spec.get('sudo'):
                rec.check_access_rule('read')  # record rules on this exact record
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        # Only the fields this system declares. Dumping every readable field
        # leaked private HR data (civil ID, birthday, marital status) and would
        # also blow up on group-restricted fields.
        skip_types = ('binary', 'image', 'one2many', 'many2many', 'html')
        allowed = spec.get('fields')
        if allowed:
            names = [f for f in allowed if f in rec._fields]
        else:
            names = [fname for fname, f in rec._fields.items()
                     if f.type not in skip_types
                     and not fname.startswith(('message_', 'activity_', 'website_'))
                     and fname not in ('id', 'display_name', '__last_update',
                                       'create_uid', 'write_uid', 'write_date')
                     and not SENSITIVE_RE.search(fname)]
        title_f, state_f = spec.get('title'), spec.get('state')
        editset = set(spec.get('edit') or [])
        # Grouped, in a fixed professional order — parties, then money, dates,
        # then everything else. The header already carries title + state, so
        # those are not repeated in the body.
        buckets = {
            'parties': {'title': 'الأطراف والعلاقات', 'title_en': 'Parties & links', 'icon': '🔗', 'fields': []},
            'amounts': {'title': 'المبالغ', 'title_en': 'Amounts', 'icon': '💰', 'fields': []},
            'dates': {'title': 'التواريخ', 'title_en': 'Dates', 'icon': '📅', 'fields': []},
            'info': {'title': 'معلومات', 'title_en': 'Details', 'icon': '📋', 'fields': []},
        }
        fields, editable = [], []
        for fname in names:
            f = rec._fields[fname]
            if f.type in skip_types:
                continue
            try:
                v = self._val(rec, fname)   # a group-restricted field raises here
            except Exception:
                continue
            # Editable field spec (type + choices) so the app can render a form.
            if fname in editset:
                em = {'name': fname, 'label': f.string, 'type': f.type,
                      'value': self._raw_edit_val(rec, fname)}
                if f.type == 'selection':
                    try:
                        em['options'] = [{'v': k, 'l': l}
                                         for k, l in f._description_selection(rec.env)]
                    except Exception:
                        em['options'] = []
                elif f.type == 'many2one':
                    em['options'] = self._m2o_options(rec, f)
                editable.append(em)
            if fname in (title_f, state_f):
                continue  # header already shows these
            if v in (None, '', False):
                continue
            meta = {'name': fname, 'label': f.string, 'value': v, 'type': f.type}
            fields.append(meta)
            sec = ('amounts' if f.type in ('monetary', 'float')
                   else 'dates' if f.type in ('date', 'datetime')
                   else 'parties' if f.type == 'many2one'
                   else 'info')
            buckets[sec]['fields'].append(meta)
        sections = [dict(v, key=k) for k, v in buckets.items() if v['fields']]
        code = self._raw_state(rec, spec)
        payload = {
            'id': rec.id, 'title': self._val(rec, spec['title']) or rec.display_name,
            'ar': spec['ar'], 'en': spec['en'], 'icon': spec['icon'],
            'state': self._val(rec, spec.get('state')),
            'state_code': code,
            'state_color': self._state_color(code) if code else None,
            'amount': self._val(rec, spec.get('amount')),
            'currency': self._currency(rec),
            'fields': fields[:40],
            'sections': sections,
            'lines': self._lines_for(rec),
            'reports': self._reports_for(env, key, rec.id),
            'editable': editable,
            'can_edit': bool(editable),
            'actions': self._actions_for(env, rec, key, spec),
        }
        if key == 'proposals':
            try:
                payload['proposal'] = self._proposal_extra(rec)
            except Exception:
                pass
        elif key == 'tenders':
            try:
                payload['tender'] = self._tender_extra(rec)
            except Exception:
                pass
        elif key in ('sales', 'purchases', 'invoices'):
            try:
                payload['order'] = self._order_extra(rec)
            except Exception:
                pass
        elif key == 'fleet':
            try:
                payload['fleet'] = self._fleet_extra(rec)
            except Exception:
                pass
        elif key == 'crm':
            try:
                payload['crm'] = self._crm_extra(rec)
            except Exception:
                pass
        elif key == 'leaves':
            try:
                payload['leave'] = self._leave_extra(rec)
            except Exception:
                pass
        elif key == 'experience':
            try:
                payload['experience'] = self._experience_extra(rec)
            except Exception:
                pass
        elif key == 'vehicle_service':
            try:
                payload['vservice'] = self._vs_extra(rec)
            except Exception:
                pass
        elif key == 'correspondence':
            try:
                payload['letter'] = self._letter_extra(rec)
            except Exception:
                pass
        elif key == 'invoice_requests':
            try:
                payload['reqinv'] = self._reqinv_extra(rec)
            except Exception:
                pass
        elif key == 'files':
            try:
                payload['document'] = self._doc_extra(rec)
            except Exception:
                pass
        elif key == 'bio_devices':
            try:
                payload['device'] = self._dev_extra(rec)
            except Exception:
                pass
        elif key == 'approvals':
            try:
                payload['approval'] = self._appr_extra(rec)
            except Exception:
                pass
        elif key == 'legal':
            try:
                payload['legal'] = self._legal_extra(rec)
            except Exception:
                pass
        elif key == 'petrol':
            try:
                payload['petrol'] = self._petrol_extra(rec)
            except Exception:
                pass
        elif key == 'passports':
            try:
                payload['passport'] = self._passport_extra(rec)
            except Exception:
                pass
        # every record: its attachments (chatter + direct), openable in-app
        try:
            payload['attachments'] = self._attachments_for(env, rec)
        except Exception:
            payload['attachments'] = []
        # ---- per-user access overrides ----
        access = self._user_access(env)
        if key in access['no_edit']:
            payload['editable'] = []
            payload['can_edit'] = False
            payload['actions'] = []          # workflow buttons are edit-like
        if access['hide_attachments']:
            payload['attachments'] = []
            payload['hide_attachments'] = True
        if access['hide_amounts']:
            payload['hide_amounts'] = True
        return _ok(payload)

    def _currency(self, rec):
        for f in ('currency_id', 'company_currency_id'):
            if f in rec._fields and rec[f]:
                return rec[f].name
        return None

    # A professional colour per workflow state, so the chip reads at a glance.
    # Keyed by the RAW state code (green = good/won, amber = in-progress,
    # red = rejected/cancelled, blue = fresh/draft, slate = neutral).
    _STATE_COLORS = {
        'draft': '#64748B', 'new': '#3B82F6', 'sent': '#3B82F6',
        'submit': '#F59E0B', 'waiting': '#F59E0B', 'under_study': '#F59E0B',
        'under_review': '#F59E0B', 'under_renewal': '#F59E0B', 'to approve': '#F59E0B',
        'verify': '#F59E0B', 'running': '#0EA5E9', 'confirm': '#F59E0B',
        'validate1': '#F59E0B', 'validate': '#16A34A',
        'approve': '#16A34A', 'approved': '#16A34A', 'posted': '#16A34A', 'post': '#0D9488',
        'done': '#16A34A', 'sale': '#16A34A', 'purchase': '#16A34A',
        'won': '#16A34A', 'contracted': '#0D9488',
        'delay': '#F59E0B', 'fail': '#DC2626',  # legal cases
        'reject': '#DC2626', 'declined': '#DC2626', 'cancel': '#DC2626',
        'refuse': '#DC2626', 'expired': '#DC2626',
        'submitted': '#F59E0B', 'invoiced': '#16A34A', 'rejected': '#DC2626',
        'confirmed': '#16A34A', 'pending': '#F59E0B', 'approved': '#16A34A', 'refused': '#DC2626',
        # HR sub-modules (allowances/bonuses/loans/penalties/eos/custody/permissions)
        'dept': '#F59E0B', 'd_manager': '#F59E0B', 'hr_manager': '#F59E0B', 'accounting': '#0EA5E9',
        'confirm': '#F59E0B', 'ongoing': '#0EA5E9', 'paid': '#16A34A', 'issued': '#16A34A',
        'returned': '#16A34A', 'lost': '#DC2626', 'damaged': '#DC2626',
        # tenders (purchase.tender)
        'under_study': '#F59E0B', 'docs_purchased': '#0EA5E9', 'interested': '#3B82F6',
        'preparing': '#F59E0B', 'participated': '#8B5CF6', 'winner': '#16A34A',
        'purchased': '#0D9488', 'in_progress': '#0EA5E9', 'completed': '#16A34A',
        'lost': '#DC2626', 'excepted': '#94A3B8', 'postponed': '#F59E0B',
        'closed': '#94A3B8', 'cancelled': '#DC2626',
    }

    def _state_color(self, code):
        return self._STATE_COLORS.get(code, '#64748B')

    def _img_b64(self, rec, fields):
        """A small base64 image (string) from the first present field, or None."""
        for fn in fields:
            if fn in rec._fields and rec[fn]:
                v = rec[fn]
                return v.decode() if isinstance(v, bytes) else v
        return None

    # ---- Proposals: professional list + detail enrichment -----------------
    _PROP_COMPONENTS = (
        ('salary_amount', 'الرواتب', 'Salaries'),
        ('material_amount', 'المواد', 'Materials'),
        ('equipment_amount', 'المعدات', 'Equipment'),
        ('transportation_amount', 'المواصلات', 'Transport'),
        ('accommodation_amount', 'السكن', 'Accommodation'),
        ('residency_amount', 'الإقامات', 'Residency'),
        ('uniform_amount', 'الزي الموحد', 'Uniform'),
        ('leave_amount', 'الإجازات والمكافآت', 'Leave & indemnity'),
        ('insurance_amount', 'التأمين', 'Insurance'),
        ('medical_amount', 'الفحص الطبي', 'Medical'),
        ('gate_amount', 'تصاريح الدخول', 'Gate pass'),
        ('fee_amount', 'الرسوم', 'Fees'),
        ('other_amount', 'أخرى', 'Other'),
        ('commission_amount', 'العمولة', 'Commission'),
    )
    _VALIDITY = {
        'valid': ('سارٍ', 'Valid', '#16A34A'),
        'expiring': ('قارب الانتهاء', 'Expiring', '#F59E0B'),
        'expired': ('منتهٍ', 'Expired', '#DC2626'),
        'none': ('—', '—', '#94A3B8'),
    }

    def _proposal_row(self, r):
        """Per-record rich data + stats shown on each proposals list card."""
        vs = r.validity_state or 'none'
        var, ven, vcol = self._VALIDITY.get(vs, self._VALIDITY['none'])
        return {
            'ref': r.ref or '',
            'customer': r.partner_id.display_name if r.partner_id else None,
            'service_type': r.service_type_id.display_name if r.service_type_id else None,
            'cost': round(r.total_pricing_cost or 0.0, 3),
            'sale': round(r.total_amount or 0.0, 3),
            'profit': round(r.margin_amount or 0.0, 3),
            'margin_pct': round(r.margin_percentage or 0.0, 1),
            'manpower': r.manpower_quantity or 0,
            'services': r.service_quantity or 0,
            'validity': vs, 'validity_ar': var, 'validity_en': ven, 'validity_color': vcol,
            'days_to_expire': r.days_to_expire or 0,
            'proposal_date': _d(r.proposal_date),
            'expire_date': _d(r.expire_date),
        }

    def _proposal_stats(self, recs):
        """Header KPIs for the proposals list (over the filtered set)."""
        WON = ('won', 'contracted')
        ACTIVE = ('draft', 'submit', 'waiting', 'approve')
        PENDING = ('submit', 'waiting')
        won = recs.filtered(lambda p: p.state in WON)
        active = recs.filtered(lambda p: p.state in ACTIVE)
        margins = [p.margin_percentage for p in recs if p.margin_percentage]
        cur = (recs[:1].currency_id.name if recs and recs[:1].currency_id else '') or ''
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': len(recs), 'icon': '📊'},
            {'key': 'pending', 'ar': 'بانتظار الاعتماد', 'en': 'Pending',
             'value': len(recs.filtered(lambda p: p.state in PENDING)), 'icon': '⏳', 'color': '#F59E0B'},
            {'key': 'won', 'ar': 'مكتسبة', 'en': 'Won', 'value': len(won), 'icon': '🏆', 'color': '#16A34A'},
            {'key': 'pipeline', 'ar': 'قيمة قيد التداول', 'en': 'Pipeline',
             'value': round(sum(active.mapped('total_amount')), 3), 'unit': cur, 'icon': '💰', 'money': True},
            {'key': 'avg_margin', 'ar': 'متوسط الربح', 'en': 'Avg margin',
             'value': round(sum(margins) / len(margins), 1) if margins else 0.0, 'unit': '%', 'icon': '📈'},
            {'key': 'expiring', 'ar': 'قارب الانتهاء', 'en': 'Expiring',
             'value': len(recs.filtered(lambda p: p.validity_state == 'expiring')), 'icon': '⚠️', 'color': '#DC2626'},
        ]

    def _proposal_extra(self, rec):
        """Rich, professional detail payload for one proposal."""
        cur = (rec.currency_id.name if rec.currency_id else '') or ''
        header = {
            'cost': round(rec.total_pricing_cost or 0.0, 3),
            'sale': round(rec.total_amount or 0.0, 3),
            'profit': round(rec.margin_amount or 0.0, 3),
            'margin_pct': round(rec.margin_percentage or 0.0, 1),
            'individual_cost': round(rec.individual_cost or 0.0, 3),
            'individual_sales': round(rec.individual_sales or 0.0, 3),
            'currency': cur,
        }
        vs = rec.validity_state or 'none'
        var, ven, vcol = self._VALIDITY.get(vs, self._VALIDITY['none'])
        dates = {
            'proposal_date': _d(rec.proposal_date),
            'expire_date': _d(rec.expire_date),
            'mobilization_date': _d(rec.mobilization_date),
            'period': rec.proposal_period or 0,
            'validity': vs, 'validity_ar': var, 'validity_en': ven, 'validity_color': vcol,
            'days_to_expire': rec.days_to_expire or 0,
        }
        breakdown = [{'ar': ar, 'en': en, 'value': round(rec[fn] or 0.0, 3)}
                     for fn, ar, en in self._PROP_COMPONENTS if (rec[fn] or 0.0)]

        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        def sel(fn):
            v = rec[fn]
            try:
                return dict(rec._fields[fn]._description_selection(rec.env)).get(v, v) if v else None
            except Exception:
                return v

        add('العميل', 'Customer', rec.partner_id.display_name if rec.partner_id else None, '🏢')
        add('نوع الخدمة', 'Service type', rec.service_type_id.display_name if rec.service_type_id else None, '🧰')
        add('موقع الخدمة', 'Service site', rec.service_site, '📍')
        add('المدينة', 'City', rec.city, '🗺️')
        add('الهاتف', 'Phone', rec.phone, '📞')
        add('نمط الفوترة', 'Billing mode', sel('mode'), '⏱️')
        add('المدة (شهور)', 'Period (months)', rec.proposal_period or None, '🗓️')
        add('عدد العمالة', 'Manpower', rec.manpower_quantity or None, '👷')
        add('عدد الخدمات', 'Services', rec.service_quantity or None, '🧾')
        add('استراتيجية التسعير', 'Pricing strategy', sel('pricing_strategy'), '🎯')
        add('هامش الربح المستهدف', 'Target margin %', ('%.1f%%' % rec.target_margin_pct) if rec.target_margin_pct else None, '📐')
        add('ملاحظات', 'Notes', rec.notes, '📝')
        # contracts (care.experience) created from this proposal
        contracts = []
        try:
            if 'care.experience' in rec.env:
                exps = rec.env['care.experience'].sudo().search([('proposal_id', '=', rec.id)])
                for e in exps:
                    code = e.state
                    contracts.append({
                        'id': e.id, 'name': e.display_name,
                        'state': self._val(e, 'state'), 'state_code': code,
                        'state_color': self._state_color(code),
                        'start': _d(e.start_date) if 'start_date' in e._fields else None,
                        'partner': e.partner_id.display_name if 'partner_id' in e._fields and e.partner_id else None,
                    })
        except Exception:
            pass
        return {
            'header': header, 'dates': dates, 'breakdown': breakdown,
            'service_info': info, 'contracts': contracts,
            'can_send': bool(rec.partner_id and rec.partner_id.email),
            'send_email': rec.partner_id.email if rec.partner_id else None,
        }

    # ---- Tenders: professional list ---------------------------------------
    _TENDER_ACTIVE = ('new', 'under_study', 'docs_purchased', 'interested',
                      'preparing', 'participated')
    _TENDER_WON = ('winner', 'purchased', 'in_progress', 'completed')

    def _tender_deadline(self, r):
        """A human, coloured countdown to the (effective) closing date."""
        d = r.days_to_close or 0
        active = r.state in self._TENDER_ACTIVE
        eff = r.new_closing_date or r.closing_date
        if not eff:
            return {'days': 0, 'ar': 'بدون موعد', 'en': 'No date', 'color': '#94A3B8', 'urgent': False}
        if not active:
            return {'days': d, 'ar': 'مغلق', 'en': 'Closed', 'color': '#94A3B8', 'urgent': False}
        if d < 0:
            return {'days': d, 'ar': 'انتهى الموعد', 'en': 'Overdue', 'color': '#DC2626', 'urgent': True}
        if d == 0:
            return {'days': 0, 'ar': 'يغلق اليوم', 'en': 'Closes today', 'color': '#DC2626', 'urgent': True}
        if d <= 7:
            return {'days': d, 'ar': 'متبقٍ %d يوم' % d, 'en': '%d days left' % d, 'color': '#F59E0B', 'urgent': True}
        return {'days': d, 'ar': 'متبقٍ %d يوم' % d, 'en': '%d days left' % d, 'color': '#16A34A', 'urgent': False}

    def _tender_row(self, r):
        cur = (r.currency_id.name if r.currency_id else '') or ''
        return {
            'logo_b64': self._img_b64(r, ('image_128',)),
            'organization': r.organization.display_name if r.organization else None,
            'tender_no': r.tender_no or '',
            'currency': cur,
            'price': round(r.price or 0.0, 3),
            'our_price': round(r.our_price or 0.0, 3),
            'guarantee': round(r.guarantee or 0.0, 3),
            'manpower': r.manpower or 0,
            'period': r.period or 0,
            'bid_type': r.bid_type.display_name if r.bid_type else None,
            'classification': r.classification_id.display_name if r.classification_id else None,
            'win_probability': round(r.win_probability or 0.0, 0),
            'prep_score': round(r.prep_score or 0.0, 0),
            'care_rank': r.care_rank or 0,
            'winner': r.winner.display_name if r.winner else None,
            'closing_date': _d(r.new_closing_date or r.closing_date),
            'issue_date': _d(r.issue_date),
            'deadline': self._tender_deadline(r),
        }

    def _tender_stats(self, recs):
        cur = (recs[:1].currency_id.name if recs and recs[:1].currency_id else '') or ''
        active = recs.filtered(lambda t: t.state in self._TENDER_ACTIVE)
        won = recs.filtered(lambda t: t.state in self._TENDER_WON)
        closing_soon = active.filtered(lambda t: 0 <= (t.days_to_close or 0) <= 7)
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': len(recs), 'icon': '📑'},
            {'key': 'active', 'ar': 'نشطة', 'en': 'Active', 'value': len(active), 'icon': '🟢', 'color': '#16A34A'},
            {'key': 'soon', 'ar': 'تُغلق قريبًا', 'en': 'Closing soon',
             'value': len(closing_soon), 'icon': '⏰', 'color': '#DC2626'},
            {'key': 'won', 'ar': 'فائزة', 'en': 'Won', 'value': len(won), 'icon': '🏆', 'color': '#16A34A'},
            {'key': 'value', 'ar': 'قيمة نشطة', 'en': 'Active value',
             'value': round(sum(active.mapped('price')), 3), 'unit': cur, 'icon': '💰', 'money': True},
            {'key': 'guarantee', 'ar': 'الضمانات', 'en': 'Guarantees',
             'value': round(sum(active.mapped('guarantee')), 3), 'unit': cur, 'icon': '🛡️', 'money': True},
        ]

    # one2many "tabs" surfaced as icon tiles on the tender detail. Each opens a
    # sub-list via /management/tenders/<id>/tab/<code>.
    _TENDER_TABS = [
        ('price_analysis_ids', 'price', '📊', 'تحليل الأسعار', 'Price analysis'),
        ('manpower_analysis_ids', 'manpower', '👷', 'تحليل العمالة', 'Manpower analysis'),
        ('vehicle_analysis_ids', 'vehicle', '🚚', 'تحليل المركبات', 'Vehicle analysis'),
        ('equipment_analysis_ids', 'equipment', '🛠️', 'تحليل المعدات', 'Equipment analysis'),
        ('material_info_ids', 'material', '📦', 'بيانات المواد', 'Material info'),
        ('initial_meeting_ids', 'meeting', '🤝', 'الاجتماعات التمهيدية', 'Initial meetings'),
        ('requirement_ids', 'requirement', '📋', 'المتطلبات', 'Requirements'),
        ('checklist_ids', 'checklist', '✅', 'قائمة التحضير', 'Checklist'),
        ('third_party_ids', 'thirdparty', '🏢', 'أطراف أخرى', 'Third parties'),
    ]

    def _tender_extra(self, rec):
        cur = (rec.currency_id.name if rec.currency_id else '') or ''
        header = {
            'price': round(rec.price or 0.0, 3),
            'our_price': round(rec.our_price or 0.0, 3),
            'price_gap': round(rec.price_gap or 0.0, 3),
            'price_gap_pct': round(rec.price_gap_pct or 0.0, 1),
            'win_probability': round(rec.win_probability or 0.0, 0),
            'prep_score': round(rec.prep_score or 0.0, 0),
            'care_rank': rec.care_rank or 0,
            'guarantee': round(rec.guarantee or 0.0, 3),
            'currency': cur,
        }
        dates = {
            'issue_date': _d(rec.issue_date),
            'closing_date': _d(rec.new_closing_date or rec.closing_date),
            'meeting_date': _d(rec.initial_meeting_date),
            'period': rec.period or 0,
            'deadline': self._tender_deadline(rec),
        }
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('الجهة', 'Organization', rec.organization.display_name if rec.organization else None, '🏢')
        add('رقم المناقصة', 'Tender no.', rec.tender_no, '#️⃣')
        add('نوع المناقصة', 'Bid type', rec.bid_type.display_name if rec.bid_type else None, '📁')
        add('التصنيف', 'Classification', rec.classification_id.display_name if rec.classification_id else None, '🏷️')
        add('المدة (شهور)', 'Period (months)', rec.period or None, '🗓️')
        add('العمالة', 'Manpower', rec.manpower or None, '👷')
        add('الشركة الحالية', 'Current contractor', rec.current_co.display_name if rec.current_co else None, '🔄')
        add('الفائز', 'Winner', rec.winner.display_name if rec.winner else None, '🏆')
        add('ترتيبنا', 'Our rank', rec.care_rank or None, '🥇')
        add('بنك الضمان', 'Guarantee bank', rec.guarantee_bank, '🏦')
        tabs = []
        for fname, code, icon, ar, en in self._TENDER_TABS:
            if fname in rec._fields:
                try:
                    cnt = len(rec[fname])
                except Exception:
                    cnt = 0
                tabs.append({'code': code, 'icon': icon, 'ar': ar, 'en': en, 'count': cnt})
        # preparation progress ring on the detail
        prep = {
            'checklist_done': rec.checklist_done or 0,
            'checklist_total': rec.checklist_total or 0,
            'checklist_pct': round(rec.checklist_progress or 0.0, 0),
            'requirement_ready': rec.requirement_ready or 0,
            'requirement_total': rec.requirement_total or 0,
            'requirement_pct': round(rec.requirement_progress or 0.0, 0),
        }
        return {'header': header, 'dates': dates, 'service_info': info,
                'tabs': tabs, 'prep': prep,
                'logo_b64': self._img_b64(rec, ('image_128',))}

    _TENDER_TAB_MODELS = {t[1]: t[0] for t in [
        ('price_analysis_ids', 'price', None, None, None),
        ('manpower_analysis_ids', 'manpower', None, None, None),
        ('vehicle_analysis_ids', 'vehicle', None, None, None),
        ('equipment_analysis_ids', 'equipment', None, None, None),
        ('material_info_ids', 'material', None, None, None),
        ('initial_meeting_ids', 'meeting', None, None, None),
        ('requirement_ids', 'requirement', None, None, None),
        ('checklist_ids', 'checklist', None, None, None),
        ('third_party_ids', 'thirdparty', None, None, None),
    ]}

    def _tender_tab_lines(self, rec, fname):
        return self._records_to_lines(rec[fname])

    def _records_to_lines(self, recs):
        """Read a recordset into display rows: title + up to 5 label:value
        pairs (non-relational + m2o names), skipping technical fields."""
        out = []
        for l in recs:
            lm = l._fields
            title = l.display_name or '—'
            pairs = []
            for nm, f in lm.items():
                if len(pairs) >= 5:
                    break
                if nm in ('id', 'display_name', 'tender_id', 'sequence', 'company_id',
                          'currency_id', 'create_uid', 'write_uid', 'create_date',
                          'write_date', '__last_update') or nm.startswith(('message_', 'activity_')):
                    continue
                if f.type in ('one2many', 'many2many', 'binary', 'image', 'html', 'text'):
                    continue
                if SENSITIVE_RE.search(nm):
                    continue
                try:
                    v = self._val(l, nm)
                except Exception:
                    continue
                if v in (None, '', False):
                    continue
                pairs.append({'label': f.string, 'value': v, 'type': f.type})
            out.append({'name': (title or '').split('\n')[0][:90], 'pairs': pairs})
            if len(out) >= 200:
                break
        return out

    # ---- Employees: photo + work status + live attendance -----------------
    def _employee_row(self, r):
        att_map = {'checked_in': ('حاضر الآن', 'On duty', '#16A34A'),
                   'checked_out': ('خارج', 'Off', '#94A3B8')}
        aar, aen, acol = att_map.get(r.attendance_state or '', ('—', '—', '#94A3B8'))
        pres_map = {'present': ('حاضر', 'Present', '#16A34A'),
                    'absent': ('غائب', 'Absent', '#DC2626'),
                    'to_define': ('غير محدد', '—', '#94A3B8')}
        par, pen, pcol = pres_map.get(r.hr_presence_state or '', ('—', '—', '#94A3B8'))
        try:
            etype = dict(r._fields['employee_type']._description_selection(r.env)).get(r.employee_type)
        except Exception:
            etype = None
        return {
            'photo_b64': self._img_b64(r, ('image_128',)),
            'job': r.job_title or (r.job_id.display_name if 'job_id' in r._fields and r.job_id else None),
            'department': r.department_id.display_name if r.department_id else None,
            'active': bool(r.active),
            'employee_type': etype,
            'attendance': r.attendance_state or '', 'attendance_ar': aar,
            'attendance_en': aen, 'attendance_color': acol,
            'presence_ar': par, 'presence_en': pen, 'presence_color': pcol,
            'phone': r.work_phone or r.mobile_phone or None,
        }

    def _employee_stats(self, env, Model, dom):
        """Cheap DB-side employee KPIs (safe on thousands of rows)."""
        total = Model.with_context(active_test=False).search_count(dom)
        active = Model.search_count(dom)
        depts = 0
        try:
            depts = len(Model.read_group(dom, ['department_id'], ['department_id']))
        except Exception:
            pass
        on_leave = 0
        try:
            today = fields.Date.context_today(Model)
            on_leave = env['hr.leave'].sudo().search_count([
                ('state', '=', 'validate'),
                ('date_from', '<=', str(today) + ' 23:59:59'),
                ('date_to', '>=', str(today) + ' 00:00:00')])
        except Exception:
            pass
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': total, 'icon': '👥'},
            {'key': 'active', 'ar': 'نشطون', 'en': 'Active', 'value': active, 'icon': '🟢', 'color': '#16A34A'},
            {'key': 'archived', 'ar': 'مؤرشفون', 'en': 'Archived', 'value': total - active, 'icon': '🗄️', 'color': '#94A3B8'},
            {'key': 'on_leave', 'ar': 'في إجازة اليوم', 'en': 'On leave today', 'value': on_leave, 'icon': '🌴', 'color': '#F59E0B'},
            {'key': 'depts', 'ar': 'الأقسام', 'en': 'Departments', 'value': depts, 'icon': '🏢'},
        ]

    def _employee_filters(self, env):
        """Options for the employee list filter chips (departments + types)."""
        depts = env['hr.department'].sudo().search([], order='name', limit=200)
        try:
            types = [{'v': k, 'l': l} for k, l in
                     env['hr.employee']._fields['employee_type']._description_selection(env)]
        except Exception:
            types = []
        return {
            'departments': [{'v': d.id, 'l': d.display_name} for d in depts],
            'types': types,
        }

    # ---- Orders (sales / purchases / invoices): partner logo + status -----
    _PAY_COLORS = {'paid': '#16A34A', 'in_payment': '#0EA5E9', 'partial': '#F59E0B',
                   'not_paid': '#DC2626', 'reversed': '#94A3B8'}
    _INVSTAT = {'invoiced': ('مفوترة', 'Invoiced', '#16A34A'),
                'to invoice': ('للفوترة', 'To invoice', '#F59E0B'),
                'no': ('لا فوترة', 'Nothing to invoice', '#94A3B8'),
                'upselling': ('بيع إضافي', 'Upselling', '#8B5CF6')}
    _RECEIPT = {'full': ('مستلمة كاملة', 'Fully received', '#16A34A'),
                'receipted': ('مستلمة', 'Received', '#16A34A'),
                'partial': ('مستلمة جزئيًا', 'Partial', '#F59E0B'),
                'to_receipt': ('للاستلام', 'To receive', '#F59E0B'),
                'pending': ('لم تُستلم', 'Not received', '#DC2626'),
                'processing': ('قيد المعالجة', 'Processing', '#0EA5E9'),
                'nothing': ('لا تسليم', 'Nothing', '#94A3B8')}
    _PICKING_STATE = {'draft': ('مسودة', 'Draft', '#64748B'),
                      'waiting': ('بانتظار', 'Waiting', '#F59E0B'),
                      'confirmed': ('بانتظار', 'Waiting', '#F59E0B'),
                      'assigned': ('جاهز', 'Ready', '#0EA5E9'),
                      'done': ('تم', 'Done', '#16A34A'),
                      'cancel': ('ملغى', 'Cancelled', '#DC2626')}

    def _order_row(self, r):
        lm = r._fields
        cur = (r.currency_id.name if 'currency_id' in lm and r.currency_id else '') or ''
        partner = r.partner_id if 'partner_id' in lm else None
        line_field = next((f for f in ('order_line', 'invoice_line_ids') if f in lm), None)
        n_lines = 0
        if line_field:
            try:
                n_lines = len(r[line_field].filtered(lambda l: not (('display_type' in l._fields) and l.display_type)))
            except Exception:
                n_lines = len(r[line_field])
        out = {
            'logo_b64': self._img_b64(partner, ('image_128',)) if partner else None,
            'partner': partner.display_name if partner else None,
            'amount': round((r.amount_total if 'amount_total' in lm else 0.0) or 0.0, 3),
            'currency': cur,
            'lines': n_lines,
            'salesperson': r.user_id.display_name if 'user_id' in lm and r.user_id else None,
        }
        if 'invoice_status' in lm and r.invoice_status:
            iar, ien, icol = self._INVSTAT.get(r.invoice_status, (r.invoice_status, r.invoice_status, '#94A3B8'))
            out.update({'inv_ar': iar, 'inv_en': ien, 'inv_color': icol})
        if 'payment_state' in lm and r.payment_state:
            try:
                plabel = dict(r._fields['payment_state']._description_selection(r.env)).get(r.payment_state, r.payment_state)
            except Exception:
                plabel = r.payment_state
            out.update({'pay_label': plabel, 'pay_color': self._PAY_COLORS.get(r.payment_state, '#94A3B8'),
                        'residual': round((r.amount_residual or 0.0) if 'amount_residual' in lm else 0.0, 3)})
        return out

    def _order_extra(self, rec):
        """Professional financial detail for a sale/purchase order or invoice."""
        lm = rec._fields
        cur = self._currency(rec) or ''

        def f(x):
            return round(((rec[x] or 0.0) if x in lm else 0.0), 3)

        header = {'untaxed': f('amount_untaxed'), 'tax': f('amount_tax'),
                  'total': f('amount_total'), 'currency': cur}
        if 'amount_residual' in lm:
            header['residual'] = f('amount_residual')
            header['paid'] = round(header['total'] - header['residual'], 3)
        status = {}
        if 'invoice_status' in lm and rec.invoice_status:
            iar, ien, icol = self._INVSTAT.get(rec.invoice_status, (rec.invoice_status, rec.invoice_status, '#94A3B8'))
            status.update({'inv_ar': iar, 'inv_en': ien, 'inv_color': icol})
        if 'payment_state' in lm and rec.payment_state:
            try:
                plabel = dict(rec._fields['payment_state']._description_selection(rec.env)).get(rec.payment_state, rec.payment_state)
            except Exception:
                plabel = rec.payment_state
            status.update({'pay_label': plabel, 'pay_color': self._PAY_COLORS.get(rec.payment_state, '#94A3B8')})
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        p = rec.partner_id if 'partner_id' in lm else None
        add('العميل/المورّد', 'Partner', p.display_name if p else None, '🏢')
        if p:
            add('الهاتف', 'Phone', p.phone or p.mobile, '📞')
            add('البريد', 'Email', p.email, '✉️')
            add('العنوان', 'Address', ', '.join([x for x in [p.city, p.country_id.name if p.country_id else None] if x]) or None, '📍')
        for fld, ar, en, ic in (('date_order', 'تاريخ الأمر', 'Order date', '📅'),
                                ('invoice_date', 'تاريخ الفاتورة', 'Invoice date', '📅'),
                                ('invoice_date_due', 'تاريخ الاستحقاق', 'Due date', '⏰'),
                                ('date_planned', 'الاستلام المتوقع', 'Planned', '🚚'),
                                ('validity_date', 'صالح حتى', 'Valid until', '⏳')):
            if fld in lm and rec[fld]:
                add(ar, en, _d(rec[fld]), ic)
        sp = (rec.user_id if 'user_id' in lm else None) or (rec.invoice_user_id if 'invoice_user_id' in lm else None)
        add('المسؤول', 'Responsible', sp.display_name if sp else None, '👤')
        if 'payment_term_id' in lm and rec.payment_term_id:
            add('شروط الدفع', 'Payment terms', rec.payment_term_id.display_name, '🧾')
        # receipt/delivery status (purchase orders)
        if 'receipt_status' in lm and rec.receipt_status:
            rar, ren, rcol = self._RECEIPT.get(rec.receipt_status, (rec.receipt_status, rec.receipt_status, '#94A3B8'))
            status.update({'recv_ar': rar, 'recv_en': ren, 'recv_color': rcol})
        # delivery + invoice tabs (purchase orders)
        tabs = []
        if 'picking_ids' in lm:
            try:
                nrec = len(rec.picking_ids)
            except Exception:
                nrec = 0
            if nrec:
                tabs.append({'code': 'deliveries', 'icon': '🚚', 'ar': 'التسليمات', 'en': 'Deliveries', 'count': nrec})
        if 'invoice_ids' in lm:
            try:
                ninv = rec.invoice_count if 'invoice_count' in lm else len(rec.invoice_ids)
            except Exception:
                ninv = 0
            if ninv:
                tabs.append({'code': 'invoices', 'icon': '🧾', 'ar': 'الفواتير', 'en': 'Invoices', 'count': ninv})
        can_send = bool(rec._name == 'purchase.order' and p and p.email
                        and (rec.state if 'state' in lm else '') in ('draft', 'sent', 'to approve'))
        return {'header': header, 'status': status, 'service_info': info, 'tabs': tabs,
                'can_send': can_send, 'send_email': p.email if p else None,
                'logo_b64': self._img_b64(p, ('image_128',)) if p else None}

    # ---- Fleet (vehicles) -------------------------------------------------
    def _fleet_state_color(self, name):
        n = (name or '').lower()
        if any(k in n for k in ('sold', 'scrap', 'inactive', 'مباع', 'خردة')):
            return '#DC2626'
        if any(k in n for k in ('reserve', 'waiting', 'order', 'حجز', 'انتظار')):
            return '#F59E0B'
        return '#16A34A'

    def _fleet_row(self, r):
        st = r.state_id.name if r.state_id else None
        try:
            fuel = dict(r._fields['fuel_type']._description_selection(r.env)).get(
                r.fuel_type) if 'fuel_type' in r._fields and r.fuel_type else None
        except Exception:
            fuel = None
        return {
            'image_b64': self._img_b64(r, ('image_128',)),
            'plate': r.license_plate or '',
            'model': r.model_id.display_name if r.model_id else None,
            'driver': r.driver_id.display_name if r.driver_id else None,
            'odometer': round(r.odometer or 0.0, 0),
            'fuel': fuel,
            'year': r.model_year or None,
            'state': st,
            'state_color': self._fleet_state_color(st),
        }

    def _fleet_extra(self, rec):
        lm = rec._fields

        def sel(fn):
            try:
                return dict(rec._fields[fn]._description_selection(rec.env)).get(rec[fn]) if rec[fn] else None
            except Exception:
                return None

        specs = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False, 0, 0.0):
                specs.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('السائق', 'Driver', rec.driver_id.display_name if rec.driver_id else None, '🧑‍✈️')
        add('العدّاد', 'Odometer', '%s' % round(rec.odometer or 0.0, 0), '🛣️')
        add('الوقود', 'Fuel', sel('fuel_type'), '⛽')
        add('سنة الصنع', 'Model year', rec.model_year, '📆')
        add('اللون', 'Color', rec.color, '🎨')
        add('المقاعد', 'Seats', rec.seats, '💺')
        add('الأبواب', 'Doors', rec.doors, '🚪')
        add('تاريخ الاقتناء', 'Acquired', _d(rec.acquisition_date), '📥')
        add('قيمة المركبة', 'Vehicle value', round(rec.car_value or 0.0, 3) or None, '💰')
        n_drivers = len(rec.log_drivers) if 'log_drivers' in lm else 0
        n_serv = len(rec.log_services) if 'log_services' in lm else 0
        n_contract = len(rec.log_contracts) if 'log_contracts' in lm else 0
        n_odo = rec.env['fleet.vehicle.odometer'].search_count([('vehicle_id', '=', rec.id)])
        counts = [
            {'code': 'services', 'icon': '🔧', 'ar': 'الصيانة', 'en': 'Services', 'count': n_serv},
            {'code': 'contracts', 'icon': '📄', 'ar': 'العقود', 'en': 'Contracts', 'count': n_contract},
            {'code': 'drivers', 'icon': '🧑‍✈️', 'ar': 'السائقون', 'en': 'Drivers', 'count': n_drivers},
            {'code': 'odometer', 'icon': '🛣️', 'ar': 'العدّاد', 'en': 'Odometer', 'count': n_odo},
        ]
        # nearest contract expiry (open/future contracts)
        contract = None
        if 'log_contracts' in lm:
            open_c = rec.log_contracts.filtered(
                lambda ct: ct.state in ('open', 'futur') and ct.expiration_date)
            if open_c:
                exp = min(open_c.mapped('expiration_date'))
                today = fields.Date.context_today(rec)
                days = (exp - today).days
                col = '#16A34A' if days > 30 else ('#F59E0B' if days >= 0 else '#DC2626')
                contract = {'expiry': _d(exp), 'days': days, 'color': col}
        return {
            'image_b64': self._img_b64(rec, ('image_256', 'image_512', 'image_128')),
            'plate': rec.license_plate or '',
            'model': rec.model_id.display_name if rec.model_id else None,
            'state': rec.state_id.name if rec.state_id else None,
            'state_color': self._fleet_state_color(rec.state_id.name if rec.state_id else None),
            'specs': specs, 'counts': counts, 'contract': contract,
        }

    _FLEET_LOGS = {'services': 'log_services', 'contracts': 'log_contracts',
                   'drivers': 'log_drivers'}

    def _crm_extra(self, rec):
        cur = (rec.company_currency.name if rec.company_currency else '') or ''
        header = {
            'expected': round(rec.expected_revenue or 0.0, 3),
            'probability': round(rec.probability or 0.0, 0),
            'stage': rec.stage_id.display_name if rec.stage_id else None,
            'stage_color': self._crm_stage_color(rec),
            'currency': cur,
        }
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('العميل', 'Customer', rec.partner_id.display_name if rec.partner_id else None, '🏢')
        add('جهة الاتصال', 'Contact', rec.contact_name, '👤')
        add('المسمّى', 'Job position', rec.function, '💼')
        add('البريد', 'Email', rec.email_from, '✉️')
        add('الهاتف', 'Phone', rec.phone, '📞')
        add('المدينة', 'City', rec.city, '🗺️')
        add('الدولة', 'Country', rec.country_id.name if rec.country_id else None, '🌍')
        add('مندوب المبيعات', 'Salesperson', rec.user_id.display_name if rec.user_id else None, '🧑‍💼')
        add('الموعد النهائي', 'Deadline', _d(rec.date_deadline), '⏰')
        if rec.tag_ids:
            add('الوسوم', 'Tags', ', '.join(rec.tag_ids.mapped('name')), '🏷️')
        return {'header': header, 'service_info': info,
                'logo_b64': self._img_b64(rec.partner_id, ('image_128',)) if rec.partner_id else None}

    def _leave_extra(self, rec):
        emp = rec.employee_id if 'employee_id' in rec._fields else None
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('الموظف', 'Employee', emp.display_name if emp else None, '👤')
        add('نوع الإجازة', 'Type', rec.holiday_status_id.display_name if rec.holiday_status_id else None, '🌴')
        add('القسم', 'Department', rec.department_id.display_name if rec.department_id else None, '🏢')
        add('المدير', 'Manager', rec.manager_id.display_name if 'manager_id' in rec._fields and rec.manager_id else None, '🧑‍💼')
        add('المدة', 'Duration', rec.duration_display if 'duration_display' in rec._fields else None, '⏱️')
        add('السبب', 'Reason', rec.name, '📝')
        return {
            'photo_b64': self._img_b64(emp, ('image_256', 'image_128')) if emp else None,
            'employee': emp.display_name if emp else None,
            'leave_type': rec.holiday_status_id.display_name if rec.holiday_status_id else None,
            'days': round(rec.number_of_days or 0.0, 1),
            'date_from': _d(rec.date_from), 'date_to': _d(rec.date_to),
            'service_info': info,
        }

    # ---- Experience / contracts ------------------------------------------
    _EXP_ACTIVE = ('valid', 'under_renewal')

    def _exp_expiry(self, rec):
        d = rec.days_to_expiry if 'days_to_expiry' in rec._fields else 0
        if rec.state not in self._EXP_ACTIVE:
            return {'days': d, 'color': '#94A3B8'}
        col = '#16A34A' if d > 30 else ('#F59E0B' if d >= 0 else '#DC2626')
        return {'days': d, 'color': col}

    def _experience_row(self, r):
        return {
            'logo_b64': self._img_b64(r.partner_id, ('image_128',)) if ('partner_id' in r._fields and r.partner_id) else None,
            'partner': r.partner_id.display_name if ('partner_id' in r._fields and r.partner_id) else None,
            'start': _d(r.start_date) if 'start_date' in r._fields else None,
            'days_to_expiry': r.days_to_expiry if 'days_to_expiry' in r._fields else 0,
            'expiry': self._exp_expiry(r),
            'renewed': len(r.renewal_ids) if 'renewal_ids' in r._fields else 0,
            'guarantees': len(r.guarantee_ids) if 'guarantee_ids' in r._fields else 0,
        }

    def _experience_stats(self, Model, dom):
        active = Model.search_count(dom + [('state', 'in', list(self._EXP_ACTIVE))])
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '🏆'},
            {'key': 'active', 'ar': 'سارية', 'en': 'Active', 'value': active, 'icon': '🟢', 'color': '#16A34A'},
            {'key': 'renewal', 'ar': 'تحت التجديد', 'en': 'Under renewal',
             'value': Model.search_count(dom + [('state', '=', 'under_renewal')]), 'icon': '🔄', 'color': '#F59E0B'},
            {'key': 'expired', 'ar': 'منتهية', 'en': 'Expired',
             'value': Model.search_count(dom + [('state', '=', 'expired')]), 'icon': '⛔', 'color': '#DC2626'},
        ]

    _EXP_LOGS = {'renewals': 'renewal_ids', 'guarantees': 'guarantee_ids', 'lines': 'line_ids'}

    def _experience_extra(self, rec):
        lm = rec._fields
        exp = self._exp_expiry(rec)
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('العميل', 'Customer', rec.partner_id.display_name if ('partner_id' in lm and rec.partner_id) else None, '🏢')
        add('تاريخ البدء', 'Start date', _d(rec.start_date) if 'start_date' in lm else None, '📅')
        if 'service_type_id' in lm and rec.service_type_id:
            add('نوع الخدمة', 'Service type', rec.service_type_id.display_name, '🧰')
        # source references (proposal / tender) — openable
        refs = []
        if 'proposal_id' in lm and rec.proposal_id:
            refs.append({'key': 'proposals', 'id': rec.proposal_id.id,
                         'name': rec.proposal_id.display_name, 'ar': 'عرض السعر', 'en': 'Proposal', 'icon': '📊'})
        if 'tender_id' in lm and rec.tender_id:
            refs.append({'key': 'tenders', 'id': rec.tender_id.id,
                         'name': rec.tender_id.display_name, 'ar': 'المناقصة', 'en': 'Tender', 'icon': '📑'})
        tabs = []
        for code, fname in self._EXP_LOGS.items():
            if fname in lm:
                try:
                    cnt = len(rec[fname])
                except Exception:
                    cnt = 0
                icon = {'renewals': '🔄', 'guarantees': '🛡️', 'lines': '📋'}[code]
                ar = {'renewals': 'التمديدات', 'guarantees': 'الكفالات', 'lines': 'البنود'}[code]
                en = {'renewals': 'Renewals', 'guarantees': 'Guarantees', 'lines': 'Lines'}[code]
                tabs.append({'code': code, 'icon': icon, 'ar': ar, 'en': en, 'count': cnt})
        return {
            'expiry': exp,
            'days_to_expiry': rec.days_to_expiry if 'days_to_expiry' in lm else 0,
            'is_renewed': bool('renewal_ids' in lm and rec.renewal_ids),
            'service_info': info, 'refs': refs, 'tabs': tabs,
        }

    # ---- Correspondence / letters (care.letter) ---------------------------
    def _letter_type_label(self, rec):
        try:
            return dict(rec._fields['letter_type']._description_selection(rec.env)).get(rec.letter_type) if rec.letter_type else None
        except Exception:
            return rec.letter_type

    def _letter_row(self, r):
        emp = r.employee_id if 'employee_id' in r._fields else None
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'employee': emp.display_name if emp else None,
            'letter_type': self._letter_type_label(r),
            'date': _d(r.date) if 'date' in r._fields else None,
        }

    def _letter_stats(self, Model, dom):
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '✉️'},
            {'key': 'draft', 'ar': 'مسودّات', 'en': 'Draft',
             'value': Model.search_count(dom + [('state', '=', 'draft')]), 'icon': '📝', 'color': '#64748B'},
            {'key': 'issued', 'ar': 'صادرة', 'en': 'Issued',
             'value': Model.search_count(dom + [('state', '=', 'issued')]), 'icon': '✅', 'color': '#16A34A'},
        ]

    def _letter_extra(self, rec):
        lm = rec._fields
        emp = rec.employee_id if 'employee_id' in lm else None
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('الموظف', 'Employee', emp.display_name if emp else None, '👤')
        add('نوع الخطاب', 'Letter type', self._letter_type_label(rec), '📄')
        add('موجَّه إلى', 'Addressed to', rec.addressed_to if 'addressed_to' in lm else None, '📮')
        add('التاريخ', 'Date', _d(rec.date) if 'date' in lm else None, '📅')
        try:
            add('الحالة', 'Status', dict(rec._fields['state']._description_selection(rec.env)).get(rec.state) if 'state' in lm else None, '🔖')
        except Exception:
            pass
        if 'department_id' in lm and rec.department_id:
            add('القسم', 'Department', rec.department_id.display_name, '🏢')
        body = None
        if 'body' in lm and rec.body:
            body = (rec.body or '')[:4000]
        return {
            'photo_b64': self._img_b64(emp, ('image_256', 'image_128')) if emp else None,
            'employee': emp.display_name if emp else None,
            'letter_type': self._letter_type_label(rec),
            'addressed_to': rec.addressed_to if 'addressed_to' in lm else None,
            'service_info': info, 'body': body,
        }

    # ---- Invoice requests (request.invoice) -------------------------------
    def _reqinv_row(self, r):
        lm = r._fields
        p = r.partner_id if 'partner_id' in lm else None
        return {
            'logo_b64': self._img_b64(p, ('image_128',)) if p else None,
            'partner': p.display_name if p else None,
            'amount': round((r.amount_total or 0.0) if 'amount_total' in lm else 0.0, 3),
            'currency': self._currency(r) or '',
            'invoice_count': r.invoice_count if 'invoice_count' in lm else 0,
            'delivered': bool(r.x_studio_delivered) if 'x_studio_delivered' in lm else False,
            'lines': len(r.request_invoice_id) if 'request_invoice_id' in lm else 0,
            'project': r.project_id.display_name if ('project_id' in lm and r.project_id) else None,
            'date': _d(r.invoice_date) if 'invoice_date' in lm else None,
        }

    def _reqinv_stats(self, Model, dom):
        cur = ''
        c = Model.search(dom, limit=1)
        if c:
            cur = self._currency(c) or ''
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '📥'},
            {'key': 'pending', 'ar': 'قيد المعالجة', 'en': 'Pending',
             'value': Model.search_count(dom + [('state', 'in', ['draft', 'submitted'])]), 'icon': '⏳', 'color': '#F59E0B'},
            {'key': 'invoiced', 'ar': 'مُفوترة', 'en': 'Invoiced',
             'value': Model.search_count(dom + [('state', '=', 'invoiced')]), 'icon': '✅', 'color': '#16A34A'},
            {'key': 'value', 'ar': 'إجمالي القيمة', 'en': 'Total value',
             'value': self._sum_field(Model, dom, 'amount_total'),
             'unit': cur, 'icon': '💰', 'money': True},
        ]

    def _sum_field(self, Model, dom, field):
        try:
            g = Model.read_group(dom, [field], [])
            return round((g[0].get(field) if g else 0.0) or 0.0, 3)
        except Exception:
            return 0.0

    def _reqinv_extra(self, rec):
        lm = rec._fields
        cur = self._currency(rec) or ''
        header = {'amount': round((rec.amount_total or 0.0) if 'amount_total' in lm else 0.0, 3), 'currency': cur}
        status = {
            'delivered': bool(rec.x_studio_delivered) if 'x_studio_delivered' in lm else False,
            'invoice_count': rec.invoice_count if 'invoice_count' in lm else 0,
        }
        # source references (proposal / contract / project) — openable
        refs = []
        if 'proposal_id' in lm and rec.proposal_id:
            refs.append({'key': 'proposals', 'id': rec.proposal_id.id, 'name': rec.proposal_id.display_name, 'ar': 'عرض السعر', 'en': 'Proposal', 'icon': '📊'})
        if 'contract_id' in lm and rec.contract_id:
            refs.append({'key': 'experience', 'id': rec.contract_id.id, 'name': rec.contract_id.display_name, 'ar': 'العقد', 'en': 'Contract', 'icon': '📜'})
        if 'project_id' in lm and rec.project_id:
            refs.append({'key': 'projects', 'id': rec.project_id.id, 'name': rec.project_id.display_name, 'ar': 'المشروع', 'en': 'Project', 'icon': '🏗️'})
        # lines
        lines = []
        if 'request_invoice_id' in lm:
            for l in rec.request_invoice_id:
                llm = l._fields
                lines.append({
                    'name': (l.label or (l.product_id.display_name if 'product_id' in llm and l.product_id else '—')),
                    'qty': l.quantity if 'quantity' in llm else None,
                    'days': l.days if 'days' in llm else None,
                    'price': round(l.price or 0.0, 3) if 'price' in llm else None,
                    'subtotal': round(l.price_subtotal or 0.0, 3) if 'price_subtotal' in llm else None,
                })
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('العميل', 'Customer', rec.partner_id.display_name if ('partner_id' in lm and rec.partner_id) else None, '🏢')
        add('القسم', 'Department', rec.department_id.display_name if ('department_id' in lm and rec.department_id) else None, '🏢')
        add('تاريخ الفاتورة', 'Invoice date', _d(rec.invoice_date) if 'invoice_date' in lm else None, '📅')
        add('مرجع الفاتورة', 'Invoice ref', rec.x_studio_invoice_ref if 'x_studio_invoice_ref' in lm else None, '#️⃣')
        add('المرجع المالي', 'Finance ref', rec.x_studio_finance_ref if 'x_studio_finance_ref' in lm else None, '💳')
        if 'labor_service' in lm and rec.labor_service:
            add('نوع', 'Type', 'خدمة عمالة' if True else 'Labor service', '👷')
        if status['delivered'] and 'x_studio_delivered_date' in lm and rec.x_studio_delivered_date:
            add('تاريخ التسليم', 'Delivered on', _d(rec.x_studio_delivered_date), '🚚')
        return {'header': header, 'status': status, 'refs': refs, 'lines': lines, 'service_info': info}

    # ---- Legal cases (hr.lawsuit) -----------------------------------------
    _LEGAL_STATE = {
        'draft': ('مسودة', 'Draft'), 'running': ('قيد النظر', 'Running'),
        'delay': ('مؤجلة', 'Postponed'), 'cancel': ('ملغاة', 'Cancelled'),
        'fail': ('خاسرة', 'Lost'), 'won': ('كاسبة', 'Won'),
    }

    def _legal_party(self, r):
        lm = r._fields
        who = r.party2 if 'party2' in lm else False
        name = r.party2_name if ('party2_name' in lm and r.party2_name) else None
        if not name:
            if who == 'employee' and r.employee_id:
                name = r.employee_id.display_name
            elif who == 'partner' and 'partner_id' in lm and r.partner_id:
                name = r.partner_id.display_name
            elif 'other_name' in lm:
                name = r.other_name
        return who, name

    def _legal_row(self, r):
        lm = r._fields
        who, party = self._legal_party(r)
        st = r.state if 'state' in lm else 'draft'
        ar, en = self._LEGAL_STATE.get(st, (st, st))
        emp = r.employee_id if ('employee_id' in lm and r.employee_id) else None
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'code': r.name or '—',
            'ref_no': r.ref_no if 'ref_no' in lm else None,
            'party': party, 'party_type': who,
            'court': r.court_name if 'court_name' in lm else None,
            'state': st, 'state_ar': ar, 'state_en': en, 'state_color': self._state_color(st),
            'hearing_date': _d(r.hearing_date) if 'hearing_date' in lm else None,
            'next_appointment': _d(r.next_appointment) if ('next_appointment' in lm and r.next_appointment) else None,
            'updates': len(r.update_ids) if 'update_ids' in lm else 0,
        }

    def _legal_stats(self, Model, dom):
        today = str(fields.Date.today())
        return [
            {'key': 'total', 'ar': 'إجمالي القضايا', 'en': 'Total cases', 'value': Model.search_count(dom), 'icon': '⚖️'},
            {'key': 'running', 'ar': 'قيد النظر', 'en': 'Running',
             'value': Model.search_count(dom + [('state', 'in', ['running', 'delay'])]), 'icon': '🔵', 'color': '#0EA5E9'},
            {'key': 'won', 'ar': 'كاسبة', 'en': 'Won',
             'value': Model.search_count(dom + [('state', '=', 'won')]), 'icon': '🏆', 'color': '#16A34A'},
            {'key': 'lost', 'ar': 'خاسرة', 'en': 'Lost',
             'value': Model.search_count(dom + [('state', '=', 'fail')]), 'icon': '❌', 'color': '#DC2626'},
            {'key': 'upcoming', 'ar': 'جلسات قادمة', 'en': 'Upcoming hearings',
             'value': Model.search_count(dom + [('hearing_date', '>=', today), ('state', 'in', ['draft', 'running', 'delay'])]),
             'icon': '📅', 'color': '#F59E0B'},
        ]

    def _legal_extra(self, rec):
        from odoo.tools import html2plaintext
        lm = rec._fields
        who, party = self._legal_party(rec)
        st = rec.state if 'state' in lm else 'draft'
        ar, en = self._LEGAL_STATE.get(st, (st, st))
        header = {
            'code': rec.name or '—',
            'state': st, 'state_ar': ar, 'state_en': en, 'state_color': self._state_color(st),
            'ref_no': rec.ref_no if 'ref_no' in lm else None,
            'filing_date': _d(rec.requested_date) if 'requested_date' in lm else None,
            'hearing_date': _d(rec.hearing_date) if 'hearing_date' in lm else None,
            'next_appointment': _d(rec.next_appointment) if ('next_appointment' in lm and rec.next_appointment) else None,
        }
        parties = []

        def addp(ar_l, en_l, val, icon):
            if val:
                parties.append({'ar': ar_l, 'en': en_l, 'value': val, 'icon': icon})
        addp('الطرف الأول', 'Party 1', rec.party1.display_name if ('party1' in lm and rec.party1) else None, '🏛️')
        ptype = {'employee': ('موظف', 'Employee'), 'partner': ('جهة', 'Partner'), 'other': ('أخرى', 'Other')}.get(who)
        addp('الطرف الثاني', 'Party 2', (party + (' — %s' % ptype[0] if ptype else '')) if party else None, '👤')
        addp('المحكمة', 'Court', rec.court_name if 'court_name' in lm else None, '🏛️')
        addp('القاضي', 'Judge', rec.judge if 'judge' in lm else None, '⚖️')
        addp('المحامي', 'Lawyer', rec.lawyer.display_name if ('lawyer' in lm and rec.lawyer) else None, '👔')
        details = None
        if 'case_details' in lm and rec.case_details:
            try:
                details = html2plaintext(rec.case_details)
            except Exception:
                details = None
        # the update log (chronological)
        updates = []
        if 'update_ids' in lm:
            for u in rec.update_ids.sorted(key=lambda x: (x.datetime or fields.Datetime.now()), reverse=True):
                ulm = u._fields
                updates.append({
                    'id': u.id,
                    'name': u.name,
                    'datetime': _d(u.datetime) if 'datetime' in ulm else None,
                    'details': u.details if 'details' in ulm else None,
                    'partner': u.partner_id.display_name if ('partner_id' in ulm and u.partner_id) else None,
                })
        return {'header': header, 'parties': parties, 'details': details, 'updates': updates}

    # POST an update onto a legal case (also posts to the chatter).
    @route(API + '/management/legal/<int:rid>/update', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_legal_update(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        acc = self._user_access(env)
        if 'legal' in acc['hidden'] or 'legal' in acc['no_edit']:
            return _err('لا تملك صلاحية إضافة تحديث', 403)
        from .api import _body
        b = _body() or {}
        name = (b.get('name') or '').strip()
        if not name:
            return _err('عنوان التحديث مطلوب', 400)
        rec = env['hr.lawsuit'].browse(rid).exists()
        if not rec:
            return _err('القضية غير موجودة', 404)
        vals = {
            'lawsuit_id': rec.id,
            'name': name,
            'details': (b.get('details') or '').strip() or False,
            'datetime': b.get('datetime') or fields.Datetime.now(),
        }
        try:
            env['hr.lawsuit.update'].create(vals)
            body = name
            if vals['details']:
                body += ' — ' + vals['details']
            rec.message_post(body='📌 %s' % body)
        except Exception as e:
            return _err('تعذّر إضافة التحديث: %s' % e, 400)
        return _ok({'saved': True})

    # ---- Fuel tanks (petrol.tank) -----------------------------------------
    def _petrol_row(self, r):
        lm = r._fields
        cap = r.capacity or 0.0
        bal = r.balance or 0.0
        return {
            'name': r.name or '—',
            'capacity': round(cap, 1), 'balance': round(bal, 1),
            'used': round(r.used or 0.0, 1), 'charged': round(r.charged or 0.0, 1),
            'progress': round((bal / cap * 100.0) if cap else 0.0, 0),
            'stage': r.stage_id.name if ('stage_id' in lm and r.stage_id) else None,
            'last_charge': _d(r.last_charge) if ('last_charge' in lm and r.last_charge) else None,
            'charges': len(r.charge_ids), 'uses': len(r.use_ids), 'transfers': len(r.transfer_ids),
        }

    def _petrol_stats(self, Model, dom):
        tanks = Model.search(dom)
        cap = sum(t.capacity or 0.0 for t in tanks)
        bal = sum(t.balance or 0.0 for t in tanks)
        low = len(tanks.filtered(lambda t: t.capacity and (t.balance / t.capacity) < 0.2))
        return [
            {'key': 'tanks', 'ar': 'الخزانات', 'en': 'Tanks', 'value': len(tanks), 'icon': '⛽'},
            {'key': 'balance', 'ar': 'إجمالي الرصيد', 'en': 'Total balance', 'value': round(bal, 0), 'unit': 'L', 'icon': '🛢️', 'color': '#16A34A'},
            {'key': 'capacity', 'ar': 'السعة الكلية', 'en': 'Total capacity', 'value': round(cap, 0), 'unit': 'L', 'icon': '📊'},
            {'key': 'low', 'ar': 'منخفضة', 'en': 'Low', 'value': low, 'icon': '⚠️', 'color': '#DC2626'},
        ]

    def _petrol_extra(self, rec):
        cap = rec.capacity or 0.0
        bal = rec.balance or 0.0
        header = {
            'capacity': round(cap, 1), 'balance': round(bal, 1),
            'used': round(rec.used or 0.0, 1), 'charged': round(rec.charged or 0.0, 1),
            'incoming': round(rec.positive_transferred or 0.0, 1) if 'positive_transferred' in rec._fields else 0.0,
            'outgoing': round(rec.negative_transferred or 0.0, 1) if 'negative_transferred' in rec._fields else 0.0,
            'progress': round((bal / cap * 100.0) if cap else 0.0, 0),
            'stage': rec.stage_id.name if rec.stage_id else None,
            'last_charge': _d(rec.last_charge) if rec.last_charge else None,
        }
        charges = [{
            'id': c.id, 'name': c.name, 'date': _d(c.charge_date),
            'quantity': round(c.quantity or 0.0, 1), 'cost': round(c.cost or 0.0, 2),
        } for c in rec.charge_ids[:40]]
        uses = [{
            'id': u.id, 'name': u.name,
            'vehicle': u.vehicle_id.display_name if u.vehicle_id else None,
            'quantity': round(u.quantity or 0.0, 1),
            'odometer': round(u.odometer_value or 0.0, 0),
            'rate': round(u.liter_per_km_rate or 0.0, 2) if 'liter_per_km_rate' in u._fields else None,
            'datetime': _d(u.datetime) if u.datetime else None,
        } for u in rec.use_ids[:40]]
        transfers = [{
            'id': t.id,
            'from': t.from_tank_id.name if t.from_tank_id else None,
            'to': t.to_tank_id.name if t.to_tank_id else None,
            'quantity': round(t.quantity or 0.0, 1),
            'date': _d(t.date) if t.date else None,
            'state': t.state,
        } for t in rec.transfer_ids[:40]]
        return {'header': header, 'charges': charges, 'uses': uses, 'transfers': transfers}

    @route(API + '/management/petrol/<int:tid>/charge', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_petrol_charge(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        acc = self._user_access(env)
        if 'petrol' in acc['hidden'] or 'petrol' in acc['no_create']:
            return _err('لا تملك صلاحية الإضافة', 403)
        from .api import _body
        b = _body() or {}
        tank = env['petrol.tank'].browse(tid).exists()
        if not tank:
            return _err('الخزان غير موجود', 404)
        try:
            env['petrol.tank.charge'].create({
                'tank_id': tank.id,
                'charge_date': b.get('charge_date') or fields.Date.today(),
                'quantity': float(b.get('quantity') or 0),
                'cost': float(b.get('cost') or 0),
            })
        except Exception as e:
            return _err('تعذّر إضافة الشحنة: %s' % e, 400)
        return _ok({'saved': True})

    @route(API + '/management/petrol/<int:tid>/use', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_petrol_use(self, tid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        acc = self._user_access(env)
        if 'petrol' in acc['hidden'] or 'petrol' in acc['no_create']:
            return _err('لا تملك صلاحية الإضافة', 403)
        from .api import _body
        b = _body() or {}
        tank = env['petrol.tank'].browse(tid).exists()
        if not tank:
            return _err('الخزان غير موجود', 404)
        vals = {
            'tank_id': tank.id,
            'quantity': float(b.get('quantity') or 0),
            'current_quantity': float(b.get('current_quantity') or 0),
            'odometer_value': float(b.get('odometer_value') or 0),
            'datetime': b.get('datetime') or fields.Datetime.now(),
        }
        if b.get('vehicle_id'):
            try:
                vals['vehicle_id'] = int(b['vehicle_id'])
            except (TypeError, ValueError):
                pass
        try:
            env['petrol.tank.use'].create(vals)
        except Exception as e:
            return _err('تعذّر تسجيل الصرف: %s' % e, 400)
        return _ok({'saved': True})

    # ---- Passports (care.passport) ----------------------------------------
    _PP_EXPIRY = {'valid': ('سارٍ', 'Valid', '#16A34A'), 'expiring': ('قارب الانتهاء', 'Expiring', '#F59E0B'),
                  'expired': ('منتهٍ', 'Expired', '#DC2626')}
    _PP_STATE = {'in_archive': ('بالأرشيف', 'In archive', '#16A34A'), 'out': ('خارج', 'Out', '#F59E0B')}

    def _passport_row(self, r):
        lm = r._fields
        emp = r.employee_id if r.employee_id else None
        ex = r.expiry_state if 'expiry_state' in lm else 'valid'
        ear, een, ecol = self._PP_EXPIRY.get(ex, (ex, ex, '#64748B'))
        sar, sen, scol = self._PP_STATE.get(r.state, (r.state, r.state, '#64748B'))
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'employee': emp.display_name if emp else None,
            'passport_no': r.passport_no if 'passport_no' in lm else None,
            'country': r.country_id.name if ('country_id' in lm and r.country_id) else None,
            'expiry_date': _d(r.expiry_date) if ('expiry_date' in lm and r.expiry_date) else None,
            'expiry_state': ex, 'expiry_ar': ear, 'expiry_en': een, 'expiry_color': ecol,
            'state': r.state, 'state_ar': sar, 'state_en': sen, 'state_color': scol,
            'holder': r.holder_id.display_name if ('holder_id' in lm and r.holder_id) else None,
            'shelf': r.shelf_location if ('shelf_location' in lm and r.shelf_location) else None,
        }

    def _passport_stats(self, Model, dom):
        return [
            {'key': 'total', 'ar': 'إجمالي الجوازات', 'en': 'Passports', 'value': Model.search_count(dom), 'icon': '🛂'},
            {'key': 'archive', 'ar': 'بالأرشيف', 'en': 'In archive',
             'value': Model.search_count(dom + [('state', '=', 'in_archive')]), 'icon': '🗄️', 'color': '#16A34A'},
            {'key': 'out', 'ar': 'خارج العهدة', 'en': 'Out',
             'value': Model.search_count(dom + [('state', '=', 'out')]), 'icon': '📤', 'color': '#F59E0B'},
            {'key': 'expiring', 'ar': 'قاربت الانتهاء', 'en': 'Expiring',
             'value': Model.search_count(dom + [('expiry_state', '=', 'expiring')]), 'icon': '⏳', 'color': '#F59E0B'},
            {'key': 'expired', 'ar': 'منتهية', 'en': 'Expired',
             'value': Model.search_count(dom + [('expiry_state', '=', 'expired')]), 'icon': '⛔', 'color': '#DC2626'},
        ]

    def _passport_extra(self, rec):
        lm = rec._fields
        emp = rec.employee_id if rec.employee_id else None
        row = self._passport_row(rec)
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})
        add('الموظف', 'Employee', emp.display_name if emp else None, '👤')
        add('رقم الجواز', 'Passport no.', rec.passport_no if 'passport_no' in lm else None, '🛂')
        add('الجنسية', 'Nationality', rec.country_id.name if ('country_id' in lm and rec.country_id) else None, '🌍')
        add('تاريخ الإصدار', 'Issue date', _d(rec.issue_date) if ('issue_date' in lm and rec.issue_date) else None, '📅')
        add('تاريخ الانتهاء', 'Expiry date', _d(rec.expiry_date) if ('expiry_date' in lm and rec.expiry_date) else None, '⏰')
        add('الموقع/الرف', 'Shelf', rec.shelf_location if ('shelf_location' in lm and rec.shelf_location) else None, '🗄️')
        add('الحائز الحالي', 'Current holder', rec.holder_id.display_name if ('holder_id' in lm and rec.holder_id) else None, '🤝')
        if 'out_reason' in lm and rec.out_reason:
            try:
                add('سبب الخروج', 'Out reason', dict(rec._fields['out_reason']._description_selection(rec.env)).get(rec.out_reason), '📤')
            except Exception:
                pass
        add('الإرجاع المتوقع', 'Expected return', _d(rec.expected_return) if ('expected_return' in lm and rec.expected_return) else None, '↩️')
        # movement history
        moves = []
        if 'movement_ids' in lm:
            hist = rec.movement_ids
        else:
            hist = rec.env['care.passport.movement'].sudo().search([('passport_ids', 'in', rec.id)], order='date desc', limit=30) if 'care.passport.movement' in rec.env else []
        for m in hist[:30]:
            mlm = m._fields
            try:
                mt = dict(m._fields['movement_type']._description_selection(m.env)).get(m.movement_type) if 'movement_type' in mlm else m.movement_type
            except Exception:
                mt = m.movement_type if 'movement_type' in mlm else None
            moves.append({
                'id': m.id, 'type': m.movement_type if 'movement_type' in mlm else None, 'type_label': mt,
                'custodian': m.custodian_id.display_name if ('custodian_id' in mlm and m.custodian_id) else None,
                'date': _d(m.date) if ('date' in mlm and m.date) else None,
                'shelf': m.shelf_location if ('shelf_location' in mlm and m.shelf_location) else None,
            })
        return {'header': row, 'info': info, 'movements': moves}

    def _passport_move(self, env, rec, mtype, vals):
        """Create a confirmed passport movement (in/out) for one passport."""
        M = env['care.passport.movement'].sudo()
        mv = {'movement_type': mtype, 'passport_ids': [(6, 0, [rec.id])]}
        mv.update(vals)
        rec_mv = M.create(mv)
        if hasattr(rec_mv, 'action_confirm'):
            rec_mv.action_confirm()
        return rec_mv

    @route(API + '/management/passport/<int:pid>/checkout', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_passport_checkout(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        acc = self._user_access(env)
        if 'passports' in acc['hidden'] or 'passports' in acc['no_edit']:
            return _err('لا تملك صلاحية', 403)
        rec = env['care.passport'].browse(pid).exists()
        if not rec:
            return _err('غير موجود', 404)
        from .api import _body
        b = _body() or {}
        vals = {'reason': b.get('reason') or 'travel_leave'}
        if b.get('custodian_id'):
            try:
                vals['custodian_id'] = int(b['custodian_id'])
            except (TypeError, ValueError):
                pass
        if b.get('expected_return'):
            vals['expected_return'] = b['expected_return']
        try:
            self._passport_move(env, rec, 'out', vals)
        except Exception as e:
            return _err('تعذّر تسجيل الخروج: %s' % e, 400)
        return _ok({'saved': True})

    @route(API + '/management/passport/<int:pid>/checkin', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_passport_checkin(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        acc = self._user_access(env)
        if 'passports' in acc['hidden'] or 'passports' in acc['no_edit']:
            return _err('لا تملك صلاحية', 403)
        rec = env['care.passport'].browse(pid).exists()
        if not rec:
            return _err('غير موجود', 404)
        from .api import _body
        b = _body() or {}
        vals = {}
        if b.get('shelf_location'):
            vals['shelf_location'] = b['shelf_location']
        try:
            self._passport_move(env, rec, 'in', vals)
        except Exception as e:
            return _err('تعذّر تسجيل الإرجاع: %s' % e, 400)
        return _ok({'saved': True})

    # ---- Documents (documents.document) -----------------------------------
    def _doc_file(self, r):
        """The openable file descriptor for a document (via ir.attachment)."""
        lm = r._fields
        mt = (r.mimetype or '').lower() if 'mimetype' in lm else ''
        att = r.attachment_id if 'attachment_id' in lm and r.attachment_id else None
        return {
            'name': r.name or 'file',
            'mimetype': mt,
            'is_image': mt.startswith('image/'),
            'is_pdf': mt == 'application/pdf' or (r.name or '').lower().endswith('.pdf'),
            'size': r.file_size if 'file_size' in lm else 0,
            'url': (r.url if ('type' in lm and r.type == 'url' and r.url) else None),
            'att_id': att.id if att else None,
            'att_url': _abs('/api/v1/management/attachment/%s' % att.id) if att else None,
        }

    def _doc_row(self, r):
        lm = r._fields
        f = self._doc_file(r)
        return {
            'name': r.name or '—',
            'folder': r.folder_id.display_name if ('folder_id' in lm and r.folder_id) else None,
            'owner': r.owner_id.display_name if ('owner_id' in lm and r.owner_id) else None,
            'mimetype': f['mimetype'], 'is_image': f['is_image'], 'is_pdf': f['is_pdf'],
            'size': f['size'], 'att_url': f['att_url'], 'url': f['url'],
            'date': _d(r.create_date) if 'create_date' in lm else None,
        }

    def _doc_stats(self, env, Model, dom):
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '🗂️'},
            {'key': 'images', 'ar': 'صور', 'en': 'Images',
             'value': Model.search_count(dom + [('mimetype', 'ilike', 'image/')]), 'icon': '🖼️', 'color': '#0EA5E9'},
            {'key': 'pdfs', 'ar': 'PDF', 'en': 'PDFs',
             'value': Model.search_count(dom + [('mimetype', '=', 'application/pdf')]), 'icon': '📕', 'color': '#DC2626'},
            {'key': 'folders', 'ar': 'المجلّدات', 'en': 'Folders',
             'value': (env['documents.folder'].sudo().search_count([]) if 'documents.folder' in env else 0), 'icon': '📁'},
        ]

    def _doc_extra(self, rec):
        lm = rec._fields
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('المجلّد', 'Folder', rec.folder_id.display_name if ('folder_id' in lm and rec.folder_id) else None, '📁')
        add('المالك', 'Owner', rec.owner_id.display_name if ('owner_id' in lm and rec.owner_id) else None, '👤')
        add('جهة الاتصال', 'Contact', rec.partner_id.display_name if ('partner_id' in lm and rec.partner_id) else None, '🏢')
        add('النوع', 'MIME type', rec.mimetype if 'mimetype' in lm else None, '📄')
        if 'file_size' in lm and rec.file_size:
            add('الحجم', 'Size', '%.0f KB' % (rec.file_size / 1024.0), '💾')
        add('مرتبط بـ', 'Linked to', rec.res_model if ('res_model' in lm and rec.res_model) else None, '🔗')
        add('تاريخ الإضافة', 'Created', _d(rec.create_date) if 'create_date' in lm else None, '📅')
        return {'file': self._doc_file(rec), 'service_info': info}

    def _doc_filters(self, env):
        folders = env['documents.folder'].sudo().search([], order='name', limit=400) if 'documents.folder' in env else []
        return {'folders': [{'v': f.id, 'l': f.display_name} for f in folders]}

    @route(API + '/management/document/<int:did>/share', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_document_share(self, did, **kw):
        """Return a real public share link for a document (Odoo documents.share),
        reusing an existing single-doc link when present — same as the backend
        Share button. Falls back to a token download URL if Documents lacks share."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        doc = env['documents.document'].sudo().browse(did).exists()
        if not doc:
            return _err('غير موجود', 404)
        # gate: the caller must be allowed to read the document
        try:
            doc.check_access_rule('read')
        except Exception:
            return _err('لا تملك صلاحية على هذا المستند', 403)
        # token download URL (always works)
        att = doc.attachment_id if doc.attachment_id else None
        token = _bearer() if callable(_bearer) else None
        dl = None
        if att:
            dl = _abs('/api/v1/management/attachment/%s?download=1&token=%s' % (att.id, token or ''))
        share_url = None
        try:
            Share = env['documents.share'].sudo()
            if doc.folder_id:
                existing = Share.search([('type', '=', 'ids'), ('folder_id', '=', doc.folder_id.id),
                                         ('document_ids', 'in', doc.id)], limit=1)
                sh = existing or Share.create({
                    'name': doc.name or 'مستند',
                    'folder_id': doc.folder_id.id,
                    'type': 'ids',
                    'document_ids': [(6, 0, [doc.id])],
                })
                share_url = sh.full_url
        except Exception:
            share_url = None
        return _ok({'name': doc.name, 'share_url': share_url, 'download_url': dl})

    # ---- Approvals (approval.request) -------------------------------------
    def _appr_row(self, r):
        lm = r._fields
        owner = r.request_owner_id if 'request_owner_id' in lm else None
        cat = r.category_id if 'category_id' in lm else None
        return {
            'photo_b64': self._img_b64(owner, ('image_128',)) if owner else None,
            'owner': owner.display_name if owner else None,
            'category': cat.display_name if cat else None,
            'amount': round(r.amount or 0.0, 3) if ('amount' in lm and r.amount) else 0,
            'approvers': len(r.approver_ids) if 'approver_ids' in lm else 0,
            'date': _d(r.date) if 'date' in lm else None,
        }

    def _appr_stats(self, Model, dom):
        def c(extra):
            return Model.search_count(dom + extra)
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': c([]), 'icon': '✔️'},
            {'key': 'pending', 'ar': 'بانتظار الاعتماد', 'en': 'Pending',
             'value': c([('request_status', 'in', ['new', 'pending'])]), 'icon': '⏳', 'color': '#F59E0B'},
            {'key': 'approved', 'ar': 'معتمدة', 'en': 'Approved',
             'value': c([('request_status', '=', 'approved')]), 'icon': '✅', 'color': '#16A34A'},
            {'key': 'refused', 'ar': 'مرفوضة', 'en': 'Refused',
             'value': c([('request_status', '=', 'refused')]), 'icon': '⛔', 'color': '#DC2626'},
        ]

    def _appr_extra(self, rec):
        lm = rec._fields
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('النوع', 'Category', rec.category_id.display_name if ('category_id' in lm and rec.category_id) else None, '📋')
        add('مقدّم الطلب', 'Requested by', rec.request_owner_id.display_name if ('request_owner_id' in lm and rec.request_owner_id) else None, '👤')
        add('الشريك', 'Partner', rec.partner_id.display_name if ('partner_id' in lm and rec.partner_id) else None, '🏢')
        if 'amount' in lm and rec.amount:
            add('المبلغ', 'Amount', round(rec.amount, 3), '💰')
        add('التاريخ', 'Date', _d(rec.date) if 'date' in lm else None, '📅')
        for fld, ar, en in (('date_start', 'من', 'From'), ('date_end', 'إلى', 'To')):
            if fld in lm and rec[fld]:
                add(ar, en, _d(rec[fld]), '🗓️')
        if 'reason' in lm and rec.reason:
            add('السبب', 'Reason', rec.reason, '📝')
        # approvers
        approvers = []
        if 'approver_ids' in lm:
            for a in rec.approver_ids:
                am = a._fields
                approvers.append({
                    'name': a.user_id.display_name if ('user_id' in am and a.user_id) else '—',
                    'status': self._val(a, 'status') if 'status' in am else None,
                    'status_code': a.status if 'status' in am else None,
                    'status_color': self._state_color(a.status) if 'status' in am else '#94A3B8',
                })
        return {'service_info': info, 'approvers': approvers}

    # ---- Attendance (hr.attendance) ---------------------------------------
    def _att_row(self, r):
        lm = r._fields
        emp = r.employee_id if 'employee_id' in lm else None
        ci, co = r.check_in, r.check_out
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'employee': emp.display_name if emp else None,
            'department': r.department_id.display_name if ('department_id' in lm and r.department_id) else None,
            'check_in': str(ci)[:16] if ci else None,
            'check_out': str(co)[:16] if co else None,
            'hours': round(r.worked_hours or 0.0, 2) if 'worked_hours' in lm else 0,
            'open': bool(ci and not co),
            'date': _d(ci) if ci else None,
        }

    def _att_stats(self, env, Model, dom):
        today = fields.Date.today()
        hgrp = self._sum_field(Model, dom, 'worked_hours')
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '⏱️'},
            {'key': 'today', 'ar': 'اليوم', 'en': 'Today',
             'value': Model.search_count(dom + [('check_in', '>=', str(today) + ' 00:00:00')]), 'icon': '📅', 'color': '#2563EB'},
            {'key': 'open', 'ar': 'مفتوح الآن', 'en': 'Open now',
             'value': Model.search_count(dom + [('check_out', '=', False)]), 'icon': '🟢', 'color': '#16A34A'},
            {'key': 'hours', 'ar': 'إجمالي الساعات', 'en': 'Total hours', 'value': round(hgrp, 1), 'icon': '⏳'},
        ]

    def _att_filters(self, env):
        depts = env['hr.department'].sudo().search([], order='name', limit=200)
        return {'departments': [{'v': d.id, 'l': d.display_name} for d in depts]}

    # ---- Biometric devices (attendance.device) ----------------------------
    def _dev_row(self, r):
        lm = r._fields
        return {
            'name': r.name or r.device_name or '—',
            'ip': r.ip if 'ip' in lm else None,
            'port': r.port if 'port' in lm else None,
            'location': r.location_id.display_name if ('location_id' in lm and r.location_id) else None,
            'stalled': bool(r.is_stalled) if 'is_stalled' in lm else False,
            'log_count': r.data_log_count if 'data_log_count' in lm else 0,
            'active': bool(r.active) if 'active' in lm else True,
        }

    def _dev_stats(self, Model, dom):
        return [
            {'key': 'total', 'ar': 'الأجهزة', 'en': 'Devices', 'value': Model.search_count(dom), 'icon': '🔌'},
            {'key': 'confirmed', 'ar': 'مؤكّدة', 'en': 'Confirmed',
             'value': Model.search_count(dom + [('state', '=', 'confirmed')]), 'icon': '✅', 'color': '#16A34A'},
            {'key': 'stalled', 'ar': 'متوقّفة', 'en': 'Stalled',
             'value': Model.search_count(dom + [('is_stalled', '=', True)]) if 'is_stalled' in Model._fields else 0,
             'icon': '⚠️', 'color': '#DC2626'},
        ]

    def _dev_extra(self, rec):
        lm = rec._fields
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('اسم الجهاز', 'Device name', rec.device_name if 'device_name' in lm else None, '🏷️')
        add('العنوان (IP)', 'IP address', rec.ip if 'ip' in lm else None, '🌐')
        add('المنفذ', 'Port', rec.port if 'port' in lm else None, '🔀')
        add('الموقع', 'Location', rec.location_id.display_name if ('location_id' in lm and rec.location_id) else None, '📍')
        add('إصدار الخادم', 'Server version', rec.server_ver if 'server_ver' in lm else None, 'ℹ️')
        add('سجلات البيانات', 'Data logs', rec.data_log_count if 'data_log_count' in lm else None, '🗄️')
        add('الوقت الحقيقي', 'Real-time', 'نعم' if ('real_time' in lm and rec.real_time) else None, '⚡')
        if 'is_stalled' in lm and rec.is_stalled:
            add('الحالة', 'Status', 'متوقّف — يحتاج فحص', '⚠️')
        return {'stalled': bool(rec.is_stalled) if 'is_stalled' in lm else False,
                'service_info': info}

    # ---- Vehicle service (fleet.vehicle.log.services) ---------------------
    def _vs_row(self, r):
        lm = r._fields
        v = r.vehicle_id if 'vehicle_id' in lm else None
        return {
            'image_b64': self._img_b64(v, ('image_128',)) if v else None,
            'vehicle': v.display_name if v else None,
            'plate': (v.license_plate if v and 'license_plate' in v._fields else '') or '',
            'service_type': r.service_type_id.display_name if r.service_type_id else None,
            'amount': round((r.amount or 0.0) if 'amount' in lm else 0.0, 3),
            'currency': self._currency(r) or '',
            'date': _d(r.date) if 'date' in lm else None,
            'next_service': _d(r.next_service_date) if 'next_service_date' in lm else None,
        }

    def _vs_stats(self, Model, dom):
        cur = ''
        c = Model.search(dom, limit=1)
        if c:
            cur = self._currency(c) or ''
        try:
            grp = Model.read_group(dom, ['amount'], [])
            cost = (grp[0].get('amount') if grp else 0.0) or 0.0
        except Exception:
            cost = 0.0
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': Model.search_count(dom), 'icon': '🔧'},
            {'key': 'open', 'ar': 'قيد التنفيذ', 'en': 'Open',
             'value': Model.search_count(dom + [('state', 'in', ['new', 'running'])]), 'icon': '🛠️', 'color': '#F59E0B'},
            {'key': 'done', 'ar': 'منجزة', 'en': 'Done',
             'value': Model.search_count(dom + [('state', '=', 'done')]), 'icon': '✅', 'color': '#16A34A'},
            {'key': 'cost', 'ar': 'إجمالي التكلفة', 'en': 'Total cost',
             'value': round(cost, 3), 'unit': cur, 'icon': '💰', 'money': True},
        ]

    def _vs_extra(self, rec):
        lm = rec._fields
        v = rec.vehicle_id if 'vehicle_id' in lm else None
        cur = self._currency(rec) or ''
        header = {'amount': round((rec.amount or 0.0) if 'amount' in lm else 0.0, 3), 'currency': cur}
        info = []

        def add(ar, en, val, icon='•'):
            if val not in (None, '', False):
                info.append({'ar': ar, 'en': en, 'value': val, 'icon': icon})

        add('المركبة', 'Vehicle', v.display_name if v else None, '🚗')
        add('اللوحة', 'Plate', (v.license_plate if v and 'license_plate' in v._fields else None), '🔖')
        add('نوع الخدمة', 'Service type', rec.service_type_id.display_name if rec.service_type_id else None, '🔧')
        try:
            add('التصنيف', 'Type', dict(rec._fields['type']._description_selection(rec.env)).get(rec.type) if ('type' in lm and rec.type) else None, '📁')
        except Exception:
            pass
        add('التاريخ', 'Date', _d(rec.date) if 'date' in lm else None, '📅')
        add('الخدمة القادمة', 'Next service', _d(rec.next_service_date) if 'next_service_date' in lm else None, '⏰')
        add('العدّاد', 'Odometer', round(rec.odometer, 0) if ('odometer' in lm and rec.odometer) else None, '🛣️')
        add('السائق', 'Driver', rec.purchaser_id.display_name if ('purchaser_id' in lm and rec.purchaser_id) else None, '👤')
        add('المورّد', 'Vendor', rec.vendor_id.display_name if ('vendor_id' in lm and rec.vendor_id) else None, '🏪')
        add('مرجع المورّد', 'Vendor ref', rec.inv_ref if ('inv_ref' in lm and rec.inv_ref) else None, '#️⃣')
        add('مدير الأسطول', 'Fleet manager', rec.manager_id.display_name if ('manager_id' in lm and rec.manager_id) else None, '👔')
        add('الوصف', 'Description', rec.description if 'description' in lm else None, '📝')
        add('ملاحظات', 'Notes', rec.notes if 'notes' in lm else None, '🗒️')
        # this vehicle's other service logs (recent history) + running total
        history, total_spent = [], 0.0
        if v:
            others = rec.search([('vehicle_id', '=', v.id)], order='date desc, id desc', limit=30)
            for s in others:
                total_spent += s.amount or 0.0
                history.append({
                    'id': s.id, 'current': s.id == rec.id,
                    'service': s.service_type_id.display_name if s.service_type_id else '—',
                    'date': _d(s.date) if s.date else None,
                    'amount': round(s.amount or 0.0, 3),
                    'odometer': round(s.odometer, 0) if s.odometer else None,
                })
        return {'header': header, 'service_info': info,
                'image_b64': self._img_b64(v, ('image_256', 'image_128')) if v else None,
                'history': history, 'total_spent': round(total_spent, 3), 'currency': cur,
                'vehicle_id': v.id if v else None}

    def _fleet_stats(self, Model, dom):
        total = Model.search_count(dom)
        with_driver = Model.search_count(dom + [('driver_id', '!=', False)])
        return [
            {'key': 'total', 'ar': 'إجمالي المركبات', 'en': 'Vehicles', 'value': total, 'icon': '🚗'},
            {'key': 'assigned', 'ar': 'مُسندة لسائق', 'en': 'Assigned', 'value': with_driver, 'icon': '🧑‍✈️', 'color': '#16A34A'},
            {'key': 'free', 'ar': 'بدون سائق', 'en': 'Unassigned', 'value': total - with_driver, 'icon': '🅿️', 'color': '#F59E0B'},
        ]

    def _agg_stats(self, Model, dom, key, amount_field='amount_total',
                   confirmed_states=(), extra=None):
        """DB-side aggregate KPIs — safe on 15k-row systems (no record loop)."""
        cur = ''
        try:
            c = Model.search(dom, limit=1)
            cur = self._currency(c) or '' if c else ''
        except Exception:
            pass
        total = Model.search_count(dom)
        stats = [{'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': total, 'icon': '📈'}]
        pend = self._PENDING.get(key)
        if pend is not None:
            stats.append({'key': 'pending', 'ar': 'بانتظار إجراء', 'en': 'Pending',
                          'value': Model.search_count(dom + pend), 'icon': '⏳', 'color': '#F59E0B'})
        if confirmed_states:
            stats.append({'key': 'confirmed', 'ar': 'معتمدة', 'en': 'Confirmed',
                          'value': Model.search_count(dom + [('state', 'in', list(confirmed_states))]),
                          'icon': '✅', 'color': '#16A34A'})
        if amount_field and amount_field in Model._fields:
            try:
                grp = Model.read_group(dom, [amount_field], [])
                val = (grp[0].get(amount_field) if grp else 0.0) or 0.0
            except Exception:
                val = 0.0
            stats.append({'key': 'value', 'ar': 'إجمالي القيمة', 'en': 'Total value',
                          'value': round(val, 3), 'unit': cur, 'icon': '💰', 'money': True})
        if extra:
            stats += extra
        return stats

    def _leave_row(self, r):
        emp = r.employee_id if 'employee_id' in r._fields else None
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'employee': emp.display_name if emp else None,
            'leave_type': r.holiday_status_id.display_name if r.holiday_status_id else None,
            'days': round(r.number_of_days or 0.0, 1),
            'date_from': _d(r.date_from),
            'date_to': _d(r.date_to),
        }

    # ---- Generic logo: any system's row gets a partner/own image ----------
    def _generic_logo(self, r):
        lm = r._fields
        for rel in ('partner_id', 'employee_id', 'organization', 'vehicle_id',
                    'driver_id', 'user_id', 'company_id'):
            if rel in lm and r[rel]:
                b = self._img_b64(r[rel], ('image_128',))
                if b:
                    return b
        return self._img_b64(r, ('image_128', 'avatar_128', 'image_512', 'image_1920', 'image'))

    # ---- CRM (opportunities) ---------------------------------------------
    def _crm_stage_color(self, r):
        st = r.stage_id
        nm = (st.name or '').lower() if st else ''
        if st and getattr(st, 'is_won', False):
            return '#16A34A'
        if 'won' in nm:
            return '#16A34A'
        if 'lost' in nm:
            return '#DC2626'
        p = r.probability or 0
        return '#16A34A' if p >= 70 else ('#F59E0B' if p >= 40 else '#3B82F6')

    def _crm_row(self, r):
        return {
            'logo_b64': self._img_b64(r.partner_id, ('image_128',)) if r.partner_id else None,
            'partner': (r.partner_id.display_name if r.partner_id else None) or r.contact_name,
            'expected': round(r.expected_revenue or 0.0, 3),
            'currency': r.company_currency.name if r.company_currency else '',
            'probability': round(r.probability or 0.0, 0),
            'stage': r.stage_id.display_name if r.stage_id else None,
            'stage_color': self._crm_stage_color(r),
            'salesperson': r.user_id.display_name if r.user_id else None,
            'phone': r.phone or None,
            'deadline': _d(r.date_deadline),
        }

    def _crm_stats(self, Model, dom):
        cur = ''
        c = Model.search(dom, limit=1)
        if c:
            cur = (c.company_currency.name if 'company_currency' in c._fields and c.company_currency else '') or ''
        total = Model.search_count(dom)
        won = Model.search_count(dom + [('stage_id.is_won', '=', True)])
        open_c = Model.search_count(dom + [('stage_id.is_won', '=', False), ('active', '=', True)])
        try:
            grp = Model.read_group(dom + [('stage_id.is_won', '=', False)], ['expected_revenue'], [])
            pipe = (grp[0].get('expected_revenue') if grp else 0.0) or 0.0
        except Exception:
            pipe = 0.0
        return [
            {'key': 'total', 'ar': 'الإجمالي', 'en': 'Total', 'value': total, 'icon': '🎯'},
            {'key': 'open', 'ar': 'مفتوحة', 'en': 'Open', 'value': open_c, 'icon': '🔵', 'color': '#3B82F6'},
            {'key': 'won', 'ar': 'مكتسبة', 'en': 'Won', 'value': won, 'icon': '🏆', 'color': '#16A34A'},
            {'key': 'pipeline', 'ar': 'الإيراد المتوقع', 'en': 'Pipeline',
             'value': round(pipe, 3), 'unit': cur, 'icon': '💰', 'money': True},
        ]

    # ---- Employee expenses -----------------------------------------------
    def _expense_row(self, r):
        emp = r.employee_id if 'employee_id' in r._fields else None
        n = 0
        if 'expense_line_ids' in r._fields:
            try:
                n = len(r.expense_line_ids)
            except Exception:
                n = 0
        try:
            pmode = dict(r._fields['payment_mode']._description_selection(r.env)).get(
                r.payment_mode) if 'payment_mode' in r._fields and r.payment_mode else None
        except Exception:
            pmode = None
        return {
            'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            'employee': emp.display_name if emp else None,
            'amount': round((r.total_amount or 0.0) if 'total_amount' in r._fields else 0.0, 3),
            'currency': self._currency(r) or '',
            'payment_mode': pmode,
            'lines': n,
        }

    def _lines_for(self, rec):
        """Order/quotation/payslip line items (name, qty, price, subtotal)."""
        lf = next((f for f in ('order_line', 'line_ids', 'invoice_line_ids') if f in rec._fields), None)
        if not lf:
            return []
        out = []
        for l in rec[lf]:
            if 'display_type' in l._fields and l.display_type:
                continue  # section/note lines
            lm = l._fields
            name = (l.name or (l.product_id.display_name if 'product_id' in lm and l.product_id else '')) or '—'
            subtotal = (l.price_subtotal if 'price_subtotal' in lm
                        else (l.total if 'total' in lm else None))
            out.append({
                'name': (name or '').split('\n')[0][:80],
                'qty': (l.product_uom_qty if 'product_uom_qty' in lm
                        else (l.quantity if 'quantity' in lm else None)),
                'price': l.price_unit if 'price_unit' in lm else None,
                'subtotal': round(subtotal, 2) if isinstance(subtotal, (int, float)) else subtotal,
            })
            if len(out) >= 100:
                break
        return out

    def _reports_for(self, env, key, rid):
        """Reports declared for this system that actually exist on this DB."""
        out = []
        for r in REPORTS.get(key, []):
            if env.ref(r['report'], raise_if_not_found=False):
                out.append({'report': r['report'], 'ar': r['ar'], 'en': r['en'], 'type': r['type'],
                            'url': _abs('/api/v1/management/%s/%s/report?report=%s' % (key, rid, r['report']))})
        return out

    @route(API + '/management/<string:key>/<int:rid>/report', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_report(self, key, rid, report=None, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        spec = self._spec(key)
        if not spec or not report:
            return request.not_found()
        # the report must be one we declared for this system (no arbitrary render)
        allowed = {r['report']: r for r in REPORTS.get(key, [])}
        rdef = allowed.get(report)
        if not rdef:
            return request.make_response('تقرير غير معروف', status=404)
        try:
            rec = env[spec['model']].browse(int(rid))
            rec.check_access_rule('read')
        except Exception:
            return request.make_response('لا صلاحية', status=403)
        try:
            # `report` is a report_name/xmlid — render via the report model, which
            # resolves the ir.actions.report and dispatches by type (pdf/xlsx).
            content, ctype = env['ir.actions.report'].sudo()._render(report, [int(rid)])
        except UserError as e:
            # e.g. "can't print in draft" — a clear reason, not a crash.
            return request.make_response(
                (getattr(e, 'args', None) and e.args[0]) or 'تعذّر إنشاء التقرير',
                status=422)
        except Exception:
            return request.make_response(
                'تعذّر إنشاء هذا التقرير لهذا السجل.', status=422)
        if rdef['type'] == 'xlsx' or ctype in ('xlsx', 'xls'):
            return request.make_response(content, headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="%s-%s.xlsx"' % (key, rid))])
        return request.make_response(content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="%s-%s.pdf"' % (key, rid))])

    # ---- rich employee file (ALL fields + every related sub-module) --------
    def _emp_related_row(self, rec):
        """A compact, defensive row for one related record."""
        M = rec._fields
        title = None
        for c in ('name', 'display_name'):
            if c in M and rec[c]:
                title = rec[c]
                break
        title = (title or rec.display_name or '—')
        if hasattr(title, 'display_name'):
            title = title.display_name
        sub = None
        for c in ('holiday_status_id', 'skill_id', 'allowance_type', 'type', 'reason',
                  'department_id', 'service_type_id', 'court_name'):
            if c in M and rec[c]:
                v = rec[c]
                sub = v.display_name if hasattr(v, 'display_name') else self._val(rec, c)
                break
        amount = None
        for c in ('amount', 'wage', 'net_wage', 'loan_amount', 'total_amount', 'number_of_days'):
            if c in M and rec[c]:
                amount = round(rec[c], 2)
                break
        date = None
        for c in ('date', 'date_from', 'date_start', 'create_date', 'expiry_date', 'hearing_date'):
            if c in M and rec[c]:
                date = _d(rec[c])
                break
        state = self._val(rec, 'state') if 'state' in M else None
        return {'id': rec.id, 'title': str(title)[:80], 'subtitle': sub,
                'amount': amount, 'date': date, 'state': state}

    @route(API + '/management/employee/<int:eid>/full', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_employee_full(self, eid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        # gate on the employees system access
        if not self._can(env, REGISTRY['employees']):
            return _err('لا تملك صلاحية على الموظفين', 403)
        try:
            emp = env['hr.employee'].browse(int(eid))
            emp.check_access_rule('read')
            emp.read(['id'])
        except Exception:
            return _err('غير موجود أو لا صلاحية', 404)

        # ---- ALL readable fields, grouped ----
        skip_types = ('binary', 'image', 'one2many', 'many2many', 'html')
        assigned = {}
        for fname, f in emp._fields.items():
            if f.type in skip_types:
                continue
            if fname.startswith(('message_', 'activity_', 'website_', '__')):
                continue
            if fname in ('id', 'display_name', 'create_uid', 'write_uid', 'write_date',
                         'create_date', 'avatar_128', 'avatar_256', 'avatar_512', 'avatar_1024',
                         'image_128', 'image_1920'):
                continue
            try:
                v = self._val(emp, fname)
            except Exception:
                continue
            if v in (None, '', False):
                continue
            low = fname.lower()
            grp = None
            for gi, (_ar, _en, kws) in enumerate(EMP_GROUPS):
                if any(k in low for k in kws):
                    grp = gi
                    break
            assigned.setdefault(grp if grp is not None else 99, []).append(
                {'name': fname, 'label': f.string, 'value': v, 'type': f.type})
        sections = []
        for gi, (ar, en, _kw) in enumerate(EMP_GROUPS):
            if assigned.get(gi):
                sections.append({'title': ar, 'title_en': en, 'fields': assigned[gi]})
        if assigned.get(99):
            sections.append({'title': '📋 بيانات أخرى', 'title_en': 'Other', 'fields': assigned[99]})

        # ---- related sub-modules ----
        related = []
        seen_labels = set()
        for model, ar, en, icon in EMP_RELATED:
            if model not in env:
                continue
            M = env[model].sudo()
            ef = 'employee_id' if 'employee_id' in M._fields else (
                'employee_ids' if 'employee_ids' in M._fields else None)
            if not ef:
                continue
            try:
                dom = [(ef, 'in', [emp.id])] if ef == 'employee_ids' else [(ef, '=', emp.id)]
                recs = M.search(dom, limit=40)
            except Exception:
                continue
            if not recs:
                continue
            key = (ar,)
            if key in seen_labels:   # care.loan/hr.loan share the label — merge count
                for r in related:
                    if r['ar'] == ar:
                        r['rows'] += [self._emp_related_row(x) for x in recs]
                        r['count'] += len(recs)
                continue
            seen_labels.add(key)
            related.append({'model': model, 'ar': ar, 'en': en, 'icon': icon,
                            'count': len(recs),
                            'can_create': model in EMP_CREATE_SPECS,
                            'rows': [self._emp_related_row(x) for x in recs]})

        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        return _ok({
            'id': emp.id, 'name': emp.name,
            'job': emp.job_title or None,
            'department': emp.department_id.display_name if emp.department_id else None,
            'badge': emp.barcode or None,
            'avatar': _abs('/api/v1/pms/employee/%s/photo' % emp.id),
            'work_email': emp.work_email or None,
            'work_phone': emp.work_phone or emp.mobile_phone or None,
            'sections': sections,
            'related': related,
        })

    # ---- run a whitelisted workflow action --------------------------------
    @route(API + '/management/<string:key>/<int:rid>/action', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_action(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        acc = self._user_access(env)
        if key in acc['hidden'] or key in acc['no_edit']:
            return _err('لا تملك صلاحية التعديل على هذا النظام', 403)
        from .api import _body
        akey = (_body() or {}).get('action')
        adef = next((a for a in (ACTIONS.get(key) or []) if a['key'] == akey), None)
        if not adef:
            return _err('إجراء غير معروف', 422)
        try:
            rec = self._model(env, spec).browse(rid)
            if not spec.get('sudo'):
                rec.check_access_rule('write')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        st = self._raw_state(rec, spec)
        if adef['states'] and st not in adef['states']:
            return _err('لا يمكن تنفيذ هذا الإجراء في الحالة الحالية', 422)
        if not hasattr(rec, adef['method']):
            return _err('الإجراء غير متاح', 422)
        try:
            getattr(rec, adef['method'])()  # may return an ir.actions dict — ignored
        except AccessError:
            return _err('لا تملك صلاحية تنفيذ هذا الإجراء', 403)
        except Exception as e:
            return _err(str(e) or 'تعذّر تنفيذ الإجراء', 422)
        rec.invalidate_recordset()
        return _ok({'id': rec.id, 'state': self._val(rec, spec.get('state')),
                    'actions': self._actions_for(env, rec, key, spec)})

    # ---- edit whitelisted fields ------------------------------------------
    @route(API + '/management/<string:key>/<int:rid>/write', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_write(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        acc = self._user_access(env)
        if key in acc['hidden'] or key in acc['no_edit']:
            return _err('لا تملك صلاحية التعديل على هذا النظام', 403)
        editset = set(spec.get('edit') or [])
        if not editset:
            return _err('التعديل غير متاح لهذا النظام', 422)
        from .api import _body
        body = _body() or {}
        try:
            rec = env[spec['model']].browse(rid)  # caller's env → Odoo enforces
            rec.check_access_rule('write')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        vals = {}
        for fname, val in body.items():
            if fname not in editset or fname not in rec._fields:
                continue
            f = rec._fields[fname]
            if f.type == 'many2one':
                vals[fname] = int(val) if val else False
            elif f.type in ('float', 'monetary'):
                try:
                    vals[fname] = float(val)
                except (TypeError, ValueError):
                    continue
            elif f.type == 'integer':
                try:
                    vals[fname] = int(val)
                except (TypeError, ValueError):
                    continue
            elif f.type == 'boolean':
                vals[fname] = bool(val)
            else:
                vals[fname] = val if val not in (None,) else False
        if not vals:
            return _err('لا حقول قابلة للحفظ', 422)
        try:
            rec.write(vals)
        except AccessError:
            return _err('لا تملك صلاحية التعديل', 403)
        except Exception as e:
            return _err(str(e) or 'تعذّر الحفظ', 422)
        return _ok({'id': rec.id})

    # ---- per-user header: who am I, and what needs me ---------------------
    # ---- Proposals: send to client ---------------------------------------
    @route(API + '/management/proposals/<int:rid>/send', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_proposal_send(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec('proposals')
        if not self._can(env, spec):
            return _err('لا تملك صلاحية على عروض الأسعار', 403)
        try:
            rec = env['proposal.proposal'].browse(rid)
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        from .api import _body
        email = (_body() or {}).get('email') or (rec.partner_id.email if rec.partner_id else '')
        if not email:
            return _err('لا يوجد بريد إلكتروني. اختر مستلمًا أو أضف بريد العميل أولًا.', 400)
        tmpl = env.ref('care_proposal.email_template_proposal', raise_if_not_found=False)
        if not tmpl:
            return _err('قالب البريد غير متوفر', 500)
        try:
            tmpl.sudo().send_mail(
                rec.id, force_send=True,
                email_values={'email_to': email},
                email_layout_xmlid='mail.mail_notification_light')
            rec.sudo().message_post(
                body='📧 تم إرسال العرض إلى %s.' % email)
        except Exception as e:
            return _err('تعذّر إرسال البريد: %s' % e, 500)
        return _ok({'sent': True, 'email': email,
                    'customer': rec.partner_id.display_name})

    # ---- Proposals: create a new quotation --------------------------------
    @route(API + '/management/proposals/meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_proposal_meta(self, **kw):
        """Pickers needed by the create form (customers, service types)."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('proposals')):
            return _err('لا تملك صلاحية', 403)
        try:
            partners = env['res.partner'].search(
                [('customer_rank', '>', 0)], order='name', limit=300)
            if not partners:
                partners = env['res.partner'].search(
                    [('is_company', '=', True)], order='name', limit=300)
        except Exception:
            partners = env['res.partner'].browse()
        types = env['proposal.service.type'].sudo().search([], order='name')
        modes = []
        try:
            modes = [{'v': k, 'l': l} for k, l in
                     env['proposal.proposal']._fields['mode']._description_selection(env)]
        except Exception:
            pass
        svc = env['proposal.service'].sudo().search([], order='name', limit=300)
        return _ok({
            'customers': [{'v': p.id, 'l': p.display_name} for p in partners],
            'service_types': [{'v': t.id, 'l': t.name} for t in types],
            'services': [{'v': s.id, 'l': s.name,
                          'type': dict(s._fields['type']._description_selection(env)).get(s.type) if s.type else ''}
                         for s in svc],
            'modes': modes,
        })

    def _proposal_service_lines(self, env, services):
        """(0,0,vals) commands for proposal.service.line from the app payload."""
        cmds = []
        for s in (services or []):
            if not s.get('service_id'):
                continue
            v = {'proposal_service_id': int(s['service_id']),
                 'quantity': float(s.get('quantity') or 1)}
            for f in ('daily_hours', 'weekly_days', 'monthly_days'):
                if s.get(f) not in (None, ''):
                    try:
                        v[f] = float(s[f])
                    except (TypeError, ValueError):
                        pass
            cmds.append((0, 0, v))
        return cmds

    def _proposal_body_vals(self, env, b, for_create=True):
        vals = {}
        if b.get('partner_id'):
            vals['partner_id'] = int(b['partner_id'])
        if b.get('service_type_id'):
            vals['service_type_id'] = int(b['service_type_id'])
        for f in ('proposal_date', 'expire_date', 'mobilization_date'):
            if b.get(f):
                vals[f] = b[f]
        if 'service_site' in b:
            vals['service_site'] = b.get('service_site') or False
        if b.get('mode'):
            vals['mode'] = b['mode']
        if 'notes' in b:
            vals['notes'] = b.get('notes') or False
        if b.get('proposal_period') not in (None, ''):
            try:
                vals['proposal_period'] = int(b['proposal_period'])
            except (TypeError, ValueError):
                pass
        if b.get('target_margin_pct') not in (None, ''):
            try:
                vals['target_margin_pct'] = float(b['target_margin_pct'])
                vals['pricing_strategy'] = 'target_margin'
            except (TypeError, ValueError):
                pass
        return vals

    @route(API + '/management/proposals/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_proposal_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if self._create_blocked(env, 'proposals'):
            return _err('لا تملك صلاحية الإنشاء', 403)
        try:
            env['proposal.proposal'].check_access_rights('create', raise_exception=True)
        except Exception:
            return _err('لا تملك صلاحية إنشاء عرض سعر', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('partner_id'):
            return _err('اختر العميل أولًا', 422)
        vals = self._proposal_body_vals(env, b)
        if b.get('services'):
            vals['service_ids'] = self._proposal_service_lines(env, b['services'])
        try:
            rec = env['proposal.proposal'].create(vals)
        except AccessError:
            return _err('لا تملك صلاحية إنشاء عرض سعر', 403)
        except Exception as e:
            return _err('تعذّر إنشاء العرض: %s' % e, 422)
        return _ok({'id': rec.id, 'ref': rec.ref, 'title': rec.name})

    @route(API + '/management/proposals/<int:rid>/edit-data', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_proposal_edit_data(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            rec = env['proposal.proposal'].browse(int(rid))
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود', 404)
        services = []
        for l in rec.service_ids:
            services.append({
                'id': l.id,
                'service_id': l.proposal_service_id.id if l.proposal_service_id else None,
                'name': l.proposal_service_id.name if l.proposal_service_id else '',
                'quantity': l.quantity,
                'daily_hours': l.daily_hours, 'weekly_days': l.weekly_days, 'monthly_days': l.monthly_days,
            })
        return _ok({
            'id': rec.id,
            'partner_id': rec.partner_id.id if rec.partner_id else None,
            'partner_name': rec.partner_id.display_name if rec.partner_id else None,
            'service_type_id': rec.service_type_id.id if rec.service_type_id else None,
            'proposal_date': _d(rec.proposal_date), 'expire_date': _d(rec.expire_date),
            'mobilization_date': _d(rec.mobilization_date),
            'service_site': rec.service_site or '', 'mode': rec.mode or None,
            'proposal_period': rec.proposal_period or 0,
            'target_margin_pct': rec.target_margin_pct or 0,
            'notes': rec.notes or '', 'state': rec.state,
            'lines_editable': rec.state in ('draft',),
            'services': services,
        })

    @route(API + '/management/proposals/<int:rid>/update', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def management_proposal_update(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            rec = env['proposal.proposal'].browse(int(rid))
            rec.check_access_rule('write')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        from .api import _body
        b = _body() or {}
        vals = self._proposal_body_vals(env, b, for_create=False)
        if b.get('services') is not None and rec.state == 'draft':
            vals['service_ids'] = [(5, 0, 0)] + self._proposal_service_lines(env, b['services'])
        try:
            rec.write(vals)
        except AccessError:
            return _err('لا تملك صلاحية التعديل', 403)
        except Exception as e:
            return _err('تعذّر الحفظ: %s' % e, 422)
        return _ok({'id': rec.id, 'title': rec.name})

    # ---- CRM: create a new opportunity ------------------------------------
    @route(API + '/management/crm/meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_crm_meta(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('crm')):
            return _err('لا تملك صلاحية', 403)
        try:
            partners = env['res.partner'].search(
                ['|', ('customer_rank', '>', 0), ('is_company', '=', True)],
                order='name', limit=400)
        except Exception:
            partners = env['res.partner'].browse()
        stages = env['crm.stage'].sudo().search([], order='sequence')
        users = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name', limit=200)
        return _ok({
            'customers': [{'v': p.id, 'l': p.display_name} for p in partners],
            'stages': [{'v': s.id, 'l': s.name} for s in stages],
            'users': [{'v': u.id, 'l': u.name} for u in users],
            'me': env.uid,
        })

    @route(API + '/management/crm/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_crm_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if self._create_blocked(env, 'crm'):
            return _err('لا تملك صلاحية الإنشاء', 403)
        try:
            env['crm.lead'].check_access_rights('create', raise_exception=True)
        except Exception:
            return _err('لا تملك صلاحية إنشاء فرصة', 403)
        from .api import _body
        b = _body() or {}
        if not (b.get('name') or '').strip():
            return _err('أدخل عنوان الفرصة أولًا', 422)
        vals = {'name': b['name'].strip(), 'type': 'opportunity'}
        if b.get('partner_id'):
            vals['partner_id'] = int(b['partner_id'])
        for f in ('contact_name', 'email_from', 'phone'):
            if b.get(f):
                vals[f] = b[f]
        if b.get('stage_id'):
            vals['stage_id'] = int(b['stage_id'])
        if b.get('user_id'):
            vals['user_id'] = int(b['user_id'])
        if b.get('expected_revenue') not in (None, ''):
            try:
                vals['expected_revenue'] = float(b['expected_revenue'])
            except (TypeError, ValueError):
                pass
        if b.get('description'):
            vals['description'] = b['description']
        try:
            rec = env['crm.lead'].create(vals)
        except AccessError:
            return _err('لا تملك صلاحية إنشاء فرصة', 403)
        except Exception as e:
            return _err('تعذّر إنشاء الفرصة: %s' % e, 422)
        return _ok({'id': rec.id, 'title': rec.name})

    # ---- Tenders: one tab's line items (price analysis, manpower, …) ------
    @route(API + '/management/tenders/<int:rid>/tab/<string:code>', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_tender_tab(self, rid, code, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('tenders')):
            return _err('لا تملك صلاحية على المناقصات', 403)
        fname = self._TENDER_TAB_MODELS.get(code)
        if not fname:
            return _err('تبويب غير معروف', 404)
        try:
            rec = env['purchase.tender'].browse(rid)
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 404)
        if fname not in rec._fields:
            return _err('التبويب غير متاح', 404)
        try:
            lines = self._tender_tab_lines(rec, fname)
        except Exception as e:
            return _err('تعذّر القراءة: %s' % e, 500)
        return _ok({'code': code, 'count': len(lines), 'lines': lines})

    # ---- Fleet: a vehicle's log records (services/contracts/drivers/odo) ---
    @route(API + '/management/fleet/<int:rid>/log/<string:code>', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_fleet_log(self, rid, code, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('fleet')):
            return _err('لا تملك صلاحية', 403)
        try:
            rec = env['fleet.vehicle'].browse(int(rid))
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود', 404)
        try:
            if code == 'odometer':
                recs = env['fleet.vehicle.odometer'].search(
                    [('vehicle_id', '=', rec.id)], order='date desc', limit=200)
            else:
                fname = self._FLEET_LOGS.get(code)
                if not fname or fname not in rec._fields:
                    return _err('سجل غير معروف', 404)
                recs = rec[fname]
            lines = self._records_to_lines(recs)
        except Exception as e:
            return _err('تعذّر القراءة: %s' % e, 500)
        return _ok({'code': code, 'count': len(lines), 'lines': lines})

    # ---- Experience: renewal / guarantee / line records -------------------
    @route(API + '/management/experience/<int:rid>/log/<string:code>', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_experience_log(self, rid, code, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('experience')):
            return _err('لا تملك صلاحية', 403)
        fname = self._EXP_LOGS.get(code)
        if not fname:
            return _err('سجل غير معروف', 404)
        try:
            rec = env['care.experience'].browse(int(rid))
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود', 404)
        if fname not in rec._fields:
            return _err('غير متاح', 404)
        try:
            lines = self._records_to_lines(rec[fname])
        except Exception as e:
            return _err('تعذّر القراءة: %s' % e, 500)
        return _ok({'code': code, 'count': len(lines), 'lines': lines})

    # ---- Generic: a record's attachments (chatter + direct), openable -----
    def _attachments_for(self, env, rec):
        """Every ir.attachment on the record itself + its chatter messages,
        newest first, with an in-app viewer URL."""
        Att = env['ir.attachment'].sudo()
        direct = Att.search([('res_model', '=', rec._name), ('res_id', '=', rec.id)])
        msg_ids = env['mail.message'].sudo().search([('model', '=', rec._name), ('res_id', '=', rec.id)]).ids
        via_msg = Att.search([('res_model', '=', 'mail.message'), ('res_id', 'in', msg_ids)]) if msg_ids else Att.browse()
        seen, out = set(), []
        for a in (direct | via_msg).sorted('id', reverse=True):
            if a.id in seen:
                continue
            seen.add(a.id)
            mt = (a.mimetype or '').lower()
            out.append({
                'id': a.id, 'name': a.name or 'attachment',
                'mimetype': mt,
                'is_image': mt.startswith('image/'),
                'is_pdf': mt == 'application/pdf' or (a.name or '').lower().endswith('.pdf'),
                'size': a.file_size or 0,
                'url': _abs('/api/v1/management/attachment/%s' % a.id),
            })
            if len(out) >= 100:
                break
        return out

    @route(API + '/management/<string:key>/<int:rid>/attachments', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_attachments(self, key, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        spec = self._spec(key)
        if not spec:
            return _err('نظام غير معروف', 404)
        if not self._can(env, spec):
            return _err('لا صلاحية', 403)
        try:
            rec = env[spec['model']].browse(int(rid))
            rec.check_access_rule('read')
            rec.read(['id'])
        except Exception:
            return _err('غير موجود', 404)
        return _ok({'attachments': self._attachments_for(env, rec)})

    @route(API + '/management/attachment/<int:aid>', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_attachment(self, aid, token=None, **kw):
        env = _auth()
        if not env:
            return request.not_found()
        a = env['ir.attachment'].sudo().browse(int(aid))
        if not a.exists():
            return request.not_found()
        # gate: the caller must be able to read the attachment's parent record
        try:
            if a.res_model and a.res_id and a.res_model in env:
                parent = env[a.res_model].browse(a.res_id)
                parent.check_access_rule('read')
                parent.read(['id'])
            elif a.res_model == 'mail.message' and a.res_id:
                msg = env['mail.message'].sudo().browse(a.res_id)
                if msg.model and msg.res_id and msg.model in env:
                    p = env[msg.model].browse(msg.res_id)
                    p.check_access_rule('read')
                    p.read(['id'])
        except Exception:
            return request.not_found()
        import base64
        data = base64.b64decode(a.datas or b'')
        disp = 'attachment' if 'download' in kw else 'inline'
        return request.make_response(data, headers=[
            ('Content-Type', a.mimetype or 'application/octet-stream'),
            ('Content-Disposition', '%s; filename="%s"' % (disp, (a.name or 'file').replace('"', ''))),
            ('Content-Length', str(len(data))),
        ])

    # ---- Purchases: deliveries, invoices, send-to-vendor ------------------
    def _po(self, env, rid):
        rec = env['purchase.order'].browse(int(rid))
        rec.check_access_rule('read')
        rec.read(['id'])
        return rec

    @route(API + '/management/purchases/<int:rid>/deliveries', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_po_deliveries(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('purchases')):
            return _err('لا تملك صلاحية', 403)
        try:
            po = self._po(env, rid)
        except Exception:
            return _err('غير موجود', 404)
        out = []
        for pk in po.picking_ids:
            par, pen, pcol = self._PICKING_STATE.get(pk.state, (pk.state, pk.state, '#94A3B8'))
            moves = []
            for mv in pk.move_ids[:60]:
                moves.append({'product': mv.product_id.display_name if mv.product_id else (mv.name or '—'),
                              'demand': round(mv.product_uom_qty or 0.0, 2),
                              'done': round(mv.quantity or 0.0, 2)})
            out.append({
                'id': pk.id, 'name': pk.name or '—',
                'type': pk.picking_type_id.display_name if pk.picking_type_id else None,
                'state': pk.state, 'state_ar': par, 'state_en': pen, 'state_color': pcol,
                'scheduled': _d(pk.scheduled_date), 'done_date': _d(pk.date_done),
                'can_validate': pk.state in ('assigned', 'confirmed', 'waiting'),
                'moves': moves,
            })
        return _ok({'count': len(out), 'deliveries': out})

    @route(API + '/management/picking/<int:pid>/validate', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def management_picking_validate(self, pid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            pk = env['stock.picking'].browse(int(pid))
            pk.check_access_rule('write')
            pk.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        try:
            # receive everything, then validate (skip the backorder wizard)
            for mv in pk.move_ids:
                if mv.state not in ('done', 'cancel') and not mv.quantity:
                    mv.quantity = mv.product_uom_qty
            res = pk.with_context(skip_backorder=True,
                                  picking_ids_not_to_backorder=pk.ids).button_validate()
            if isinstance(res, dict) and res.get('res_model'):
                # a wizard would open (backorder/immediate) — force it through
                pk.with_context(skip_backorder=True).button_validate()
        except UserError as e:
            return _err((e.args and e.args[0]) or 'تعذّر تأكيد الاستلام', 422)
        except Exception as e:
            return _err('تعذّر تأكيد الاستلام: %s' % e, 422)
        par, pen, pcol = self._PICKING_STATE.get(pk.state, (pk.state, pk.state, '#94A3B8'))
        return _ok({'id': pk.id, 'state': pk.state, 'state_ar': par, 'state_color': pcol})

    @route(API + '/management/purchases/<int:rid>/invoices', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_po_invoices(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('purchases')):
            return _err('لا تملك صلاحية', 403)
        try:
            po = self._po(env, rid)
        except Exception:
            return _err('غير موجود', 404)
        out = []
        for inv in po.invoice_ids:
            im = inv._fields
            try:
                plabel = dict(im['payment_state']._description_selection(inv.env)).get(inv.payment_state, inv.payment_state) if inv.payment_state else None
            except Exception:
                plabel = inv.payment_state
            code = inv.state
            out.append({
                'id': inv.id, 'name': inv.name or '/',
                'amount': round(inv.amount_total or 0.0, 3),
                'residual': round(inv.amount_residual or 0.0, 3),
                'currency': inv.currency_id.name if inv.currency_id else '',
                'state': self._val(inv, 'state'), 'state_code': code,
                'state_color': self._state_color(code),
                'payment': plabel, 'payment_color': self._PAY_COLORS.get(inv.payment_state, '#94A3B8'),
                'date': _d(inv.invoice_date), 'due': _d(inv.invoice_date_due),
            })
        return _ok({'count': len(out), 'invoices': out})

    @route(API + '/management/purchases/<int:rid>/send', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def management_po_send(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('purchases')):
            return _err('لا تملك صلاحية', 403)
        try:
            po = self._po(env, rid)
        except Exception:
            return _err('غير موجود', 404)
        from .api import _body
        b = _body() or {}
        email = (b.get('email') or '').strip() or (po.partner_id.email if po.partner_id else '')
        if not email:
            return _err('لا يوجد بريد للمورّد. اختر مستلمًا أو أضف بريد المورّد.', 400)
        tmpl = env.ref('purchase.email_template_edi_purchase', raise_if_not_found=False)
        try:
            if tmpl:
                tmpl.sudo().send_mail(po.id, force_send=True,
                                      email_values={'email_to': email},
                                      email_layout_xmlid='mail.mail_notification_light')
            else:
                env['mail.mail'].sudo().create({
                    'subject': 'Purchase Order %s' % (po.name or ''),
                    'email_to': email,
                    'body_html': '<p>Please find attached purchase order %s.</p>' % (po.name or ''),
                }).send()
            if po.state == 'draft':
                po.sudo().write({'state': 'sent'})
            po.sudo().message_post(body='📧 تم إرسال أمر الشراء إلى %s.' % email)
        except Exception as e:
            return _err('تعذّر الإرسال: %s' % e, 500)
        return _ok({'sent': True, 'email': email})

    @route(API + '/management/purchases/recipients', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_po_recipients(self, rid=None, **kw):
        """Vendor contacts + other partners to pick a send recipient from."""
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        parts = env['res.partner'].search(
            ['|', ('supplier_rank', '>', 0), ('email', '!=', False)],
            order='name', limit=400)
        return _ok({'recipients': [{'v': p.id, 'l': p.display_name, 'email': p.email}
                                   for p in parts if p.email]})

    @route(API + '/management/purchases/meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_po_meta(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._can(env, self._spec('purchases')):
            return _err('لا صلاحية', 403)
        vendors = env['res.partner'].search([('supplier_rank', '>', 0)], order='name', limit=500)
        if not vendors:
            vendors = env['res.partner'].search([('is_company', '=', True)], order='name', limit=500)
        cur = env.company.currency_id.name
        return _ok({
            'vendors': [{'v': p.id, 'l': p.display_name, 'email': p.email} for p in vendors],
            'currency': cur,
        })

    @route(API + '/management/products/search', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_products_search(self, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        q = (q or '').strip()
        dom = [('purchase_ok', '=', True)]
        if q:
            dom = ['&', ('purchase_ok', '=', True),
                   '|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        prods = env['product.product'].search(dom, order='name', limit=40)
        out = []
        for p in prods:
            price = p.standard_price or p.list_price or 0.0
            try:
                if p.seller_ids:
                    price = p.seller_ids[0].price or price
            except Exception:
                pass
            out.append({
                'id': p.id, 'name': p.display_name,
                'code': p.default_code or '',
                'price': round(price, 3),
                'uom': (p.uom_po_id or p.uom_id).name if (p.uom_po_id or p.uom_id) else '',
            })
        return _ok({'products': out})

    def _po_line_vals(self, env, l):
        prod = env['product.product'].browse(int(l['product_id']))
        return (0, 0, {
            'product_id': prod.id,
            'name': (l.get('name') or prod.display_name),
            'product_qty': float(l.get('qty') or 1),
            'price_unit': float(l.get('price') or 0),
            'product_uom': (prod.uom_po_id or prod.uom_id).id,
            'date_planned': fields.Datetime.now(),
        })

    @route(API + '/management/purchases/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_po_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if self._create_blocked(env, 'purchases'):
            return _err('لا تملك صلاحية الإنشاء', 403)
        try:
            env['purchase.order'].check_access_rights('create', raise_exception=True)
        except Exception:
            return _err('لا تملك صلاحية إنشاء أمر شراء', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('partner_id'):
            return _err('اختر المورّد أولًا', 422)
        lines = b.get('lines') or []
        if not lines:
            return _err('أضف بندًا واحدًا على الأقل', 422)
        vals = {'partner_id': int(b['partner_id'])}
        if b.get('partner_ref'):
            vals['partner_ref'] = b['partner_ref']
        if b.get('notes'):
            vals['notes'] = b['notes']
        try:
            vals['order_line'] = [self._po_line_vals(env, l) for l in lines]
            rec = env['purchase.order'].create(vals)
        except AccessError:
            return _err('لا تملك صلاحية إنشاء أمر شراء', 403)
        except Exception as e:
            return _err('تعذّر الإنشاء: %s' % e, 422)
        return _ok({'id': rec.id, 'title': rec.name})

    @route(API + '/management/purchases/<int:rid>/edit-data', type='http',
           auth='public', methods=['GET'], csrf=False, cors='*')
    def management_po_edit_data(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            po = self._po(env, rid)
        except Exception:
            return _err('غير موجود', 404)
        lines = []
        for l in po.order_line:
            if l.display_type:
                continue
            lines.append({
                'product_id': l.product_id.id if l.product_id else None,
                'name': l.name or (l.product_id.display_name if l.product_id else ''),
                'qty': l.product_qty, 'price': l.price_unit,
                'uom': l.product_uom.name if l.product_uom else '',
                'received': l.qty_received or 0,
            })
        return _ok({
            'id': po.id, 'partner_id': po.partner_id.id if po.partner_id else None,
            'partner_name': po.partner_id.display_name if po.partner_id else None,
            'partner_ref': po.partner_ref or '', 'notes': po.notes or '',
            'state': po.state, 'lines_editable': po.state in ('draft', 'sent'),
            'currency': po.currency_id.name if po.currency_id else '',
            'lines': lines,
        })

    @route(API + '/management/purchases/<int:rid>/update', type='http',
           auth='public', methods=['POST'], csrf=False, cors='*')
    def management_po_update(self, rid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            po = env['purchase.order'].browse(int(rid))
            po.check_access_rule('write')
            po.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        from .api import _body
        b = _body() or {}
        vals = {}
        if b.get('partner_id'):
            vals['partner_id'] = int(b['partner_id'])
        if 'partner_ref' in b:
            vals['partner_ref'] = b.get('partner_ref') or False
        if 'notes' in b:
            vals['notes'] = b.get('notes') or False
        # lines: only editable while draft/sent
        if b.get('lines') is not None and po.state in ('draft', 'sent'):
            try:
                cmds = [(5, 0, 0)] + [self._po_line_vals(env, l) for l in b['lines']]
                vals['order_line'] = cmds
            except Exception as e:
                return _err('خطأ في البنود: %s' % e, 422)
        try:
            po.write(vals)
        except AccessError:
            return _err('لا تملك صلاحية التعديل', 403)
        except Exception as e:
            return _err('تعذّر الحفظ: %s' % e, 422)
        return _ok({'id': po.id, 'title': po.name})

    # ---- Housing «السكن» hub (hostels / rooms / beds / occupancy) ---------
    def _housing_ok(self, env):
        return 'hostel.bed' in env and self._can(env, {'model': 'hostel.bed'})

    _BAND_COLOR = {'low': '#DC2626', 'mid': '#F59E0B', 'high': '#16A34A'}

    @route(API + '/management/housing/hub', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_housing_hub(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._housing_ok(env):
            return _err('لا تملك صلاحية على السكن', 403)
        Bed = env['hostel.bed']
        Room = env['hostel.room']
        Hostel = env['hostel']
        total_beds = Bed.search_count([])
        occupied = Bed.search_count([('employee_id', '!=', False)])
        vacant = total_beds - occupied
        pct = round(occupied / total_beds * 100, 1) if total_beds else 0.0
        stats = [
            {'key': 'buildings', 'ar': 'المباني', 'en': 'Buildings', 'value': Hostel.search_count([]), 'icon': '🏢'},
            {'key': 'rooms', 'ar': 'الغرف', 'en': 'Rooms', 'value': Room.search_count([]), 'icon': '🚪'},
            {'key': 'beds', 'ar': 'الأسرّة', 'en': 'Beds', 'value': total_beds, 'icon': '🛏️'},
            {'key': 'occupied', 'ar': 'مشغولة', 'en': 'Occupied', 'value': occupied, 'icon': '🧑', 'color': '#16A34A'},
            {'key': 'vacant', 'ar': 'شاغرة', 'en': 'Vacant', 'value': vacant, 'icon': '🟢', 'color': '#F59E0B'},
            {'key': 'occupancy', 'ar': 'نسبة الإشغال', 'en': 'Occupancy', 'value': pct, 'unit': '%', 'icon': '📊'},
        ]
        buildings = []
        for h in Hostel.search([], order='name'):
            beds = Bed.search_count([('hostel_id', '=', h.id)])
            occ = Bed.search_count([('hostel_id', '=', h.id), ('employee_id', '!=', False)])
            band = h.occupancy_band if 'occupancy_band' in h._fields else None
            hf = h._fields
            buildings.append({
                'id': h.id, 'name': h.display_name,
                'beds': beds, 'occupied': occ, 'vacant': beds - occ,
                'pct': round(occ / beds * 100, 0) if beds else 0,
                'band': band, 'band_color': self._BAND_COLOR.get(band, '#94A3B8'),
                # richer per-hostel figures (mirror the backend hostel form)
                'address': h.address if 'address' in hf else None,
                'floors': h.floor_count if 'floor_count' in hf else None,
                'flats': h.flat_count if 'flat_count' in hf else None,
                'rooms': h.room_count if 'room_count' in hf else None,
                'capacity': h.total_capacity if 'total_capacity' in hf else None,
                'maintenance': h.maintenance if 'maintenance' in hf else None,
                'price': round(h.price or 0.0, 2) if 'price' in hf else None,
                'labor_cost': round(h.labor_cost or 0.0, 2) if 'labor_cost' in hf else None,
            })
        return _ok({'stats': stats, 'buildings': buildings,
                    'can_write': Bed.check_access_rights('write', raise_exception=False),
                    'can_maintain': ('hostel.maintenance' in env and env['hostel.maintenance'].check_access_rights('create', raise_exception=False))})

    # ---- Housing: internal maintenance sub-module -------------------------
    @route(API + '/management/housing/maintenance', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_housing_maintenance(self, hostel=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'hostel.maintenance' not in env:
            return _ok({'items': [], 'total_expected': 0, 'total_actual': 0})
        M = env['hostel.maintenance']
        dom = []
        if hostel:
            try:
                dom.append(('hostel_id', '=', int(hostel)))
            except (TypeError, ValueError):
                pass
        recs = M.search(dom, order='id desc', limit=200)
        items = [{
            'id': m.id, 'name': m.name,
            'hostel': m.hostel_id.display_name if m.hostel_id else None,
            'floor': m.floor_id.display_name if m.floor_id else None,
            'flat': m.flat_id.display_name if m.flat_id else None,
            'room': m.room_id.display_name if m.room_id else None,
            'expected_cost': round(m.expected_cost or 0.0, 2),
            'actual_cost': round(m.actually_cost or 0.0, 2),
        } for m in recs]
        hostels = env['hostel'].sudo().search([], order='name') if 'hostel' in env else []
        return _ok({
            'items': items,
            'total_expected': round(sum(m.expected_cost or 0.0 for m in recs), 2),
            'total_actual': round(sum(m.actually_cost or 0.0 for m in recs), 2),
            'can_create': M.check_access_rights('create', raise_exception=False),
            'hostels': [{'v': h.id, 'l': h.display_name} for h in hostels],
        })

    @route(API + '/management/housing/maintenance', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_housing_maintenance_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if 'hostel.maintenance' not in env:
            return _err('وحدة الصيانة غير مفعّلة', 404)
        from .api import _body
        b = _body() or {}
        try:
            vals = {
                'name': (b.get('name') or 'صيانة').strip(),
                'hostel_id': int(b['hostel_id']),
                'expected_cost': float(b.get('expected_cost') or 0),
                'actually_cost': float(b.get('actual_cost') or 0),
            }
            for f in ('floor_id', 'flat_id', 'room_id'):
                if b.get(f):
                    vals[f] = int(b[f])
            rec = env['hostel.maintenance'].create(vals)
        except Exception as e:
            return _err('تعذّر إضافة سجل الصيانة: %s' % e, 400)
        return _ok({'saved': True, 'id': rec.id})

    @route(API + '/management/housing/beds', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_housing_beds(self, hostel=None, status=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._housing_ok(env):
            return _err('لا صلاحية', 403)
        Bed = env['hostel.bed']
        dom = []
        if hostel:
            try:
                dom.append(('hostel_id', '=', int(hostel)))
            except (TypeError, ValueError):
                pass
        if status == 'occupied':
            dom.append(('employee_id', '!=', False))
        elif status == 'vacant':
            dom.append(('employee_id', '=', False))
        q = (q or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q), ('room_id.name', 'ilike', q), ('employee_id.name', 'ilike', q)]
        beds = Bed.search(dom, order='hostel_id, name', limit=300)
        out = []
        for b in beds:
            emp = b.employee_id if 'employee_id' in b._fields else None
            out.append({
                'id': b.id, 'name': b.name or '—',
                'room': b.room_id.display_name if ('room_id' in b._fields and b.room_id) else None,
                'hostel': b.hostel_id.display_name if ('hostel_id' in b._fields and b.hostel_id) else None,
                'occupied': bool(emp),
                'employee': emp.display_name if emp else None,
                'employee_id': emp.id if emp else None,
                'photo_b64': self._img_b64(emp, ('image_128',)) if emp else None,
            })
        return _ok({'count': Bed.search_count(dom), 'beds': out})

    @route(API + '/management/housing/bed/<int:bid>/assign', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_housing_assign(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._housing_ok(env):
            return _err('لا صلاحية', 403)
        from .api import _body
        b = _body() or {}
        if not b.get('employee_id'):
            return _err('اختر العامل أولًا', 422)
        try:
            bed = env['hostel.bed'].browse(int(bid))
            bed.check_access_rule('write')
            bed.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        if bed.employee_id:
            return _err('السرير مشغول بالفعل بـ %s. أخلِه أولًا.' % bed.employee_id.display_name, 422)
        emp_id = int(b['employee_id'])
        other = env['hostel.bed'].sudo().search([('employee_id', '=', emp_id)], limit=1)
        if other:
            return _err('هذا العامل مسكّن بالفعل في سرير آخر (%s). أخرجه منه أولًا.' % other.name, 422)
        try:
            bed.write({'employee_id': emp_id})
            emp = env['hr.employee'].sudo().browse(emp_id)
            bed.sudo().message_post(body='🛏️ تم تسكين %s في السرير %s.' % (emp.display_name, bed.name))
        except AccessError:
            return _err('لا تملك صلاحية التسكين', 403)
        except Exception as e:
            return _err('تعذّر التسكين: %s' % e, 422)
        return _ok({'id': bed.id, 'employee': bed.employee_id.display_name, 'employee_id': bed.employee_id.id})

    @route(API + '/management/housing/bed/<int:bid>/vacate', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_housing_vacate(self, bid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._housing_ok(env):
            return _err('لا صلاحية', 403)
        try:
            bed = env['hostel.bed'].browse(int(bid))
            bed.check_access_rule('write')
            bed.read(['id'])
        except Exception:
            return _err('غير موجود أو غير مصرّح', 403)
        if not bed.employee_id:
            return _err('السرير شاغر بالفعل.', 422)
        name = bed.employee_id.display_name
        try:
            bed.sudo().message_post(body='🚪 تم إخلاء %s من السرير %s.' % (name, bed.name))
            bed.write({'employee_id': False})
        except AccessError:
            return _err('لا تملك صلاحية الإخلاء', 403)
        except Exception as e:
            return _err('تعذّر الإخلاء: %s' % e, 422)
        return _ok({'id': bed.id, 'vacated': True, 'was': name})

    # ---- Analytics dashboard (DB-side aggregation across systems) ----------
    def _analytics_data(self, env, period=None):
        cur = env.company.currency_id.name or ''

        # period → date-domain factory (point-in-time metrics ignore it)
        period = period if period in ('month', 'year', 'all') else 'all'
        _today = fields.Date.today()
        if period == 'month':
            _since = _today.replace(day=1)
        elif period == 'year':
            _since = _today.replace(month=1, day=1)
        else:
            _since = None

        def pdom(field):
            return [(field, '>=', str(_since))] if _since else []

        def can(model):
            return model in env and self._can(env, {'model': model})

        def ssum(model, dom, field='amount_total'):
            try:
                g = env[model].read_group(dom, [field], [])
                return round((g[0].get(field) if g else 0.0) or 0.0, 3)
            except Exception:
                return 0.0

        def cnt(model, dom):
            try:
                return env[model].search_count(dom)
            except Exception:
                return 0

        kpis, charts = [], {}

        # --- headline KPIs ---
        if can('sale.order'):
            kpis.append({'key': 'sales', 'ar': 'المبيعات المؤكدة', 'en': 'Confirmed sales',
                         'value': ssum('sale.order', [('state', 'in', ('sale', 'done'))] + pdom('date_order')),
                         'unit': cur, 'icon': '💰', 'color': '#16A34A', 'money': True})
        if can('purchase.order'):
            kpis.append({'key': 'purchases', 'ar': 'المشتريات', 'en': 'Purchases',
                         'value': ssum('purchase.order', [('state', 'in', ('purchase', 'done'))] + pdom('date_order')),
                         'unit': cur, 'icon': '🛒', 'color': '#2563EB', 'money': True})
        if can('proposal.proposal'):
            active = [('state', 'in', ('draft', 'submit', 'waiting', 'approve'))]
            kpis.append({'key': 'pipeline', 'ar': 'عروض قيد التداول', 'en': 'Proposals pipeline',
                         'value': ssum('proposal.proposal', active + pdom('proposal_date'), 'total_amount'),
                         'unit': cur, 'icon': '📊', 'color': '#7C3AED', 'money': True})
            # proposals by state (chart)
            try:
                labels = dict(env['proposal.proposal']._fields['state']._description_selection(env))
                g = env['proposal.proposal'].read_group(pdom('proposal_date'), ['state'], ['state'])
                charts['proposals_by_state'] = [
                    {'label': labels.get(r['state'], r['state']), 'value': r['state_count'],
                     'code': r['state'], 'color': self._state_color(r['state'])} for r in g if r.get('state')]
            except Exception:
                pass
        if can('crm.lead'):
            kpis.append({'key': 'crm', 'ar': 'الإيراد المتوقع', 'en': 'CRM pipeline',
                         'value': ssum('crm.lead', [('stage_id.is_won', '=', False)] + pdom('create_date'), 'expected_revenue'),
                         'unit': cur, 'icon': '🎯', 'color': '#F59E0B', 'money': True})
        if can('purchase.tender'):
            kpis.append({'key': 'tenders', 'ar': 'مناقصات نشطة', 'en': 'Active tenders',
                         'value': cnt('purchase.tender', [('state', 'in', list(self._TENDER_ACTIVE))]),
                         'icon': '📑', 'color': '#0891B2'})
        # housing occupancy
        if 'hostel.bed' in env and self._housing_ok(env):
            tb = cnt('hostel.bed', [])
            occ = cnt('hostel.bed', [('employee_id', '!=', False)])
            pct = round(occ / tb * 100, 1) if tb else 0
            kpis.append({'key': 'occupancy', 'ar': 'إشغال السكن', 'en': 'Housing occupancy',
                         'value': pct, 'unit': '%', 'icon': '🏠', 'color': '#0D9488'})
            charts['housing'] = {'occupied': occ, 'vacant': tb - occ, 'pct': pct}
        if can('fleet.vehicle'):
            total = cnt('fleet.vehicle', [])
            assigned = cnt('fleet.vehicle', [('driver_id', '!=', False)])
            charts['fleet'] = {'assigned': assigned, 'free': total - assigned, 'total': total}
        if can('hr.employee'):
            kpis.append({'key': 'employees', 'ar': 'الموظفون', 'en': 'Employees',
                         'value': cnt('hr.employee', []), 'icon': '👥', 'color': '#334155'})

        # --- monthly trend: sales vs purchases (last 6 months, explicit ranges) ---
        from dateutil.relativedelta import relativedelta
        first = fields.Date.today().replace(day=1)
        axis = []
        for i in range(5, -1, -1):
            m = first - relativedelta(months=i)
            axis.append((m.strftime('%b'), str(m), str(m + relativedelta(months=1))))
        if can('sale.order') or can('purchase.order'):
            charts['trend'] = {
                'labels': [lbl for lbl, _s, _e in axis],
                'sales': [ssum('sale.order', [('state', 'in', ('sale', 'done')), ('date_order', '>=', s), ('date_order', '<', e)]) for _l, s, e in axis] if can('sale.order') else [],
                'purchases': [ssum('purchase.order', [('state', 'in', ('purchase', 'done')), ('date_order', '>=', s), ('date_order', '<', e)]) for _l, s, e in axis] if can('purchase.order') else [],
            }

        # --- CRM pipeline by stage (expected revenue) ---
        if can('crm.lead'):
            try:
                g = env['crm.lead'].read_group(
                    [('stage_id.is_won', '=', False)] + pdom('create_date'), ['expected_revenue'], ['stage_id'])
                charts['crm_stages'] = [
                    {'label': (r['stage_id'][1] if r.get('stage_id') else '—'),
                     'value': round(r.get('expected_revenue') or 0.0, 2), 'count': r['stage_id_count']}
                    for r in g][:6]
            except Exception:
                pass

        # --- needs attention: pending items across systems (actionable) ---
        attention = []
        _ATT = [
            ('proposals', 'عروض بانتظار الاعتماد', 'Proposals to approve', '📊', '#7C3AED'),
            ('purchases', 'مشتريات للاعتماد', 'Purchases to approve', '🛒', '#2563EB'),
            ('leaves', 'إجازات للاعتماد', 'Leaves to approve', '🌴', '#0891B2'),
            ('expenses', 'مصروفات للاعتماد', 'Expenses to approve', '🧾', '#F59E0B'),
            ('invoices', 'فواتير مسودّة', 'Draft invoices', '🧾', '#DC2626'),
            ('tenders', 'مناقصات قيد الدراسة', 'Tenders under study', '📑', '#0891B2'),
        ]
        for key, ar, en, icon, color in _ATT:
            spec = REGISTRY.get(key)
            pend = self._PENDING.get(key)
            if not spec or pend is None or not can(spec['model']):
                continue
            dom = list(spec.get('domain') or []) + pend
            n = cnt(spec['model'], dom)
            if n:
                # states from the pending domain → comma list for the list filter
                states = ','.join(v for (f, op, v) in
                                  [t for t in pend if isinstance(t, tuple) and t[0] == 'state']
                                  for v in (v if isinstance(v, (list, tuple)) else [v]))
                attention.append({'key': key, 'ar': ar, 'en': en, 'icon': icon,
                                  'color': color, 'count': n, 'states': states})

        return {'currency': cur, 'period': period, 'kpis': kpis,
                'charts': charts, 'attention': attention}

    @route(API + '/management/analytics', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_analytics(self, period=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        period = period if period in ('month', 'year', 'all') else 'all'
        return _ok(self._analytics_data(env, period))

    @route(API + '/management/analytics/export', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_analytics_export(self, period=None, lang=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        period = period if period in ('month', 'year', 'all') else 'all'
        d = self._analytics_data(env, period)
        ar = (lang != 'en')
        import io
        import xlsxwriter
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Analytics')
        if ar:
            ws.right_to_left()
        H = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#B01C2E', 'border': 1})
        SUB = wb.add_format({'bold': True, 'bg_color': '#F1F5F9', 'border': 1})
        C = wb.add_format({'border': 1})
        N = wb.add_format({'border': 1, 'num_format': '#,##0.000'})
        ws.set_column(0, 0, 34)
        ws.set_column(1, 3, 18)
        plabel = {'all': ('الكل', 'All'), 'year': ('هذه السنة', 'This year'),
                  'month': ('هذا الشهر', 'This month')}[period]
        r = 0
        ws.write(r, 0, ('لوحة تحليلات الإدارة' if ar else 'Management Analytics') + ' — ' + (plabel[0] if ar else plabel[1]), H)
        ws.write(r, 1, '', H)
        r += 2
        # KPIs
        ws.write(r, 0, 'المؤشرات' if ar else 'KPIs', SUB); ws.write(r, 1, '', SUB); r += 1
        for k in d['kpis']:
            ws.write(r, 0, (k['ar'] if ar else k['en']), C)
            unit = (' %s' % k['unit']) if k.get('unit') else ''
            ws.write(r, 1, '%s%s' % (k['value'], unit), C)
            r += 1
        r += 1
        # Needs attention
        if d.get('attention'):
            ws.write(r, 0, 'يحتاج إجراء' if ar else 'Needs attention', SUB); ws.write(r, 1, '', SUB); r += 1
            for a in d['attention']:
                ws.write(r, 0, (a['ar'] if ar else a['en']), C)
                ws.write(r, 1, a['count'], C)
                r += 1
            r += 1
        # Trend
        tr_ = d['charts'].get('trend')
        if tr_:
            ws.write(r, 0, 'المبيعات مقابل المشتريات' if ar else 'Sales vs Purchases', SUB)
            ws.write(r, 1, 'المبيعات' if ar else 'Sales', SUB)
            ws.write(r, 2, 'المشتريات' if ar else 'Purchases', SUB); r += 1
            for i, lbl in enumerate(tr_['labels']):
                ws.write(r, 0, lbl, C)
                ws.write(r, 1, (tr_['sales'][i] if i < len(tr_['sales']) else 0), N)
                ws.write(r, 2, (tr_['purchases'][i] if i < len(tr_['purchases']) else 0), N)
                r += 1
            r += 1
        # Proposals by state / CRM stages
        for ck, title_ar, title_en in (('proposals_by_state', 'العروض حسب الحالة', 'Proposals by state'),
                                       ('crm_stages', 'الفرص حسب المرحلة', 'CRM by stage')):
            rows = d['charts'].get(ck)
            if rows:
                ws.write(r, 0, title_ar if ar else title_en, SUB); ws.write(r, 1, '', SUB); r += 1
                for x in rows:
                    ws.write(r, 0, x['label'], C)
                    ws.write(r, 1, x['value'], N if ck == 'crm_stages' else C)
                    r += 1
                r += 1
        wb.close()
        data = buf.getvalue()
        buf.close()
        return request.make_response(data, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="analytics-%s.xlsx"' % period),
            ('Content-Length', str(len(data)))])

    # ---- Config-driven generic create (every eligible system) -------------
    @route(API + '/management/relation/search', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_relation_search(self, model=None, q=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        fields_ = RELATION_SEARCH.get(model)
        if not fields_:
            return _err('نموذج غير مسموح', 403)
        q = (q or '').strip()
        dom = []
        if q:
            sub = [(f, 'ilike', q) for f in fields_ if f in env[model]._fields]
            dom = ['|'] * (len(sub) - 1) + sub
        try:
            recs = env[model].search(dom, order='name', limit=40)
        except Exception:
            recs = env[model].search(dom, limit=40)
        return _ok({'options': [{'v': r.id, 'l': r.display_name} for r in recs]})

    @route(API + '/management/<string:key>/create-meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_create_meta(self, key, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cs = CREATE_SPECS.get(key)
        if not cs:
            return _err('الإنشاء غير متاح لهذا النظام', 404)
        Model = env[cs['model']]
        fields_out = []
        for f in cs['fields']:
            item = {k: f[k] for k in ('name', 'ar', 'en', 'type', 'required') if k in f}
            if f['name'] not in Model._fields:
                continue
            mf = Model._fields[f['name']]
            if f['type'] == 'selection':
                try:
                    item['options'] = [{'v': k2, 'l': l2} for k2, l2 in mf._description_selection(env)]
                except Exception:
                    item['options'] = []
            elif f['type'] == 'many2one':
                if f.get('search'):
                    item['search'] = f['search']
                elif f.get('model') and f['model'] in env:
                    recs = env[f['model']].sudo().search([], limit=200)
                    item['options'] = [{'v': r.id, 'l': r.display_name} for r in recs]
                else:
                    item['options'] = []
            fields_out.append(item)
        return _ok({'key': key, 'ar': cs['ar'], 'en': cs['en'], 'fields': fields_out})

    @route(API + '/management/<string:key>/generic-create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_generic_create(self, key, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cs = CREATE_SPECS.get(key)
        if not cs:
            return _err('الإنشاء غير متاح لهذا النظام', 404)
        if self._create_blocked(env, key):
            return _err('لا تملك صلاحية الإنشاء', 403)
        reg = REGISTRY.get(key) or {}
        Model = env[cs['model']].sudo() if reg.get('sudo') else env[cs['model']]
        if not reg.get('sudo'):
            try:
                Model.check_access_rights('create', raise_exception=True)
            except Exception:
                return _err('لا تملك صلاحية الإنشاء', 403)
        elif not (env.user.has_group('base.group_erp_manager') or env.user.has_group('base.group_system')):
            return _err('لا تملك صلاحية الإنشاء', 403)
        from .api import _body
        b = _body() or {}
        vals = dict(cs.get('defaults') or {})
        for f in cs['fields']:
            name, typ = f['name'], f['type']
            if name not in Model._fields:
                continue
            v = b.get(name)
            if v in (None, ''):
                if f.get('required'):
                    return _err('الحقل «%s» مطلوب' % f['ar'], 422)
                continue
            try:
                if typ in ('many2one', 'integer'):
                    vals[name] = int(v)
                elif typ in ('float', 'monetary'):
                    vals[name] = float(v)
                elif typ == 'boolean':
                    vals[name] = bool(v)
                else:
                    vals[name] = v
            except (TypeError, ValueError):
                return _err('قيمة غير صحيحة للحقل «%s»' % f['ar'], 422)
        try:
            rec = Model.create(vals)
        except AccessError:
            return _err('لا تملك صلاحية الإنشاء', 403)
        except Exception as e:
            return _err('تعذّر الإنشاء: %s' % e, 422)
        title = rec.display_name
        for tf in ('name', 'display_name'):
            if tf in rec._fields and rec[tf]:
                title = rec[tf] if isinstance(rec[tf], str) else rec.display_name
                break
        return _ok({'id': rec.id, 'title': title})

    # ---- Employee sub-module quick-create (allowance/loan/permission/…) ----
    def _cast_create_vals(self, Model, spec_fields, b):
        """Cast body values per field spec; return (vals, error_or_None)."""
        vals = {}
        for f in spec_fields:
            name, typ = f['name'], f['type']
            if name not in Model._fields:
                continue
            v = b.get(name)
            if v in (None, ''):
                if f.get('required'):
                    return None, 'الحقل «%s» مطلوب' % f['ar']
                continue
            try:
                if typ in ('many2one', 'integer'):
                    vals[name] = int(v)
                elif typ in ('float', 'monetary'):
                    vals[name] = float(v)
                elif typ == 'boolean':
                    vals[name] = bool(v)
                else:
                    vals[name] = v
            except (TypeError, ValueError):
                return None, 'قيمة غير صحيحة للحقل «%s»' % f['ar']
        return vals, None

    @route(API + '/management/emp-sub/create-meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_empsub_meta(self, model=None, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        cs = EMP_CREATE_SPECS.get(model)
        if not cs or model not in env:
            return _err('غير متاح', 404)
        Model = env[model]
        out = []
        for f in cs['fields']:
            if f['name'] not in Model._fields:
                continue
            item = {k: f[k] for k in ('name', 'ar', 'en', 'type', 'required') if k in f}
            if f['type'] == 'selection':
                try:
                    item['options'] = [{'v': k2, 'l': l2} for k2, l2 in Model._fields[f['name']]._description_selection(env)]
                except Exception:
                    item['options'] = []
            out.append(item)
        return _ok({'model': model, 'ar': cs['ar'], 'en': cs['en'], 'fields': out})

    @route(API + '/management/emp-sub/create', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_empsub_create(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        from .api import _body
        b = _body() or {}
        model = b.get('model')
        cs = EMP_CREATE_SPECS.get(model)
        if not cs or model not in env:
            return _err('غير متاح', 404)
        if not b.get('employee_id'):
            return _err('الموظف مطلوب', 422)
        Model = env[model]
        try:
            Model.check_access_rights('create', raise_exception=True)
        except Exception:
            return _err('لا تملك صلاحية الإنشاء', 403)
        vals, err = self._cast_create_vals(Model, cs['fields'], b)
        if err:
            return _err(err, 422)
        vals['employee_id'] = int(b['employee_id'])
        try:
            rec = Model.create(vals)
        except AccessError:
            return _err('لا تملك صلاحية الإنشاء', 403)
        except Exception as e:
            return _err('تعذّر الإنشاء: %s' % e, 422)
        return _ok({'id': rec.id, 'title': rec.display_name})

    # ---- Access administration (managers configure per-user permissions) ---
    @route(API + '/management/access/meta', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_access_meta(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._is_mgmt_admin(env):
            return _err('هذه الإعدادات للمدراء فقط', 403)
        systems = [{'key': k, 'ar': s['ar'], 'en': s['en'], 'icon': s['icon']}
                   for k, s in REGISTRY.items()]
        users = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)], order='name', limit=400)
        return _ok({
            'systems': systems,
            'users': [{'v': u.id, 'l': u.name, 'login': u.login} for u in users],
        })

    @route(API + '/management/access/<int:uid>', type='http', auth='public',
           methods=['GET'], csrf=False, cors='*')
    def management_access_get(self, uid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._is_mgmt_admin(env):
            return _err('للمدراء فقط', 403)
        cfg = self._access_all(env).get(str(uid)) or {}
        return _ok({
            'user_id': uid,
            'hidden': cfg.get('hidden') or [],
            'no_create': cfg.get('no_create') or [],
            'no_edit': cfg.get('no_edit') or [],
            'hide_attachments': bool(cfg.get('hide_attachments')),
            'hide_amounts': bool(cfg.get('hide_amounts')),
        })

    @route(API + '/management/access/<int:uid>', type='http', auth='public',
           methods=['POST'], csrf=False, cors='*')
    def management_access_save(self, uid, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        if not self._is_mgmt_admin(env):
            return _err('للمدراء فقط', 403)
        from .api import _body
        b = _body() or {}
        import json
        valid = set(REGISTRY.keys())

        def clean(lst):
            return [k for k in (b.get(lst) or []) if k in valid]

        allcfg = self._access_all(env)
        entry = {
            'hidden': clean('hidden'),
            'no_create': clean('no_create'),
            'no_edit': clean('no_edit'),
            'hide_attachments': bool(b.get('hide_attachments')),
            'hide_amounts': bool(b.get('hide_amounts')),
        }
        # drop empty entries to keep the param compact
        if any(entry[k] for k in ('hidden', 'no_create', 'no_edit')) or entry['hide_attachments'] or entry['hide_amounts']:
            allcfg[str(uid)] = entry
        else:
            allcfg.pop(str(uid), None)
        env['ir.config_parameter'].sudo().set_param(self._ACCESS_PARAM, json.dumps(allcfg))
        return _ok({'saved': True, 'user_id': uid})

    # ---- Approvals inbox: records awaiting THIS user's action -------------
    # The featured "الاعتمادات" tile. Genuine "needs me" signals only:
    #   • Odoo activities assigned to me (covers leave/expense/PO approvers,
    #     to-approve routing, follow-ups) — grouped by the record's model.
    #   • approval.request where I'm a still-pending approver.
    # Both map back to the Management systems so the app can open the record
    # and act on it via the normal detail screen.
    def _inbox_build(self, env):
        uid = env.uid
        # reverse model -> system-key map (first system that owns a model wins)
        model_key = {}
        for k, s in REGISTRY.items():
            model_key.setdefault(s['model'], k)
        access = self._user_access(env)

        # 1) my open activities grouped by model
        by_key = {}   # key -> {'count':int, 'ids':set(res_id)}
        try:
            grp = env['mail.activity'].sudo().read_group(
                [('user_id', '=', uid)], ['res_model', 'res_id:array_agg'],
                ['res_model'], lazy=False)
        except Exception:
            grp = []
        for g in grp:
            model = g.get('res_model')
            key = model_key.get(model)
            if not key or key in access['hidden']:
                continue
            spec = REGISTRY.get(key)
            if not spec or not self._can(env, spec):
                continue
            ids = set(i for i in (g.get('res_id') or []) if i)
            b = by_key.setdefault(key, {'count': 0, 'ids': set()})
            b['ids'] |= ids

        # 2) approval.request where I'm a pending approver
        try:
            appr_key = model_key.get('approval.request')
            if appr_key and appr_key not in access['hidden']:
                lines = env['approval.approver'].sudo().search([
                    ('user_id', '=', uid),
                    ('status', 'in', ['new', 'pending', 'waiting']),
                ])
                rids = set(l.request_id.id for l in lines
                           if l.request_id and l.request_id.request_status in ('new', 'pending'))
                if rids:
                    b = by_key.setdefault(appr_key, {'count': 0, 'ids': set()})
                    b['ids'] |= rids
        except Exception:
            pass

        # materialise: per-source count + a flat item list to open & act on
        sources, items = [], []
        hide_amounts = access['hide_amounts']
        for key, data in by_key.items():
            spec = REGISTRY[key]
            ids = [i for i in data['ids'] if i]
            if not ids:
                continue
            try:
                recs = self._model(env, spec).browse(ids).exists()
            except Exception:
                continue
            n = len(recs)
            if not n:
                continue
            sources.append({'key': key, 'icon': spec['icon'], 'ar': spec['ar'],
                            'en': spec['en'], 'count': n})
            tf, df, af = spec.get('title'), spec.get('date'), spec.get('amount')
            for r in recs[:12]:
                try:
                    title = (r[tf] if tf and tf in r._fields else False) or r.display_name
                except Exception:
                    title = r.display_name
                sub = spec.get('subtitle')
                subtitle = None
                if sub and sub in r._fields:
                    try:
                        sv = r[sub]
                        subtitle = sv.display_name if hasattr(sv, 'display_name') else (str(sv) if sv else None)
                    except Exception:
                        subtitle = None
                amount = None
                if af and not hide_amounts and af in r._fields:
                    try:
                        amount = r[af]
                    except Exception:
                        amount = None
                dt = None
                if df and df in r._fields:
                    try:
                        dt = _d(r[df])
                    except Exception:
                        dt = None
                items.append({
                    'key': key, 'system_ar': spec['ar'], 'system_en': spec['en'],
                    'icon': spec['icon'], 'id': r.id, 'title': str(title),
                    'subtitle': subtitle, 'amount': amount, 'date': dt,
                })
        sources.sort(key=lambda s: -s['count'])
        # newest first where a date exists, else keep grouping
        items.sort(key=lambda x: (x['date'] or ''), reverse=True)
        total = sum(s['count'] for s in sources)
        return {'total': total, 'sources': sources, 'items': items[:40]}

    @route(API + '/management/inbox', type='http', auth='public', methods=['GET'],
           csrf=False, cors='*')
    def management_inbox(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        try:
            return _ok(self._inbox_build(env))
        except Exception as e:
            return _ok({'total': 0, 'sources': [], 'items': [], 'error': str(e)})

    @route(API + '/management/me', type='http', auth='public', methods=['GET'],
           csrf=False, cors='*')
    def management_me(self, **kw):
        env = _auth()
        if not env:
            return _err('غير مصرّح', 401)
        u = env.user
        emp = u.employee_id if 'employee_id' in u._fields and u.employee_id else None

        def _count(model, domain):
            try:
                return env[model].search_count(domain)
            except Exception:
                return None

        stats = []
        sys_count = sum(1 for _k, s in REGISTRY.items() if self._can(env, s))
        stats.append({'key': 'systems', 'ar': 'أنظمتك', 'en': 'Your systems',
                      'value': sys_count, 'icon': '🗂️'})
        pending = 0
        for model, dom in (('hr.leave', [('state', 'in', ('confirm', 'validate1'))]),
                           ('hr.expense.sheet', [('state', '=', 'submit')]),
                           ('purchase.order', [('state', '=', 'to approve')])):
            c = _count(model, dom)
            if c:
                pending += c
        stats.append({'key': 'approvals', 'ar': 'بانتظار اعتمادك', 'en': 'Awaiting you',
                      'value': pending, 'icon': '✅'})
        tasks = _count('project.task', [('user_ids', 'in', u.id), ('state', 'not in', ('1_done', '1_canceled'))])
        if tasks is not None:
            stats.append({'key': 'tasks', 'ar': 'مهامي المفتوحة', 'en': 'My open tasks',
                          'value': tasks, 'icon': '📋'})
        my_leaves = _count('hr.leave', [('employee_id', '=', emp.id)]) if emp else None
        if my_leaves is not None:
            stats.append({'key': 'my_leaves', 'ar': 'إجازاتي', 'en': 'My time off',
                          'value': my_leaves, 'icon': '🌴'})
        return _ok({
            'name': u.name,
            'login': u.login,
            'job': (emp.job_title if emp else None)
                   or (u.function if 'function' in u._fields else None),
            'department': emp.department_id.display_name if emp and emp.department_id else None,
            # base64 avatar embedded directly — /web/image needs a web session the
            # app doesn't have (it authenticates by token), so the network URL
            # rendered a blank placeholder. The 128px image is small enough to inline.
            'avatar_b64': self._img_b64(u, ('image_128', 'image_256')),
            'avatar_url': '/web/image/res.users/%s/avatar_128' % u.id,
            'is_manager': u.has_group('base.group_erp_manager'),
            'employee_id': emp.id if emp else None,
            'stats': stats,
        })
