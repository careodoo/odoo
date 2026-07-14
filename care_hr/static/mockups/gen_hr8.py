# -*- coding: utf-8 -*-
"""Care HR — payroll accuracy: attendance->timesheet->payroll, rules, validation/audit, payslip trail."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=150):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
S=[]

# 46 ATTENDANCE -> TIMESHEET -> PAYROLL
body=f"""<div class='sub'>المسار: البصمة → تحويل لتايم شيت (care_timesheet) → اعتماد مدير العقد → الرواتب (Odoo) — مع اختيار المصدر</div>
<div class='card' style='width:1170px'><div class='ct'>تدفق البيانات</div>
<div style='font-size:13px;text-align:center;line-height:40px'>
<span class='badge blue'>🕗 البصمة (hr.attendance)</span> &nbsp;⟵ جهاز + موبايل + جماعي&nbsp; → &nbsp;
<span class='badge indigo'>📋 تحويل لتايم شيت</span> &nbsp;(متوقّع مقابل فعلي)&nbsp; → &nbsp;
<span class='badge amber'>✔ اعتماد مدير العقد</span> &nbsp;(يبرّر الفروق + يقفل)&nbsp; → &nbsp;
<span class='badge green'>💰 الرواتب (Odoo payslip)</span></div></div>
<div class='card' style='width:560px'><div class='ct'>اختيار أساس الحساب (لكل عقد/قسيمة)</div>
<div class='kv'><span class='radio'>بصمة مباشرة</span><span class='radio on'>تايم شيت معتمد</span><span class='radio'>يدوي (بمبرّر)</span></div>
<div class='kv'><b>الافتراضي/المشروع</b> تايم شيت معتمد</div>
<div class='warn'>اليدوي يتطلب مبرّر + مرفق + اعتماد إضافي (مايبقاش باب خلفي).</div></div>
<div class='card' style='width:560px'><div class='ct'>اعتماد مدير العقد — TS-031 مشروع A</div>
<table><tr><th>الموظف</th><th class='center'>متوقّع</th><th class='center'>فعلي (بصمة)</th><th class='center'>فرق</th><th>تبرير</th></tr>
<tr><td>Bir</td><td class='center'>26</td><td class='center'>24</td><td class='center red'>2</td><td class='small'>إجازة ✓</td></tr>
<tr><td>Gita</td><td class='center'>26</td><td class='center'>25</td><td class='center'>1</td><td class='small'>إذن ✓</td></tr></table>
<div class='ok'>المعتمد فقط يتحوّل للرواتب → يتقفل (تعديل = إعادة فتح بسجل).</div></div>
<div class='idea' style='width:1170px'>💡 البصمة تُصنّف لـ work-entries (عادي/أوفر تايم/ليلي/عطلة) عبر محرّك القواعد؛ الإذن/الإجازة تُربط بنوعها؛ تقريب وفترات سماح.</div>"""
S.append(("46_att_to_payroll","البصمة → تايم شيت → الرواتب",shell("مسار الرواتب","Employees › Payroll › Source Pipeline",body)))

# 47 SALARY STRUCTURE & RULES (Odoo)
rows=[("الأساسي","BASIC","ثابت من العقد","180.000","earn"),
      ("بدل سكن","HOUSING","من الإعدادات/العقد","—","earn"),
      ("أوفر تايم","OT","ساعات×سعر×معدل (محرّك القواعد)","33.750","earn"),
      ("خصم غياب","ABS","أيام×سعر اليوم","-7.500","ded"),
      ("قسط قرض","LOAN","من Compensation Hub","-20.000","ded"),
      ("سلفة","ADV","من Hub","—","ded"),
      ("تأمينات GOSI","GOSI","نسبة (قابلة للضبط)","-12.500","ded"),
      ("مخصّص نهاية خدمة","EOS","قانون الكويت (استحقاق)","18.000","prov"),
      ("الصافي","NET","BASIC+بدلات+OT−خصومات","198.750","net")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center mono'>{r[1]}</td><td class='small'>{r[2]}</td><td class='right'>{r[3]}</td><td><span class='badge {('green' if r[4]=='earn' else 'red' if r[4]=='ded' else 'slate' if r[4]=='prov' else 'indigo')}'>{r[4]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>هيكل وقواعد الرواتب — <b>مبني على Odoo hr_payroll</b> (structures + salary rules + work entries)</div>
<div class='card' style='width:830px'><div class='ct'>هيكل «عامل ميداني» — القواعد</div>
<table><tr><th>القاعدة</th><th class='center'>الكود</th><th>طريقة الحساب</th><th class='right'>القيمة</th><th>النوع</th></tr>{tr}</table>
<div class='ok'>المدخلات تلقائية من work entries (الحضور) + Compensation Hub — بدون نسخ يدوي.</div></div>
<div class='card' style='width:320px'><div class='ct'>إعدادات صارمة (قابلة للضبط)</div>
<div style='font-size:13px;line-height:26px'>⚙️ تقريب الساعات (5 د)<br>⚙️ سقف الأوفر تايم 2س/يوم<br>⚙️ الحد الأدنى للأجر<br>⚙️ نسبة GOSI<br>⚙️ سعر اليوم = أجر÷26<br>⚙️ هيكل لكل فئة (عامل/سائق/مشرف/إداري)</div>
<div class='idea'>💡 كل المعدلات من الإعدادات؛ الحساب آلي ودقيق 100% من القواعد.</div></div>"""
S.append(("47_salary_rules","هيكل وقواعد الرواتب (Odoo)",shell("هياكل الرواتب","Employees › Payroll › Structures & Rules",body)))

# 48 PAYROLL VALIDATION & MULTI-STAGE AUDIT
checks=[("مطابقة الحضور (لا فقد/تكرار/تداخل)","✔","green"),("كل التايم شيت معتمد من مديري العقود","✔","green"),
        ("كل بنود Compensation Hub معتمدة","✔","green"),("لا إقامة منتهية (محظورون مستبعدون)","✗ 3","red"),
        ("الأجر ≥ الحد الأدنى","✔","green"),("الأوفر تايم ≤ السقف","! 5","amber"),
        ("GOSI مطبّق","✔","green"),("انحراف عن الشهر السابق (>10%)","! 8","amber")]
ci="".join([f"<div class='kv'><span class='badge {c}' style='width:24px;text-align:center'>{m}</span> {n}</div>" for n,m,c in checks])
body=f"""<div class='sub'>التحقق ومراحل التدقيق — صارمة قبل الاعتماد والصرف</div>
<div class='card' style='width:560px'><div class='ct'>الفحوصات القبلية — دورة يونيو</div>{ci}
<div class='warn'>الصرف ممنوع حتى حل الحظر · الاستثناءات تُحلّ أو تُبرّر موثّقاً.</div></div>
<div class='card' style='width:600px'><div class='ct'>مراحل الاعتماد والتدقيق (sign-off لكل مرحلة)</div>
<div style='font-size:13px;line-height:31px'>
<span class='badge green'>1 ✓</span> حساب مبدئي (Odoo payslips)<br>
<span class='badge green'>2 ✓</span> مراجعة موظف الرواتب (تقرير الانحراف + استثناءات)<br>
<span class='badge amber'>3 ●</span> تدقيق 1 — مشرف الرواتب (تحقق تطبيق القواعد)<br>
<span class='badge slate'>4 ☐</span> تدقيق 2 — المالية/التدقيق الداخلي (عينة/كامل)<br>
<span class='badge slate'>5 ☐</span> اعتماد نهائي (مدير HR/المالية)<br>
<span class='badge slate'>6 ☐</span> صرف WPS + قفل الفترة</div>
<div class='ok'>فصل المهام: طالب ≠ معتمِد ≠ مدقّق ≠ صارف · كله في الشتر.</div></div>
<div class='idea' style='width:1170px'>💡 لوحة استثناءات موحّدة تُحلّ قبل التشغيل؛ مقارنة بالشهر السابق؛ لا اعتماد بمرحلة مفتوحة.</div>"""
S.append(("48_payroll_audit","التحقق ومراحل التدقيق",shell("تدقيق الرواتب","Employees › Payroll › Validation & Audit",body)))

# 49 PAYSLIP AUDIT TRAIL
rows=[("أوفر تايم 33.750","← تايم شيت TS-031 (12 س) ← بصمة 12 يوم ← قاعدة OT ×1.25","green"),
      ("خصم غياب -7.500","← بصمة: يومين غياب غير مبرّر ← سعر اليوم 3.75","red"),
      ("قسط قرض -20.000","← Compensation Hub: LOAN-0188 قسط 3/6","red"),
      ("GOSI -12.500","← قاعدة GOSI 8% × الأجر الخاضع","red"),
      ("الصافي 198.750","← مجموع القواعد","indigo")]
tr="".join([f"<tr><td><b>{r[0]}</b></td><td class='small'>{r[1]}</td></tr>" for r in rows])
body=f"""<div class='sub'>أثر التدقيق لكل سطر — كل رقم له مرجع كامل (شفافية ودقة)</div>
<div class='card' style='width:760px'><div class='ct'>قسيمة Bir Bahadur — مصدر كل سطر</div>
<table><tr><th>السطر</th><th>المصدر (Traceability)</th></tr>{tr}</table></div>
<div class='card' style='width:400px'><div class='ct'>أدوات الدقة</div>
<div style='font-size:13px;line-height:27px'>🧪 محاكاة (dry-run) قبل الترحيل<br>🔁 فرق «قبل/بعد» عند تغيّر مدخل<br>📊 تقرير مطابقة (تايم شيت ↔ قسيمة ↔ حضور)<br>🔒 قفل + سجل تعديلات</div>
<div class='idea'>💡 موظف الرواتب يشوف مصدر كل رقم → ثقة كاملة + تدقيق سريع + صفر أخطاء يدوية.</div></div>"""
S.append(("49_payslip_trail","أثر التدقيق للقسيمة",shell("أثر القسيمة","Employees › Payroll › Payslip Trail",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
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
("39_residency_tx","معاملة الإقامة (Workflow) ⭐"),("40_residency_board","لوحة الإقامات + الدفعات ⭐"),("41_deployment","تمركز العمال في المشاريع ⭐"),("42_quality","جودة العامل (التصنيف) ⭐"),("43_requests_hub","مركز الطلبات الإدارية ⭐"),("44_payroll_run","تشغيل الرواتب (محكم) ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
