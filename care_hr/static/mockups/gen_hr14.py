# -*- coding: utf-8 -*-
"""Care HR — allowance approval matrix (configurable approvers)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:6px 10px;font-size:12px;margin:3px 0;font-weight:bold}
.arr{color:#94a3b8;margin:0 3px;font-weight:bold}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])

# 70 ALLOWANCE APPROVAL MATRIX
mtx=[("بدل مواصلات داخل الراتب","≤ 10 د","مدير الإدارة","—","green"),
     ("بدل مواصلات / فطور كاش","أي قيمة","مدير الإدارة","عضو إدارة عليا","amber"),
     ("بدل طبيعة عمل (HARDSHIP)","≤ 5 د","مدير الإدارة","—","green"),
     ("بدل طبيعة عمل (HARDSHIP)","> 5 د","مدير الإدارة","عضو إدارة عليا","amber"),
     ("بدل استثنائي/خاص","أي قيمة","مدير الإدارة","إدارة عليا (شخصان)","red")]
mt="".join([f"<tr><td>{m[0]}</td><td class='center'>{m[1]}</td><td>{m[2]}</td><td><span class='badge {m[4]}'>{m[3]}</span></td></tr>" for m in mtx])
reqs=[("ALW-0142","راج · بدل كاش 10 د","مدير الإدارة ✓ · إدارة عليا ⏳","amber","بانتظار إدارة عليا"),
      ("ALW-0141","بير · HARDSHIP +10","مدير الإدارة ✓ · أ. خالد ✓","green","معتمد → العقد"),
      ("ALW-0140","حسن · بدل استثنائي","مدير الإدارة ✓ · 1/2 إدارة عليا","amber","ناقص اعتماد ثانٍ")]
rt="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='small'>{r[2]}</td><td class='center'><span class='badge {r[3]}'>{r[4]}</span></td></tr>" for r in reqs])
body=f"""<div class='sub'>اعتماد البدلات — مصفوفة معتمدين قابلة للضبط: مدير الإدارة + أشخاص من الإدارة العليا · <b>تُحدَّد لاحقاً من الإعدادات</b></div>
<div class='card' style='width:1170px'><div class='sec'>المسار</div>
{flow(['طلب/تعديل بدل','مدير الإدارة','عضو الإدارة العليا (حسب النوع/القيمة)','اعتماد نهائي','ينعكس على العقد + قواعد الرواتب'])}
<div class='cap'><b>⚙️ كيف يعمل:</b> أي إجراء يخص بدلاً لا يُطبَّق إلا بعد سلسلة الاعتماد المحدَّدة في الإعدادات؛ المعتمدون (مدير الإدارة + أعضاء الإدارة العليا) والعتبات تُضبَط لاحقاً دون برمجة؛ ولا يدخل الراتب إلا بعد اكتمال الاعتمادات.</div></div>
<div class='card' style='width:680px'><div class='ct'>مصفوفة الاعتماد (إعدادات)</div>
<table><tr><th>نوع البدل</th><th class='center'>العتبة</th><th>معتمد 1</th><th>معتمد 2 (إدارة عليا)</th></tr>{mt}</table>
<div class='idea'>💡 الصفوف/العتبات/الأشخاص كلها قابلة للإضافة والتعديل من الإعدادات لاحقاً — كل نوع بدل بسلسلة اعتماده.</div></div>
<div class='card' style='width:470px'><div class='ct'>الإعدادات (تُحدَّد لاحقاً)</div>
<div class='kv'><b>معتمدو الإدارات</b> مدير كل إدارة (حقل)</div>
<div class='kv'><b>أعضاء الإدارة العليا</b> قائمة أشخاص محدَّدة</div>
<div class='kv'><b>العتبات</b> قيمة البدل التي تستدعي إدارة عليا</div>
<div class='kv'><b>عدد الاعتمادات</b> 1 أو 2 من الإدارة العليا</div>
<div class='warn'>⚠ تُترك فارغة الآن وتُملأ عند التشغيل — بدون تعديل برمجي.</div>
<div class='ct' style='margin-top:10px'>طلبات بدلات جارية</div>
<table><tr><th>المرجع</th><th>البدل</th><th>الاعتمادات</th><th class='center'>الحالة</th></tr>{rt}</table></div>"""
html=shell("اعتماد البدلات","Employees › Payroll › Allowance Approvals",body)
hp=os.path.join(OUT,"70_allowance_approvals.html");pp=os.path.join(OUT,"70_allowance_approvals.png")
open(hp,"w",encoding="utf-8").write(html)
subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.remove(hp);print("rendered 70_allowance_approvals")

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐ جديد"),("65_penalties","الجزاءات حسب المشروع ⭐"),
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
