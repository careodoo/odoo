# -*- coding: utf-8 -*-
{
    'name': "Care CAFM — Security Bridge",
    'summary': "Makes the standalone Security Manager the Security service inside the "
               "CAFM platform — one and the same module, still fully independent. "
               "Links Security premises to CAFM facilities and opens Security Manager "
               "from the CAFM app.",
    'author': "care-kw",
    'category': 'Services/Facility Management',
    'version': '17.0.2.0.0',
    'license': 'LGPL-3',
    'depends': ['care_cafm', 'security_management'],
    'data': [
        'views/bridge_views.xml',
    ],
    'installable': True,
}
