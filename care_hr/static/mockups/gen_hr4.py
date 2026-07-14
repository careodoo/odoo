# -*- coding: utf-8 -*-
"""Care HR — loans/advances, bonus, resignation/offboarding, uniform. Rebuilds index."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=160):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
S=[]

# 30 LOANS & ADVANCES
inst="".join([f"<tr><td>القسط {i}</td><td class='center'>2026-{m:02d}</td><td class='right'>20.000</td><td class='center'>{'✔ مدفوع' if i<3 else '—'}</td></tr>" for i,m in enumerate([7,8,9,10,11,12],1)])
body=f"""<div class='sub'>السلف والأدفانس بايمنت — قرض بأقساط + سلفة راتب، الاسترداد آلي من الراتب (Compensation Hub)</div>
<div style='margin-bottom:10px'><span class='stage done'>طلب</span><span class='stage on'>اعتماد</span><span class='stage'>صرف</span><span class='stage'>استرداد بالأقساط</span></div>
<div class='card' style='width:600px'><div class='ct'>طلب قرض LOAN-0188 — Bir Bahadur</div>
<div class='kv'><b>نوع القرض</b> شخصي ▾ &nbsp; <b style='width:70px'>المبلغ</b> 120.000</div>
<div class='kv'><b>عدد الأقساط</b> 6 &nbsp; <b style='width:90px'>القسط/شهر</b> 20.000</div>
<table style='margin-top:6px'><tr><th>القسط</th><th class='center'>تاريخ</th><th class='right'>مبلغ</th><th class='center'>الحالة</th></tr>{inst}</table></div>
<div class='card' style='width:400px'><div class='ct'>سلفة راتب (Advance)</div>
<div class='kv'><b>المبلغ</b> 50.000</div><div class='kv'><b>الاسترداد</b> الراتب القادم</div>
<div class='warn'>سقف: لا يتجاوز 50% من الراتب — تحقق آلي.</div>
<div class='sec' style='margin-top:8px'>إجماليات</div>{bar('قروض قائمة',70,'KWD 8,400','bar')}{bar('استرداد هذا الشهر',40,'2,100','b3')}
<div class='ok'>كل استرداد سطر في Compensation Hub → خصم تلقائي بالراتب.</div></div>
<div class='idea' style='width:1170px'>💡 توحيد ohrms_loan + ent_ohrms_loan (نسخة واحدة)؛ أنواع قروض متعددة؛ فائدة اختيارية؛ سلفة باسترداد آلي؛ ربط محاسبي + Hub.</div>"""
S.append(("30_loans","السلف والأدفانس",shell("السلف والأدفانس","Employees › Payroll › Loans & Advances",body)))

# 31 BONUS
rows=[("Bir Bahadur","مبلغ","KWD 50","أداء متميز","معتمد","green"),("Gita Devi","أيام","3 أيام (×يومية)","عمل إضافي","مالية","amber"),("Ramesh","مبلغ","KWD 30","التزام","مدير الإدارة","blue")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='right'>{r[2]}</td><td>{r[3]}</td><td><span class='badge {r[5]}'>{r[4]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>البونص والمكافآت — اعتماد متعدّد المستويات ثم يغذّي الراتب (إصلاح الفجوة: حالياً يُعتمد ولا يُصرف)</div>
<div style='margin-bottom:10px'><span class='stage on'>مدير الإدارة</span><span class='stage'>HR</span><span class='stage'>المالية</span><span class='stage'>معتمد → الراتب</span></div>
<div class='card' style='width:760px'><div class='ct'>طلبات البونص</div>
<table><tr><th>الموظف</th><th>النوع</th><th class='right'>القيمة</th><th>السبب</th><th>الحالة</th></tr>{tr}</table>
<div class='ok'>عند الاعتماد النهائي → سطر «مكافأة» في Compensation Hub → يظهر في قسيمة الراتب.</div></div>
<div class='card' style='width:400px'><div class='ct'>قيمة اليوم (قابلة للضبط)</div>
<div class='kv'><b>الأساس</b> الأجر ÷ <span class='inp'>26</span> يوم</div>
<div class='warn'>كان ثابتاً wage/26 → بقى من الإعدادات.</div>
<div class='idea'>💡 بونص مرتبط بالأداء (آلي من KPIs)؛ سقف ميزانية؛ تتبّع في الشتر؛ يغذّي الراتب فعلياً.</div></div>"""
S.append(("31_bonus","البونص والمكافآت",shell("البونص والمكافآت","Employees › Payroll › Bonus",body)))

# 32 RESIGNATION & OFFBOARDING
items=[("استقالة/إنهاء خدمة","✔","green"),("موافقة HR","✔","green"),("موافقة المالية","●","amber"),
       ("إخلاء طرف (عُهد/أصول)","☐","slate"),("مقابلة خروج","☐","slate"),("تسوية نهاية الخدمة (EOS)","☐","slate"),
       ("إرجاع السكن + الزي","☐","slate"),("تذكرة السفر","☐","slate"),("الصرف النهائي + أرشفة","☐","slate"),("إلغاء الكفالة/الإقامة","☐","slate")]
li="".join([f"<div class='kv'><span class='badge {c}' style='width:22px;text-align:center'>{m}</span> {n}</div>" for n,m,c in items])
body=f"""<div class='sub'>الاستقالة وإنهاء الخدمة — offboarding مُنسّق ومترابط (مش خطوات منفصلة)</div>
<div class='card' style='width:560px'><div class='ct'>RES-0042 — Kamal · استقالة</div>
<div class='kv'><b>النوع</b> استقالة / إنهاء / وفاة</div><div class='kv'><b>آخر يوم عمل</b> 2026-07-15</div><div class='kv'><b>السبب</b> ...</div>
<div class='sec' style='margin-top:8px'>قائمة الإنهاء (Checklist مترابطة)</div>{li}</div>
<div class='card' style='width:600px'><div class='ct'>تسوية نهاية الخدمة (آلية)</div>
<table><tr><th>البند</th><th class='right'>القيمة</th></tr>
<tr><td>مكافأة نهاية الخدمة (قانون الكويت)</td><td class='right'>798.000</td></tr>
<tr><td>بدل رصيد الإجازة (18 ي)</td><td class='right'>108.000</td></tr>
<tr><td>تذكرة السفر</td><td class='right'>85.000</td></tr>
<tr><td>خصم: قرض متبقٍ</td><td class='right'>-60.000</td></tr>
<tr><td>خصم: عُهد غير مُرجعة</td><td class='right'>-15.000</td></tr>
<tr style='background:#f8fafc'><td><b>صافي المستحق النهائي</b></td><td class='right'><b>KWD 916.000</b></td></tr></table>
<div class='idea'>💡 مترابط ومُبوّب: إخلاء الطرف قبل الصرف؛ EOS آلي؛ إلغاء الكفالة/الإقامة؛ مسار الهروب؛ أرشفة الموظف. (يبني على nthub_hr_resignation + clearance + exit_interview + EOS).</div></div>"""
S.append(("32_offboarding","الاستقالة وإنهاء الخدمة",shell("إنهاء الخدمة","Employees › Offboarding › Resignation",body)))

# 33 UNIFORM ENHANCED
rows=[("Bir Bahadur","زي نظافة","3","2025-12 (صرف)","2026-06 (استبدال)","ساري","green"),
      ("Gita Devi","قفازات/حذاء","2","2026-01","2026-04","مستحق استبدال","amber"),
      ("فريق A (جماعي)","أطقم كاملة","31","2026-03","2026-09","ساري","green")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>الزي والمهمات (مطوّر) — دورة استبدال + إرجاع/تالف + مخزون + تكلفة على المشروع</div>
<div class='card' style='width:830px'><div class='ct'>صرف الزي/المهمات</div>
<table><tr><th>الموظف</th><th>الصنف</th><th class='center'>عدد</th><th class='center'>تاريخ الصرف</th><th class='center'>موعد الاستبدال</th><th>الحالة</th></tr>{tr}</table>
<div class='warn'>⚠ Gita: مستحقة استبدال → تنبيه آلي + طلب صرف جديد.</div></div>
<div class='card' style='width:320px'><div class='ct'>المخزون والتكلفة</div>
{bar('زي نظافة (مخزون)',30,'منخفض ⚠','b4')}{bar('قفازات',70,'كافٍ','b3')}
<div class='kv' style='margin-top:6px'><b>تكلفة الزي/الشهر</b> KWD 1,840</div><div class='kv'><b>تُحمّل على</b> المشروع</div>
<div class='idea'>💡 دورة حياة (صرف→استبدال→إرجاع/تالف)؛ ربط بالمخزون + تنبيه نفاد؛ صرف جماعي بتوقيع؛ توزيع التكلفة. (يبني على care_uniform_delivery).</div></div>"""
S.append(("33_uniform_plus","الزي والمهمات (مطوّر)",shell("الزي والمهمات","Employees › Welfare › Uniform & PPE",body)))

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
("30_loans","السلف والأدفانس ⭐"),("31_bonus","البونص والمكافآت ⭐"),("32_offboarding","الاستقالة وإنهاء الخدمة ⭐"),("33_uniform_plus","الزي والمهمات (مطوّر) ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
