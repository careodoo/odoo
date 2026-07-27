{
    'name': 'CARE — الأمن (إدارة المرافق)',
    'version': '17.0',
    'category': 'Services/Facility Management',
    'sequence': 10,
    'summary': 'Manage security services, premises, and teams',
    'description': """
Security Manager
===============
A comprehensive security management platform designed to streamline operations, enhance accountability,
and improve client transparency through structured data tracking, real-time monitoring, and automated reporting.

Features:
---------
* Guard and Security Team Management
* Client and Premises Management (with QR codes)
* Key Management with Check-in/Check-out
* Task Assignment and Tracking
* Shift Scheduling
* Patrol Management with Checkpoint verification
* Visitor Management
* Incident Reporting
* GPS Tracking for Guards
    """,
    'author': 'care-kw',
    'depends': [
        'care_cafm',
        'base',
        'hr',
        'mail',
        'portal',
        'web',
        'resource',
        'contacts',
        'account',
        'report_xlsx',
        'hr_attendance',
        'hr_contract',
    ],
    "data": [
        "security/security.xml",
        "views/hr_employee_views.xml",
        "views/dashboard_views.xml",
        "views/client_views.xml",
        "views/visitor_views.xml",
        "views/premises_views.xml",
        "views/report_views.xml",
        "views/incident_views.xml",
        "views/team_views.xml",
        "views/task_checklist_views.xml",
         "views/key_views.xml",
        "views/task_category_views.xml",
        "views/task_views.xml",
        "views/schedule_views.xml",
        "views/patrolling_views.xml",
        "views/gate_pass_views.xml",
        "views/gate_pass_scanner_templates.xml",
        "views/unit_views.xml",
        "views/floor_views.xml",
        "views/inspection_views.xml",
        "views/inspection_issue_views.xml",
        "views/security_employee_views.xml",
        "views/shift_assignment_views.xml",
        "views/menu_views.xml",
        "views/role_views.xml",
        "views/security_gate_cashier_views.xml",
        "views/gate_cashier_menu.xml",
        "views/security_gate_pass_payment_views.xml",
        "security/ir.model.access.csv",
        "data/security_sequence_data.xml",
        "data/security_client_data.xml",
        "data/security_team_data.xml",
        "data/mail_activity_data.xml",
        "data/email_templates.xml",
        "data/mail_templates.xml",
        "reports/gate_pass_receipt_template.xml",
        "wizards/views/wizard_views.xml",
        "wizards/views/patrol_complete_wizard_views.xml",
        "wizards/police_report_wizard.xml",
        "reports/key_report.xml",
        "reports/incidence_report_templates.xml",
        "reports/incidence_reports.xml",
        "reports/gate_pass_templates.xml",
        "reports/gate_pass_reports.xml",
        "reports/employee_report_templates.xml",
        "reports/employee_reports.xml",
        "reports/patrol_point_templates.xml",
        "reports/patrol_point_reports.xml",
        "reports/premise_templates.xml",
        "reports/premise_reports.xml",
        "reports/floor_templates.xml",
        "reports/floor_reports.xml",
        "reports/security_team_report.xml",
        "reports/security_unit_qrcode_report.xml",
        "reports/inspection_templates.xml",
        "reports/inspection_reports.xml",
        "views/security_vehicle_views.xml",
        "views/cafm_bridge_views.xml",
        "views/cafm_incident_views.xml",
        
        
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            # JavaScript files
            'security_management/static/src/js/security_dashboard.js',
            'security_management/static/src/js/qr_scanner.js',
            'security_management/static/src/js/patrol_dashboard.js',
            'security_management/static/src/js/gate_pass.js',
            'security_management/static/src/js/gate_pass_scanner.js',
            'security_management/static/src/js/key_management.js',
            'security_management/static/src/js/incident_reporting.js',
            
            # CSS files
            'security_management/static/src/css/security_dashboard.css',
            'security_management/static/src/css/gate_pass_scanner.css',
            
            # Libraries
            # 'security_management/static/lib/jsQR.js',  # Removed - now using browser's BarcodeDetector API
            'security_management/static/lib/chart.min.js',  # External lib, needs to be downloaded locally
            'security_management/static/lib/leaflet/leaflet.js',  # External lib, needs to be downloaded locally
            'security_management/static/lib/leaflet/leaflet.css',
            
            # SCSS files
            'security_management/static/src/scss/security_management.scss',
            'security_management/static/src/security_dashboard.scss',
            
            # xml files
            'security_management/static/src/xml/qr_scanner.xml',
            'security_management/static/src/xml/patrol_dashboard.xml',
            'security_management/static/src/xml/gate_pass.xml',
            'security_management/static/src/xml/gate_pass_scanner.xml',
            'security_management/static/src/xml/key_management.xml',
            'security_management/static/src/xml/incident_reporting.xml',
            'security_management/static/src/xml/security_dashboard.xml',

        ]
    },
    'license': 'LGPL-3',
}
