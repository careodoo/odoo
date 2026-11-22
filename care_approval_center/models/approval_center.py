# -*- coding: utf-8 -*-
# Approvals center — a unified service that gathers pending requests from all modules according to the
# user's permissions, executes the approve/reject decision on each model per its workflow, and writes a log of the decision.
#
# Extension: add a new request type by adding a line in REGISTRY (the model + the status field + the
# pending states + the approve/reject functions + the groups + the icon). Types are excluded automatically
# if the model or the functions do not exist.
import os
import re
import json
import logging
import traceback
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# key, model, state_field, pending_states, approve_method, reject_method, groups, module(ar), icon, color
REGISTRY = [
    {'key': 'suspend', 'model': 'care.suspension.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'الإيقاف عن العمل', 'icon': '⛔', 'color': '#b0343f'},
    {'key': 'passport', 'model': 'care.passport.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'سحب الجوازات', 'icon': '🛂', 'color': '#8a3b8a'},
    {'key': 'bankcard', 'model': 'care.bank.card.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_bank_card.group_bank_card_finance'], 'module': 'كروت البنك', 'icon': '💳', 'color': '#2a6ab0'},
    {'key': 'leave', 'model': 'hr.leave', 'state_field': 'state',
     'pending': ['confirm'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_user'], 'module': 'الإجازات', 'icon': '🌴', 'color': '#1f9d63'},
    {'key': 'item', 'model': 'care.item.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_item_request.group_item_manager'], 'module': 'طلب الأصناف', 'icon': '📦', 'color': '#7a5bbf'},
    # ===== Additional types (unifying all the system's approvals) — excluded automatically if the model/functions are missing =====
    {'key': 'resignation', 'model': 'hr.employee.resignation', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'action_hr_approve', 'reject': 'action_resignation_refuse',
     'groups': ['hr.group_hr_manager', 'hr.group_hr_user'], 'module': 'الاستقالة', 'icon': '🚪', 'color': '#b0343f'},
    {'key': 'transfer', 'model': 'employee.shift.request', 'state_field': 'state',
     'pending': ['hr_review'], 'approve': 'action_hr_approve', 'reject': 'action_hr_refuse',
     'groups': ['hr.group_hr_manager'], 'module': 'النقل / التكليف', 'icon': '🔄', 'color': '#2a6ab0'},
    {'key': 'loan', 'model': 'care.loan', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_manager', 'hr.group_hr_user'], 'module': 'السلف والقروض', 'icon': '💸', 'color': '#7a5bbf'},
    {'key': 'permission', 'model': 'permission.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'الاستئذان', 'icon': '⏱️', 'color': '#1f9d63'},
    {'key': 'settlement', 'model': 'care.leave.settlement', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['hr.group_hr_manager'], 'module': 'تسوية الإجازات', 'icon': '🧮', 'color': '#017e84'},
    {'key': 'salcert', 'model': 'care.salary.certificate', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_user'], 'module': 'شهادة الراتب', 'icon': '📜', 'color': '#8a3b8a'},
    {'key': 'docreq', 'model': 'care.document.request', 'state_field': 'state',
     'pending': ['uploaded'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'طلب مستند', 'icon': '📄', 'color': '#2a6ab0'},
    {'key': 'overtime', 'model': 'overtime.request', 'state_field': 'state',
     'pending': ['submit', 'waiting'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'العمل الإضافي', 'icon': '⏲️', 'color': '#e08a00'},
    {'key': 'penalty', 'model': 'care.penalty', 'state_field': 'state',
     'pending': ['hr_review'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_manager'], 'module': 'الجزاءات', 'icon': '⚖️', 'color': '#b0343f'},
    {'key': 'bonus', 'model': 'care.bonus', 'state_field': 'state',
     'pending': ['hr_review'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_manager'], 'module': 'المكافآت', 'icon': '🎁', 'color': '#1f9d63'},
    {'key': 'store', 'model': 'care.pms.store.order', 'state_field': 'state',
     'pending': ['sent'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['purchase.group_purchase_manager'], 'module': 'طلبات المتجر', 'icon': '🛒', 'color': '#1b3a6b'},
    {'key': 'reqinv', 'model': 'request.invoice', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_manager_approve', 'reject': 'action_refuse',
     'groups': ['account.group_account_manager', 'hr.group_hr_manager'], 'module': 'طلب فاتورة', 'icon': '🧾', 'color': '#017e84'},
    {'key': 'resume', 'model': 'care.resume.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'مباشرة بعد توقف', 'icon': '▶️', 'color': '#1f9d63'},
    {'key': 'leave_return', 'model': 'hr.action.leave.return', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'العودة من إجازة', 'icon': '↩️', 'color': '#1f9d63'},
    {'key': 'absence', 'model': 'hr.action.absence', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'الغياب', 'icon': '🚫', 'color': '#b0343f'},
    {'key': 'joining', 'model': 'hr.action.joining', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'مباشرة العمل', 'icon': '🚀', 'color': '#2a6ab0'},
    {'key': 'clearance', 'model': 'hr.action.clearance', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'إخلاء طرف', 'icon': '✅', 'color': '#017e84'},
    # ===== The comprehensive batch (we leave no module out) =====
    {'key': 'leave_adj', 'model': 'care.leave.adjustment', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_manager'], 'module': 'تسوية رصيد إجازة', 'icon': '➕', 'color': '#017e84'},
    {'key': 'perm_extra', 'model': 'permission.request.extra.hour', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_user'], 'module': 'ساعات إضافية (استئذان)', 'icon': '⏳', 'color': '#1f9d63'},
    {'key': 'expense', 'model': 'care.expense.claim', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_finance_approve', 'reject': 'action_refuse',
     'groups': ['account.group_account_manager', 'hr.group_hr_manager'], 'module': 'مطالبة مصروفات', 'icon': '🧾', 'color': '#e08a00'},
    {'key': 'care_request', 'model': 'care.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'طلب عام', 'icon': '📋', 'color': '#7a5bbf'},
    {'key': 'eos_withdraw', 'model': 'care.eos.withdrawal', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_manager'], 'module': 'عدول عن إنهاء خدمة', 'icon': '↩️', 'color': '#b0343f'},
    {'key': 'resign_withdraw', 'model': 'care.resignation.withdrawal', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_manager'], 'module': 'عدول عن استقالة', 'icon': '↩️', 'color': '#2a6ab0'},
    {'key': 'sensitive', 'model': 'care.sensitive.edit.request', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_manager'], 'module': 'تعديل بيانات حسّاسة', 'icon': '✏️', 'color': '#8a3b8a'},
    {'key': 'petty_settle', 'model': 'care.pms.petty.settlement', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['account.group_account_manager', 'care_pms.group_pms_manager'], 'module': 'تسوية عهدة نقدية', 'icon': '💵', 'color': '#017e84'},
    {'key': 'pay_expedite', 'model': 'supplier.payment.expedite', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['account.group_account_manager'], 'module': 'تعجيل دفع مورّد', 'icon': '💰', 'color': '#e08a00'},
    {'key': 'cafm_stock', 'model': 'care.cafm.stock.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['base.group_user'], 'module': 'طلب مخزون (CAFM)', 'icon': '📦', 'color': '#7a5bbf'},
    {'key': 'cafm_req', 'model': 'care.cafm.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['base.group_user'], 'module': 'طلب شراء (CAFM)', 'icon': '🧰', 'color': '#2a6ab0'},
    {'key': 'offboard', 'model': 'care.cafm.offboard.request', 'state_field': 'state',
     'pending': ['pending'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['base.group_user'], 'module': 'إنهاء تعيين (CAFM)', 'icon': '👋', 'color': '#b0343f'},
    {'key': 'hosp_purchase', 'model': 'care.hosp.purchase', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['base.group_user'], 'module': 'مشتريات الضيافة', 'icon': '🍽️', 'color': '#e08a00'},
    {'key': 'prod_update', 'model': 'product.update.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['stock.group_stock_manager'], 'module': 'تحديث منتج', 'icon': '🔄', 'color': '#7a5bbf'},
    {'key': 'gatepass', 'model': 'security.gate.pass', 'state_field': 'state',
     'pending': ['draft'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['security_management.group_security_manager'], 'module': 'تصريح بوابة', 'icon': '🚧', 'color': '#2a6ab0'},
    # The main EOS (if the approval functions exist)
    {'key': 'eos', 'model': 'care.eos', 'state_field': 'state',
     'pending': ['submitted', 'submit'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_manager'], 'module': 'إنهاء الخدمة', 'icon': '🏁', 'color': '#b0343f'},
    # ===== توسعة التغطية (2026-11): أنواع اعتماد كانت ناقصة — تُستبعَد تلقائيًّا إن غاب النموذج/الدالّة =====
    {'key': 'substitution', 'model': 'care.worker.substitution', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_substitution.group_substitution_hr', 'hr.group_hr_user'], 'module': 'البدلاء (الإحلال)', 'icon': '🔄', 'color': '#4f46e5'},
    {'key': 'transport_req', 'model': 'care.transport.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user', 'base.group_user'], 'module': 'المواصلات', 'icon': '🚌', 'color': '#0ea5e9'},
    {'key': 'insurance_req', 'model': 'care.insurance.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_finance_approve', 'reject': 'action_reject',
     'groups': ['account.group_account_manager', 'hr.group_hr_user'], 'module': 'صرف التأمين', 'icon': '🛡️', 'color': '#16a34a'},
    {'key': 'exp_cert', 'model': 'care.experience.certificate', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_user'], 'module': 'شهادة خبرة', 'icon': '📄', 'color': '#7a5bbf'},
    {'key': 'extra_work', 'model': 'care.extra.work', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_hr_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'العمل الإضافي', 'icon': '⚡', 'color': '#d97706'},
    {'key': 'extra_ts', 'model': 'care.extra.timesheet', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['hr.group_hr_user'], 'module': 'التايم شيت الإضافي', 'icon': '⏱️', 'color': '#b45309'},
    {'key': 'fuel_recharge', 'model': 'care.fuel.recharge.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user', 'base.group_user'], 'module': 'شحن الوقود', 'icon': '⛽', 'color': '#dc2626'},
    {'key': 'pms_doc', 'model': 'care.pms.doc.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user', 'base.group_user'], 'module': 'طلب مستند (مشروع)', 'icon': '📑', 'color': '#2a6ab0'},
    {'key': 'traffic_viol', 'model': 'care.traffic.violation', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_user', 'fleet.fleet_group_manager'], 'module': 'المخالفات المرورية', 'icon': '🚦', 'color': '#b0343f'},
    {'key': 'veh_handover', 'model': 'care.vehicle.handover', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['fleet.fleet_group_manager', 'hr.group_hr_user'], 'module': 'استلام المركبات', 'icon': '🚗', 'color': '#0a1f44'},
    {'key': 'workshop', 'model': 'c2c.workshop', 'state_field': 'state',
     'pending': ['hr_review'], 'approve': 'action_hr_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'الورش', 'icon': '🔧', 'color': '#7a5bbf'},
    {'key': 'entitled', 'model': 'care.entitled', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_user'], 'module': 'الاستحقاق', 'icon': '✅', 'color': '#16a34a'},
    {'key': 'proposal', 'model': 'proposal.proposal', 'state_field': 'state',
     'pending': ['submit', 'waiting'], 'approve': 'button_approve', 'reject': 'button_reject',
     'groups': ['sales_team.group_sale_manager'], 'module': 'عروض الأسعار', 'icon': '💰', 'color': '#d97706',
     'report': 'care_proposal.proposal_pdf_report'},
    {'key': 'supplier_price', 'model': 'supplier.price.update', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['purchase.group_purchase_manager'], 'module': 'تحديث أسعار الموردين', 'icon': '🏷️', 'color': '#2a6ab0'},
    {'key': 'invoice_req', 'model': 'request.invoice', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_manager_approve', 'reject': 'action_refuse',
     'groups': ['account.group_account_manager', 'hr.group_hr_user'], 'module': 'طلبات الفواتير', 'icon': '🧾', 'color': '#0d9488'},
    {'key': 'disbursement', 'model': 'care.disbursement.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_disbursement.group_disbursement_approver', 'account.group_account_manager', 'hr.group_hr_user'],
     'module': 'طلبات الصرف', 'icon': '💵', 'color': '#16a34a'},
    # ===== جولة التدقيق الشامل 2026-11-20: موديلات موافقة لم تكن مُدرجة (فحص جميع الموديلات) =====
    {'key': 'c2c_contract', 'model': 'c2c.contract.request', 'state_field': 'state',
     'pending': ['reviewing'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['sales_team.group_sale_manager', 'base.group_erp_manager'],
     'module': 'طلبات عقود C2C', 'icon': '📑', 'color': '#0891b2'},
    {'key': 'c2c_review', 'model': 'c2c.review', 'state_field': 'state',
     'pending': ['pending'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['sales_team.group_sale_manager', 'base.group_erp_manager'],
     'module': 'تقييمات العملاء', 'icon': '⭐', 'color': '#d97706'},
    {'key': 'facade_permit', 'model': 'care.cafm.facade.permit', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_deny',
     'groups': ['base.group_erp_manager'], 'module': 'تصاريح الواجهات', 'icon': '🧗', 'color': '#0f766e'},
    {'key': 'stock_count', 'model': 'care.cafm.stock.count', 'state_field': 'state',
     'pending': ['review'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['stock.group_stock_manager', 'base.group_erp_manager'],
     'module': 'جرد المخزون', 'icon': '📦', 'color': '#7c3aed'},
    {'key': 'eos_timesheet', 'model': 'care.eos.timesheet.request', 'state_field': 'state',
     'pending': ['sent'], 'approve': 'action_pm_approve', 'reject': 'action_reject',
     'groups': ['hr.group_hr_manager', 'hr.group_hr_user'],
     'module': 'تايم شيت نهاية الخدمة', 'icon': '⏱️', 'color': '#b45309'},
    {'key': 'esign_enroll', 'model': 'care.esign.enrollment', 'state_field': 'state',
     'pending': ['to_approve'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_esignature.group_esign_manager', 'base.group_erp_manager'],
     'module': 'اعتماد التوقيع الإلكتروني', 'icon': '✍️', 'color': '#2a6ab0'},
    {'key': 'exp_renewal', 'model': 'care.experience.renewal', 'state_field': 'state',
     'pending': ['requested'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['base.group_erp_manager'], 'module': 'تجديد الخبرات/العقود', 'icon': '🔄', 'color': '#059669'},
    {'key': 'svc_request', 'model': 'proposal.service.request', 'state_field': 'state',
     'pending': ['under_review'], 'approve': 'action_approve', 'reject': 'action_cancel',
     'groups': ['care_proposal.group_proposal_manager', 'sales_team.group_sale_manager'],
     'module': 'طلبات عروض الأسعار', 'icon': '📝', 'color': '#d97706'},
    {'key': 'bulk_attendance', 'model': 'bulk.attendance', 'state_field': 'state',
     'pending': ['confirm'], 'approve': 'button_approve', 'reject': 'button_refuse',
     'groups': ['care_attendance.group_bulk_attendance_approver', 'hr.group_hr_manager'],
     'module': 'الحضور الجماعي', 'icon': '🕐', 'color': '#0ea5e9'},
    # ===== جولة التدقيق الثانية (أسماء دوال/حقول غير قياسية) =====
    {'key': 'announcement', 'model': 'hr.announcement', 'state_field': 'state',
     'pending': ['to_approve'], 'approve': 'action_approve_announcement', 'reject': 'action_reject_announcement',
     'groups': ['hr.group_hr_manager', 'hr.group_hr_user'], 'module': 'الإعلانات', 'icon': '📢', 'color': '#2a6ab0'},
    {'key': 'manpower_req', 'model': 'manpower.requisition', 'state_field': 'state',
     'pending': ['submit'], 'approve': 'button_hr_approve', 'reject': 'button_reject',
     'groups': ['hr.group_hr_manager', 'hr.group_hr_user'], 'module': 'طلب القوى العاملة', 'icon': '🧑‍💼', 'color': '#7c3aed'},
    {'key': 'allowance', 'model': 'care.allowance', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_dept_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_user', 'hr.group_hr_manager'], 'module': 'البدلات — موافقة القسم', 'icon': '💰', 'color': '#16a34a'},
    {'key': 'allowance_senior', 'model': 'care.allowance', 'state_field': 'state',
     'pending': ['dept'], 'approve': 'action_senior_approve', 'reject': 'action_refuse',
     'groups': ['hr.group_hr_manager'], 'module': 'البدلات — موافقة عليا', 'icon': '💰', 'color': '#15803d'},
    {'key': 'defense_permit', 'model': 'care.defense.permit', 'state_field': 'state',
     'pending': ['draft'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['base.group_erp_manager', 'hr.group_hr_manager'], 'module': 'تصاريح الدفاع', 'icon': '🛡️', 'color': '#0a1f44'},
    {'key': 'hosp_order', 'model': 'care.hosp.order', 'state_field': 'state',
     'pending': ['await_approval'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['base.group_erp_manager'], 'module': 'طلبات الضيافة', 'icon': '🍽️', 'color': '#b45309'},
    {'key': 'c2c_booking', 'model': 'c2c.booking', 'state_field': 'state',
     'pending': ['review'], 'approve': 'action_approve_completion', 'reject': 'action_reject_completion',
     'groups': ['sales_team.group_sale_manager', 'base.group_erp_manager'], 'module': 'إنجاز حجوزات C2C', 'icon': '📅', 'color': '#0891b2'},
    {'key': 'warranty_claim', 'model': 'warranty.claim', 'state_field': 'state',
     'pending': ['draft'], 'approve': 'change_status_approved', 'reject': 'change_status_rejected',
     'groups': ['base.group_erp_manager'], 'module': 'مطالبات الضمان', 'icon': '🧰', 'color': '#0f766e'},
    {'key': 'bill_finance', 'model': 'account.move', 'state_field': 'bill_approval_state',
     'pending': ['submitted'], 'approve': 'action_bill_finance_approve', 'reject': 'action_bill_finance_reject',
     'groups': ['account.group_account_manager'], 'module': 'اعتماد فواتير الموردين', 'icon': '🧾', 'color': '#0d9488'},
    # ===== طلبات الموظفين (سدّ فجوات تقرير التاسكات) =====
    {'key': 'residency_renewal', 'model': 'care.residency.renewal', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_staff_requests.group_staff_request_manager', 'hr.group_hr_manager'],
     'module': 'تجديد الإقامات', 'icon': '🪪', 'color': '#2a6ab0'},
    {'key': 'deduction', 'model': 'care.general.deduction', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_staff_requests.group_staff_request_manager', 'hr.group_hr_manager'],
     'module': 'الخصومات العامة', 'icon': '➖', 'color': '#b0343f'},
    {'key': 'housing_req', 'model': 'care.housing.request', 'state_field': 'state',
     'pending': ['submitted'], 'approve': 'action_approve', 'reject': 'action_reject',
     'groups': ['care_staff_requests.group_housing_admin', 'hr.group_hr_manager'],
     'module': 'طلبات السكن', 'icon': '🏠', 'color': '#7a5bbf'},
]


class CareApprovalCenter(models.AbstractModel):
    _name = 'care.approval.center'
    _description = 'Approval Center Service'

    # ===================== Helpers =====================
    def _entries(self):
        """الأنواع الصالحة فعلياً (النموذج والدوال موجودة)."""
        out = []
        for e in REGISTRY:
            M = self.env.get(e['model'])
            if M is None:
                continue
            if e['state_field'] not in M._fields:
                continue
            if not (hasattr(M, e['approve']) and hasattr(M, e['reject'])):
                continue
            out.append(e)
        return out

    def _user_allowed(self, entry):
        u = self.env.user
        if u.has_group('base.group_system'):
            return True
        for g in entry['groups']:
            try:
                if u.has_group(g):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _initials(name):
        parts = (name or '').strip().split()
        return ''.join(p[0] for p in parts[:2]) or '؟'

    @staticmethod
    def _d(v):
        if not v:
            return '—'
        try:
            return str(v)[:10]
        except Exception:
            return '—'

    def _ref(self, rec):
        nm = rec.name if 'name' in rec._fields else False
        if nm and nm not in ('/', 'New', False):
            return nm
        return '#%s' % rec.id

    def _sel(self, rec, field):
        try:
            return dict(rec._fields[field].selection).get(rec[field], rec[field]) or '—'
        except Exception:
            return '—'

    # ===================== Build the display of each request =====================
    @staticmethod
    def _primary_employee(rec):
        """العامل الأساسي للسجل: employee_id مباشرةً، أو أول عامل في line_ids."""
        if 'employee_id' in rec._fields and rec.employee_id:
            return rec.employee_id[:1]
        if 'line_ids' in rec._fields and rec.line_ids and 'employee_id' in rec.line_ids._fields:
            emps = rec.line_ids.mapped('employee_id')
            if emps:
                return emps[:1]
        return rec.env['hr.employee']

    def _emp_badge(self, rec):
        """رقم بادج العامل (barcode) — أو employee_no إن خُزِّن على السجل مباشرةً."""
        emp = self._primary_employee(rec)
        if emp and emp.barcode:
            return emp.barcode
        if 'employee_no' in rec._fields and rec.employee_no:
            return rec.employee_no
        return ''

    def _payload(self, entry, rec):
        key = entry['key']
        p = {'model': entry['model'], 'id': rec.id, 'ref': self._ref(rec),
             'by': '', 'by_role': 'مُقدّم الطلب', 'subject': '', 'urgency': 'mid', 'fields': []}

        if key == 'suspend':
            cnt = rec.worker_count or len(rec.line_ids)
            names = ', '.join(rec.line_ids.mapped('employee_id.name')[:2]) or (rec.employee_id.name or '')
            p.update({
                'title': 'إيقاف عن العمل — %s عامل' % cnt, 'subject': names, 'urgency': 'high',
                'by': rec.requested_by.name or '', 'by_role': 'مدير المشروع', 'date': self._d(rec.date),
                'fields': [['المشروع', rec.project_id.display_name or '—'],
                           ['العدد', '%s عامل' % cnt],
                           ['السبب', self._sel(rec, 'reason')]]})
        elif key == 'passport':
            emp = rec.employee_id
            p.update({
                'title': 'سحب جواز — %s' % (emp.name or ''), 'subject': emp.name or '', 'urgency': 'mid',
                'by': rec.requested_by.name or '', 'date': self._d(rec.request_date),
                'fields': [['السبب', self._sel(rec, 'reason')],
                           ['رقم الجواز', rec.passport_no or '—'],
                           ['الإرجاع المتوقع', self._d(rec.expected_return)]]})
        elif key == 'bankcard':
            emp = rec.employee_id
            tlabel = 'إصدار' if rec.request_type == 'issue' else 'إلغاء'
            p.update({
                'title': '%s كارت بنك — %s' % (tlabel, emp.name or ''), 'subject': emp.name or '', 'urgency': 'mid',
                'by': rec.requested_by.name or '', 'date': self._d(rec.request_date),
                'fields': [['النوع', self._sel(rec, 'request_type')],
                           ['السبب', self._sel(rec, 'reason') if rec.reason else '—'],
                           ['الرقم الوظيفي', rec.employee_no or '—']]})
        elif key == 'leave':
            emp = rec.employee_id
            p.update({
                'title': 'إجازة — %s' % (emp.name or ''), 'subject': emp.name or '', 'urgency': 'low',
                'by': emp.name or '', 'by_role': 'موظف', 'date': self._d(rec.create_date),
                'fields': [['النوع', rec.holiday_status_id.name or '—'],
                           ['المدة', '%g يوم' % (rec.number_of_days or 0)],
                           ['من', self._d(rec.date_from)]]})
        elif key == 'item':
            p.update({
                'title': 'طلب أصناف — %s' % (rec.project_id.display_name or ''),
                'subject': rec.project_id.display_name or '', 'urgency': 'mid',
                'by': rec.requested_by.name or '', 'date': self._d(rec.request_date),
                'fields': [['عدد الأصناف', '%d صنف' % len(rec.line_ids)],
                           ['المشروع', rec.project_id.display_name or '—'],
                           ['التاريخ', self._d(rec.request_date)]]})
        else:
            # Smart generic display for any new type: captures the employee/project/amount/reason/date/submitter
            emp = rec.employee_id.name if ('employee_id' in rec._fields and rec.employee_id) else ''
            p['title'] = entry['module'] + (' — %s' % emp if emp else (' %s' % self._ref(rec)))
            p['subject'] = emp or self._ref(rec)
            p['date'] = '—'
            for df in ('date', 'request_date', 'pr_date', 'create_date', 'date_from'):
                if df in rec._fields and rec[df]:
                    p['date'] = self._d(rec[df]); break
            for bf in ('requested_by', 'create_uid', 'user_id'):
                if bf in rec._fields and rec[bf]:
                    p['by'] = rec[bf].name or ''; break
            flds = []
            for label, fn in [('المشروع', 'project_id'), ('القسم', 'department_id'),
                              ('المبلغ', 'amount'), ('القيمة', 'loan_amount'),
                              ('النوع', 'request_type'), ('السبب', 'reason')]:
                if fn in rec._fields and rec[fn]:
                    v = rec[fn]
                    ftype = rec._fields[fn].type
                    if ftype == 'selection':
                        cell = self._sel(rec, fn)
                    elif hasattr(v, 'display_name'):
                        cell = v.display_name
                    else:
                        cell = ('%g' % v) if ftype in ('float', 'monetary') else str(v)
                    flds.append([label, cell])
                if len(flds) >= 3:
                    break
            p['fields'] = flds
        p['badge'] = self._emp_badge(rec)
        p['initials'] = self._initials(p.get('by') or p.get('subject') or '؟')
        return p

    # ===================== Service interface =====================
    @api.model
    def get_pending_data(self):
        user = self.env.user
        groups_out, total = [], 0
        for entry in self._entries():
            if not self._user_allowed(entry):
                continue
            M = self.env[entry['model']].sudo()
            recs = M.search([(entry['state_field'], 'in', entry['pending'])], order='id desc', limit=200)
            records = []
            for rec in recs:
                try:
                    records.append(self._payload(entry, rec))
                except Exception:
                    continue
            if records:
                total += len(records)
                groups_out.append({'key': entry['key'], 'module': entry['module'],
                                   'icon': entry['icon'], 'color': entry['color'],
                                   'count': len(records), 'records': records})
        return {'count': total, 'groups': groups_out,
                'user': {'name': user.name, 'initials': self._initials(user.name)}}

    # ===================== التقرير الصحيح + الإجراءات + مؤشّرات القرار =====================
    def _report_for(self, model):
        """تقرير السجلّ المناسب: override من REGISTRY (مثل تقرير التسعير الداخلي للعروض)
        وإلا أول تقرير PDF للموديل. يعيد سجلّ ir.actions.report أو recordset فارغ."""
        entry = next((e for e in self._entries() if e['model'] == model), None)
        Rep = self.env['ir.actions.report'].sudo()
        if entry and entry.get('report'):
            r = Rep.search([('report_name', '=', entry['report'])], limit=1)
            if not r:
                r = self.env.ref(entry['report'], raise_if_not_found=False)
            if r:
                return r
        return (Rep.search([('model', '=', model), ('report_type', '=', 'qweb-pdf'), ('binding_model_id', '!=', False)], limit=1)
                or Rep.search([('model', '=', model), ('report_type', '=', 'qweb-pdf')], limit=1))

    @staticmethod
    def _btn_hidden(expr, state):
        """تقدير بسيط لإخفاء الزرّ حسب الحالة (تعابير أودو 17 مثل state != 'draft')."""
        expr = (expr or '').strip()
        if not expr or expr in ('0', 'False'):
            return False
        if expr in ('1', 'True'):
            return True
        if '[' in expr or '(' in expr:  # أسلوب domain قديم — يصعب تقديره، أظهِر الزرّ
            return False
        try:
            return bool(eval(expr, {'__builtins__': {}}, {'state': state}))
        except Exception:
            return False

    def _form_actions(self, rec, exclude=()):
        """أزرار الإجراء (type=object) من نموذج السجلّ المطبّقة في حالته الحالية —
        فيُظهر المركز «الأزرار الأخرى كلٌّ حسب نوعه» تلقائيًّا لكل موديل."""
        try:
            from lxml import etree
        except Exception:
            return []
        try:
            arch = rec.get_view(view_type='form')['arch']
            tree = etree.fromstring(arch.encode() if isinstance(arch, str) else arch)
        except Exception:
            return []
        state = ''
        try:
            sf = 'state' if 'state' in rec._fields else None
            state = rec[sf] if sf else ''
        except Exception:
            state = ''
        excl = {e for e in exclude if e}
        skipnames = {'toggle_active', 'unlink', 'copy', 'open_wizard'}
        seen, out = set(), []
        for btn in tree.xpath('//button[@type="object"]'):
            name, label = btn.get('name'), (btn.get('string') or '').strip()
            if not name or not label or name in excl or name in seen or name in skipnames:
                continue
            st = btn.get('states')
            if st and state and state not in [s.strip() for s in st.split(',')]:
                continue
            if self._btn_hidden(btn.get('invisible'), state):
                continue
            seen.add(name)
            out.append({'name': name, 'string': label, 'primary': btn.get('class', '').find('btn-primary') >= 0})
            if len(out) >= 8:
                break
        return out

    def _money(self, rec, v):
        try:
            cur = rec.currency_id if 'currency_id' in rec._fields and rec.currency_id else None
            sym = cur.name if cur else 'د.ك'
            return '%s %s' % ('{:,.3f}'.format(float(v or 0)), sym)
        except Exception:
            return str(v)

    def _decision_metrics(self, entry, rec):
        """مؤشّرات تُسهّل القرار — منسّقة لكل نوع. العروض مثالٌ كامل (تسعير)."""
        k = entry['key']
        M = self._money
        if k == 'proposal':
            mp = rec.manpower_quantity or 0
            sell_total = rec.total_sales or rec.total_amount or 0.0
            cost_total = rec.total_cost or 0.0
            net = rec.margin_amount if 'margin_amount' in rec._fields else (sell_total - cost_total)
            unit_cost = rec.individual_cost or (cost_total / mp if mp else 0.0)
            unit_sell = (sell_total / mp) if mp else 0.0
            unit_profit = unit_sell - unit_cost
            return [
                {'label': 'عدد العمال', 'value': '%d عامل' % mp},
                {'label': 'سعر العامل (بيع)', 'value': M(rec, unit_sell)},
                {'label': 'تكلفة العامل', 'value': M(rec, unit_cost)},
                {'label': 'الربح الفردي', 'value': M(rec, unit_profit), 'good': unit_profit >= 0},
                {'label': 'إجمالي البيع', 'value': M(rec, sell_total)},
                {'label': 'إجمالي التكلفة', 'value': M(rec, cost_total)},
                {'label': 'صافي الربح', 'value': M(rec, net), 'good': (net or 0) >= 0, 'big': True},
                {'label': 'الهامش %', 'value': '%.1f%%' % (rec.margin_percentage or 0.0)},
                {'label': 'إجمالي الفاتورة', 'value': M(rec, rec.total_amount or sell_total), 'big': True},
            ]
        if k in ('disbursement', 'allowance', 'allowance_senior'):
            amt = rec.amount if 'amount' in rec._fields else 0.0
            return [
                {'label': 'المبلغ', 'value': M(rec, amt), 'big': True},
                {'label': 'المستفيد', 'value': (rec.employee_id.name if 'employee_id' in rec._fields and rec.employee_id else (getattr(rec, 'beneficiary', '') or '—'))},
                {'label': 'طريقة الصرف', 'value': self._sel(rec, 'payment_method') if 'payment_method' in rec._fields else '—'},
            ]
        if k == 'bill_finance':
            return [
                {'label': 'المورّد', 'value': rec.partner_id.display_name if rec.partner_id else '—'},
                {'label': 'المرجع', 'value': rec.ref or rec.name or '—'},
                {'label': 'الإجمالي', 'value': M(rec, rec.amount_total), 'big': True},
                {'label': 'غير المدفوع', 'value': M(rec, rec.amount_residual)},
            ]
        if k in ('leave',):
            return [
                {'label': 'الموظف', 'value': rec.employee_id.name or '—'},
                {'label': 'النوع', 'value': rec.holiday_status_id.name or '—'},
                {'label': 'المدة', 'value': '%g يوم' % (rec.number_of_days or 0), 'big': True},
            ]
        if k == 'substitution':
            out = []
            if 'absent_employee_id' in rec._fields and rec.absent_employee_id:
                out.append({'label': 'العامل الغائب', 'value': rec.absent_employee_id.name})
            if 'line_ids' in rec._fields:
                try:
                    subs = [s for s in rec.line_ids.mapped('employee_id.name') if s]
                    if subs:
                        out.append({'label': 'البديل', 'value': '، '.join(subs[:2]) + (' +%d' % (len(subs) - 2) if len(subs) > 2 else '')})
                except Exception:
                    pass
            if 'total_cost' in rec._fields:
                out.append({'label': 'إجمالي التكلفة', 'value': M(rec, rec.total_cost), 'big': True})
            if 'date_from' in rec._fields and rec.date_from:
                out.append({'label': 'من تاريخ', 'value': self._d(rec.date_from)})
            return out or self._generic_metrics(rec)
        if k == 'loan' and 'loan_amount' in rec._fields:
            out = []
            e2 = self._primary_employee(rec)
            if e2:
                out.append({'label': 'الموظف', 'value': e2.name})
            out.append({'label': 'قيمة السلفة', 'value': M(rec, rec.loan_amount or (rec.amount if 'amount' in rec._fields else 0)), 'big': True})
            if 'installment' in rec._fields and rec.installment:
                out.append({'label': 'عدد الأقساط', 'value': '%d' % rec.installment})
            return out
        # أي نوع آخر: مؤشّرات عامّة مستنبطة تلقائيًّا من حقول السجلّ
        return self._generic_metrics(rec)

    def _generic_metrics(self, rec):
        """مؤشّرات قرار عامّة لأي موديل: المستفيد/المشروع/المبلغ/العدد/النوع/المدة/التاريخ."""
        M, out = self._money, []
        F = rec._fields
        def has(n): return n in F and rec[n]
        # المستفيد
        emp = self._primary_employee(rec)
        if emp:
            out.append({'label': 'الموظف', 'value': emp.name or '—'})
        elif has('partner_id'):
            out.append({'label': 'الجهة', 'value': rec.partner_id.display_name})
        elif has('beneficiary'):
            out.append({'label': 'المستفيد', 'value': rec.beneficiary})
        # المشروع/القسم
        for fn, lbl in (('project_id', 'المشروع'), ('department_id', 'القسم')):
            if has(fn):
                out.append({'label': lbl, 'value': rec[fn].display_name}); break
        # المبلغ الرئيسي (أول حقل نقدي موجود) — بارز
        money_fields = ['amount', 'amount_total', 'total_amount', 'total', 'grand_total',
                        'total_cost', 'net_amount', 'loan_amount', 'value', 'salary', 'fee_amount']
        shown_money = False
        for fn in money_fields:
            if fn in F and F[fn].type in ('float', 'monetary') and rec[fn]:
                out.append({'label': F[fn].string or fn, 'value': M(rec, rec[fn]), 'big': True}); shown_money = True; break
        # المدة/العدد
        for fn, suf in (('number_of_days', 'يوم'), ('days', 'يوم'), ('duration', ''), ('hours', 'ساعة'),
                        ('worker_count', 'عامل'), ('quantity', '')):
            if fn in F and rec[fn]:
                out.append({'label': F[fn].string or fn, 'value': ('%g %s' % (rec[fn], suf)).strip()}); break
        # عدد السطور
        if 'line_ids' in F:
            try:
                n = len(rec.line_ids)
                if n:
                    out.append({'label': 'عدد البنود', 'value': '%d' % n})
            except Exception:
                pass
        # النوع
        for fn in ('request_type', 'type', 'reason'):
            if fn in F and F[fn].type == 'selection' and rec[fn]:
                out.append({'label': F[fn].string or fn, 'value': self._sel(rec, fn)}); break
        # التاريخ
        for fn in ('date', 'request_date', 'date_from', 'pr_date'):
            if fn in F and rec[fn]:
                out.append({'label': F[fn].string or fn, 'value': self._d(rec[fn])}); break
        return out[:6]

    @api.model
    def get_record_detail(self, model, res_id):
        """تفاصيل شاملة لسجلّ واحد — تُعرض في ديالوج مركز الاعتمادات."""
        entry = next((e for e in self._entries() if e['model'] == model), None)
        if not entry:
            return {'error': 'unknown'}
        rec = self.env[model].sudo().browse(int(res_id))
        if not rec.exists():
            return {'error': 'missing'}
        # جارد: لا تُفصح عن الحقول المالية/الرواتب والمقاييس إلا لمن يملك صلاحية اعتماد هذا النوع (أو مُنشئ الطلب)
        if not self._user_allowed(entry) and not (rec.create_uid and rec.create_uid.id == self.env.uid):
            return {'error': 'forbidden'}
        base = self._payload(entry, rec)
        base.update({'module': entry['module'], 'icon': entry['icon'], 'color': entry['color'],
                     'state_label': self._sel(rec, entry['state_field']),
                     'can_act': self._user_allowed(entry)})
        skip = {'id', 'display_name', 'create_uid', 'write_uid', 'write_date', 'create_date',
                '__last_update', 'message_ids', 'message_follower_ids', 'message_main_attachment_id',
                'activity_ids', 'access_url', 'access_token', 'access_warning'}
        rows = []
        for fname, f in rec._fields.items():
            if fname in skip or f.type in ('binary', 'one2many', 'many2many', 'html', 'json'):
                continue
            try:
                v = rec[fname]
            except Exception:
                continue
            if v in (None, False, '') or v == 0 or v == 0.0:
                continue
            try:
                if f.type == 'selection':
                    val = self._sel(rec, fname)
                elif f.type == 'many2one':
                    val = v.display_name
                elif f.type in ('date', 'datetime'):
                    val = self._d(v)
                elif f.type in ('float', 'monetary'):
                    val = '%g' % v
                else:
                    val = str(v)
            except Exception:
                continue
            rows.append([f.string or fname, str(val)[:140]])
        base['all_fields'] = rows[:40]
        # مؤشّرات القرار + الأزرار الأخرى + توفّر النموذج الداخلي
        try:
            base['metrics'] = self._decision_metrics(entry, rec)
        except Exception as ex:
            _logger.warning('approval-center metrics failed %s: %s', model, ex); base['metrics'] = []
        try:
            base['actions'] = self._form_actions(rec, exclude=(entry.get('approve'), entry.get('reject')))
        except Exception as ex:
            _logger.warning('approval-center actions failed %s: %s', model, ex); base['actions'] = []
        base['report_available'] = bool(self._report_for(model))
        return base

    @api.model
    def run_action(self, model, res_id, method):
        """تنفيذ زرّ إجراء (غير الموافقة/الرفض) على السجلّ — بقائمة بيضاء من أزرار النموذج."""
        entry = next((e for e in self._entries() if e['model'] == model), None)
        if not entry:
            raise UserError(_('نوع غير معروف.'))
        if not self._user_allowed(entry):
            raise AccessError(_('غير مصرّح.'))
        rec = self.env[model].sudo().browse(int(res_id))
        if not rec.exists():
            return {'ok': False, 'error': 'missing'}
        allowed = {entry.get('approve'), entry.get('reject')}
        allowed |= {a['name'] for a in self._form_actions(rec)}
        allowed.discard(None)
        if method not in allowed:
            return {'ok': False, 'error': 'إجراء غير مسموح على هذا السجلّ'}
        try:
            res = getattr(rec, method)()
        except (UserError, AccessError) as ex:
            return {'ok': False, 'error': str(ex) or 'لم يُقبل الإجراء في حالته الحالية.'}
        except Exception as ex:
            _logger.error('approval-center run_action %s.%s(%s):\n%s', model, method, res_id, traceback.format_exc())
            return {'ok': False, 'error': 'خطأ: %s' % (str(ex) or type(ex).__name__)}
        opened = isinstance(res, dict) and str(res.get('type', '')).startswith('ir.actions')
        return {'ok': True, 'opened_action': bool(opened)}

    # ===================== Decision helpers =====================
    def _find_requester_user(self, rec):
        """مستخدم مُنشئ الطلب — لإشعاره عند الرفض/القبول."""
        rec = rec.sudo()
        # 1) حقل مستخدم صريح
        for f in ('requested_by', 'user_id', 'request_user_id', 'submitted_by'):
            if f in rec._fields and rec[f]:
                u = rec[f]
                if u._name == 'res.users':
                    return u[:1]
                # قد يكون employee → نأخذ مستخدمه
                if u._name == 'hr.employee' and u.user_id:
                    return u.user_id[:1]
        # 2) مستخدم الموظف صاحب الطلب
        emp = self._primary_employee(rec)
        if emp and emp.user_id:
            return emp.user_id[:1]
        # 3) مُنشئ السجل
        if rec.create_uid:
            return rec.create_uid[:1]
        return self.env['res.users'].browse()

    def _approver_role(self, entry):
        """صفة المعتمِد للتوقيع — من الإدخال إن حُدِّد، وإلا استدلالٌ من الدالة/المجموعات."""
        if entry.get('esign_role'):
            return entry['esign_role'], entry.get('esign_role_en') or 'Approver'
        groups = entry.get('groups') or []
        gstr = ' '.join(groups)
        method = entry.get('approve') or ''
        if 'account' in gstr or 'finance' in gstr or 'disbursement' in gstr:
            return 'الإدارة المالية', 'Finance'
        if 'hr_approve' in method or 'hr.' in gstr:
            return 'الموارد البشرية', 'HR'
        if 'purchase' in gstr:
            return 'مدير المشتريات', 'Procurement Manager'
        if 'sale' in gstr:
            return 'الإدارة التجارية', 'Sales Management'
        return 'المعتمِد', 'Approver'

    def _stamp_approver_esign(self, entry, rec):
        """يختم توقيع المعتمِد الحالي على المستند وقت الاعتماد (idempotent)."""
        Esign = self.env.get('care.esignature')
        if Esign is None:
            return
        role, role_en = self._approver_role(entry)
        try:
            Esign.sudo().esign_sign(rec._name, rec.id, role=role, role_en=role_en)
        except Exception as ex:
            _logger.warning('approval-center: esign stamp failed for %s/%s: %s', rec._name, rec.id, ex)

    def _approver_recipients(self, entry):
        """مستخدمو الاعتماد لنوعٍ ما — اتحاد مجموعاته، مع استبعاد المجموعات شديدة الاتساع.
        منظومة الصلاحيات (care_access_hub): إن عُيّنت مسمّيات/مستخدمون معتمِدون لمراحل هذا النوع،
        تُقيَّد عليهم (عزل)؛ وإن لم يُعيَّن أحد = المعتمِدون الافتراضيون للموديول (ليس «الكل»)."""
        users = self.env['res.users'].browse()
        broad = {'base.group_user', 'base.group_portal', 'base.group_public'}
        for g in entry.get('groups') or []:
            if g in broad:
                continue
            try:
                grp = self.env.ref(g, raise_if_not_found=False)
                if grp:
                    users |= grp.users
            except Exception:
                continue
        # تقييد على المعتمِدين المُعيَّنين في منظومة الصلاحيات (إن وُجدوا)
        AT = self.env.get('care.approval.type')
        if AT is not None:
            try:
                t = AT.sudo().search([('model_name', '=', entry.get('model'))], limit=1)
                if t:
                    configured = t.stage_ids.mapped('role_ids.user_ids') | t.stage_ids.mapped('extra_user_ids')
                    if configured:
                        users = configured  # عزل: المعتمِدون المُعيَّنون فقط
            except Exception:
                pass
        # التفويضات (الإنابة): المفوَّض إليه يُضاف لأنواع المفوِّض النشطة ضمن المدّة
        Deleg = self.env.get('care.user.delegation')
        if Deleg is not None and users and AT is not None:
            try:
                atype = AT.sudo().search([('model_name', '=', entry.get('model'))], limit=1)
                if atype:
                    for d in Deleg.sudo().search([('delegator_id', 'in', users.ids), ('active', '=', True)]):
                        if d.covers_type(atype):
                            users |= d.delegate_id
            except Exception:
                pass
        return users.filtered(lambda u: u.active and not u.share)[:300]

    @api.model
    def cron_notify_new_pending(self):
        """يُشعِر المعتمِدين بالطلبات الجديدة التي دخلت حالة الانتظار منذ آخر تشغيل.
        أول تشغيل يضبط الأساس فقط (بلا إرسال) تفاديًا لإغراقٍ على الركام القائم."""
        ICP = self.env['ir.config_parameter'].sudo()
        now = fields.Datetime.now()
        last = ICP.get_param('care_approval.notify_last')
        if not last:
            ICP.set_param('care_approval.notify_last', fields.Datetime.to_string(now))
            return
        try:
            last_dt = fields.Datetime.from_string(last)
        except Exception:
            ICP.set_param('care_approval.notify_last', fields.Datetime.to_string(now))
            return
        Notif = self.env.get('care.cafm.notification')
        if Notif is None:
            ICP.set_param('care_approval.notify_last', fields.Datetime.to_string(now))
            return
        for entry in self._entries():
            try:
                M = self.env[entry['model']].sudo()
                recs = M.search([(entry['state_field'], 'in', entry['pending']),
                                 ('create_date', '>', last_dt)], order='id desc', limit=500)
                if not recs:
                    continue
                recipients = self._approver_recipients(entry)
                if not recipients:
                    continue
                # منظومة الصلاحيات (care_access_hub): القنوات الثلاث لكل مُعتمِد
                # (📱 تطبيق / 🔔 أودو / 📧 بريد) مع الإلزامي المقفل — حارس وجود الموديول.
                AN = self.env.get('care.access.notify.channel')
                app_rcp, odoo_rcp, email_rcp = recipients, self.env['res.users'], self.env['res.users']
                if AN is not None:
                    try:
                        app_rcp, odoo_rcp, email_rcp = AN.sudo().split_recipients(recipients, entry.get('key'))
                    except Exception:
                        app_rcp, odoo_rcp, email_rcp = recipients, self.env['res.users'], self.env['res.users']
                for rec in recs:
                    batch = 'apnew-%s-%s' % (entry['model'], rec.id)
                    if Notif.sudo().search_count([('batch', '=', batch)]):
                        continue
                    try:
                        payload = self._payload(entry, rec)
                        title = '%s %s' % (entry['icon'], entry['module'])
                        body = 'طلب جديد بانتظار اعتمادك: %s' % (payload.get('title') or self._ref(rec))
                        if payload.get('by'):
                            body += '\nمن: %s' % payload['by']
                        action_url = '/approval?model=%s&id=%s' % (entry['model'], rec.id)
                        if app_rcp:
                            Notif.sudo().push(app_rcp, title, body=body, ntype='task',
                                              action_url=action_url, batch=batch, record=rec)
                        if odoo_rcp:
                            self._notify_in_odoo(odoo_rcp, title, body, rec)
                        if email_rcp:
                            self._notify_by_email(email_rcp, title, body, action_url)
                    except Exception as ex:
                        _logger.warning('approval-center: new-pending push failed %s/%s: %s',
                                        entry['model'], rec.id, ex)
            except Exception as ex:
                _logger.warning('approval-center: cron entry %s failed: %s', entry.get('key'), ex)
        ICP.set_param('care_approval.notify_last', fields.Datetime.to_string(now))

    def _notify_in_odoo(self, users, title, body, rec):
        """إشعار داخل أودو (صندوق الوارد/الجرس) للمعتمِدين عبر message_post."""
        try:
            partners = users.mapped('partner_id')
            if partners and hasattr(rec, 'message_post'):
                rec.sudo().message_post(
                    body='%s — %s' % (title, body.replace('\n', ' · ')),
                    partner_ids=partners.ids, subtype_xmlid='mail.mt_comment')
        except Exception:
            pass

    def _notify_by_email(self, users, title, body, action_url):
        """إشعار بريد خفيف للمعتمِدين الذين قناتهم «بريد» (منظومة الصلاحيات)."""
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for u in users:
            email = u.partner_id.email or u.login
            if not email or '@' not in email:
                continue
            try:
                self.env['mail.mail'].sudo().create({
                    'subject': title,
                    'email_to': email,
                    'body_html': '<div style="font-family:Tajawal,Arial,sans-serif;direction:rtl">'
                                 '<p>%s</p><p><a href="%s%s" style="background:#0f2b5b;color:#fff;'
                                 'padding:8px 16px;border-radius:8px;text-decoration:none">فتح مركز الموافقات</a></p></div>'
                                 % (body.replace('\n', '<br/>'), base, action_url),
                    'auto_delete': True,
                }).send()
            except Exception:
                pass

    def _notify_requester(self, entry, rec, approve, reason):
        """إشعار مُنشئ الطلب على التطبيق (care.cafm.notification + FCM) وبالإيميل (chatter)."""
        requester = self._find_requester_user(rec)
        if not requester:
            return
        ref = self._ref(rec)
        if approve:
            title = '✅ تمّت الموافقة — %s' % entry['module']
            body = 'تمّت الموافقة على طلبك «%s» (%s).' % (ref, entry['module'])
            ntype = 'info'
        else:
            title = '✖ تم رفض الطلب — %s' % entry['module']
            body = 'نأسف، تم رفض طلبك «%s» (%s).' % (ref, entry['module'])
            if reason:
                body += '\nالسبب: %s' % reason
            body += '\nيمكنك تعديله وإعادته إلى مسودة ثم إرساله من جديد.'
            ntype = 'warning'
        # (أ) إشعار التطبيق + دفع FCM — عند الرفض: رابط يفتح السجل بزرّ «إعادة لمسودة»
        Notif = self.env.get('care.cafm.notification')
        nav_url = None if approve else '/reqreset?model=%s&id=%s' % (rec._name, rec.id)
        if Notif is not None:
            try:
                Notif.sudo().push(requester, title, body=body, ntype=ntype,
                                  author=self.env.user, action_url=nav_url, record=rec.sudo())
            except Exception as ex:
                _logger.warning('approval-center: app notify failed: %s', ex)
        # (ب) إشعار + إيميل عبر chatter — عند الرفض فقط (تجنّبًا لإغراق الإيميل عند الاعتماد الجماعي)
        try:
            if not approve and hasattr(rec, 'message_post') and requester.partner_id:
                rec.sudo().message_post(
                    body=body.replace('\n', '<br/>'),
                    subject=title,
                    partner_ids=requester.partner_id.ids,
                    subtype_xmlid='mail.mt_comment',
                    message_type='comment')
        except Exception as ex:
            _logger.warning('approval-center: chatter notify failed: %s', ex)

    @api.model
    def reset_to_draft(self, model, res_id):
        """يُعيد طلبًا مرفوضًا إلى مسودة — لمُنشئ الطلب أو مدير مخوّل."""
        entry = next((e for e in self._entries() if e['model'] == model), None)
        if not entry:
            raise UserError(_('نوع طلب غير معروف.'))
        rec = self.env[model].sudo().browse(int(res_id))
        if not rec.exists():
            return {'ok': False, 'error': 'missing'}
        requester = self._find_requester_user(rec)
        allowed = (requester and requester.id == self.env.uid) or self._user_allowed(entry)
        if not allowed:
            raise AccessError(_('غير مصرّح بإعادة هذا الطلب إلى مسودة.'))
        for m in ('action_reset_draft', 'action_reset_to_draft', 'action_draft',
                  'button_draft', 'action_set_draft', 'action_back_draft'):
            if hasattr(rec, m):
                try:
                    getattr(rec, m)()
                    return {'ok': True}
                except Exception as ex:
                    return {'ok': False, 'error': (str(ex) or type(ex).__name__)}
        # fallback: كتابة الحالة مباشرةً إن وُجدت 'draft'
        sf = entry['state_field']
        try:
            sel = dict(rec._fields[sf].selection)
            if 'draft' in sel:
                rec.write({sf: 'draft'})
                return {'ok': True}
        except Exception:
            pass
        return {'ok': False, 'error': 'لا توجد وسيلة لإعادة هذا الطلب إلى مسودة.'}

    @api.model
    def decide(self, model, res_id, approve, reason=None, notify=True):
        entry = next((e for e in self._entries() if e['model'] == model), None)
        if not entry:
            raise UserError(_('Unknown approval type.'))
        if not self._user_allowed(entry):
            raise AccessError(_('You are not allowed to approve this request.'))
        rec = self.env[model].sudo().browse(int(res_id))
        if not rec.exists():
            return {'ok': False, 'error': 'missing'}
        # Snapshot of the record before the status change
        payload = self._payload(entry, rec)
        # Pass the rejection reason where the model supports it
        if not approve and reason:
            for f in ('reject_reason', 'refuse_reason', 'rejection_reason', 'refusal_reason'):
                if f in rec._fields:
                    try:
                        rec.write({f: reason})
                    except Exception:
                        pass
                    break
        method = entry['approve'] if approve else entry['reject']
        # نُنفّذ الإجراء بصلاحيات متجاوِزة (المركز أجاز المستخدم مسبقًا) مع التقاط الخطأ الحقيقي
        try:
            getattr(rec, method)()
        except (UserError, AccessError) as ex:
            msg = (str(ex) or 'لم يُقبل الإجراء في حالته الحالية.')
            return {'ok': False, 'error': msg}
        except Exception as ex:
            _logger.error('approval-center decide %s.%s(%s) failed:\n%s',
                          model, method, res_id, traceback.format_exc())
            msg = (str(ex) or type(ex).__name__ or 'تعذّر تنفيذ الإجراء.')
            return {'ok': False, 'error': 'خطأ أثناء التنفيذ: %s' % msg}
        # ختم توقيع المعتمِد وقت الاعتماد
        if approve:
            self._stamp_approver_esign(entry, rec)
        # إشعار مُنشئ الطلب (تطبيق + إيميل) — يُتخطّى في الاعتماد الجماعي تخفيفًا للحمل
        if notify:
            try:
                self._notify_requester(entry, rec, approve, reason)
            except Exception as ex:
                _logger.warning('approval-center: notify failed: %s', ex)
        # سجلّ القرار
        self.env['care.approval.log'].sudo().create({
            'module_key': entry['key'], 'module_name': entry['module'], 'module_icon': entry['icon'],
            'res_model': model, 'res_id': rec.id,
            'request_ref': payload['ref'], 'request_title': payload.get('title') or payload['ref'],
            'subject': payload.get('subject') or '', 'requested_by': payload.get('by') or '',
            'decision': 'approved' if approve else 'rejected',
            'decided_by': self.env.uid, 'decided_date': fields.Datetime.now(),
            'reason': reason or '',
        })
        return {'ok': True}

    @api.model
    def decide_bulk(self, model, res_ids, approve=True, reason=''):
        """اعتماد/رفض جماعي — لتفريغ الأنواع عالية الحجم (الحضور/القوى العاملة).
        يتخطّى إشعار كل سجلّ تخفيفًا، ويُرسِل إشعارًا تجميعيًّا واحدًا للمُقدّم عند الرفض لاحقًا."""
        entry = next((e for e in self._entries() if e['model'] == model), None)
        if not entry:
            raise UserError(_('نوع غير معروف.'))
        if not self._user_allowed(entry):
            raise AccessError(_('غير مصرّح.'))
        ids = [int(r) for r in (res_ids or [])][:200]
        done, failed = 0, []
        for rid in ids:
            try:
                r = self.decide(model, rid, bool(approve), reason or '', notify=False)
                if isinstance(r, dict) and r.get('ok'):
                    done += 1
                else:
                    failed.append({'id': rid, 'error': (r or {}).get('error') or 'تعذّر'})
            except Exception as ex:
                failed.append({'id': rid, 'error': str(ex)[:80]})
        return {'ok': True, 'done': done, 'failed': failed, 'total': len(ids)}

    # ===================== Effort statistics (daily cron) =====================
    # Scans the filesystem and stores the numbers in ir.config_parameter, so the /care/effort page injects them.
    _EXTRA_MODULES = {'purchase_report', 'purchase_tender', 'service_order', 'security_management',
                      'hr_employee_shift', 'to_attendance_device', 'manpower_requisition', 'exit_interview'}

    @api.model
    def cron_compute_effort_stats(self):
        care_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        mobile = os.path.join(os.path.dirname(care_dir), 'care_mobile', 'lib')

        def walk(root, exts, skip=()):
            out = []
            if not os.path.isdir(root):
                return out
            for dp, _dn, fn in os.walk(root):
                if any(s in dp for s in skip):
                    continue
                for f in fn:
                    if f.endswith(exts):
                        out.append(os.path.join(dp, f))
            return out

        def read(p):
            try:
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    return fh.read()
            except Exception:
                return ''

        def counts(files):
            nl = nw = 0
            for p in files:
                d = read(p)
                nl += d.count('\n') + (1 if d and not d.endswith('\n') else 0)
                nw += len(d.split())
            return len(files), nl, nw

        def grep(files, pat, flags=0):
            rx = re.compile(pat, flags)
            return sum(len(rx.findall(read(p))) for p in files)

        py = walk(care_dir, ('.py',))
        xml = walk(care_dir, ('.xml',))
        js = [f for f in walk(care_dir, ('.js',)) if '/lib/' not in f and not f.endswith('.min.js')]
        scss = walk(care_dir, ('.scss', '.css'))
        dart = walk(mobile, ('.dart',))

        pf, pl, pw = counts(py)
        xf, xl, xw = counts(xml)
        jf, jl, jw = counts(js)
        sf, sl, sw = counts(scss)
        df, dl, dw = counts(dart)

        mods = set()
        try:
            for d in os.listdir(care_dir):
                man = os.path.join(care_dir, d, '__manifest__.py')
                if not os.path.isfile(man):
                    continue
                if d.startswith('care') or d in self._EXTRA_MODULES:
                    mods.add(d)
                elif 'CARE' in read(man):
                    mods.add(d)
        except Exception:
            pass

        stats = {
            'snapshot': fields.Date.to_string(fields.Date.context_today(self)),
            'modules': len(mods),
            'words_total': pw + xw + jw + sw + dw,
            'functions': grep(py, r'^[ \t]*def ', re.M),
            'models': grep(py, r"_name\s*=\s*['\"]"),
            'fields': grep(py, r"fields\.(?:Char|Integer|Float|Many2one|One2many|Many2many|Boolean|Date|Datetime|Selection|Text|Html|Binary|Monetary)\("),
            'reports': grep(xml, r'ir\.actions\.report'),
            'routes': grep(py, r'@(?:http\.)?route'),
            'py_files': pf, 'xml_files': xf, 'js_files': jf, 'dart_files': df,
            'total_lines': pl + xl + jl + sl + dl,
            'lines': {'py': pl, 'xml': xl, 'dart': dl, 'js': jl, 'other': sl},
        }
        self.env['ir.config_parameter'].sudo().set_param(
            'care_approval.effort_stats', json.dumps(stats))
        return stats
