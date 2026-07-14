# -*- coding: utf-8 -*-
from odoo import models, api

# Top-level menus to move under the Employees app (hr.menu_hr_root)
_MENUS_UNDER_EMPLOYEES = [
    'care_timesheet.care_timesheet_root',
    'permission_request.permission_request_root',
    'exit_interview.exit_interview_root',
    'care_hr.care_hr_leave_menu',
    'hr_overtime_compensation.menu_overtime_compensation',
    'care_hr.absence_root',
    'care_hr.clearance_root',
    'manpower_requisition.manpower_requisition_menu',
    'care.menu_root',
]


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _care_reparent_under_employees(self):
        """Move the listed standalone menus to live inside the Employees app.
        Tolerant of missing menus; idempotent."""
        root = self.env.ref('hr.menu_hr_root', raise_if_not_found=False)
        if not root:
            return
        for xmlid in _MENUS_UNDER_EMPLOYEES:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.parent_id.id != root.id:
                menu.parent_id = root.id

    @api.model
    def _care_reorganize_menus(self):
        """Reorganize the Employees app into <=9 clean top-level sections,
        each grouping the relevant sub-menus. Tolerant + idempotent."""
        ref = lambda x: self.env.ref(x, raise_if_not_found=False)
        # menu_xmlid -> section_xmlid
        mapping = {
            # People
            'hr.menu_hr_main': 'care_hr.menu_sec_people',
            'hr.menu_hr_department_kanban': 'care_hr.menu_sec_people',
            'hr.menu_hr_employee_payroll': 'care_hr.menu_sec_people',
            'hr.menu_hr_employee': 'care_hr.menu_sec_people',
            # Attendance & Leaves
            'hr_overtime_compensation.menu_overtime_compensation': 'care_hr.menu_sec_time',
            'care_hr.absence_root': 'care_hr.menu_sec_time',
            'care_hr.leave_return_root': 'care_hr.menu_sec_time',
            'permission_request.permission_request_root': 'care_hr.menu_sec_time',
            'care_timesheet.care_timesheet_root': 'care_hr.menu_sec_time',
            'care_hr.care_hr_leave_menu': 'care_hr.menu_sec_time',
            # Payroll (reuse existing payroll section)
            'ent_ohrms_loan.hr_loan_menu_for_loan_and_advances': 'care_hr.menu_care_hr_payroll_root',
            # Recruitment & Onboarding
            'manpower_requisition.manpower_requisition_menu': 'care_hr.menu_sec_recruit',
            'care_hr.joining_root': 'care_hr.menu_sec_recruit',
            # Offboarding
            'exit_interview.exit_interview_root': 'care_hr.menu_sec_offboard',
            'care_hr.clearance_root': 'care_hr.menu_sec_offboard',
            # Compliance & Government (reuse existing compliance section)
            'care_hr.menu_care_archive_root': 'care_hr.menu_care_hr_compliance_root',
            'care.hr_social_contracts_menu': 'care_hr.menu_care_hr_compliance_root',
            'care.social_contracts_date_types_menu': 'care_hr.menu_care_hr_compliance_root',
            'care.social_contracts_authorized_persons_menu': 'care_hr.menu_care_hr_compliance_root',
            'oh_hr_lawsuit_management.hr_lawsuit_sub_menu': 'care_hr.menu_care_hr_compliance_root',
            # Welfare & Admin
            'care.menu_root': 'care_hr.menu_sec_welfare',
            'care_hr.menu_care_hr_admin_root': 'care_hr.menu_sec_welfare',
            'care_hr.menu_care_hr_relations_root': 'care_hr.menu_sec_welfare',
            # Settings & Reports (reuse existing config section)
            'hr.menu_human_resources_configuration': 'care_hr.menu_care_hr_config_root',
            'hr.hr_menu_hr_reports': 'care_hr.menu_care_hr_config_root',
        }
        for menu_xid, sec_xid in mapping.items():
            menu = ref(menu_xid)
            sec = ref(sec_xid)
            if menu and sec and menu.parent_id.id != sec.id and menu.id != sec.id:
                menu.parent_id = sec.id
        # Deactivate the messy Studio "Skills" menu — replaced by the clean
        # Skills Center hub (Matrix / Gap / Certifications / Catalog / Types).
        root = ref('hr.menu_hr_root')
        people = ref('care_hr.menu_sec_people')
        if root and people:
            for m in root.child_id:
                if (m.name or '').strip() == 'Skills':
                    m.parent_id = people.id
                    if not self.env['ir.model.data'].search_count([
                            ('model', '=', 'ir.ui.menu'), ('res_id', '=', m.id),
                            ('module', '=', 'care_hr')]):
                        m.active = False

    @api.model
    def _care_cleanup_skills(self):
        """Deactivate the messy/duplicate Skills menus (Studio + scattered
        duplicates); the clean Skills Center hub replaces them all."""
        # duplicate Skill Types menus from other modules
        for x in ['hr_skills.hr_skill_type_menu',
                  'hr_recruitment_skills.hr_recruitment_skill_type_menu']:
            m = self.env.ref(x, raise_if_not_found=False)
            if m:
                m.active = False
        # Studio "Skills" menu + all its children
        IMD = self.env['ir.model.data']
        for m in self.with_context(active_test=False).search([('name', '=', 'Skills')]):
            d = IMD.search([('model', '=', 'ir.ui.menu'), ('res_id', '=', m.id)], limit=1)
            if d and d.module == 'studio_customization':
                (m | m.child_id).write({'active': False})

    @api.model
    def _care_translate_menus(self):
        """Set Arabic (ar_001) translations for the section menus so English
        users see English and Arabic users see Arabic."""
        if not self.env['res.lang'].search_count([('code', '=', 'ar_001')]):
            return
        ar = {
            'care_hr.menu_hr_dashboard': 'لوحة المؤشرات',
            'care_hr.menu_sec_people': 'الموظفون',
            'care_hr.menu_sec_time': 'الحضور والإجازات',
            'care_hr.menu_care_hr_payroll_root': 'الرواتب',
            'care_hr.menu_sec_recruit': 'التوظيف والتعيين',
            'care_hr.menu_sec_offboard': 'إنهاء الخدمة',
            'care_hr.menu_care_hr_compliance_root': 'الامتثال والحكومة',
            'care_hr.menu_sec_welfare': 'الرعاية والإدارة',
            'care_hr.menu_care_hr_config_root': 'الإعدادات والتقارير',
        }
        for xmlid, name_ar in ar.items():
            m = self.env.ref(xmlid, raise_if_not_found=False)
            if m:
                m.with_context(lang='ar_001').write({'name': name_ar})
