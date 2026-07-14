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
    'depends': ['base', 'mail', 'product', 'crm', 'portal', 'website', 'report_xlsx', 'report_xlsx_helper'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/activity_type.xml',
        'data/cost_component_data.xml',
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
        'data/service_request_data.xml',
        'views/proposal_cost_component.xml',
        'views/proposal_service_cost.xml',
        'views/proposal_service_request.xml',
        'views/service_request_templates.xml',
        'views/res_config_settings.xml',
        'views/proposal_dashboard.xml',
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
        'web.assets_backend': [
            'care_proposal/static/src/dashboard/proposal_dashboard.scss',
            'care_proposal/static/src/dashboard/proposal_dashboard.js',
            'care_proposal/static/src/dashboard/proposal_dashboard.xml',
        ],
    },
    'license': 'LGPL-3',

}
