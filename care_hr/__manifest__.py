# -*- coding: utf-8 -*-
{
    'name': "Care HR",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_holidays', 'hr_skills', 'hr_payroll', 'project',
                'fleet', 'care', 'purchase_report', 'care_department', 'training_management',
                'hr_recruitment', 'report_xlsx'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/care_payroll_data.xml',
        'views/care_job_grade_views.xml',
        'views/care_manpower_file_views.xml',
        'views/care_penalty_views.xml',
        'views/care_allowance_views.xml',
        'reports/allowance_payout_report.xml',
        'views/care_allowance_payout_views.xml',
        'views/care_violation_views.xml',
        'views/hr_employee.xml',
        'views/care_coverage_views.xml',
        'views/care_passport_views.xml',
        'views/care_skills_views.xml',
        'views/care_lifecycle_views.xml',
        'views/care_operations_views.xml',
        'views/care_finance_views.xml',
        'views/care_governance_views.xml',
        'views/care_billing_views.xml',
        'views/care_welfare_views.xml',
        'views/care_analytics_views.xml',
        'views/care_reuse_views.xml',
        'views/care_sla_views.xml',
        'views/care_loan_views.xml',
        'views/care_hostel_dashboard.xml',
        'views/care_dept_link_views.xml',
        'data/care_i18n_data.xml',
        'reports/passport_reports.xml',
        'views/care_grievance_views.xml',
        'views/care_custody_views.xml',
        'views/care_gov_transaction_views.xml',
        'views/care_site_permit_views.xml',
        'views/care_absconding_views.xml',
        'views/care_access_profile_views.xml',
        'views/care_announcement_views.xml',
        'views/care_config_settings_views.xml',
        'views/care_menus.xml',
        'views/hr_action_joining.xml',
        'views/hr_action_clearance.xml',
        'views/hr_action_absence.xml',
        'views/hr_action_leave_return.xml',
        'views/hr_leave.xml',
        'views/hr_skills.xml',
        'views/hr_dashboard.xml',
        'wizards/hr_employee_suspend.xml',
        'reports/joining_report.xml',
        'reports/clearance_report.xml',
        'reports/absence_report.xml',
        'reports/leave_return_report.xml',
        'reports/leave_request_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'care_hr/static/src/employee_chatter.scss',
            'care_hr/static/src/hr_dashboard/hr_dashboard.scss',
            'care_hr/static/src/hr_dashboard/hr_dashboard.js',
            'care_hr/static/src/hr_dashboard/hr_dashboard.xml',
            'care_hr/static/src/skills_dashboard/skills_dashboard.js',
            'care_hr/static/src/skills_dashboard/skills_dashboard.xml',
        ],
    },
    }
