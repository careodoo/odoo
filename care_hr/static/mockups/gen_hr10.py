# -*- coding: utf-8 -*-
"""Care HR — automation engine, exception center, smart approvals, data quality, integrations."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=150):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:170px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
S=[]

# 55 AUTOMATION & RULES ENGINE
def rule(when,iff,then,on=True):
    return f"""<div class='card' style='width:560px;padding:12px'><div style='font-size:13px;line-height:24px'>
<span class='badge blue'>لمّا</span> {when}<br><span class='badge amber'>إذا</span> {iff}<br><span class='badge green'>نفّذ</span> {then}</div>
<div class='small' style='margin-top:6px'><span class='badge {'green' if on else 'slate'}'>{'مفعّلة' if on else 'متوقفة'}</span></div></div>"""
body=f"""<div class='sub'>محرّك الأتمتة والقواعد (No-Code) — يخلّي الإجراءات تمشي لوحدها بسرعة ودقة وتناسق</div>
{rule('إقامة عامل تنتهي خلال 30 يوم','القطاع = حكومي','إنشاء معاملة تجديد + طلب عهدة + تنبيه المندوب')}
{rule('تايم شيت يُعتمد من مدير العقد','—','ترحيل تلقائي إلى work entries / الرواتب')}
{rule('غياب 3 أيام متتالية بدون إذن','الموظف ليس في إجازة','إنشاء إجراء تأديبي (مسودة) + تنبيه المشرف')}
{rule('نشر عامل لموقع حساس','بدون تصريح أمني ساري','منع النشر + تنبيه + طلب تصريح')}
<div class='card' style='width:1170px'><span class='btn p'>+ قاعدة جديدة</span>
<div class='idea' style='margin-top:8px'>💡 قواعد بصرية بدون كود؛ يبني على Odoo automation/server actions؛ يضمن أن كل إجراء حكومي/تأديبي/راتب يتم آلياً ومتّسقاً — لا نسيان ولا تأخير.</div></div>"""
S.append(("55_automation","محرّك الأتمتة والقواعد",shell("الأتمتة","Employees › Configuration › Automation",body)))

# 56 EXCEPTION CENTER
rows=[("حظر امتثال (إقامة/تصريح منتهٍ)","20","🚫","red","يمنع النشر/الراتب"),
      ("خرق تغطية SLA (مواقع تحت المطلوب)","3","⚠","amber","مخاطرة غرامة"),
      ("انحراف راتب >10% عن الشهر السابق","8","📊","amber","مراجعة قبل الصرف"),
      ("تايم شيت غير معتمد","2","📋","amber","يعطّل الرواتب"),
      ("عودة إجازة متأخرة","7","🌴","amber","متابعة"),
      ("بيانات ناقصة (IBAN/عقد)","11","🧩","red","يكسر الرواتب"),
      ("موافقات تجاوزت الـSLA","5","⏰","amber","تصعيد")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[2]}</td><td class='center'><span class='badge {r[3]}'>{r[1]}</span></td><td class='small'>{r[4]}</td><td><span class='btn' style='padding:3px 9px'>معالجة</span></td></tr>" for r in rows])
body=f"""<div class='sub'>مركز الاستثناءات — أدِر بالاستثناء: النظام يطلّع الخطأ فقط، تتصرّف في المهم وبسرعة</div>
<div class='card' style='width:830px'><div class='ct'>كل الاستثناءات (عبر المنظومة)</div>
<table><tr><th>النوع</th><th class='center'></th><th class='center'>العدد</th><th>الأثر</th><th></th></tr>{tr}</table></div>
<div class='card' style='width:320px'><div class='ct'>الملخّص</div>
<div style='text-align:center'><div style='font-size:34px;font-weight:bold;color:#dc2626'>56</div><span class='small'>استثناء يحتاج إجراء</span></div>
{bar('حرجة',55,'31','b4',120)}{bar('تحذير',45,'25','b2',120)}
<div class='idea'>💡 بدل فحص 2400 سجل، تشوف 56 استثناء بس → سرعة هائلة.</div></div>"""
S.append(("56_exceptions","مركز الاستثناءات والتنبيهات",shell("الاستثناءات","Employees › Control › Exceptions",body)))

# 57 SMART APPROVALS
rows=[("إجازة سنوية ≤ الرصيد","تلقائي فوري","green","Bir · 3 أيام"),
      ("سلفة ≤ 50% الراتب","تلقائي فوري","green","Gita · 50.000"),
      ("إجازة تتجاوز الرصيد","تصعيد للمدير","amber","Ramesh · 35 يوم"),
      ("سلفة تتجاوز السقف","موافقة مالية","amber","Anil · 200.000"),
      ("موافقة تجاوزت 48 ساعة","تصعيد للأعلى","red","قرض Kamal")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge {r[2]}'>{r[1]}</span></td><td class='small'>{r[3]}</td></tr>" for r in rows])
body=f"""<div class='sub'>موافقات ذكية — داخل السياسة يُعتمد فوراً، خارجها يُوجّه ويُصعّد (سرعة + تحكّم)</div>
<div class='card' style='width:760px'><div class='ct'>قواعد الموافقة الذكية</div>
<table><tr><th>الحالة</th><th>المسار</th><th>مثال</th></tr>{tr}</table>
<div class='ok'>الروتيني داخل السياسة لا ينتظر بشراً؛ الاستثناء فقط يُراجَع.</div></div>
<div class='card' style='width:400px'><div class='ct'>الأثر</div>
{bar('معتمد تلقائياً',72,'72%','b3')}{bar('يحتاج مراجعة',28,'28%','b4')}
<div class='kv' style='margin-top:4px'><b>متوسط زمن الاعتماد</b> 4 دقائق (كان 1.8 يوم)</div>
<div class='idea'>💡 تفويض عند الإجازة + تصعيد آلي عند تجاوز SLA + كله موثّق.</div></div>"""
S.append(("57_smart_approvals","موافقات ذكية + تصعيد",shell("الموافقات الذكية","Employees › Control › Smart Approvals",body)))

# 58 DATA QUALITY
rows=[("عمّال بدون تاريخ إقامة","6","يكسر تنبيه الانتهاء","red"),
      ("عمّال بدون IBAN/حساب بنكي","11","يكسر WPS/الرواتب","red"),
      ("عمّال بدون عقد ساري","3","يكسر EOS/الرواتب","red"),
      ("عمّال بدون هيكل راتب","2","لا تُحسب القسيمة","red"),
      ("تكرار محتمل (نفس الجواز)","1","ازدواج","amber"),
      ("تداخل نشر (موقعين بنفس اليوم)","4","تعارض حضور","amber"),
      ("بدون جنسية/مهنة","9","تقارير ناقصة","amber")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'><span class='badge {r[3]}'>{r[1]}</span></td><td class='small'>{r[2]}</td><td><span class='btn' style='padding:3px 9px'>إصلاح</span></td></tr>" for r in rows])
body=f"""<div class='sub'>مركز جودة وسلامة البيانات — يلقط الخطأ قبل ما يكسر الرواتب/الامتثال</div>
<div class='card' style='width:830px'><div class='ct'>مشاكل البيانات</div>
<table><tr><th>المشكلة</th><th class='center'>العدد</th><th>الأثر</th><th></th></tr>{tr}</table></div>
<div class='card' style='width:320px'><div class='ct'>درجة جودة البيانات</div>
<div style='text-align:center'><div style='font-size:38px;font-weight:bold;color:#16a34a'>94<span style='font-size:16px'>%</span></div></div>
<div class='warn'>16 سجل حرج يجب إصلاحه قبل تشغيل الرواتب.</div>
<div class='idea'>💡 فحص مستمر يومي → بحلول نهاية الشهر كل البيانات نظيفة → إقفال رواتب سريع وبصفر أخطاء.</div></div>"""
S.append(("58_data_quality","مركز جودة البيانات",shell("جودة البيانات","Employees › Control › Data Quality",body)))

# 59 INTEGRATIONS HUB
def integ(name,desc,st,col):
    return f"<div class='card' style='width:370px;padding:14px'><div style='font-weight:bold;font-size:14px'>{name} <span class='badge {col}' style='float:left'>{st}</span></div><div class='small' style='margin-top:6px'>{desc}</div></div>"
body=f"""<div class='sub'>مركز التكاملات — أتمتة طرف-لطرف تربط HR بالحكومة والبنك والمحاسبة والعروض</div>
{integ('🏛️ البوابات الحكومية (PACI/PAM/MOI)','جلب/تحديث تواريخ الإقامة والإذن + المعاملات','متصل','green')}
{integ('🏦 البنك / WPS (حماية الأجور)','توليد ملف WPS + متابعة حالة الدفع','متصل','green')}
{integ('📒 المحاسبة','قيود الرواتب + العهد + مراكز تكلفة المشاريع','متصل','green')}
{integ('📄 العروض / التندر','عقد جديد فائز → خطة عمالة + تأهيل تلقائي','مربوط','blue')}
{integ('🤝 CRM','العميل والعقد والموقع','مربوط','blue')}
{integ('🕗 أجهزة البصمة (ZKTeco)','بصمة → hr.attendance → تايم شيت','متصل','green')}
<div class='idea' style='width:1170px'>💡 يقفل كل الـ loops: عقد→عمالة→تأهيل→نشر→حضور→فوترة→راتب→محاسبة، آلياً وبدون إدخال مزدوج.</div>"""
S.append(("59_integrations","مركز التكاملات",shell("التكاملات","Employees › Configuration › Integrations",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

NEW=[("55_automation","محرّك الأتمتة والقواعد ⭐"),("56_exceptions","مركز الاستثناءات والتنبيهات ⭐"),("57_smart_approvals","موافقات ذكية + تصعيد ⭐"),("58_data_quality","مركز جودة البيانات ⭐"),("59_integrations","مركز التكاملات ⭐")]
BASE=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
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
("39_residency_tx","معاملة الإقامة (Workflow) ⭐"),("40_residency_board","لوحة الإقامات + الدفعات ⭐"),("41_deployment","تمركز العمال في المشاريع ⭐"),("42_quality","جودة العامل (التصنيف) ⭐"),("43_requests_hub","مركز الطلبات الإدارية ⭐"),("44_payroll_run","تشغيل الرواتب (محكم) ⭐"),
("50_compliance_center","مركز قيادة الامتثال ⭐"),("51_ai_assistant","مساعد HR الذكي (AI) ⭐"),("52_client_billing","فوترة العميل من الحضور ⭐"),("53_eos_liability","التزام نهاية الخدمة ⭐"),("54_kiosk","كشك الخدمة الذاتية للعمال ⭐")]
ALL=BASE+NEW
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
