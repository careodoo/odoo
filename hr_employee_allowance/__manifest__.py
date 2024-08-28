{
    'name':
        "HR Employee Allowance",
    'summary':
        """
        HR Employee Allowance
        """,
    'category':
        'Uncategorized',
    'version':
        '15.0.0.0.1',
    'license':
        'Other proprietary',
    'depends': ['hr',],
    'data': [
        'security/hr_allowance_security.xml',
        'security/ir.model.access.csv',
        'views/hr_allowance_type_views.xml',
        'views/hr_allowance_request_views.xml',
        'views/hr_employee_views.xml',
    ],
}
