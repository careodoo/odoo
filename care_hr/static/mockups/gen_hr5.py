# -*- coding: utf-8 -*-
"""Care HR — HSE, recruitment ATS, training academy, insurance/GOSI, equipment. Rebuilds index."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=160):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
def kol(h,items):
    return f"<div class='kol'><div class='h'>{h}</div>"+"".join([f"<div class='kc'>{i}</div>" for i in items])+"</div>"
S=[]

# 34 HSE / INCIDENT
phone=f"""<div class='phone' style='width:250px'><div class='screen' style='min-height:300px'>
<div style='font-weight:bold;color:#0b1220'>بلاغ حادث — موبايل</div>
<div style='background:#fff;border-radius:10px;margin-top:8px;padding:10px;font-size:12px;line-height:24px'>
النوع: إصابة عمل ▾<br>الموقع: مشروع A 📍<br>الخطورة: متوسطة<br>المصاب: Ramesh<br>📷 صور (2) · إجراء فوري</div>
<div style='margin-top:8px;background:#dc2626;color:#fff;border-radius:10px;padding:10px;text-align:center;font-weight:bold'>إرسال البلاغ</div></div></div>"""
body=f"""<div class='sub'>السلامة والحوادث (HSE) — بلاغ من الموقع + تحقيق + إجراء تصحيحي + مطالبة تأمين</div>
{phone}
<div class='card' style='width:560px'><div class='ct'>سجل الحوادث</div>
<table><tr><th>#</th><th>النوع</th><th>الموقع</th><th class='center'>الخطورة</th><th>الحالة</th></tr>
<tr><td>INC-031</td><td>إصابة عمل</td><td>مشروع A</td><td class='center'><span class='badge amber'>متوسطة</span></td><td>تحقيق</td></tr>
<tr><td>INC-030</td><td>وشيك (near-miss)</td><td>مشروع B</td><td class='center'><span class='badge green'>منخفضة</span></td><td>مغلق</td></tr>
<tr><td>INC-029</td><td>حادث أمني</td><td>مشروع C</td><td class='center'><span class='badge red'>عالية</span></td><td>إجراء تصحيحي</td></tr></table>
<div class='idea'>💡 يبني على incident في security_management؛ ربط بمطالبة تأمين + أيام التغيّب (lost-time)؛ تدريب HSE إجباري.</div></div>
<div class='card' style='width:330px'><div class='ct'>مؤشرات السلامة</div>
{bar('حوادث/مشروع A',60,'5','b4')}{bar('وشيك',40,'9','b3')}
<div class='kv' style='margin-top:4px'><b>أيام بدون حادث</b> 24</div><div class='kv'><b>معدل الإصابات (LTIR)</b> 1.2</div></div>"""
S.append(("34_hse","السلامة والحوادث (HSE)",shell("السلامة والحوادث","Employees › HSE › Incidents",body)))

# 35 RECRUITMENT ATS
body=f"""<div class='sub'>التوظيف (ATS) — من طلب العمالة إلى الاستقدام، خط واحد متّصل</div>
{kol('طلب عمالة (3)',['مشروع A · نظافة ×8','مشروع D · ضيافة ×60'])}
{kol('مرشّحون (42)',['من وكالة ABC','من XYZ','+40'])}
{kol('فرز/مقابلة (18)',['Anil ✓','Sunil — مقابلة'])}
{kol('عرض (9)',['Bishnu · مقبول'])}
{kol('كشف طبي (6)',['Hari ✓','Kamal رسب'])}
{kol('→ استقدام/تأهيل',['→ Mobilization'])}
<div class='card' style='width:1170px;margin-top:4px'><div class='idea'>💡 يقفل الـ loop: manpower_requisition → recruitment → mobilization. تتبّع: مصدر الوكالة، نسبة الرسوب الطبي، زمن الملء (time-to-fill)، تكلفة التعيين. يبني على hr_recruitment + manpower_requisition.</div></div>"""
S.append(("35_recruitment","التوظيف (ATS Pipeline)",shell("التوظيف","Employees › Recruitment › Pipeline",body)))

# 36 TRAINING ACADEMY
rows=[("السلامة HSE","إجباري","42 / 50","شهادة (سنة)","2 منتهية → محظور نشر","red"),
      ("تدريب أمني","إجباري للأمن","100 / 100","رخصة","ساري","green"),
      ("تشغيل معدات","حسب الدور","30 / 45","شهادة","قيد التدريب","amber"),
      ("خدمة عملاء","اختياري","18","—","—","slate")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge {('red' if 'إجباري' in r[1] and 'HSE' in r[0] else 'indigo' if 'إجباري' in r[1] else 'slate')}'>{r[1]}</span></td><td class='center'>{r[2]}</td><td>{r[3]}</td><td class='small'>{r[4]}</td></tr>" for r in rows])
body=f"""<div class='sub'>أكاديمية التدريب والشهادات — كورسات + جلسات + شهادات بانتهاء + تدريب إجباري شرط للنشر</div>
<div class='card' style='width:830px'><div class='ct'>الكورسات ومصفوفة الإجبارية</div>
<table><tr><th>الكورس</th><th>الإلزام</th><th class='center'>مكتمل/مطلوب</th><th>الناتج</th><th>ملاحظة</th></tr>{tr}</table>
<div class='warn'>⚠ 2 شهادات HSE منتهية → بوابة تمنع النشر حتى إعادة التدريب.</div></div>
<div class='card' style='width:330px'><div class='ct'>جلسة قادمة</div>
<div class='kv'><b>الكورس</b> HSE</div><div class='kv'><b>التاريخ</b> 2026-07-05</div><div class='kv'><b>المدرّب</b> Eng. Ali</div><div class='kv'><b>المسجّلون</b> 12</div>
<div class='idea'>💡 فجوة المهارة → تدريب آلي؛ انتهاء الشهادة → إعادة تدريب؛ يبني على employee_orientation/training + hr_skills.</div></div>"""
S.append(("36_training","أكاديمية التدريب والشهادات",shell("التدريب","Employees › Learning › Academy",body)))

# 37 INSURANCE & GOSI
body=f"""<div class='sub'>التأمين والتأمينات الاجتماعية (GOSI) — إلزامي بالكويت + يغذّي الراتب</div>
<div class='card' style='width:560px'><div class='ct'>التأمين الصحي</div>
<table><tr><th>العامل</th><th>الوثيقة</th><th class='center'>الفئة</th><th class='center'>تنتهي</th><th>الحالة</th></tr>
<tr><td>Bir Bahadur</td><td>POL-2231</td><td class='center'>C</td><td class='center'>2026-12</td><td><span class='badge green'>سارية</span></td></tr>
<tr><td>Ramesh</td><td>POL-2232</td><td class='center'>C</td><td class='center'>2026-07</td><td><span class='badge amber'>تجديد قريب</span></td></tr></table>
<div class='idea'>💡 انتهاء الوثيقة → تنبيه + تجديد؛ مطالبات مرتبطة بحوادث HSE.</div></div>
<div class='card' style='width:600px'><div class='ct'>التأمينات الاجتماعية (GOSI)</div>
<div class='kv'><b>التسجيل</b> رقم اشتراك لكل موظف</div>
<div class='kv'><b>الاشتراك الشهري</b> نسبة من الأجر (قابلة للضبط)</div>
{bar('حصة الشركة',60,'11.5%','bar')}{bar('حصة الموظف',40,'8%','b4')}
<div class='ok'>حصة الموظف = خصم تلقائي في Compensation Hub → قسيمة الراتب.</div></div>"""
S.append(("37_insurance","التأمين و GOSI",shell("التأمين والتأمينات","Employees › Payroll › Insurance & GOSI",body)))

# 38 EQUIPMENT / ASSET
rows=[("ماكينة تنظيف صناعية","EQ-104","Bir Bahadur","مشروع A","جيدة","صيانة 2026-08","green"),
      ("جهاز لاسلكي أمن","EQ-220","فريق أمن B","مشروع B","جيدة","—","green"),
      ("ماكينة جلي أرضيات","EQ-131","Gita Devi","مشروع A","تحتاج صيانة","متأخرة","amber")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td class='center'><span class='badge {r[6]}'>{r[4]}</span></td><td class='small'>{r[5]}</td></tr>" for r in rows])
body=f"""<div class='sub'>المعدات والأصول المخصّصة للعمال — معدات العقود + صيانة + إرجاع عند الإنهاء + تكلفة على المشروع</div>
<div class='card' style='width:830px'><div class='ct'>المعدات المخصّصة</div>
<table><tr><th>المعدة</th><th class='center'>الكود</th><th>المخصّص له</th><th>الموقع</th><th class='center'>الحالة</th><th>الصيانة</th></tr>{tr}</table>
<div class='warn'>⚠ صيانة EQ-131 متأخرة → تنبيه + جدولة.</div></div>
<div class='card' style='width:330px'><div class='ct'>التكلفة والإرجاع</div>
<div class='kv'><b>إهلاك/الشهر</b> على المشروع</div><div class='kv'><b>عند الإنهاء</b> إرجاع إلزامي (مع الزي)</div>
<div class='idea'>💡 يبني على care_asset؛ يربط معدات العقد (نوت 2) بالعامل/الموقع؛ صيانة + إرجاع في offboarding + تكلفة على P&L.</div></div>"""
S.append(("38_equipment","المعدات والأصول للعامل",shell("المعدات والأصول","Employees › Assets › Equipment",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
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
("34_hse","السلامة والحوادث (HSE) ⭐"),("35_recruitment","التوظيف (ATS) ⭐"),("36_training","أكاديمية التدريب والشهادات ⭐"),("37_insurance","التأمين و GOSI ⭐"),("38_equipment","المعدات والأصول للعامل ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
