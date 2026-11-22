# -*- coding: utf-8 -*-
{
    'name': 'CARE · التوقيع الإلكتروني وسجل السيريالات',
    'version': '17.0.1.0.0',
    'summary': 'توقيع إلكتروني لكل مستخدم + ختمه على التقارير بسيريال فريد + سجل مركزي للتحقق',
    'description': """
التوقيع الإلكتروني الموحّد (CARE E-Signature)
=============================================
- نموذج توقيع لكل مستخدم في بروفايله (res.users.esign_signature).
- عند الاعتماد: يُختَم توقيع المستخدم على التقرير في مكان التوقيع، وتحته سيريال فريد
  (SIG-YYYYMMDD-HHMM-CODE-RESID-HASH) يحمل التاريخ والوقت ورمز الموديول ورقم السجل.
- موديول سجل مركزي (care.esignature) يحفظ كل عملية توقيع: من، متى، أي موديول، أي سجل — للقراءة فقط (تدقيق).
- مكوّن QWeb موحّد (esign_box) يُحقَن في أي تقرير فيه مربّع توقيع.
- شاشة تحقّق: من أي سيريال تعرف صاحب التوقيع ووقته ومستنده.
""",
    'author': 'CARE',
    'category': 'Human Resources',
    'depends': ['mail', 'hr', 'web'],
    'data': [
        'security/esign_security.xml',
        'security/ir.model.access.csv',
        'data/esign_data.xml',
        'data/esign_enrollment_data.xml',
        'reports/esign_templates.xml',
        'reports/esign_log_report.xml',
        'reports/esign_enrollment_report.xml',
        'reports/esign_revocation_report.xml',
        'views/esignature_views.xml',
        'views/esign_enrollment_views.xml',
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
        'views/esign_verify_views.xml',
    ],
    'demo': ['demo/demo.xml', 'demo/esign_enrollment_demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
