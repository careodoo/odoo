# -*- coding: utf-8 -*-
"""Care HR — traffic violations (redesign+dashboard+payroll) + manager OT/allowance requests."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.tile{display:inline-block;vertical-align:top;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 9px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:20px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:6px 10px;font-size:12px;margin:3px 0;font-weight:bold}
.arr{color:#94a3b8;margin:0 3px;font-weight:bold}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
.fcard{display:inline-block;vertical-align:top;width:262px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:0 9px 9px 0}
.fcard .t{font-weight:bold;font-size:13px;margin-bottom:4px}.fcard .d{font-size:11.5px;color:#64748b;line-height:1.6}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(data):
    return "".join([f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in data])
def hbars(data,wmax=200):
    mx=max(v for _,v,_ in data) or 1; rows=""
    for l,v,c in data:
        rows+=f"<div style='margin:6px 0'><span style='display:inline-block;width:90px;font-size:11.5px'>{l}</span><span style='display:inline-block;width:{wmax}px;background:#eef2f7;border-radius:5px;vertical-align:middle'><span style='display:inline-block;height:13px;border-radius:5px;width:{int(v/mx*wmax)}px;background:{c}'></span></span><span style='font-size:11.5px;margin-right:6px'>{v}</span></div>"
    return rows
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])
S=[]

# 74 TRAFFIC VIOLATIONS
kp=[("مخالفات الشهر","42","#e25563"),("إجمالي المبلغ","1,260","#714B67"),("على السائق","780","#f59e0b"),
("تتحمّلها الشركة","480","#0ea5e9"),("قيد الخصم","9","#8b5cf6"),("مسدّدة للجهة","27","#21b07b")]
rows=[("VIO-0231","2026-06-12","ل/و 45-218","حسن (سائق)","تجاوز سرعة","20","السائق","طلب خصم → HR","amber"),
      ("VIO-0230","2026-06-10","ن/ر 12-880","علي","وقوف خاطئ","5","الشركة","سداد الجهة","blue"),
      ("VIO-0229","2026-06-08","ل/و 45-218","حسن","قطع إشارة","30","السائق","معتمد → خصم قسط 2/3","green"),
      ("VIO-0228","2026-06-03","س/ط 77-410","راج","حادث بسيط","45","قيد التحقيق","تحديد المسؤول","slate")]
tr="".join([f"<tr><td>{r[0]}</td><td class='small'>{r[1]}</td><td class='small'>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td class='center'>{r[5]}</td><td class='center'>{r[6]}</td><td class='center'><span class='badge {r[8]}'>{r[7]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>المخالفات المرورية — تصميم جديد + داشبورد · مدير السيارات يرفع طلب خصم إلى HR لينعكس في الرواتب (بدل موديول الاستوديو القديم)</div>
{tiles(kp)}
<div class='card' style='width:850px'><div class='ct'>سجل المخالفات</div>
<table><tr><th>المرجع</th><th>التاريخ</th><th>المركبة</th><th>السائق</th><th>النوع</th><th class='center'>المبلغ</th><th class='center'>المسؤول</th><th class='center'>الحالة</th></tr>{tr}</table></div>
<div class='card' style='width:320px'><div class='ct'>حسب السائق / النوع</div>{hbars([('حسن',50,'#e25563'),('راج',45,'#f59e0b'),('علي',5,'#0ea5e9')],150)}
<div style='height:6px'></div>{hbars([('سرعة',20,'#e25563'),('إشارة',30,'#f59e0b'),('وقوف',5,'#0ea5e9'),('حادث',45,'#8b5cf6')],150)}</div>
<div class='card' style='width:1170px'><div class='sec'>الإجراء + المعالجة في الرواتب</div>
{flow(['رصد المخالفة (مدير السيارات)','تحديد المسؤول: سائق/شركة','طلب خصم إلى HR','موافقة HR','خصم بالراتب (كامل/أقساط)','سطر VIOLATION + أيقونة','سداد الجهة وأرشفة'])}
<div class='cap'><b>⚙️ كيف يعمل:</b> مدير السيارات يسجّل المخالفة ويحدّد المسؤول؛ ما يخص السائق يُرفَع كطلب خصم إلى HR؛ بعد الاعتماد يظهر كسطر <b>VIOLATION</b> في القسيمة (كامل أو أقساط) بأيقونة مصدر قابلة للضغط (انظر شاشة 67)؛ وما تتحمّله الشركة يُسجَّل كمصروف ويُسوّى مع الجهة. كل ذلك بأثر كامل وربط بالمركبة والسائق.</div></div>"""
S.append(("74_violations","المخالفات المرورية + الداشبورد",shell("المخالفات المرورية","Employees › Fleet › Traffic Violations",body)))

# 75 MANAGER OT / ALLOWANCE REQUESTS
kp=[("طلبات معلّقة","14","#f59e0b"),("ساعات أوفر الشهر","1,860","#8b5cf6"),("كلفة الأوفر","31.2k","#017e84"),("بدلات مطلوبة","2.3k","#0ea5e9")]
rows=[("REQ-0142","مدير السيارات","حسن (سائق)","أوفر تايم 18 س","مشروع نقل ليلي","مدير الإدارة ⏳","amber"),
      ("REQ-0141","مدير النظافة","فريق مشروع A (12)","أوفر تايم جماعي 6 س","تغطية طارئة","معتمد → الرواتب","green"),
      ("REQ-0140","مدير السيارات","علي","بدل وجبة 15 (كاش)","مهمة خارجية","مدير الإدارة ✓ · إدارة عليا ⏳","amber"),
      ("REQ-0139","مدير الأمن","راج","أوفر تايم 10 س","تغطية وردية","مرفوض — تجاوز السقف","red")]
tr="".join([f"<tr><td>{r[0]}</td><td class='small'>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td class='small'>{r[4]}</td><td class='center'><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
ideas=[("⚙️ احتساب آلي للسعر","سعر ساعة الأوفر/البدل يُجلب من عقد الموظف وقواعد Odoo — لا إدخال يدوي."),
("📏 سقوف وضوابط","سقف شهري لساعات الأوفر لكل عامل/مشروع — تجاوزه يرفض أو يصعّد لإدارة عليا."),
("👥 طلب جماعي","أوفر تايم لفريق/وردية كاملة بضغطة واحدة بدل عامل عامل."),
("✅ ربط بالحضور الفعلي","التحقق أن ساعات الأوفر مغطّاة ببصمة فعلية قبل الاعتماد — لا أوفر وهمي."),
("💳 نوع الصرف","بدل داخل الراتب أو كاش منفصل (يرث منطق شاشة البدلات 64)."),
("🏗 ميزانية المشروع","خصم الأوفر/البدل من ميزانية المشروع وربطه بربحيته وفوترة العميل."),
("📱 طلب من الموبايل","المدير يرفع الطلب ويعتمد من تطبيق الموبايل فوراً."),
("🔁 بدل متكرر","بدل دوري (شهري) بموافقة واحدة بدل تكرار الطلب كل شهر.")]
ic="".join([f"<div class='fcard'><div class='t'>{t}</div><div class='d'>{d}</div></div>" for t,d in ideas])
body=f"""<div class='sub'>طلبات الأوفر تايم والبدلات — أي مدير (سيارات/إدارة) يطلب لأي سائق/عامل · مطوّر فوق موديول Overtime Requests الحالي · ينعكس في الرواتب</div>
{tiles(kp)}
<div class='card' style='width:980px'><div class='ct'>الطلبات</div>
<table><tr><th>المرجع</th><th>مقدّم الطلب</th><th>الموظف</th><th>النوع</th><th>السبب</th><th class='center'>الاعتماد</th></tr>{tr}</table>
<div class='warn'>⚠ يمرّ الطلب بمصفوفة الاعتماد (مدير الإدارة + إدارة عليا حسب النوع/القيمة — شاشة 70) ثم ينعكس كسطر OT/بدل في القسيمة بأيقونته.</div></div>
<div class='card' style='width:1170px'><div class='sec'>أفكار تطوير الموديول</div>{ic}</div>"""
S.append(("75_ot_requests","طلبات الأوفر تايم والبدلات",shell("طلبات الأوفر تايم","Employees › Payroll › OT & Allowance Requests",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("71_residency_dashboard","داشبورد الإقامات ⭐"),("72_payroll_dashboard","داشبورد الرواتب ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("73_coverage_monitor","مراقب تغطية الحضور ⭐"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
("66_payroll_routing","مسار وتقسيم الرواتب ⭐"),("67_payslip_icons","أيقونات المؤثّرات على السطر ⭐"),("75_ot_requests","طلبات الأوفر تايم والبدلات ⭐ جديد"),("74_violations","المخالفات المرورية + داشبورد ⭐ جديد"),("69_payroll_extras","أفكار إضافية في الرواتب ⭐"),
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
