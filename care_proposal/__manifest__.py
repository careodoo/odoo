{
    'name': "Care Proposal",
    'description': """
        Long description of module's purpose
    """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'product', 'crm', 'report_xlsx', 'report_xlsx_helper'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/activity_type.xml',
        'views/proposal.xml',
        'views/proposal_service.xml',
        'views/proposal_transportation.xml',
        'views/proposal_manpower.xml',
        'views/proposal_scope.xml',
        'views/proposal_term.xml',
        'views/crm_lead.xml',
        'views/proposal_approver.xml',
        'views/proposal_service_type.xml',
        'views/proposal_service_location.xml',
        'views/proposal_service_unit.xml',
        'reports/proposal_report.xml',
        'reports/proposal_sheet_xlsx.xml',
        'reports/proposal_scope_xlsx.xml',
        'reports/proposal_manpower_xlsx.xml',
        'reports/proposal_material_xlsx.xml',
        'reports/proposal_equipment_xlsx.xml',
        'reports/proposal_transportation_xlsx.xml',
        'reports/proposal_term_xlsx.xml',
        'reports/customer_proposal.xml',
        'data/mail_template.xml',
    ],
    'assets': {
        'web.assets_common': [
            'care_proposal/static/src/scss/cairofont.scss',
        ],
        'web.report_assets_common': [
            'care_proposal/static/src/scss/cairofont.scss',
        ],
    },
    'license': 'LGPL-3',

}
