{
    'name': 'Letter Management',
    'version': '15.0',
    'depends': [
               'base','hr',
                ],
    'data': [
        'security/ir.model.access.csv',
        'view/letter_file.xml',
        'view/outgoing_tag.xml',
        'view/outgoing_stage.xml',
        'view/menu_view.xml',
        'view/outgoing_report.xml',
    ],
    "application":  False,
    "installable":  True,
    "auto_install":  False,
}
