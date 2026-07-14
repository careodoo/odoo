# -*- coding: utf-8 -*-
"""Care HR — attendance coverage / gap monitor (unassigned & no-attendance workers)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.tile{display:inline-block;vertical-align:top;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 9px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:21px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
.toggle{display:inline-block;width:34px;height:18px;border-radius:10px;background:#21b07b;position:relative;vertical-align:middle}
.toggle:after{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:#fff;top:2px;left:2px}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""

kp=[("مسجّل بلا مشروع/إدارة","37","#e25563"),("مسجّل بإدارة بلا بصمة","52","#f59e0b"),
("غير ظاهر في التايم شيت","61","#f59e0b"),("بلا حضور 3+ أيام","18","#e25563"),("مستثنى (موثّق)","9","#64748b")]
tl="".join([f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in kp])
rows=[("EMP-5012","سونيل","بلا مشروع/إدارة","—","لم يُسجَّل بعد","red","تعيين لمشروع"),
      ("EMP-4880","ديباك","مسجّل: نظافة","مشروع A","بلا بصمة منذ 4 أيام","red","مراجعة/تنبيه"),
      ("EMP-4771","رمضان","مسجّل: أمن","مشروع B","غير ظاهر في التايم شيت","amber","فحص الربط"),
      ("EMP-4655","أنيل","مسجّل: ضيافة","مشروع C","مستثنى — إجازة بإذن","slate","مستثنى ✓")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='small'>{r[2]}</td><td class='center'>{r[3]}</td><td>{r[4]}</td><td class='center'><span class='badge {r[5]}'>{r[6]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>مراقب التغطية — يكشف كل عامل مسجّل لدينا وليس له حضور/انصراف أو غير مربوط بمشروع/إدارة، قبل أن يسبّب مشكلة في الرواتب</div>
{tl}
<div class='card' style='width:820px'><div class='ct'>العمالة المرصودة (فحص يومي آلي)</div>
<table><tr><th>الكود</th><th>الاسم</th><th>التسجيل</th><th class='center'>المشروع</th><th>السبب</th><th class='center'>الحالة/الإجراء</th></tr>{tr}</table>
<div class='warn'>⚠ النظام ينبّه يومياً: "عمالة مسجّلة لديك بلا حضور/انصراف" — حتى لا تمر دون ملاحظة وتُفسد التايم شيت والرواتب.</div></div>
<div class='card' style='width:330px'><div class='ct'>استثناء — من الملف الشخصي فقط</div>
<div class='kv'><b>أنيل · EMP-4655</b></div>
<div class='kv'>استثناء من تنبيه عدم الحضور <span class='toggle'></span></div>
<div class='kv'><b>السبب</b> إجازة/مهمة بإذن</div>
<div class='kv'><b>المدة</b> 2026-06-20 → 06-30</div>
<div class='kv'><b>بواسطة</b> مدير إدارة الضيافة</div>
<div class='warn'>⚠ الاستثناء صلاحية <b>مدير الإدارة</b> فقط، ومن داخل ملف الموظف، وموثّق بمدة وسبب (ينتهي تلقائياً).</div></div>
<div class='card' style='width:1170px'><div class='sec'>كيف يعمل</div>
<div class='cap'><b>⚙️ المنطق:</b> فحص يومي يطابق (الموظفون النشطون) ضد (سجل البصمة/التايم شيت + الربط بمشروع/إدارة). أي عامل بلا تعيين أو بلا حضور يُرفَع كاستثناء ويُنبَّه مديره. <b>الاستثناء:</b> يُفعَّل فقط من ملف الموظف وبصلاحية مدير الإدارة، بمدة وسبب موثّقين، فلا يختفي العامل من الرقابة إلا بقرار مسؤول. <b>الأثر:</b> يمنع رواتب ناقصة/زائدة وعمالة "شبح" غير مرصودة.</div></div>"""
html=shell("مراقب تغطية الحضور","Employees › Attendance › Coverage Monitor",body)
hp=os.path.join(OUT,"73_coverage_monitor.html");pp=os.path.join(OUT,"73_coverage_monitor.png")
open(hp,"w",encoding="utf-8").write(html)
subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.remove(hp);print("rendered 73_coverage_monitor")

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("71_residency_dashboard","داشبورد الإقامات ⭐"),("72_payroll_dashboard","داشبورد الرواتب ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("73_coverage_monitor","مراقب تغطية الحضور ⭐ جديد"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
("66_payroll_routing","مسار وتقسيم الرواتب ⭐"),("67_payslip_icons","أيقونات المؤثّرات على السطر ⭐"),("69_payroll_extras","أفكار إضافية في الرواتب ⭐"),
("68_contracts","إدارة عقود الموظفين ⭐"),
("07_overtime_rules","قواعد الأوفر تايم وساعات العمل"),("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)"),("09_eos","حاسبة نهاية الخدمة (قانون الكويت)"),
("10_payroll","الرواتب + Compensation Hub"),("11_documents","مركز انتهاء المستندات"),("12_discipline","الانضباط والقانوني"),
("13_housing","السكن (Hostel)"),("14_uniform_transport","الزي والمواصلات (أساسي)"),("15_performance","الأداء والمهارات (أساسي)"),
("16_access","شجرة الصلاحيات (Access Profiles)"),("17_reports","مركز التقارير"),
("18_profitability","ربحية العقد/المشروع (P&L) ⭐"),("19_workforce_planning","تخطيط القوى العاملة والإحلال ⭐"),
("20_sponsorship","امتثال العمالة المكفولة ⭐"),("21_sla_client","SLA وبوابة العميل"),("22_roster","جدولة الورديات + الاحتياطي"),
("23_agency","أداء وكالات الاستقدام"),("24_probation","محرّك فترة التجربة"),("25_letters","مركز الخطابات والشهادات"),
("26_movement","سجل حركة الموظف الداخلية"),("27_attrition","تحليل التسرّب (Attrition)"),
("28_gov_custody","المصروفات الحكومية وتسوية العُهد ⭐"),("29_performance_plus","الأداء والمهارات (مطوّر) ⭐"),
("30_loans","السلف والأدفانس ⭐"),("31_bonus","البونص والمكافآت ⭐"),("32_offboarding","الاستقالة وإنهاء الخدمة ⭐"),("33_uniform_plus","الزي والمهمات (مطوّر) ⭐"),
("34_hse","السلامة والحوادث (HSE) ⭐"),("35_recruitment","التوظيف (ATS) ⭐"),("36_training","أكاديمية التدريب والشهادات ⭐"),("37_insurance","التأمين و GOSI ⭐"),("38_equipment","المعدات والأصول للعامل ⭐"),
("39_residency_tx","معاملة الإقامة (Workflow) ⭐"),("40_residency_board","لوحة الإقامات + الدفعات ⭐"),("41_deployment","تمركز العمال في المشاريع ⭐"),("42_quality","جودة العامل (التصنيف) ⭐"),("43_requests_hub","مركز الطلبات الإدارية ⭐"),("44_payroll_run","تشغيل الرواتب (محكم) ⭐"),
("50_compliance_center","مركز قيادة الامتثال ⭐"),("51_ai_assistant","مساعد HR الذكي (AI) ⭐"),("52_client_billing","فوترة العميل من الحضور ⭐"),("53_eos_liability","التزام نهاية الخدمة ⭐"),("54_kiosk","كشك الخدمة الذاتية للعمال ⭐"),
("55_automation","محرّك الأتمتة والقواعد ⭐"),("56_exceptions","مركز الاستثناءات والتنبيهات ⭐"),("57_smart_approvals","موافقات ذكية + تصعيد ⭐"),("58_data_quality","مركز جودة البيانات ⭐"),("59_integrations","مركز التكاملات ⭐"),
("60_social_contracts","العقود الاجتماعية (ملفات PAM) ⭐"),("61_cycles1","سيكلات: الإجازات + الاستقالة ⭐"),("62_cycles2","سيكلات: الاستقدام + الرواتب ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
