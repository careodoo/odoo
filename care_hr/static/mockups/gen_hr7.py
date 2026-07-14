# -*- coding: utf-8 -*-
"""Care HR — enhanced employee kanban + filters. Rebuilds index."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.ecard{display:inline-block;vertical-align:top;width:282px;background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 1px 4px rgba(15,23,42,.06);padding:13px;margin:0 12px 12px 0}
.ecard.blocked{border:2px solid #ef4444}
.av{width:46px;height:46px;border-radius:50%;background:#e0e7ff;display:inline-block;text-align:center;line-height:46px;font-size:22px;vertical-align:middle}
.nm{display:inline-block;vertical-align:middle;margin-right:8px}.nm .n{font-weight:bold;font-size:14px}.nm .j{font-size:12px;color:#64748b}
.gr{float:left;width:24px;height:24px;border-radius:7px;text-align:center;line-height:24px;font-weight:bold;font-size:13px;color:#fff}
.pill{display:block;border-radius:8px;padding:5px 9px;font-size:12px;font-weight:bold;margin:8px 0 6px}
.p-in{background:#dcfce7;color:#166534}.p-out{background:#fee2e2;color:#991b1b}.p-leave{background:#dbeafe;color:#1e40af}.p-perm{background:#fef3c7;color:#92400e}.p-none{background:#f1f5f9;color:#64748b}
.hbar{background:#eef2f7;border-radius:6px;height:8px;margin:5px 0}.hbar > i{display:block;height:8px;border-radius:6px;background:#10b981}
.cdot{width:9px;height:9px;border-radius:50%;display:inline-block;margin:0 2px}
.qa{display:inline-block;width:30px;height:28px;line-height:28px;text-align:center;border:1px solid #e2e8f0;border-radius:7px;margin-top:7px;margin-left:4px;font-size:13px}
.fbar{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin-bottom:14px}
.fchip{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:18px;padding:5px 12px;font-size:12px;margin:3px;color:#334155}
.fchip.on{background:#4f46e5;color:#fff;border-color:#4f46e5;font-weight:bold}
.fsel{display:inline-block;border:1px solid #cbd5e1;border-radius:8px;padding:6px 12px;font-size:12px;background:#fbfdff;margin:3px}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""

def card(name,job,nat,flag,proj,grade,gcol,pcls,ptxt,hours,comp,blocked=False,extra=""):
    hp=int(hours/8*100)
    cdots="".join([f"<span class='cdot' style='background:{c}'></span>{l}&nbsp;" for l,c in comp])
    qa="".join([f"<span class='qa'>{x}</span>" for x in ['📞','💬','👤','📋']])
    rib=f"<div style='font-size:11px;color:#92400e;background:#fef3c7;border-radius:6px;padding:2px 7px;display:inline-block;margin-bottom:5px'>{extra}</div>" if extra else ""
    return f"""<div class='ecard {'blocked' if blocked else ''}'>
<div class='gr' style='background:{gcol}'>{grade}</div>
<div class='av'>👷</div><div class='nm'><div class='n'>{name}</div><div class='j'>{job} · {flag} {nat}</div></div>
{rib}
<div class='small' style='margin-top:6px'>📍 {proj}</div>
<div class='pill {pcls}'>{ptxt}</div>
<div class='small'>ساعات اليوم {hours}/8</div><div class='hbar'><i style='width:{hp}%'></i></div>
<div class='small' style='margin-top:5px'>الامتثال: {cdots}</div>
<div>{qa}</div></div>"""

g=("green","#16a34a");a=("amber","#f59e0b");c=("slate","#64748b")
G={'A':'#16a34a','B':'#0ea5e9','C':'#64748b'}
COK=[('إقامة','#16a34a'),('إذن','#16a34a'),('HSE','#16a34a')]
CWARN=[('إقامة','#16a34a'),('إذن','#f59e0b'),('HSE','#16a34a')]
CBAD=[('إقامة','#ef4444'),('إذن','#16a34a'),('HSE','#f59e0b')]

filters=f"""<div class='fbar'>
<input class='fsel' style='min-width:240px' value='🔎 بحث: اسم / كود / إقامة / جواز'/>
<span class='fsel'>القطاع: حكومي ▾</span><span class='fsel'>الإدارة ▾</span><span class='fsel'>المشروع/الموقع ▾</span><span class='fsel'>الوظيفة ▾</span><span class='fsel'>الجنسية ▾</span><span class='fsel'>التصنيف ▾</span><span class='fsel'>الوكالة ▾</span>
<span class='fsel'>تجميع حسب ▾</span>
<div style='margin-top:6px'>
<span class='fchip on'>● حاضر الآن</span><span class='fchip'>غائب</span><span class='fchip'>في إجازة</span><span class='fchip'>إذن</span><span class='fchip'>لم يبصم</span><span class='fchip'>إقامة تنتهي ≤30ي</span><span class='fchip'>محظور النشر</span><span class='fchip'>تحت التجربة</span><span class='fchip'>تصنيف A</span><span class='fchip'>موقوف</span></div>
<div style='float:left;margin-top:-22px'><span class='fsel'>▦ كانبان</span><span class='fsel'>≣ قائمة</span><span class='fsel'>🗺️ خريطة</span><span class='small'>2,418 موظف</span></div></div>"""

cards=(
 card("Bir Bahadur","عامل نظافة","نيبال","🇳🇵","مشروع A · وزارة الصحة","A",G['A'],"p-in","● حاضر · منذ 06:58 · موقع A",6.5,COK)+
 card("Gita Devi","عاملة نظافة","بنجلاديش","🇧🇩","مشروع A · مبنى الإدارة","B",G['B'],"p-perm","⏱️ إذن · يعود 11:00",3.0,CWARN)+
 card("Ramesh","عامل عام","الهند","🇮🇳","مشروع B · بنك الخليج","C",G['C'],"p-out","✖ غائب اليوم",0.0,COK,extra="إنذار سابق")+
 card("Sunil","فني","نيبال","🇳🇵","مشروع C","B",G['B'],"p-leave","🌴 إجازة · حتى 2026-07-10",0.0,COK)+
 card("Anil","حارس أمن","الهند","🇮🇳","مشروع D · موقع حساس","A",G['A'],"p-in","● حاضر · منذ 22:00 · وردية ليل",8.0,COK)+
 card("Kamal","عامل","بنجلاديش","🇧🇩","غير منشور (Pool)","C",G['C'],"p-none","⚠ لم يبصم · إقامة منتهية",0.0,CBAD,blocked=True,extra="محظور النشر")
)
body=f"<div class='sub'>عرض الموظفين المطوّر — كارت غني + مؤشر حضور ذكي + فلاتر أكثر (أداء عالٍ: حالة الحضور حقل مخزّن يتحدّث عند البصمة)</div>{filters}{cards}<div class='idea' style='width:1170px'>💡 مؤشر الحضور يوضّح: حاضر/غائب/إجازة/إذن/لم يبصم + الوقت + الموقع + ساعات اليوم؛ إشارات امتثال (إقامة/إذن/HSE)؛ إطار أحمر للمحظور؛ أزرار سريعة؛ فلاتر وchips غنية + خريطة. الأداء: presence_state مخزّن + صور lazy + pagination.</div>"
S=[("45_employee_kanban","عرض الموظفين (كانبان مطوّر)",shell("الموظفون","Employees › Directory",body))]

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐ جديد"),("03_mobilization","رحلة الاستقدام والتأهيل"),
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
