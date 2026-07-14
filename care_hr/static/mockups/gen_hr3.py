# -*- coding: utf-8 -*-
"""Care HR — more mockup screens (gov custody + performance/skills). Rebuilds index."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(title,crumb,body):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{crumb}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{title}</div>{body}</div></body></html>"""
def bar(l,p,v,c="bar",w=160):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
S=[]

# 28 GOVERNMENT EXPENSES & CUSTODY
wrows=[("Bir Bahadur","12.000","8.000","20.000","2026-09-01 ✓ (محدّث)","green"),
       ("Ramesh","12.000","8.000","20.000","2027-06-30 ✓ (محدّث)","green"),
       ("Kamal","12.000","8.000","20.000","بانتظار المستند","amber")]
tr="".join([f"<tr><td>{r[0]}</td><td class='right'>{r[1]}</td><td class='right'>{r[2]}</td><td class='right'>{r[3]}</td><td><span class='badge {r[5]}'>{r[4]}</span></td></tr>" for r in wrows])
body=f"""<div class='sub'>المصروفات الحكومية وتسوية العُهد — اختيار العمال → إجراء → مبلغ آلي → صرف → تسوية تحدّث الإقامات</div>
<div style='margin-bottom:10px'><span class='stage done'>طلب صرف</span><span class='stage done'>اعتماد</span><span class='stage on'>صرف (عهدة المندوب)</span><span class='stage'>تسوية بالمستندات</span></div>
<div class='card' style='width:760px'><div class='ct'>طلب صرف EXP-0231 — تجديد إقامة (دفعة 3 عمال)</div>
<div class='kv'><b>الإجراء</b> تجديد إقامة ▾ (الرسم من الإعدادات)</div>
<table style='margin-top:6px'><tr><th>العامل</th><th class='right'>رسم حكومي</th><th class='right'>رسم خدمة</th><th class='right'>الإجمالي</th><th>الإقامة بعد التسوية</th></tr>{tr}
<tr style='background:#f8fafc'><td><b>الإجمالي</b></td><td class='right'>36.000</td><td class='right'>24.000</td><td class='right'><b>60.000</b></td><td></td></tr></table>
<div style='margin-top:8px'><span class='btn'>🖨️ طباعة طلب الصرف</span><span class='btn'>🖨️ طباعة الإقامات</span></div></div>
<div class='card' style='width:400px'><div class='ct'>العهدة والمندوب</div>
<div class='kv'><b>المندوب</b> Khaled (مندوب حكومي)</div><div class='kv'><b>عهدة مصروفة</b> KWD 60.000</div><div class='kv'><b>مُسوّى</b> 40.000 (عاملين)</div><div class='kv'><b>متبقّي مفتوح</b> 20.000</div>
<div class='warn'>تسوية Kamal معلّقة → العهدة لا تُقفل + تنبيه تقادم.</div>
<div class='ok' style='margin-top:6px'>عند إرفاق الإقامة الجديدة: تاريخ الانتهاء يتحدّث آلياً + المستند يُحفظ + يدخل السجل التاريخي.</div></div>
<div class='idea' style='width:1170px'>💡 ربط محاسبي (عهدة→مصروف على مركز تكلفة المشروع)؛ توزيع رسوم الإقامة على التكلفة المحمّلة للعامل (P&L)؛ معالجة بالدفعات؛ OCR لتاريخ الإقامة؛ مهل قانونية + تنبيهات.</div>"""
S.append(("28_gov_custody","المصروفات الحكومية وتسوية العُهد",shell("المصروفات الحكومية والعُهد","Employees › Admin › Gov Expenses & Custody",body)))

# 29 PERFORMANCE & SKILLS (enhanced)
srows=[("تشغيل معدات ثقيلة","3","4","تدريب","amber","—"),
       ("مناولة كيماويات","4","4","مطابق","green","شهادة سارية"),
       ("السلامة HSE","2","4","حرج","red","منتهية → محظور النشر"),
       ("خدمة عملاء","4","3","ممتاز","green","—")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'><span class='badge {r[4]}'>{r[3]}</span></td><td class='small'>{r[5]}</td></tr>" for r in srows])
phone=f"""<div class='phone' style='width:250px'><div class='screen' style='min-height:300px'>
<div style='font-weight:bold;color:#0b1220'>تقييم سريع — بعد الوردية</div>
<div style='background:#fff;border-radius:10px;margin-top:8px;padding:10px;font-size:12px;line-height:26px'>
العامل: Bir Bahadur<br>الالتزام ★★★★☆<br>الجودة ★★★★★<br>السلوك ★★★★☆<br>الحضور ★★★★★</div>
<div style='margin-top:8px;background:#16a34a;color:#fff;border-radius:10px;padding:10px;text-align:center;font-weight:bold'>حفظ التقييم</div>
<div class='small' style='margin-top:6px'>يبني درجة أداء متجدّدة لكل عامل.</div></div></div>"""
body=f"""<div class='sub'>الأداء والمهارات (تطوير hr_skills) — مصفوفة مهارات + شهادات + تقييم 360 + تقييم المشرف السريع</div>
<div class='card' style='width:600px'><div class='ct'>مصفوفة مهارات — Bir Bahadur (عامل نظافة)</div>
<table><tr><th>المهارة</th><th class='center'>الحالي</th><th class='center'>المطلوب</th><th class='center'>الحالة</th><th>الشهادة</th></tr>{tr}</table>
<div class='warn'>⚠ HSE منتهية → بوابة تمنع النشر حتى التجديد + خطة تدريب تلقائية.</div></div>
<div class='card' style='width:330px'><div class='ct'>تقييم 360°</div>
{bar('المدير',90,'4.5','bar')}{bar('الزملاء',82,'4.1','b2')}{bar('تقييم ذاتي',78,'3.9','b4')}{bar('العميل (بوابة)',86,'4.3','b3')}
<div class='kv' style='margin-top:4px'><b>الدرجة المركّبة</b> 4.2/5 <span class='badge green'>عالٍ</span></div>
<div class='kv'><b>أهلية النشر</b> <span class='badge indigo'>عملاء مميّزون</span></div></div>
{phone}
<div class='idea' style='width:900px'>💡 KPIs خدمية (انتظام/شكاوى/حوادث/مهام) → درجة مركّبة؛ الأداء يقود المكافأة/الإنذار/التثبيت/مراجعة الراتب/أهلية النشر؛ تنبّؤ بالخطر؛ تطابق المهارة بالموقع.</div>"""
S.append(("29_performance_plus","الأداء والمهارات (مطوّر)",shell("الأداء والمهارات","Employees › Performance › Skills & Appraisal",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("07_overtime_rules","قواعد الأوفر تايم وساعات العمل"),("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)"),("09_eos","حاسبة نهاية الخدمة (قانون الكويت)"),
("10_payroll","الرواتب + Compensation Hub"),("11_documents","مركز انتهاء المستندات"),("12_discipline","الانضباط والقانوني"),
("13_housing","السكن (Hostel)"),("14_uniform_transport","الزي والمواصلات"),("15_performance","الأداء والمهارات (أساسي)"),
("16_access","شجرة الصلاحيات (Access Profiles)"),("17_reports","مركز التقارير"),
("18_profitability","ربحية العقد/المشروع (P&L) ⭐"),("19_workforce_planning","تخطيط القوى العاملة والإحلال ⭐"),
("20_sponsorship","امتثال العمالة المكفولة ⭐"),("21_sla_client","SLA وبوابة العميل"),("22_roster","جدولة الورديات + الاحتياطي"),
("23_agency","أداء وكالات الاستقدام"),("24_probation","محرّك فترة التجربة (مقترح موظفين)"),("25_letters","مركز الخطابات والشهادات (مقترح موظفين)"),
("26_movement","سجل حركة الموظف الداخلية (مقترح موظفين)"),("27_attrition","تحليل التسرّب (Attrition)"),
("28_gov_custody","المصروفات الحكومية وتسوية العُهد ⭐"),("29_performance_plus","الأداء والمهارات (مطوّر) ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
