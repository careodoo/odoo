# -*- coding: utf-8 -*-
"""Care HR — administrative gap screens: site/security permits, PRO/gov transactions,
grievances, custody register, accommodation ops, expense claims, DMS, announcements."""
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
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(data):
    return "".join([f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in data])
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])
def tbl(head,rows):
    h="".join([f"<th class='center'>{x}</th>" if i else f"<th>{x}</th>" for i,x in enumerate(head)])
    r=""
    for row in rows:
        cells=""
        for i,c in enumerate(row):
            if isinstance(c,tuple): cells+=f"<td class='center'><span class='badge {c[1]}'>{c[0]}</span></td>"
            elif i==0: cells+=f"<td>{c}</td>"
            else: cells+=f"<td class='center'>{c}</td>"
        r+=f"<tr>{cells}</tr>"
    return f"<table><tr>{h}</tr>{r}</table>"
S=[]

# 84 SITE ACCESS & SECURITY PERMITS
body=f"""<div class='sub'>تصاريح المواقع والتصاريح الأمنية — للمواقع الحكومية/الحساسة (دفاع/جهات سيادية) · لا تمركز لعامل بلا تصريح ساري</div>
{tiles([('تصاريح سارية','412','#21b07b'),('قيد الفحص الأمني','37','#f59e0b'),('تنتهي ≤30ي','21','#f59e0b'),('مرفوض/موقوف','5','#e25563'),('مواقع مؤمّنة','9','#3a7afe')])}
<div class='card' style='width:840px'><div class='ct'>التصاريح</div>
{tbl(['العامل','الموقع/الجهة','نوع التصريح','الفحص الأمني','الانتهاء','الحالة'],[
['راج (أمن)','معسكر — جهة سيادية','تصريح دخول أمني',('مجتاز','green'),'2026-11',('ساري','green')],
['سونام (نظافة)','وزارة — مبنى حكومي','تصريح موقع',('قيد الفحص','amber'),'—',('معلّق','amber')],
['علي (سائق)','ميناء — منطقة مقيّدة','تصريح مركبة+سائق',('مجتاز','green'),'2026-07',('ينتهي قريباً','amber')],
['بير (ضيافة)','منشأة حساسة','تصريح أمني',('مرفوض','red'),'—',('بديل مطلوب','red')]])}</div>
<div class='card' style='width:390px'><div class='ct'>الإجراء + الربط</div>
{flow(['طلب','فحص أمني','موافقة الجهة','إصدار','تجديد'])}
<div class='warn'>⚠ يربط <b>تمركز العمال (41)</b>: النظام يمنع نشر عامل في موقع مؤمّن دون تصريح ساري، وينبّه قبل انتهاء التصريح ويقترح بديلاً.</div></div>"""
S.append(("84_site_permits","تصاريح المواقع والأمن",shell("تصاريح المواقع","Employees › Compliance › Site & Security Permits",body)))

# 85 PRO / GOV TRANSACTIONS TRACKER
body=f"""<div class='sub'>متابعة المعاملات الحكومية (المندوب/PRO) — لوحة تشغيلية لكل معاملة: الحالة، المسؤول، الرسوم، الموعد النهائي و SLA</div>
{tiles([('معاملات جارية','58','#3a7afe'),('متأخرة عن SLA','6','#e25563'),('منجزة هذا الشهر','143','#21b07b'),('رسوم قيد الصرف','3.4k','#714B67'),('مناديب','5','#0ea5e9')])}
<div class='card' style='width:900px'><div class='ct'>المعاملات</div>
{tbl(['المرجع','نوع المعاملة','المندوب','الرسوم','الموعد','الحالة'],[
['TX-5521','تجديد إقامة','أبو محمد','12.000','2026-06-28',('قيد الإنجاز','amber')],
['TX-5520','إذن عمل جديد','سعيد','—','2026-07-02',('بانتظار مستند','slate')],
['TX-5519','توثيق عقد — القوى العاملة','أبو محمد','5.000','2026-06-20',('متأخرة','red')],
['TX-5518','تجديد بطاقة (PACI)','ناصر','3.000','2026-06-25',('منجزة','green')]])}</div>
<div class='card' style='width:330px'><div class='ct'>كيف يعمل</div>
<div class='cap'><b>⚙️</b> كل معاملة لها نوع، مندوب مسؤول، رسوم، ومؤقّت SLA يصعّد عند التأخّر. يربط الإقامات (39) والمراسلات (83) والعُهد المالية (28). لوحة لكل مندوب بعبئه وإنجازه.</div></div>"""
S.append(("85_pro_tracker","متابعة المعاملات الحكومية",shell("معاملات المندوب","Employees › Documents › Gov Transactions (PRO)",body)))

# 86 GRIEVANCES & COMPLAINTS
body=f"""<div class='sub'>التظلّمات والشكاوى — قناة رسمية للعامل (موبايل/هاتف/شخصي) مع SLA وتحقيق وحل موثّق</div>
{tiles([('مفتوحة','19','#f59e0b'),('متأخرة SLA','3','#e25563'),('حُلّت هذا الشهر','64','#21b07b'),('رضا الحل','88%','#3a7afe'),('متكرّرة (نمط)','نمطان','#8b5cf6')])}
<div class='card' style='width:840px'><div class='ct'>الشكاوى</div>
{tbl(['المرجع','مقدّمها','الفئة','القناة','SLA','الحالة'],[
['GRV-231','سونام','تأخّر صرف بدل','موبايل','خلال المدة',('قيد التحقيق','amber')],
['GRV-230','راج','مشكلة سكن','هاتف','متأخرة',('تصعيد','red')],
['GRV-229','علي','معاملة المشرف','شخصي','خلال المدة',('قيد الحل','blue')],
['GRV-228','بير','استفسار راتب','كشك','—',('مغلقة — مُرضٍ','green')]])}</div>
<div class='card' style='width:390px'><div class='ct'>الإجراء</div>
{flow(['تقديم','فرز وتصنيف','تحقيق','حل','إغلاق + قياس الرضا'])}
<div class='cap'><b>⚙️</b> كل شكوى بمؤقّت SLA وتصعيد للإدارة عند التأخّر؛ تحليل الأنماط المتكرّرة يكشف مشاكل جذرية (سكن/أجور/مشرف) لمعالجتها وقائياً. يربط الكشك (54) والموبايل (80).</div></div>"""
S.append(("86_grievances","التظلّمات والشكاوى",shell("التظلّمات","Employees › Employee Relations › Grievances",body)))

# 87 CUSTODY & HANDOVER REGISTER
body=f"""<div class='sub'>سجل العُهد والتسليم/الاستلام — هويات، شرائح اتصال، بطاقات دخول، أدوات، أجهزة · بتوقيع وحالة وربط بإخلاء الطرف</div>
{tiles([('عُهد مسلّمة','1,840','#3a7afe'),('غير مُعادة','73','#f59e0b'),('تالفة/مفقودة','12','#e25563'),('قيد التسوية','9','#8b5cf6'),('أنواع العُهد','11','#0ea5e9')])}
<div class='card' style='width:840px'><div class='ct'>العُهد</div>
{tbl(['الكود','العامل','العُهدة','تاريخ التسليم','الحالة','الإجراء'],[
['CST-901','حسن','شريحة اتصال + هاتف','2025-03-04',('بحوزته','blue'),'—'],
['CST-900','كومار','بطاقة دخول + أدوات','2025-01-10',('غير مُعادة','amber'),'مطالبة عند الإخلاء'],
['CST-899','راج','هوية شركة','2024-11-20',('مفقودة','red'),'بدل فاقد + جزاء'],
['CST-898','سونام','زي + معدات','2025-05-02',('مُعادة','green'),'مغلقة']])}</div>
<div class='card' style='width:390px'><div class='ct'>الربط</div>
<div class='warn'>⚠ لا يُغلق <b>إخلاء الطرف (32)</b> ولا يُصرف المستحق النهائي قبل إعادة كل العُهد أو تسوية قيمتها. يوحّد الزي (33) والمعدات (38) في سجل واحد بتوقيع استلام/إعادة.</div></div>"""
S.append(("87_custody","سجل العُهد والتسليم",shell("العُهد والتسليم","Employees › Admin › Custody Register",body)))

# 88 ACCOMMODATION OPERATIONS
body=f"""<div class='sub'>تشغيل سكن العمال — توزيع الغرف والإشغال والتفتيش والصيانة والإعاشة (تشغيلي، بخلاف التكلفة في 13)</div>
{tiles([('مبانٍ','14','#3a7afe'),('غرف','312','#0ea5e9'),('نسبة الإشغال','86%','#21b07b'),('تفتيش مستحق','4','#f59e0b'),('طلبات صيانة','11','#e25563')])}
<div class='card' style='width:840px'><div class='ct'>المباني والإشغال</div>
{tbl(['المبنى','المنطقة','السعة','مشغول','إشغال','الحالة'],[
['سكن A','جليب','120','116','97%',('تفتيش مستحق','amber')],
['سكن B','الفروانية','90','71','79%',('سليم','green')],
['سكن C','الأحمدي','102','82','80%',('صيانة مفتوحة','red')]])}</div>
<div class='card' style='width:390px'><div class='ct'>التشغيل</div>
<div class='kv'>🛏 توزيع الغرف وربط العامل بسريره</div><div class='kv'>🧹 جدول التفتيش والنظافة (checklist)</div><div class='kv'>🔧 طلبات الصيانة وتتبّعها</div><div class='kv'>🍽 الإعاشة/الوجبات إن وُجدت</div>
<div class='idea'>💡 يربط تكلفة السكن (13) لكل عامل، ويكشف الغرف الشاغرة لاستقبال الدُفعات الجديدة من الاستقدام (3).</div></div>"""
S.append(("88_accommodation","تشغيل سكن العمال",shell("تشغيل السكن","Employees › Welfare › Accommodation Ops",body)))

# 89 EXPENSE CLAIMS / PETTY CASH
body=f"""<div class='sub'>مطالبات المصروفات والنثريات — استرداد مصروفات الموظفين + عُهد نقدية للمسؤولين (بخلاف الرسوم الحكومية في 28)</div>
{tiles([('مطالبات معلّقة','17','#f59e0b'),('قيمة قيد الاعتماد','1.9k','#714B67'),('مردودة هذا الشهر','142','#21b07b'),('عُهد نقدية','6','#0ea5e9'),('قيد التسوية','3','#8b5cf6')])}
<div class='card' style='width:840px'><div class='ct'>المطالبات</div>
{tbl(['المرجع','الموظف','النوع','القيمة','الإيصال','الحالة'],[
['EXP-441','مشرف A','مواصلات مهمة','8.500',('مرفق','green'),('مدير الإدارة ⏳','amber')],
['EXP-440','مندوب','رسوم متفرقة','15.000',('مرفق','green'),('معتمد → صرف','green')],
['EXP-439','مشرف B','أدوات طارئة','22.000',('ناقص','red'),('مرتجع','red')]])}</div>
<div class='card' style='width:390px'><div class='ct'>المعالجة</div>
{flow(['مطالبة + إيصال','اعتماد المدير','المالية','رد عبر الراتب/كاش','تسوية العُهدة'])}
<div class='cap'><b>⚙️</b> الرد إمّا كسطر في الراتب أو صرف كاش؛ كل عُهدة نقدية لها رصيد يُسوّى بالمطالبات؛ يرث مصفوفة الاعتماد ويُؤرشَف بالإيصالات.</div></div>"""
S.append(("89_expense_claims","المطالبات والنثريات",shell("المطالبات والنثريات","Employees › Admin › Expense Claims & Petty Cash",body)))

# 90 DOCUMENT MANAGEMENT & RETENTION
body=f"""<div class='sub'>إدارة الوثائق والأرشفة — مستودع مركزي مصنّف، نُسخ، صلاحيات وصول، وسياسة احتفاظ/إتلاف (يعمّق مركز الانتهاء 11)</div>
{tiles([('إجمالي الوثائق','48,210','#3a7afe'),('مصنّفة','97%','#21b07b'),('تنتهي ≤30ي','173','#f59e0b'),('للإتلاف (انتهت المدة)','62','#64748b'),('تحت حجز قانوني','14','#e25563')])}
<div class='card' style='width:840px'><div class='ct'>التصنيفات وسياسة الاحتفاظ</div>
{tbl(['التصنيف','العدد','مدة الاحتفاظ','صلاحية الوصول','الحالة'],[
['عقود وملفات الموظفين','12,400','طوال الخدمة + 5 سنوات','HR + المدير',('فعّال','green')],
['إقامات/أذونات','9,820','حتى الانتهاء + سنة','HR + امتثال',('فعّال','green')],
['مستندات مالية/رواتب','15,300','10 سنوات','مالية',('فعّال','green')],
['مراسلات حكومية','6,200','حسب الجهة','PRO + امتثال',('مراجعة إتلاف','amber')]])}</div>
<div class='card' style='width:390px'><div class='ct'>المزايا</div>
<div class='kv'>🔢 ترقيم ونُسخ (Versioning)</div><div class='kv'>🔐 وصول حسب الصلاحية (Access Profiles)</div><div class='kv'>⏳ احتفاظ/إتلاف آلي + حجز قانوني</div><div class='kv'>🔎 بحث وفهرسة كاملة</div>
<div class='warn'>⚠ الإتلاف لا يتم إلا بعد انتهاء مدة الاحتفاظ وغياب الحجز القانوني، وبأثر موثّق.</div></div>"""
S.append(("90_dms","إدارة الوثائق والأرشفة",shell("إدارة الوثائق","Employees › Documents › DMS & Retention",body)))

# 91 ANNOUNCEMENTS & POLICY ACKNOWLEDGMENT
body=f"""<div class='sub'>الإعلانات وإقرار اللوائح — نشر التعاميم والسياسات بلغات العمال مع تتبّع القراءة والإقرار الإلكتروني</div>
{tiles([('إعلانات نشطة','8','#3a7afe'),('إقرارات مطلوبة','2,418','#f59e0b'),('تمّت','2,106','#21b07b'),('متأخرة','312','#e25563'),('لغات','عربي+نيبالي+بنغالي','#0ea5e9')])}
<div class='card' style='width:840px'><div class='ct'>الإعلانات والسياسات</div>
{tbl(['العنوان','النوع','الجمهور','اللغات','الإقرار'],[
['تحديث لائحة الجزاءات','سياسة — إقرار إلزامي','جميع العمال','3',('1,940 / 2,418','amber')],
['تعميم مواعيد الصرف','إعلان','جميع الموظفين','2',('قراءة فقط','blue')],
['دليل السلامة (HSE)','سياسة — إقرار إلزامي','المواقع الميدانية','3',('مكتمل','green')]])}</div>
<div class='card' style='width:390px'><div class='ct'>كيف يعمل</div>
<div class='cap'><b>⚙️</b> الإعلان يُنشر للجمهور المستهدف بلغته (موبايل العامل 80 + الكشك 54)؛ السياسات الإلزامية تتطلّب إقراراً إلكترونياً يُسجَّل بالاسم والوقت كإثبات قانوني؛ تذكير آلي للمتأخّرين.</div></div>"""
S.append(("91_announcements","الإعلانات وإقرار اللوائح",shell("الإعلانات والإقرارات","Employees › Communication › Announcements",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("71_residency_dashboard","داشبورد الإقامات ⭐"),("72_payroll_dashboard","داشبورد الرواتب ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("76_org_structure","الهيكل التنظيمي والدرجات ⭐"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("73_coverage_monitor","مراقب تغطية الحضور ⭐"),("05_mobile","تطبيق الموبايل للحضور"),("80_self_service","الخدمة الذاتية + موبايل العامل ⭐"),("91_announcements","الإعلانات وإقرار اللوائح ⭐ جديد"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
("66_payroll_routing","مسار وتقسيم الرواتب ⭐"),("67_payslip_icons","أيقونات المؤثّرات على السطر ⭐"),("75_ot_requests","طلبات الأوفر تايم والبدلات ⭐"),("74_violations","المخالفات المرورية + داشبورد ⭐"),("78_accounting","التكامل المحاسبي للرواتب ⭐"),("89_expense_claims","المطالبات والنثريات ⭐ جديد"),("69_payroll_extras","أفكار إضافية في الرواتب ⭐"),
("68_contracts","إدارة عقود الموظفين ⭐"),
("07_overtime_rules","قواعد الأوفر تايم وساعات العمل"),("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)"),("09_eos","حاسبة نهاية الخدمة (قانون الكويت)"),
("10_payroll","الرواتب + Compensation Hub"),("11_documents","مركز انتهاء المستندات"),("90_dms","إدارة الوثائق والأرشفة ⭐ جديد"),("12_discipline","الانضباط والقانوني"),("86_grievances","التظلّمات والشكاوى ⭐ جديد"),
("13_housing","السكن (Hostel)"),("88_accommodation","تشغيل سكن العمال ⭐ جديد"),("14_uniform_transport","الزي والمواصلات (أساسي)"),("15_performance","الأداء والمهارات (أساسي)"),
("16_access","شجرة الصلاحيات (Access Profiles)"),("79_settings_engine","محرّك الإعدادات واللائحة ⭐"),("82_delegation","تفويض الصلاحيات والإنابة ⭐"),("17_reports","مركز التقارير"),
("18_profitability","ربحية العقد/المشروع (P&L) ⭐"),("19_workforce_planning","تخطيط القوى العاملة والإحلال ⭐"),
("20_sponsorship","امتثال العمالة المكفولة ⭐"),("77_absconding","التغيّب والهروب ونقل الكفالة ⭐"),("84_site_permits","تصاريح المواقع والأمن ⭐ جديد"),("21_sla_client","SLA وبوابة العميل"),("22_roster","جدولة الورديات + الاحتياطي"),
("23_agency","أداء وكالات الاستقدام"),("24_probation","محرّك فترة التجربة"),("25_letters","مركز الخطابات والشهادات"),("83_gov_correspondence","المراسلات الحكومية + التوقيع ⭐"),("85_pro_tracker","متابعة المعاملات الحكومية ⭐ جديد"),
("26_movement","سجل حركة الموظف الداخلية"),("27_attrition","تحليل التسرّب (Attrition)"),
("28_gov_custody","المصروفات الحكومية وتسوية العُهد ⭐"),("87_custody","سجل العُهد والتسليم ⭐ جديد"),("29_performance_plus","الأداء والمهارات (مطوّر) ⭐"),
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
