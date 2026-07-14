# -*- coding: utf-8 -*-
"""Care HR — the 8 gap screens: org structure, absconding, accounting, settings engine,
ESS/MSS+mobile, fleet, delegation, government correspondence."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.tile{display:inline-block;vertical-align:top;width:148px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 9px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:20px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:6px 10px;font-size:12px;margin:3px 0;font-weight:bold}
.arr{color:#94a3b8;margin:0 3px;font-weight:bold}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.7}
.cap b{color:#0c4a6e}
.fcard{display:inline-block;vertical-align:top;width:262px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:0 9px 9px 0}
.fcard .t{font-weight:bold;font-size:13px;margin-bottom:4px}.fcard .d{font-size:11.5px;color:#64748b;line-height:1.6}
.ob{display:inline-block;background:#fff;border:1px solid #cbd5e1;border-radius:9px;padding:7px 11px;font-size:12px;margin:4px;font-weight:bold;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.phone{width:240px;border:7px solid #1f2937;border-radius:24px;padding:10px;background:#f8fafc;display:inline-block;vertical-align:top}
.set{display:inline-block;vertical-align:top;width:360px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:13px;margin:0 9px 9px 0}
.set .sh{font-weight:bold;font-size:13px;margin-bottom:7px}.set .r{font-size:12px;padding:4px 0;border-bottom:1px dashed #eef2f7}.set .r b{color:#475569}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(data):
    return "".join([f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in data])
def flow(steps):
    return "<span class='arr'>→</span>".join([f"<span class='step'>{s}</span>" for s in steps])
S=[]

# 76 ORG STRUCTURE & POSITIONS
pos=[("مدير عمليات","الدرجة 1","2","2","0","green"),("مشرف موقع","الدرجة 3","45","41","4","amber"),
     ("عامل نظافة","الدرجة 6","820","780","40","amber"),("حارس أمن","الدرجة 5","300","262","38","amber"),
     ("سائق","الدرجة 5","120","110","10","amber")]
pt="".join([f"<tr><td>{p[0]}</td><td class='small'>{p[1]}</td><td class='center'>{p[2]}</td><td class='center'>{p[3]}</td><td class='center'><span class='badge {p[5]}'>{p[4]}</span></td></tr>" for p in pos])
body=f"""<div class='sub'>الهيكل التنظيمي والدرجات والملاك — أساس تستند إليه باقي الموديولات (الرواتب/التوظيف/الترقيات)</div>
{tiles([('الإدارات','7','#3a7afe'),('المسميات الوظيفية','34','#0ea5e9'),('الملاك المعتمد','1,750','#714B67'),('المشغول','1,602','#21b07b'),('الشاغر','148','#f59e0b')])}
<div class='card' style='width:1170px'><div class='ct'>المخطط التنظيمي</div>
<div class='center'><span class='ob'>الإدارة العليا</span></div>
<div class='center'><span class='ob'>عمليات</span><span class='ob'>موارد بشرية</span><span class='ob'>أسطول</span><span class='ob'>مالية</span><span class='ob'>مشتريات</span></div>
<div class='center'><span class='ob'>نظافة</span><span class='ob'>أمن</span><span class='ob'>ضيافة</span><span class='ob'>غسيل</span><span class='ob' style='background:#eef2ff'>+ مشاريع</span></div></div>
<div class='card' style='width:760px'><div class='ct'>الملاك حسب الوظيفة (معتمد/مشغول/شاغر)</div>
<table><tr><th>الوظيفة</th><th>الدرجة</th><th class='center'>معتمد</th><th class='center'>مشغول</th><th class='center'>شاغر</th></tr>{pt}</table></div>
<div class='card' style='width:390px'><div class='ct'>الدرجات الوظيفية</div>
<div class='kv'><b>درجة 1–2</b> قيادة/إشراف عليا</div><div class='kv'><b>درجة 3–4</b> إشراف ميداني</div><div class='kv'><b>درجة 5</b> أمن/سائق (75–90)</div><div class='kv'><b>درجة 6</b> عمالة (75–85)</div>
<div class='idea'>💡 كل درجة تربط نطاق الأجر والبدلات والصلاحيات؛ الشاغر يغذّي تخطيط القوى والتوظيف تلقائياً.</div></div>"""
S.append(("76_org_structure","الهيكل التنظيمي والدرجات",shell("الهيكل والملاك","Employees › Organization › Structure & Grades",body)))

# 77 ABSCONDING / TRANSFER
rows=[("ABS-031","ديباك (نظافة)","تغيّب","6 أيام","إنذار + تجميد راتب","amber"),
      ("ABS-030","سونيل (أمن)","هروب","21 يوم","بلاغ هروب للهيئة + الداخلية","red"),
      ("ABS-029","راج (سائق)","نقل كفالة","—","موافقة + تحديث الملف","blue"),
      ("ABS-028","أنيل (ضيافة)","عودة بعد تغيّب","3 أيام","غلق الحالة + جزاء","green")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td>{r[4]}</td><td class='center'><span class='badge {r[5]}'>●</span></td></tr>" for r in rows])
body=f"""<div class='sub'>التغيّب والهروب ونقل الكفالة — إدارة قانونية-مالية لمخاطر العمالة المكفولة في الكويت</div>
{tiles([('حالات تغيّب','9','#f59e0b'),('بلاغات هروب','4','#e25563'),('رواتب مجمّدة','3','#8b5cf6'),('نقل كفالة','6','#0ea5e9'),('أثر مالي تقديري','14.2k','#714B67')])}
<div class='card' style='width:820px'><div class='ct'>الحالات</div>
<table><tr><th>المرجع</th><th>العامل</th><th class='center'>النوع</th><th class='center'>المدة</th><th>الإجراء</th><th class='center'>الخطورة</th></tr>{tr}</table></div>
<div class='card' style='width:330px'><div class='ct'>الأثر المالي للحالة</div>
<div class='kv'><b>تجميد الراتب</b> فوراً عند التغيّب</div><div class='kv'><b>تكلفة الاستقدام المهدرة</b> تُرصد</div><div class='kv'><b>استرداد من التأمين/الكفالة</b> إن وُجد</div><div class='kv'><b>إخطار الجهات</b> الهيئة + الداخلية</div></div>
<div class='card' style='width:1170px'><div class='sec'>الإجراء</div>
{flow(['رصد التغيّب (يربط بمراقب التغطية 73)','إنذار','تجميد الراتب','بلاغ هروب للهيئة/الداخلية','إجراءات قانونية','عودة أو إغلاق نهائي + إلغاء إقامة'])}
<div class='cap'><b>📖 اللائحة:</b> التغيّب عن العمل له مدد محددة قبل اعتباره هروباً، ويجب إبلاغ الهيئة العامة للقوى العاملة لرفع المسؤولية عن الشركة. <b>⚙️ النظام:</b> يجمّد الراتب آلياً، يولّد البلاغ، يرصد الأثر المالي، ويربط الحالة بالإقامة والملف وإلغاء الكفالة.</div></div>"""
S.append(("77_absconding","التغيّب والهروب ونقل الكفالة",shell("التغيّب والهروب","Employees › Compliance › Absconding & Transfer",body)))

# 78 ACCOUNTING INTEGRATION
je=[("مصروف رواتب (أساسي)","498,000","",""),("مصروف بدلات","48,300","",""),("مصروف أوفر تايم","31,200","",""),
    ("مخصّص نهاية الخدمة (شهري)","21,400","",""),("دائنون — صافي الرواتب (WPS)","","548,100",""),
    ("التأمينات GOSI مستحقة","","27,400",""),("خصومات (سلف/جزاءات/مخالفات)","","23,400","")]
jt="".join([f"<tr><td>{j[0]}</td><td class='center'>{j[1]}</td><td class='center'>{j[2]}</td></tr>" for j in je])
body=f"""<div class='sub'>التكامل المحاسبي — يقفل الحلقة مع المالية: قيد الرواتب + مخصّص نهاية الخدمة + توزيع التكلفة على المشاريع</div>
{tiles([('قيد الرواتب','جاهز','#21b07b'),('مخصّص EOS شهري','21.4k','#714B67'),('موزّع على مشاريع','7','#3a7afe'),('فروقات مطابقة','0','#21b07b')])}
<div class='card' style='width:680px'><div class='ct'>معاينة قيد الرواتب (يونيو 2026)</div>
<table><tr><th>الحساب</th><th class='center'>مدين</th><th class='center'>دائن</th></tr>{jt}
<tr style='background:#f8fafc'><td><b>الإجمالي</b></td><td class='center'><b>598,900</b></td><td class='center'><b>598,900</b></td></tr></table></div>
<div class='card' style='width:470px'><div class='ct'>توزيع التكلفة على المشاريع</div>
<div class='kv'><b>مشروع A</b> 286,000 → ربحية A</div><div class='kv'><b>مشروع B</b> 158,000 → فوترة العميل</div><div class='kv'><b>إداري/غير مباشر</b> 30,000</div>
<div class='idea'>💡 كل قسيمة تُرحَّل آلياً للمحاسبة بالحساب والمركز التكلفي الصحيح؛ مخصّص نهاية الخدمة يُستحق شهرياً (يربط شاشة 53)؛ ولا ترحيل إلا بعد قفل الفترة.</div></div>
<div class='card' style='width:1170px'><div class='sec'>الإجراء</div>
{flow(['قسيمة معتمدة','توليد قيد الرواتب','استحقاق مخصّص EOS','توزيع على المشاريع/الحسابات','مطابقة','ترحيل للمحاسبة','قفل الفترة'])}</div>"""
S.append(("78_accounting","التكامل المحاسبي للرواتب",shell("التكامل المحاسبي","Employees › Payroll › Accounting Integration",body)))

# 79 SETTINGS / LABOR-LAW ENGINE
def setcard(title,rows):
    rr="".join([f"<div class='r'><b>{k}</b> · {v}</div>" for k,v in rows])
    return f"<div class='set'><div class='sh'>{title}</div>{rr}</div>"
body=f"""<div class='sub'>محرّك الإعدادات واللائحة — قواعد العمل كإعدادات قابلة للتعديل بدون برمجة</div>
{setcard('الإجازات',[('سنوية','30 يوم/سنة'),('الاستحقاق','بعد 9 أشهر'),('مرضية','15 كامل/¾/½/¼'),('ترحيل الرصيد','حتى X يوم')])}
{setcard('نهاية الخدمة (EOS)',[('أول 5 سنوات','15 يوم/سنة'),('بعد 5','شهر/سنة'),('السقف','1.5 سنة راتب'),('تدرّج الاستقالة','مفعّل')])}
{setcard('الإشعار والاستقالة',[('مدة الإشعار','30 يوم'),('فترة التجربة','100 يوم'),('بدل الإشعار','مفعّل')])}
{setcard('ساعات العمل والأوفر',[('اليومي','8 ساعات'),('سعر الأوفر','1.25× / 1.5×'),('سقف الأوفر الشهري','قابل للضبط')])}
{setcard('الأجور والبدلات',[('الأساسي','75 / 80 / 85'),('بدل المواصلات','داخل/كاش'),('عتبات اعتماد البدل','شاشة 70')])}
{setcard('الجزاءات والحدود',[('كتالوج لكل مشروع','مفعّل'),('سقف الجزاء الشهري','قابل للضبط'),('حق التظلّم','مفعّل')])}
<div class='cap' style='width:1140px'><b>⚙️ الفكرة:</b> كل أرقام اللوائح أعلاه حقول إعدادات (Configuration) لا كود — تُعدَّل عند تغيّر القانون أو سياسة الشركة وتنعكس فوراً على الحسابات والمسارات، مع أثر للتغيير (من/متى/قبل/بعد).</div>"""
S.append(("79_settings_engine","محرّك الإعدادات واللائحة",shell("الإعدادات واللائحة","Employees › Configuration › Policy Engine",body)))

# 80 ESS / MSS + WORKER MOBILE
body=f"""<div class='sub'>الخدمة الذاتية للموظف والمدير + تطبيق العامل بلغته — يرفع التبنّي ويقلّل العبء على HR</div>
<div class='card' style='width:430px'><div class='ct'>الخدمة الذاتية للموظف (ESS)</div>
<div class='kv'>📄 عرض/تحميل قسيمة الراتب</div><div class='kv'>🌴 طلب إجازة ومتابعة الرصيد</div><div class='kv'>📑 مستنداتي (إقامة/عقد/شهادات)</div><div class='kv'>🧾 طلب شهادة/خطاب</div><div class='kv'>💳 رصيد السلف والأقساط</div></div>
<div class='card' style='width:430px'><div class='ct'>الخدمة الذاتية للمدير (MSS)</div>
<div class='kv'>✅ اعتماد الطلبات (إجازة/أوفر/بدل)</div><div class='kv'>👥 فريقي وحضوره اليوم</div><div class='kv'>📊 مؤشرات إدارته</div><div class='kv'>⚠ تنبيهات (تغطية/مستندات)</div><div class='kv'>🔁 تفويض صلاحياته (شاشة 82)</div></div>
<div class='phone'><div style='font-size:12px;font-weight:bold;text-align:center;margin-bottom:7px'>📱 تطبيق العامل · नेपाली / বাংলা</div>
<div class='kv' style='font-size:11px'>✓ تسجيل حضور (GPS/بصمة)</div><div class='kv' style='font-size:11px'>📄 قسيمتي (بلغتي)</div><div class='kv' style='font-size:11px'>🌴 طلب إجازة</div><div class='kv' style='font-size:11px'>📢 إعلانات الشركة</div><div class='kv' style='font-size:11px'>🆘 شكوى/طلب مساعدة</div></div>
<div class='idea' style='width:1170px'>💡 محتوى العامل بلغته الأم (نيبالي/بنغالي) لرفع الفهم والالتزام؛ كل طلب يدخل نفس مسارات الاعتماد؛ ويقلّل مراجعات HR الورقية.</div>"""
S.append(("80_self_service","الخدمة الذاتية + موبايل العامل",shell("الخدمة الذاتية","Employees › Self-Service (ESS/MSS)",body)))

# 82 DELEGATION OF AUTHORITY
rows=[("DEL-014","مدير المالية","نائب المالية","اعتماد الرواتب النهائي","20→30 يونيو","green"),
      ("DEL-013","مدير النظافة","مشرف أول","اعتماد الإجازات","إجازة المدير","green"),
      ("DEL-012","مدير HR","أخصائي HR","اعتماد طلبات الأوفر","حتى إشعار","amber")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td class='small'>{r[4]}</td><td class='center'><span class='badge {r[5]}'>●</span></td></tr>" for r in rows])
body=f"""<div class='sub'>تفويض الصلاحيات/التكليف بالإنابة — استمرارية الاعتمادات عند غياب المسؤول مع أثر كامل</div>
{tiles([('تفويضات نشطة','6','#21b07b'),('تنتهي هذا الأسبوع','2','#f59e0b'),('اعتمادات تمّت بالإنابة','41','#3a7afe')])}
<div class='card' style='width:980px'><div class='ct'>التفويضات</div>
<table><tr><th>المرجع</th><th>المفوِّض (من)</th><th>المفوَّض إليه</th><th>الصلاحية</th><th>المدة</th><th class='center'>الحالة</th></tr>{tr}</table></div>
<div class='card' style='width:1170px'><div class='sec'>الإجراء</div>
{flow(['تحديد الصلاحية والمدة','اختيار المفوَّض إليه','موافقة الإدارة العليا','تفعيل مؤقت','اعتماد بالإنابة (موسوم)','انتهاء آلي + استرداد'])}
<div class='cap'><b>⚙️ كيف يعمل:</b> التفويض محدود بصلاحية ومدة، ينتهي تلقائياً، وكل قرار يُتخذ بالإنابة يُوسَم باسم المفوَّض والمفوِّض في سجل الأثر — فلا توقف للعمل ولا ضياع للمسؤولية.</div></div>"""
S.append(("82_delegation","تفويض الصلاحيات والإنابة",shell("تفويض الصلاحيات","Employees › Configuration › Delegation",body)))

# 83 GOVERNMENT CORRESPONDENCE + E-SIGN
docs=[("إذن عمل جديد","الهيئة العامة للقوى العاملة","عربي/إنجليزي","تم التوقيع ✓","green"),
      ("تجديد إقامة","الإدارة العامة للإقامة","عربي","بانتظار توقيع المدير","amber"),
      ("شهادة راتب","بنك / جهة","عربي/إنجليزي","صادر للموظف","blue"),
      ("استمارة GOSI","التأمينات الاجتماعية","عربي","مُرسلة إلكترونياً","green"),
      ("بلاغ تغيّب","الهيئة/الداخلية","عربي","مسودة","slate")]
dt="".join([f"<tr><td>{d[0]}</td><td class='small'>{d[1]}</td><td class='center'>{d[2]}</td><td class='center'><span class='badge {d[4]}'>{d[3]}</span></td></tr>" for d in docs])
body=f"""<div class='sub'>المراسلات الحكومية والخطابات ثنائية اللغة + التوقيع الإلكتروني — توليد ومتابعة وأرشفة</div>
{tiles([('قوالب جاهزة','24','#3a7afe'),('بانتظار توقيع','7','#f59e0b'),('موقّعة إلكترونياً','312','#21b07b'),('مُرسلة للجهات','188','#0ea5e9')])}
<div class='card' style='width:820px'><div class='ct'>المستندات والمراسلات</div>
<table><tr><th>النوع</th><th>الجهة</th><th class='center'>اللغة</th><th class='center'>الحالة</th></tr>{dt}</table></div>
<div class='card' style='width:330px'><div class='ct'>المزايا</div>
<div class='kv'>🌐 قوالب عربي/إنجليزي تلقائية</div><div class='kv'>✍ توقيع إلكتروني معتمد</div><div class='kv'>🏛 ربط الجهات (PAM/PACI/GOSI/الداخلية)</div><div class='kv'>📥 أرشفة في ملف الموظف</div>
<div class='idea'>💡 يربط مركز الخطابات (25) والإقامات (39) والتغيّب (77) — كل مخاطبة رسمية تُولَّد وتُوقَّع وتُؤرشَف وتُتابَع من مكان واحد.</div></div>"""
S.append(("83_gov_correspondence","المراسلات الحكومية + التوقيع",shell("المراسلات الحكومية","Employees › Documents › Gov Correspondence",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("63_mega_dashboard","الداشبورد الشامل (Executive) ⭐"),("71_residency_dashboard","داشبورد الإقامات ⭐"),("72_payroll_dashboard","داشبورد الرواتب ⭐"),
("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("76_org_structure","الهيكل التنظيمي والدرجات ⭐ جديد"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("73_coverage_monitor","مراقب تغطية الحضور ⭐"),("05_mobile","تطبيق الموبايل للحضور"),("80_self_service","الخدمة الذاتية + موبايل العامل ⭐ جديد"),("06_timesheet","التايم شيت + الاعتماد"),
("46_att_to_payroll","البصمة → تايم شيت → الرواتب ⭐"),("47_salary_rules","هيكل وقواعد الرواتب (Odoo) ⭐"),("48_payroll_audit","التحقق ومراحل التدقيق ⭐"),("49_payslip_trail","أثر التدقيق للقسيمة ⭐"),
("64_pay_structure","هيكلة الأجر والبدلات ⭐"),("70_allowance_approvals","اعتماد البدلات (مصفوفة) ⭐"),("65_penalties","الجزاءات حسب المشروع ⭐"),
("66_payroll_routing","مسار وتقسيم الرواتب ⭐"),("67_payslip_icons","أيقونات المؤثّرات على السطر ⭐"),("75_ot_requests","طلبات الأوفر تايم والبدلات ⭐"),("74_violations","المخالفات المرورية + داشبورد ⭐"),("78_accounting","التكامل المحاسبي للرواتب ⭐ جديد"),("69_payroll_extras","أفكار إضافية في الرواتب ⭐"),
("68_contracts","إدارة عقود الموظفين ⭐"),
("07_overtime_rules","قواعد الأوفر تايم وساعات العمل"),("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)"),("09_eos","حاسبة نهاية الخدمة (قانون الكويت)"),
("10_payroll","الرواتب + Compensation Hub"),("11_documents","مركز انتهاء المستندات"),("12_discipline","الانضباط والقانوني"),
("13_housing","السكن (Hostel)"),("14_uniform_transport","الزي والمواصلات (أساسي)"),("15_performance","الأداء والمهارات (أساسي)"),
("16_access","شجرة الصلاحيات (Access Profiles)"),("79_settings_engine","محرّك الإعدادات واللائحة ⭐ جديد"),("82_delegation","تفويض الصلاحيات والإنابة ⭐ جديد"),("17_reports","مركز التقارير"),
("18_profitability","ربحية العقد/المشروع (P&L) ⭐"),("19_workforce_planning","تخطيط القوى العاملة والإحلال ⭐"),
("20_sponsorship","امتثال العمالة المكفولة ⭐"),("77_absconding","التغيّب والهروب ونقل الكفالة ⭐ جديد"),("21_sla_client","SLA وبوابة العميل"),("22_roster","جدولة الورديات + الاحتياطي"),
("23_agency","أداء وكالات الاستقدام"),("24_probation","محرّك فترة التجربة"),("25_letters","مركز الخطابات والشهادات"),("83_gov_correspondence","المراسلات الحكومية + التوقيع ⭐ جديد"),
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
