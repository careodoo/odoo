{
    'name': "HR Overtime Compensation",
    'summary': """HR Overtime Compensation""",
    'category': 'Uncategorized',
    'version': '17.0',
    'license': 'Other proprietary',
    'depends': ['hr', 'project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/activity_type.xml',
        'data/mail_template.xml',
        'views/overtime_request_views.xml',
        'views/overtime_approval_views.xml',
        'views/overtime_menuitem.xml',
        'wizards/overtime_reject.xml',
        'report/overtime_request_printout.xml',
    ],
}
