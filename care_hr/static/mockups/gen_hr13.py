# -*- coding: utf-8 -*-
"""Care HR — payroll routing/split, line-impact icons, contract mgmt, extra ideas."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:6px 10px;font-size:12px;margin:3px 0;font-weight:bold}
.arr{color:#94a3b8;margin:0 3px;font-weight:bold}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
.ic{display:inline-block;font-size:10px;font-weight:bold;border-radius:6px;padding:2px 6px;margin:0 2px;cursor:pointer}
.pop{background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:10px 12px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.12);width:300px}
.fcard{display:inline-block;vertical-align:top;width:262px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:0 9px 9px 0}
.fcard .t{font-weight:bold;font-size:13px;margin-bottom:4px}.fcard .d{font-size:11.5px;color:#64748b;line-height:1.6}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])
S=[]

# 66 PAYROLL ROUTING & SPLIT
batch=[("B-06A","ملف الشؤون 12345 (نظافة)","780","معتمد HR","slate","→ التدقيق"),
       ("B-06B","إدارة الأمن","262","تحت التدقيق — أحمد","amber","المدقق"),
       ("B-06C","مشاريع 01–10 يونيو","410","تم التدقيق","blue","→ المالية"),
       ("B-06D","ضيافة + سائقون","166","اعتماد مالية نهائي","green","جاهز ✓")]
bt="".join([f"<tr><td>{b[0]}</td><td>{b[1]}</td><td class='center'>{b[2]}</td><td class='small'>{b[3]}</td><td class='center'><span class='badge {b[4]}'>{b[5]}</span></td></tr>" for b in batch])
body=f"""<div class='sub'>مسار اعتماد وتقسيم الرواتب — HR ينهي → تدقيق (المدقق من الإعدادات) → الإدارة المالية → ملف جاهز · يمكن الإرسال على دفعات</div>
<div class='card' style='width:1170px'><div class='sec'>المسار</div>
{flow(['HR يُنهي الحساب','إرسال للتدقيق','المدقق المعيَّن (إعدادات)','نتيجة التدقيق','الإدارة المالية','مراجعة نهائية','ملف الرواتب جاهز بالكامل'])}
<div class='cap'><b>⚙️ كيف يعمل:</b> يُحدَّد المدقق من الإعدادات (Routing Rules)؛ كل دفعة تمشي بالمسار مستقلة؛ لا تصل المالية إلا بعد التدقيق؛ والملف لا يُقفل إلا بعد الاعتماد المالي النهائي.</div></div>
<div class='card' style='width:640px'><div class='ct'>الدفعات (Batches)</div>
<table><tr><th>الدفعة</th><th>التقسيم</th><th class='center'>عدد</th><th>الحالة</th><th class='center'>المرحلة</th></tr>{bt}</table></div>
<div class='card' style='width:510px'><div class='ct'>خيارات التقسيم (Split)</div>
<div class='kv'><b>حسب ملفات الشؤون</b> دفعة لكل ملف قوى عاملة</div><div class='kv'><b>حسب الإدارات</b> أمن / نظافة / ضيافة …</div>
<div class='kv'><b>حسب التواريخ</b> فترة/نطاق أيام</div><div class='kv'><b>دفعات يدوية</b> اختيار موظفين</div>
<div class='idea'>💡 كل دفعة لها مدقق ومسار وحالة مستقلة → تدقيق متوازٍ وأسرع، والمالية تستلم جاهزاً جزءاً جزءاً.</div></div>"""
S.append(("66_payroll_routing","مسار وتقسيم الرواتب",shell("مسار الرواتب","Employees › Payroll › Routing & Approval",body)))

# 67 PAYSLIP LINE IMPACT ICONS
def ic(t,bg,fg): return f"<span class='ic' style='background:{bg};color:{fg}'>{t}</span>"
icons_legend=ic('جزاء','#fde2e2','#b91c1c')+ic('سلفة','#e0e7ff','#3730a3')+ic('بدل','#dcfce7','#15803d')+ic('o.t','#ede9fe','#6d28d9')+ic('تعديل','#fef3c7','#b45309')+ic('رجعي','#cffafe','#0e7490')
prows=[("BASIC أساسي","85.000","",""),
       ("HARDSHIP فرق طبيعة العمل","5.000",ic('بدل','#dcfce7','#15803d'),""),
       ("OT أوفر تايم","22.500",ic('o.t','#ede9fe','#6d28d9'),"4,820 مصدر: تايم شيت معتمد"),
       ("PENALTY جزاء (مشروع B)","-10.000",ic('جزاء','#fde2e2','#b91c1c'),"PEN-0231 نوم بالوردية · اعتمده HR"),
       ("LOAN قسط سلفة","-15.000",ic('سلفة','#e0e7ff','#3730a3'),"LN-088 قسط 3/12"),
       ("ADJ تعديل يدوي","-3.000",ic('تعديل','#fef3c7','#b45309'),"صحّحه: المدقق أحمد"),
       ("ARREARS مستحق رجعي","8.000",ic('رجعي','#cffafe','#0e7490'),"فرق مايو بأثر رجعي")]
pt="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[1]}</td><td class='center'>{r[2]}</td><td class='small'>{r[3]}</td></tr>" for r in prows])
body=f"""<div class='sub'>أيقونة في نهاية كل سطر تتأثّر بإجراء — المراجع/المدقق يضغطها ليرى مصدر التأثير والأثر الكامل</div>
<div class='card' style='width:760px'><div class='ct'>قسيمة — راج (أمن) · يونيو 2026</div>
<table><tr><th>السطر</th><th class='center'>القيمة</th><th class='center'>مؤثّر</th><th>تفاصيل عند الضغط</th></tr>{pt}
<tr style='background:#f8fafc'><td><b>الصافي</b></td><td class='center'><b>92.500</b></td><td colspan='2'></td></tr></table>
<div style='margin-top:8px'>الدليل: {icons_legend}</div></div>
<div class='card' style='width:330px'><div class='ct'>عند الضغط على ⚖ جزاء</div>
<div class='pop'><b>PEN-0231 — جزاء</b><br>المخالفة: نوم أثناء الوردية<br>المشروع: B — أمن · القيمة: 10 د<br>الإثبات: مرفق ✓ · اعتمده: HR (أحمد)<br>التاريخ: 2026-06-18<br><span class='small'>↪ فتح المصدر</span></div>
<div class='idea'>💡 كل سطر مؤثَّر يحمل أيقونته ومصدره (جزاء/سلفة/بدل/أوفر/تعديل/رجعي) → شفافية كاملة وتدقيق أسرع بلا بحث.</div></div>"""
S.append(("67_payslip_icons","أيقونات المؤثّرات على السطر",shell("مؤثّرات القسيمة","Employees › Payroll › Payslip Impacts",body)))

# 68 CONTRACT MANAGEMENT
def kol(t,items,c):
    its="".join([f"<div class='kc'>{i}</div>" for i in items])
    return f"<div class='kcol'><div class='kh' style='border-top:3px solid {c}'>{t}</div>{its}</div>"
CSS_extra="<style>.kcol{display:inline-block;vertical-align:top;width:262px;margin:0 8px 0 0}.kh{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:7px 10px;font-weight:bold;font-size:13px;margin-bottom:7px}.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:9px;font-size:12px;margin-bottom:7px;box-shadow:0 1px 3px rgba(0,0,0,.05)}</style>"
body=f"""{CSS_extra}<div class='sub'>إدارة عقود الموظفين — أدق وأسهل: أساسي/بدلات/مشروع/تواريخ + تجديد آلي + نُسخ تعديلات + إجراءات جماعية</div>
<div style='margin-bottom:10px'>
{kol('نشط',['سونام · 85 د · مشروع A<br><span class="small">حتى 2027-01 · بدل داخل الراتب</span>','راج · 90 د · أمن<br><span class="small">حتى 2026-12 · بدل كاش</span>'],'#21b07b')}
{kol('ينتهي ≤60 يوم',['بير · 100 د · ضيافة<br><span class="badge amber">تجديد خلال 41 يوم</span>'],'#f59e0b')}
{kol('تحت التجديد',['حسن · سائق<br><span class="small">نسخة تعديل: +5 بدل · بانتظار توقيع</span>'],'#3a7afe')}
{kol('منتهٍ/مؤرشف',['كومار · انتهى 2026-05<br><span class="small">مرتبط بإخلاء طرف</span>'],'#94a3b8')}
</div>
<div class='card' style='width:760px'><div class='ct'>تفاصيل العقد (نموذج)</div>
<div class='kv'><b>الأساسي</b> 85 · <b>طبيعة عمل</b> +5 · <b>بدل مواصلات</b> 10 (داخل الراتب)</div>
<div class='kv'><b>المشروع</b> A — نظافة · <b>ملف الشؤون</b> 12345 · <b>الإقامة</b> سارية حتى 2027-03</div>
<div class='kv'><b>المدة</b> 2025-01 → 2027-01 · <b>التجديد</b> آلي بتنبيه قبل 60 يوم</div>
<div class='kv'><b>النُسخ (Amendments)</b> v1 تعيين · v2 زيادة بدل (موثّقة بأثر وتاريخ)</div></div>
<div class='card' style='width:390px'><div class='ct'>إجراءات جماعية</div>
<div class='kv'>زيادة جماعية بنسبة/قيمة لمشروع</div><div class='kv'>تجديد دفعة عقود تنتهي</div><div class='kv'>نقل عقود بين مشاريع</div>
<div class='warn'>⚠ كل تعديل ينشئ نسخة موثّقة (من/متى/لماذا) وينعكس تلقائياً على قواعد الرواتب.</div></div>"""
S.append(("68_contracts","إدارة عقود الموظفين",shell("العقود","Employees › Contracts",body)))

# 69 MORE PAYROLL IDEAS
cards=[("📊 مقارنة بالشهر السابق","فرق كل بند مقابل الشهر الماضي مع تمييز القفزات الشاذة للمراجعة قبل الترحيل."),
("⏸ تعليق/حجز سطر","تعليق راتب موظف (مستند منتهٍ/خلاف) دون تعطيل الدفعة — يُصرف لاحقاً off-cycle."),
("🏦 توليد WPS وتقسيم البنوك","ملف WPS جاهز للبنك + تقسيم التحويلات حسب بنك كل عامل تلقائياً."),
("🔁 دورة خارج الجدول","Off-cycle run للتسويات والمستحقات الطارئة دون انتظار رواتب الشهر."),
("🧾 التسوية النهائية","ربط آلي بنهاية الخدمة: EOS + رصيد إجازات + عُهد + آخر راتب في مستند واحد."),
("⏪ مستحقات رجعية (Retro)","فروقات بأثر رجعي (زيادة/تصحيح) تُحسب وتُضاف كسطر ARREARS موثّق."),
("🏗 توزيع التكلفة على المشاريع","توزيع كلفة كل عامل على مشروعه → ربحية دقيقة وفوترة العميل."),
("👥 تفويض الاعتماد","تفويض مؤقت لصلاحية التدقيق/الاعتماد عند غياب المسؤول مع أثر كامل."),
("🛡 سجل GOSI والخصومات","سجل التأمينات والخصومات الحكومية ومطابقتها قبل الإقفال."),
("📅 تقويم الرواتب والأقفال","مواعيد الإنهاء/التدقيق/الصرف + قفل الفترة يمنع أي تعديل بعد الاعتماد."),
("🧪 محاكاة قبل الترحيل","Simulation: نتيجة الدفعة قبل الاعتماد لاكتشاف الأخطاء مبكراً."),
("📑 سجل التغييرات (Audit)","كل تعديل على أي سطر مسجّل (من/متى/قبل/بعد) — أثر لا يُمحى.")]
cc="".join([f"<div class='fcard'><div class='t'>{t}</div><div class='d'>{d}</div></div>" for t,d in cards])
body=f"""<div class='sub'>أفكار إضافية لإحكام ودقة نظام الرواتب — كلها فوق نواة Odoo payroll</div>{cc}
<div class='idea' style='width:1170px'>💡 مجتمعة تعطي: دقة (محاكاة/مقارنة/تدقيق)، مرونة (off-cycle/تعليق/تفويض)، وامتثال (WPS/GOSI/أقفال) — مع أثر كامل لكل حركة.</div>"""
S.append(("69_payroll_extras","أفكار إضافية في الرواتب",shell("أفكار الرواتب","Employees › Payroll › Advanced",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
("66_payroll_routing","مسار وتقسيم الرواتب ⭐ جديد"),("67_payslip_icons","أيقونات المؤثّرات على السطر ⭐ جديد"),("69_payroll_extras","أفكار إضافية في الرواتب ⭐ جديد"),
("68_contracts","إدارة عقود الموظفين ⭐ جديد"),
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
