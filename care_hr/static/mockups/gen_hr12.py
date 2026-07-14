# -*- coding: utf-8 -*-
"""Care HR — pay structure / allowances + per-project penalties."""
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
S=[]

# 64 PAY STRUCTURE & ALLOWANCES
rows=[("EMP-1042","سونام (نظافة)","75","—","بدل مواصلات 10","داخل الراتب","85"),
      ("EMP-2231","راج (أمن)","80","طبيعة عمل صعبة +5","بدل مواصلات 10","كاش منفصل","80 + 10 كاش"),
      ("EMP-3119","بير (ضيافة)","85","طبيعة عمل صعبة +10","فطور 15","كاش منفصل","85 + 15 كاش"),
      ("EMP-4407","حسن (سائق)","75","—","بدل مواصلات 20","داخل الراتب","95")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='small'>{r[3]}</td><td class='small'>{r[4]}</td><td class='center'><span class='badge {'blue' if 'داخل' in r[5] else 'amber'}'>{r[5]}</span></td><td class='center'><b>{r[6]}</b></td></tr>" for r in rows])
body=f"""<div class='sub'>هيكلة الأجر والبدلات — مبنية على قواعد رواتب Odoo · الأساسي 75 وبعضهم 80/85 لطبيعة العمل · بدلات داخل الراتب أو كاش منفصل</div>
<div class='card' style='width:760px'><div class='ct'>إعداد أجر الموظف (Contract)</div>
<table><tr><th>الموظف</th><th>الاسم/المهنة</th><th class='center'>الأساسي</th><th>فرق طبيعة العمل</th><th>البدل</th><th class='center'>طريقة الصرف</th><th class='center'>الإجمالي</th></tr>{tr}</table>
<div class='idea'>💡 كل صف = إعداد فردي على عقد الموظف: أساسي (75/80/85) + بدل + طريقة الصرف. النظام يحسب القسيمة من قواعد Odoo والكاش المنفصل يُسجَّل ويُسوّى.</div></div>
<div class='card' style='width:390px'><div class='ct'>الإعدادات (Salary Rules)</div>
<div class='kv'><b>BASIC</b> أساسي العقد</div><div class='kv'><b>HARDSHIP</b> فرق طبيعة العمل (+5/+10)</div>
<div class='kv'><b>TRANSPORT_IN</b> بدل مواصلات داخل الراتب</div><div class='kv'><b>TRANSPORT_CASH</b> صرف كاش منفصل (Payout)</div><div class='kv'><b>MEAL_CASH</b> بدل فطور كاش</div>
<div class='warn'>⚠ البدلات الكاش لا تدخل القسيمة لكن تُسجَّل في كشف صرف نقدي منفصل + توقيع استلام.</div></div>
<div class='card' style='width:1170px'><div class='sec'>إجراء الصرف</div>
{flow(['تحديد الأساسي والبدل على العقد','اختيار طريقة الصرف (راتب/كاش)','احتساب القسيمة (Odoo)','كشف الكاش المنفصل','توقيع استلام','تسوية محاسبية'])}
<div class='cap'><b>⚙️ كيف يعمل:</b> البدل داخل الراتب يظهر كسطر في القسيمة ويدخل WPS؛ البدل الكاش يخرج في كشف صرف نقدي مستقل بتوقيع العامل ويُسوّى محاسبياً — كله مرتبط بالموظف والمشروع.</div></div>"""
S.append(("64_pay_structure","هيكلة الأجر والبدلات",shell("الأجر والبدلات","Employees › Payroll › Compensation",body)))

# 65 PER-PROJECT PENALTIES
cat=[("مشروع A — نظافة","تأخّر بالزي الرسمي","2 د","موافقة المشرف"),
     ("مشروع A — نظافة","ترك الموقع بدون إذن","5 د","موافقة المشرف + HR"),
     ("مشروع B — أمن","نوم أثناء الوردية","10 د","موافقة HR"),
     ("مشروع B — أمن","عدم الالتزام بالتعليمات","3 د","موافقة المشرف")]
ct="".join([f"<tr><td>{c[0]}</td><td>{c[1]}</td><td class='center'><span class='badge red'>{c[2]}</span></td><td class='small'>{c[3]}</td></tr>" for c in cat])
app=[("PEN-0231","راج (أمن) · مشروع B","نوم أثناء الوردية","10 د","amber","بانتظار HR"),
     ("PEN-0230","سونام (نظافة) · مشروع A","ترك الموقع","5 د","green","معتمد → خصم يونيو"),
     ("PEN-0229","بير (ضيافة) · مشروع C","—","—","slate","ملغى (إثبات غير كافٍ)")]
at="".join([f"<tr><td>{a[0]}</td><td>{a[1]}</td><td class='small'>{a[2]}</td><td class='center'>{a[3]}</td><td class='center'><span class='badge {a[4]}'>{a[5]}</span></td></tr>" for a in app])
body=f"""<div class='sub'>الجزاءات (Penalties) — ليست قيمة الساعة/اليوم الغائب، بل عقوبة تُوقَّع على العامل · <b>تُعرَّف لكل مشروع على حدة</b> وتُطبَّق على عامل دون آخر</div>
<div class='card' style='width:640px'><div class='ct'>كتالوج الجزاءات (إعدادات لكل مشروع)</div>
<table><tr><th>المشروع</th><th>المخالفة</th><th class='center'>القيمة</th><th>الاعتماد المطلوب</th></tr>{ct}</table>
<div class='idea'>💡 لكل مشروع لائحة جزاءات خاصة (نوع المخالفة + القيمة + مستوى الاعتماد). تُضاف/تُعدَّل من الإعدادات حسب عقد المشروع.</div></div>
<div class='card' style='width:510px'><div class='ct'>جزاءات موقّعة</div>
<table><tr><th>المرجع</th><th>العامل/المشروع</th><th>المخالفة</th><th class='center'>القيمة</th><th class='center'>الحالة</th></tr>{at}</table>
<div class='warn'>⚠ لا يُخصم أي جزاء من الراتب إلا بعد الاعتماد — ويظهر كسطر مستقل في القسيمة (PENALTY) منفصل عن خصم الغياب.</div></div>
<div class='card' style='width:1170px'><div class='sec'>إجراء الجزاء (Workflow)</div>
{flow(['رصد المخالفة','اختيار من كتالوج المشروع','إرفاق إثبات','موافقة المشرف','موافقة HR','إخطار العامل','خصم في القسيمة (PENALTY)','أرشفة'])}
<div class='cap'><b>📖 اللائحة:</b> الجزاء عقوبة تأديبية محدّدة سلفاً حسب عقد كل مشروع، بسقف وعدالة. <b>الالتزامات:</b> إثبات موثّق · إخطار العامل · حق التظلّم · لا ازدواج مع خصم الغياب. <b>⚙️ النظام:</b> كتالوج لكل مشروع، تطبيق فردي لكل عامل، اعتماد متدرّج، وسطر خصم مستقل في الرواتب مع أثر كامل.</div></div>"""
S.append(("65_penalties","الجزاءات حسب المشروع",shell("الجزاءات","Employees › Payroll › Penalties",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

# rebuild index: prepend mega dashboard, append all in order
ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐ جديد"),("65_penalties","الجزاءات حسب المشروع ⭐ جديد"),
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
