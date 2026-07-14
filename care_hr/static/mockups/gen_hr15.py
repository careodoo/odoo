# -*- coding: utf-8 -*-
"""Care HR — residency dashboard + payroll dashboard (stats/KPIs/charts)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.tile{display:inline-block;vertical-align:top;width:140px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 9px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:20px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.chart{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:13px;margin:0 9px 9px 0}
.chart .ct{font-weight:bold;font-size:13px;margin-bottom:9px}
.lg{font-size:11px;color:#475569;margin-top:6px}.lg i{display:inline-block;width:9px;height:9px;border-radius:2px;margin:0 3px}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(data):
    return "".join([f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in data])
def hbars(data,wmax=210):
    mx=max(v for _,v,_ in data) or 1
    rows=""
    for l,v,c in data:
        rows+=f"<div style='margin:6px 0'><span style='display:inline-block;width:96px;font-size:11.5px'>{l}</span><span style='display:inline-block;width:{wmax}px;background:#eef2f7;border-radius:5px;vertical-align:middle'><span style='display:inline-block;height:13px;border-radius:5px;width:{int(v/mx*wmax)}px;background:{c}'></span></span><span style='font-size:11.5px;margin-right:6px'>{v}</span></div>"
    return rows
def segbar(segs,w=300):
    tot=sum(v for _,v,_ in segs) or 1
    s="".join([f"<span style='display:inline-block;height:20px;width:{int(v/tot*w)}px;background:{c}'></span>" for _,v,c in segs])
    lg="".join([f"<span style='margin-left:9px'><i style='background:{c}'></i>{l} {v}</span>" for l,v,c in segs])
    return f"<div style='border-radius:6px;overflow:hidden;width:{w}px'>{s}</div><div class='lg'>{lg}</div>"
def line(pts,col,w=300,h=70):
    mx=max(pts) or 1; n=len(pts)
    coords=" ".join([f"{int(5+i*(w-10)/(n-1))},{int(h-5-(v/mx)*(h-15))}" for i,v in enumerate(pts)])
    return f"<svg width='{w}' height='{h}'><polyline points='{coords}' style='fill:none;stroke:{col};stroke-width:3'/></svg>"
S=[]

# 71 RESIDENCY / IQAMA DASHBOARD
kp=[("إجمالي الإقامات","2,418","#3a7afe"),("سارية","2,201","#21b07b"),("تنتهي ≤30ي","173","#f59e0b"),
("تنتهي ≤60ي","96","#f59e0b"),("منتهية","44","#e25563"),("قيد التجديد","61","#8b5cf6"),
("محظور النشر","20","#e25563"),("حصص متاحة","148","#0ea5e9"),("كلفة تجديد الشهر","18.6k","#017e84")]
body=f"""<div class='sub'>داشبورد الإقامات — كل الإحصائيات · كل بطاقة/شريحة قابلة للضغط لعرض القائمة وراءها</div>
{tiles(kp)}
<div class='chart' style='width:330px'><div class='ct'>حالة الإقامات</div>{segbar([('سارية',2201,'#21b07b'),('تنتهي',269,'#f59e0b'),('منتهية',44,'#e25563')],300)}</div>
<div class='chart' style='width:390px'><div class='ct'>انتهاءات الإقامات (6 أشهر)</div>{line([42,58,77,96,131,173],'#f59e0b',360)}<div class='lg'>يوليو→ديسمبر · تصاعدي = ضغط تجديد قادم</div></div>
<div class='chart' style='width:360px'><div class='ct'>الإقامات حسب الملف (الحصة)</div>{hbars([('12345',780,'#3a7afe'),('22871',262,'#0ea5e9'),('30912',150,'#e25563'),('41255',410,'#21b07b')],190)}</div>
<div class='chart' style='width:360px'><div class='ct'>حسب الجنسية</div>{hbars([('نيبال',980,'#3a7afe'),('بنغلاديش',760,'#8b5cf6'),('الهند',430,'#0ea5e9'),('أخرى',248,'#94a3b8')],190)}</div>
<div class='chart' style='width:430px'><div class='ct'>معاملات الإقامة حسب الحالة</div>{hbars([('جديدة',73,'#3a7afe'),('تجديد',61,'#8b5cf6'),('نقل كفالة',14,'#0ea5e9'),('إلغاء',9,'#e25563'),('مكتملة',512,'#21b07b')],240)}</div>
<div class='idea' style='width:1170px'>💡 المصدر: ملفات القوى العاملة + سجل الإقامات. تنبيهات 30/60 يوم، حظر النشر للمنتهي، وربط كل إقامة بملفها وحصتها. الضغط يفتح القائمة المفلترة.</div>"""
S.append(("71_residency_dashboard","داشبورد الإقامات",shell("داشبورد الإقامات","Employees › Dashboard › Residency",body)))

# 72 PAYROLL DASHBOARD
kp=[("كلفة الرواتب","612.4k","#017e84"),("عدد القسائم","2,392","#3a7afe"),("صافي مدفوع","548.1k","#21b07b"),
("البدلات","48.3k","#0ea5e9"),("أوفر تايم","31.2k","#8b5cf6"),("الخصومات","26.0k","#e25563"),
("التزام EOS","1.84M","#714B67"),("GOSI","27.4k","#f59e0b"),("متوسط الراتب","82.9","#3a7afe")]
body=f"""<div class='sub'>داشبورد الرواتب — كل الإحصائيات والمكوّنات · مبني على Odoo payroll · كل عنصر قابل للضغط</div>
{tiles(kp)}
<div class='chart' style='width:360px'><div class='ct'>مكوّنات كلفة الرواتب</div>{segbar([('أساسي',498,'#3a7afe'),('بدلات',48,'#0ea5e9'),('أوفر',31,'#8b5cf6'),('GOSI',27,'#f59e0b'),('خصومات-',26,'#e25563')],330)}</div>
<div class='chart' style='width:390px'><div class='ct'>اتجاه كلفة الرواتب (6 أشهر)</div>{line([561,574,588,596,605,612],'#017e84',360)}<div class='lg'>يناير→يونيو (بالألف د.ك) · نمو مع زيادة العمالة</div></div>
<div class='chart' style='width:380px'><div class='ct'>الرواتب حسب الإدارة</div>{hbars([('نظافة',286,'#3a7afe'),('أمن',158,'#0ea5e9'),('ضيافة',92,'#21b07b'),('سائقون',46,'#8b5cf6'),('إداري',30,'#94a3b8')],200)}</div>
<div class='chart' style='width:360px'><div class='ct'>الخصومات (تفصيل)</div>{hbars([('سلف',12.4,'#3730a3'),('غياب',7.1,'#94a3b8'),('جزاءات',3.2,'#e25563'),('أخرى',3.3,'#f59e0b')],190)}</div>
<div class='chart' style='width:410px'><div class='ct'>حالة تدقيق دفعات الرواتب</div>{segbar([('جاهز',1,'#21b07b'),('بالمالية',1,'#3a7afe'),('بالتدقيق',1,'#f59e0b'),('بـHR',1,'#94a3b8')],280)}
<div class='lg'>4 دفعات · كل دفعة بمرحلتها (انظر شاشة مسار الرواتب)</div></div>
<div class='chart' style='width:330px'><div class='ct'>WPS / GOSI</div><div class='kv'><b>WPS</b> <span class='badge green'>مُرسل ✓</span> 548.1k</div><div class='kv'><b>GOSI</b> <span class='badge amber'>مطابقة</span> 27.4k</div><div class='kv'><b>محظور صرف</b> <span class='badge red'>3 قسائم</span></div></div>
<div class='idea' style='width:1170px'>💡 يجمع: الأساسي/البدلات/الأوفر/الخصومات/الجزاءات/السلف/EOS/GOSI/WPS. الضغط على أي شريحة يفتح القسائم/السطور المعنية مع أيقونات المؤثّرات.</div>"""
S.append(("72_payroll_dashboard","داشبورد الرواتب",shell("داشبورد الرواتب","Employees › Dashboard › Payroll",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("71_residency_dashboard","داشبورد الإقامات ⭐ جديد"),("72_payroll_dashboard","داشبورد الرواتب ⭐ جديد"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
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
