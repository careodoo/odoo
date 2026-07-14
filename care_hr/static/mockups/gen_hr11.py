# -*- coding: utf-8 -*-
"""Care HR — social contracts (manpower files), process cycles, mega dashboard."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:6px 10px;font-size:12px;margin:3px 0;font-weight:bold}
.arr{color:#94a3b8;margin:0 3px;font-weight:bold}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
.tile{display:inline-block;vertical-align:top;width:148px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 9px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:21px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])
def bar(l,p,v,c="bar",w=150):
    return f"<div style='margin:5px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
S=[]

# 60 SOCIAL CONTRACTS / MANPOWER FILES
rows=[("ملف 12345","الهيئة العامة للقوى العاملة","نظافة","800","780","20","98%","2027-03","green"),
      ("ملف 22871","القوى العاملة","أمن","300","262","38","87%","2026-11","amber"),
      ("ملف 30912","الشؤون الاجتماعية","ضيافة","150","150","0","100%","2026-08","red"),
      ("ملف 41255","القوى العاملة","عام","500","410","90","82%","2027-06","green")]
tr="".join([f"<tr><td>{r[0]}</td><td class='small'>{r[1]}</td><td>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td class='center'>{r[5]}</td><td class='center'><span class='badge {r[8]}'>{r[6]}</span></td><td class='center'>{r[7]}</td></tr>" for r in rows])
body=f"""<div class='sub'>العقود الاجتماعية / ملفات القوى العاملة (PAM) — تُسجَّل عليها الإقامات وأذون العمل، ولكل ملف حصة تأشيرات</div>
<div class='card' style='width:830px'><div class='ct'>الملفات والحصص (Quota)</div>
<table><tr><th>الملف</th><th>الجهة</th><th>النشاط</th><th class='center'>الحصة</th><th class='center'>مستخدم</th><th class='center'>متاح</th><th class='center'>الإشغال</th><th class='center'>تجديد الملف</th></tr>{tr}
<tr style='background:#f8fafc'><td colspan='3'><b>الإجمالي</b></td><td class='center'><b>1,750</b></td><td class='center'>1,602</td><td class='center'>148</td><td class='center'>92%</td><td></td></tr></table>
<div class='warn'>⚠ ملف 30912 ممتلئ (100%) → لا تأشيرات متاحة · ملف 22871 يُجدّد قريباً.</div></div>
<div class='card' style='width:320px'><div class='ct'>إحصائيات (للداشبورد)</div>
<div class='kv'><b>عدد الملفات</b> 4</div><div class='kv'><b>إجمالي الحصة</b> 1,750</div><div class='kv'><b>متاح للاستقدام</b> 148</div>
{bar('الإشغال الكلي',92,'92%','bar',120)}
<div class='idea'>💡 الحصة المتاحة تقود تخطيط الاستقدام؛ كل إقامة/إذن مربوط بملف؛ تنبيه تجديد الملف وامتلاء الحصة.</div></div>"""
S.append(("60_social_contracts","العقود الاجتماعية (ملفات PAM)",shell("ملفات القوى العاملة","Employees › Compliance › Manpower Files",body)))

# 61 CYCLES 1 — LEAVES + RESIGNATION/EOS
body=f"""<div class='sub'>سيكلات احترافية — مع كابشن تعريفي للائحة والالتزامات وكيف يعمل النظام</div>
<div class='card' style='width:1170px'><div class='sec'>🌴 سيكل الإجازات</div>
{flow(['طلب الموظف','فحص الرصيد','موافقة المشرف','موافقة HR','اعتماد','خصم الرصيد','عند العودة: تسجيل عودة','تحديث/خصم تأخير'])}
<div class='cap'><b>📖 اللائحة:</b> إجازة سنوية 30 يوم/سنة (تُستحق بعد 9 أشهر) · مرضية متدرّجة (15 كامل ثم ¾ ثم ½ ثم ¼). <b>الالتزامات:</b> تُقدّم قبل X يوم · لا تتجاوز الرصيد إلا بموافقة. <b>⚙️ النظام:</b> رصيد آلي، تنبيه قبل الانتهاء، تسجيل العودة يكشف التأخّر ويخصمه.</div></div>
<div class='card' style='width:1170px'><div class='sec'>🚪 سيكل الاستقالة / إنهاء الخدمة</div>
{flow(['استقالة/إنهاء','موافقة HR','موافقة المالية','إخلاء طرف','مقابلة خروج','حساب EOS','إرجاع عُهد/سكن/زي','صرف نهائي','إلغاء كفالة/إقامة','أرشفة'])}
<div class='cap'><b>📖 اللائحة:</b> مكافأة نهاية الخدمة (15 يوم/سنة أول 5، شهر/سنة بعدها، سقف 1.5 سنة) + تدرّج الاستقالة. <b>الالتزامات:</b> مهلة إشعار · إخلاء طرف قبل الصرف · إلغاء الإقامة قانونياً. <b>⚙️ النظام:</b> مترابط ومُبوّب — مايتمش الصرف إلا بعد إخلاء الطرف، وEOS يُحسب آلياً.</div></div>"""
S.append(("61_cycles1","سيكلات: الإجازات + الاستقالة",shell("السيكلات","Employees › Process Cycles › Leaves & Offboarding",body)))

# 62 CYCLES 2 — RECRUITMENT/HIRING + PAYROLL
body=f"""<div class='sub'>سيكلات احترافية — الاستقدام/التعيين + الرواتب</div>
<div class='card' style='width:1170px'><div class='sec'>🧱 سيكل طلب الاستقدام والتعيين</div>
{flow(['طلب عمالة','موافقات','حجز تأشيرة على ملف القوى العاملة','استقدام (وكالة)','مرشّحون','مقابلة/عرض','كشف طبي','بصمة','إذن عمل','إقامة','تعيين/تأهيل','نشر'])}
<div class='cap'><b>📖 اللائحة:</b> التأشيرة تُفتح على ملف القوى العاملة ضمن الحصة المتاحة · شروط القطاع (حكومي يحتاج تصاريح). <b>الالتزامات:</b> كشف طبي وبصمة قبل الإذن · الإقامة قبل النشر. <b>⚙️ النظام:</b> الطلب يولّد التأشيرة تلقائياً، والامتثال بوابة للنشر.</div></div>
<div class='card' style='width:1170px'><div class='sec'>💰 سيكل الرواتب (مبني على Odoo payroll)</div>
{flow(['الحضور (بصمة)','تحويل لتايم شيت','اعتماد مدير العقد','حساب (قواعد Odoo)','فحوصات صارمة','تدقيق 1','تدقيق 2','اعتماد نهائي','WPS','قيد محاسبي','قفل الفترة'])}
<div class='cap'><b>📖 اللائحة:</b> الأجر ≥ الحد الأدنى · WPS إلزامي · GOSI. <b>الالتزامات:</b> تايم شيت معتمد · فصل المهام · لا صرف بمستند منتهٍ. <b>⚙️ النظام:</b> موظف الرواتب يختار الأساس (بصمة/تايم شيت/يدوي)، فحوصات قبلية + مراحل تدقيق + أثر لكل سطر.</div></div>"""
S.append(("62_cycles2","سيكلات: الاستقدام + الرواتب",shell("السيكلات","Employees › Process Cycles › Recruitment & Payroll",body)))

# 63 MEGA DASHBOARD
tiles=[("إجمالي الموظفين","2,418","#3a7afe"),("حاضر اليوم %","91%","#21b07b"),("في الاستقدام","73","#8b5cf6"),
("حصة تأشيرات متاحة","148","#0ea5e9"),("مستندات تنتهي ≤30ي","173","#f59e0b"),("محظور النشر","20","#e25563"),
("موافقات معلّقة","12","#f59e0b"),("تكلفة الرواتب","612k","#017e84"),("أوفر تايم (س)","4,820","#8b5cf6"),
("إشغال السكنات","86%","#0ea5e9"),("هامش العقود","22%","#21b07b"),("التزام EOS","1.84M","#714B67"),
("حوادث HSE (شهر)","3","#e25563"),("تسرّب %","9.5%","#f59e0b"),("استثناءات","56","#e25563"),("جودة البيانات","94%","#21b07b")]
tl="".join([f"<div class='tile'><div class='l'>{l}</div><div class='v'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in tiles])
body=f"""<div class='sub'>الداشبورد الشامل — كل ما صمّمناه في مكان واحد · دقيق · <b>كل جزء قابل للضغط لعرض بياناته</b> · محكوم بالصلاحيات</div>
{tl}
<div class='card' style='width:388px'><div class='ct'>القوى حسب القطاع</div>{bar('حكومي',100,'1,510','bar')}{bar('خاص/تجاري',62,'908','b2')}</div>
<div class='card' style='width:388px'><div class='ct'>قمع الاستقدام</div>{bar('وصول→نشر',26,'73→19','b6')}</div>
<div class='card' style='width:360px'><div class='ct'>الحضور (اتجاه)</div><svg width='330' height='60'><polyline points='5,45 60,38 115,40 170,28 225,32 280,22 325,26' style='fill:none;stroke:#21b07b;stroke-width:3'/></svg></div>
<div class='card' style='width:388px'><div class='ct'>الملفات والحصص</div>{bar('مستخدم',92,'1,602','b4')}{bar('متاح',8,'148','b3')}</div>
<div class='card' style='width:388px'><div class='ct'>أعلى المشاريع (هامش)</div>{bar('مشروع A',100,'30%','b3')}{bar('مشروع B',55,'14%','b4')}{bar('مشروع C',20,'-4%','b5')}</div>
<div class='card' style='width:360px'><div class='ct'>يحتاج انتباه</div><div style='font-size:12px;line-height:24px'><span class='badge red'>20</span> محظور · <span class='badge amber'>173</span> مستند ينتهي · <span class='badge amber'>56</span> استثناء</div></div>
<div class='idea' style='width:1170px'>💡 كل بطاقة/شريحة تفتح القائمة المفلترة وراءها؛ الشاشة الرئيسية للنظام؛ محكومة بالصلاحيات (كل دور يشوف المسموح).</div>"""
S.append(("63_mega_dashboard","الداشبورد الشامل (Executive)",shell("الداشبورد الشامل","Employees › Dashboard",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

NEW=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("60_social_contracts","العقود الاجتماعية (ملفات PAM) ⭐"),("61_cycles1","سيكلات: الإجازات + الاستقالة ⭐"),("62_cycles2","سيكلات: الاستقدام + الرواتب ⭐")]
import re
# load previous ALL by reading existing index titles is complex; rebuild from known full list + append NEW(minus dashboard which we put first)
PREV=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
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
("50_compliance_center","مركز قيادة الامتثال ⭐"),("51_ai_assistant","مساعد HR الذكي (AI) ⭐"),("52_client_billing","فوترة العميل من الحضور ⭐"),("53_eos_liability","التزام نهاية الخدمة ⭐"),("54_kiosk","كشك الخدمة الذاتية للعمال ⭐"),
("55_automation","محرّك الأتمتة والقواعد ⭐"),("56_exceptions","مركز الاستثناءات والتنبيهات ⭐"),("57_smart_approvals","موافقات ذكية + تصعيد ⭐"),("58_data_quality","مركز جودة البيانات ⭐"),("59_integrations","مركز التكاملات ⭐")]
ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐ جديد")]+PREV+[("60_social_contracts","العقود الاجتماعية (ملفات PAM) ⭐ جديد"),("61_cycles1","سيكلات: الإجازات + الاستقالة ⭐ جديد"),("62_cycles2","سيكلات: الاستقدام + الرواتب ⭐ جديد")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
