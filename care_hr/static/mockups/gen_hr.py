# -*- coding: utf-8 -*-
"""Care HR — full system mockup images (wkhtmltoimage friendly)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280

CSS="""
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DejaVu Sans',Arial,sans-serif;background:#eef2f7;color:#0f172a;width:1280px}
.top{background:#0b1220;color:#fff;height:52px;padding:0 20px;line-height:52px}
.top .b{font-weight:bold;font-size:17px;color:#7dd3fc;display:inline-block}
.top .c{color:#94a3b8;font-size:13px;margin-left:14px}
.top .u{float:right;color:#cbd5e1;font-size:13px}
.side{position:absolute;top:52px;right:0;width:0}
.wrap{padding:18px 22px}
.h1{font-size:22px;font-weight:bold}
.sub{color:#64748b;font-size:13px;margin-bottom:14px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 1px 3px rgba(15,23,42,.05);padding:15px;margin:0 13px 13px 0}
.ct{color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:7px}
.kpi .v{font-size:25px;font-weight:bold}.kpi .d{font-size:12px;margin-top:3px}
.up{color:#16a34a}.dn{color:#dc2626}.mut{color:#94a3b8}
.btn{display:inline-block;border-radius:8px;padding:7px 13px;font-size:13px;border:1px solid #cbd5e1;background:#fff;margin-right:7px}
.btn.p{background:#4f46e5;border-color:#4f46e5;color:#fff;font-weight:bold}
.btn.g{background:#16a34a;border-color:#16a34a;color:#fff}
.badge{display:inline-block;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:bold}
.green{background:#dcfce7;color:#166534}.amber{background:#fef3c7;color:#92400e}.red{background:#fee2e2;color:#991b1b}
.blue{background:#dbeafe;color:#1e40af}.slate{background:#e2e8f0;color:#334155}.indigo{background:#e0e7ff;color:#3730a3}.teal{background:#ccfbf1;color:#115e59}
table{border-collapse:collapse;width:100%}
th{background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase;text-align:left;padding:8px 9px;border-bottom:1px solid #e2e8f0}
td{padding:9px;border-bottom:1px solid #eef2f7;font-size:13px}
.bar{height:13px;border-radius:7px;background:#4f46e5;display:inline-block;vertical-align:middle}
.b2{background:#0ea5e9}.b3{background:#10b981}.b4{background:#f59e0b}.b5{background:#64748b}.b6{background:#8b5cf6}
.barbg{background:#eef2f7;border-radius:7px;display:inline-block;width:150px;height:13px;vertical-align:middle;margin-right:7px}
.barbg .bar{display:block}
.stage{display:inline-block;padding:5px 13px;border-radius:20px;background:#e2e8f0;color:#475569;font-size:12px;margin-right:5px}
.stage.on{background:#4f46e5;color:#fff}.stage.done{background:#10b981;color:#fff}
.kol{display:inline-block;vertical-align:top;width:150px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;margin-right:8px;padding:8px}
.kol .h{font-size:12px;font-weight:bold;color:#334155;margin-bottom:6px}
.kc{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:6px;font-size:11px;margin-bottom:6px}
.kv{font-size:13px;line-height:25px}.kv b{color:#475569;display:inline-block;width:150px;font-weight:600}
.panel{background:#0b1220;color:#e2e8f0;border-radius:12px;padding:13px 15px}.panel .big{font-size:21px;font-weight:bold;color:#fff}.panel .s{font-size:11px;color:#94a3b8}
.tab{display:inline-block;padding:7px 13px;font-size:13px;color:#64748b}.tab.on{color:#4f46e5;border-bottom:2px solid #4f46e5;font-weight:bold}
.tabbar{border-bottom:2px solid #e2e8f0;margin:4px 0 12px}
.chip{display:inline-block;background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;border-radius:7px;padding:3px 9px;font-size:12px;margin:2px}
.sec{font-weight:bold;font-size:13px;color:#334155;margin:4px 0 8px;border-bottom:1px solid #eef2f7;padding-bottom:5px}
.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.ok{background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.idea{background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.right{text-align:right}.center{text-align:center}.small{font-size:12px;color:#64748b}
.inp{display:inline-block;border:1px solid #cbd5e1;border-radius:7px;padding:5px 9px;font-size:12px;background:#fbfdff;min-width:70px}
.phone{width:300px;background:#0b1220;border-radius:26px;padding:12px;margin:0 16px 0 0;display:inline-block;vertical-align:top}
.screen{background:#f4f7fb;border-radius:16px;padding:12px;min-height:520px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}
"""
def shell(title,crumb,body):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{crumb}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{title}</div>{body}</div></body></html>"""
def barrow(l,p,v,c="bar",w=150):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:120px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"

S=[]

# 1 DASHBOARD
kpis="".join([f"<div class='card kpi' style='width:188px'><div class='ct'>{t}</div><div class='v'>{v}</div><div class='d {c}'>{d}</div></div>" for t,v,d,c in [
 ("إجمالي الموظفين","2,418","▲ 64 هذا الشهر","up"),("حاضر اليوم","91%","2,201 / 2,418","mut"),
 ("في الاستقدام","73","قيد التأهيل","mut"),("مستندات تنتهي ≤30ي","48","إقامات/تصاريح","dn"),
 ("موافقات معلّقة (لي)","12","إجازات/أوفرتايم","mut"),("تكلفة الرواتب/شهر","KWD 612,400","▲ 3%","up"),
 ("أوفر تايم (الشهر)","4,820 س","12 مشروع","mut"),("إشغال السكنات","86%","1,940 سرير","mut")]])
body=f"""<div class='sub'>الصفحة الرئيسية · إحصائيات كل النظام · <span class='badge indigo'>محكومة بالصلاحيات</span> (كل دور يشوف المسموح له فقط)</div>{kpis}
<div class='card' style='width:412px'><div class='ct'>الموظفون حسب القطاع/الجنسية</div>{barrow('حكومي',100,'1,510','bar')}{barrow('خاص/تجاري',62,'908','b2')}<div style='margin-top:6px' class='small'>الجنسيات</div>{barrow('نيبال',100,'880','b3')}{barrow('بنجلاديش',80,'710','b4')}{barrow('الهند',45,'400','b6')}{barrow('أخرى',30,'428','b5')}</div>
<div class='card' style='width:412px'><div class='ct'>قمع الاستقدام/التأهيل</div>{barrow('وصول',100,'73','b5')}{barrow('كشف طبي',82,'60','b2')}{barrow('بصمة',70,'51','b6')}{barrow('إذن عمل',55,'40','b4')}{barrow('إقامة',40,'29','b3')}{barrow('تم النشر',26,'19','bar')}</div>
<div class='card' style='width:388px'><div class='ct'>يحتاج انتباه</div><div style='font-size:13px;line-height:29px'><span class='badge red'>48</span> مستند/إقامة تنتهي قريباً<br><span class='badge amber'>12</span> موافقات بانتظارك<br><span class='badge blue'>7</span> عودة إجازة متأخرة<br><span class='badge slate'>5</span> عمال تصريحهم منتهٍ (محظور النشر)</div></div>
<div class='card' style='width:840px'><div class='ct'>اتجاه الحضور (حاضر/غائب/إجازة)</div><svg width='800' height='120'><polyline points='10,90 120,70 230,80 340,50 450,60 560,40 670,55 790,45' style='fill:none;stroke:#10b981;stroke-width:3'/><polyline points='10,105 120,100 230,102 340,95 450,98 560,92 670,96 790,93' style='fill:none;stroke:#dc2626;stroke-width:2'/></svg></div>
<div class='card' style='width:388px'><div class='ct'>تكلفة الرفاهية حسب المشروع</div>{barrow('مشروع A',100,'سكن+نقل 42k','bar')}{barrow('مشروع B',70,'30k','b2')}{barrow('مشروع C',45,'19k','b3')}</div>"""
S.append(("01_dashboard","الداشبورد (رئيسية)",shell("لوحة معلومات الموارد البشرية","Employees › Dashboard",body)))

# 2 EMPLOYEE 360
body=f"""<div class='sub'>ملف الموظف الموحّد 360°</div>
<div class='card' style='width:300px'><div style='text-align:center'><div style='width:80px;height:80px;border-radius:50%;background:#e0e7ff;margin:0 auto;line-height:80px;font-size:30px'>👷</div><div style='font-weight:bold;font-size:16px;margin-top:8px'>Bir Bahadur</div><div class='small'>عامل نظافة · نيبال</div><div style='margin-top:6px'><span class='badge green'>نشط</span></div></div>
<div class='kv' style='margin-top:10px'><b>الرقم الوظيفي</b> EMP-02418</div><div class='kv'><b>القطاع/المشروع</b> حكومي · مشروع A</div><div class='kv'><b>الموقع</b> وزارة الصحة</div><div class='kv'><b>تاريخ الالتحاق</b> 01-Mar-2024</div>
<div class='sec' style='margin-top:10px'>الامتثال (Compliance)</div><div style='font-size:13px;line-height:24px'><span class='dot' style='background:#10b981'></span>الإقامة سارية (تنتهي 2026-09)<br><span class='dot' style='background:#f59e0b'></span>إذن العمل ينتهي خلال 22 يوم<br><span class='dot' style='background:#10b981'></span>الكشف الطبي ✓ · البصمة ✓</div></div>
<div class='card' style='width:840px'>
<div class='tabbar'><span class='tab on'>نظرة عامة</span><span class='tab'>العقد/الراتب</span><span class='tab'>الحضور</span><span class='tab'>الإجازات</span><span class='tab'>المستندات</span><span class='tab'>المستحقات</span><span class='tab'>الانضباط</span><span class='tab'>السكن</span><span class='tab'>الزي</span><span class='tab'>المهارات</span></div>
<div>{"".join([f"<span class='card' style='width:185px;padding:12px'><div class='ct'>{t}</div><div style='font-size:20px;font-weight:bold'>{v}</div></span>" for t,v in [('مستندات','6'),('حضور (شهر)','24 ي'),('رصيد إجازات','18 ي'),('قروض نشطة','1'),('مخالفات','0'),('السكن','سرير B-12'),('الزي','3 أطقم'),('نهاية الخدمة (تقديري)','KWD 1,240')]])}</div>
<div class='idea'>💡 فكرة: شريط حالة + إشارة مرور للامتثال؛ أزرار إحصائية لكل مجال؛ تقدير نهاية الخدمة لحظي.</div></div>"""
S.append(("02_employee360","ملف الموظف 360°",shell("ملف الموظف","Employees › Directory › Bir Bahadur",body)))

# 3 MOBILIZATION
def kol(h,items,onlast=False):
    cards="".join([f"<div class='kc'>{i}</div>" for i in items])
    return f"<div class='kol'><div class='h'>{h}</div>{cards}</div>"
body=f"""<div class='sub'>رحلة استقدام وتأهيل العمالة الأجنبية — كل بطاقة عامل تتحرّك بين المراحل (drag)</div>
{kol('وصول (5)',['Ram K. · نيبال','Anil S. · بنجلاديش','+3'])}
{kol('كشف طبي (8)',['Sunil · بانتظار النتيجة','Kamal · ✓','+6'])}
{kol('بصمة (6)',['Hari · موعد غداً','+5'])}
{kol('إذن عمل (4)',['Bishnu · مقدّم','+3'])}
{kol('إقامة (3)',['Raju · قيد الإصدار','+2'])}
{kol('سكن+نقل (2)',['Gita · سرير A-3','+1'])}
{kol('تم النشر',['→ مشروع A'])}
<div class='card' style='width:1198px;margin-top:6px'><div class='sec'>بطاقة عامل في المرحلة</div>
<div class='kv'><b>الاسم/الجنسية</b> Sunil · بنجلاديش &nbsp;&nbsp; <b>الوكالة</b> ABC Recruitment</div>
<div class='kv'><b>checklist</b> <span class='badge green'>كشف طبي ✓</span> <span class='badge amber'>بصمة قيد الحجز</span> <span class='badge slate'>إذن عمل</span> <span class='badge slate'>إقامة</span> <span class='badge slate'>سكن</span> <span class='badge slate'>نقل</span></div>
<div class='idea'>💡 كل مرحلة تنشئ مستند + تاريخ انتهاء تلقائياً (إقامة/إذن) + مهمة + تكلفة. النشر محظور حتى اكتمال الامتثال (والتصريح الأمني للمواقع الحساسة).</div></div>"""
S.append(("03_mobilization","رحلة الاستقدام والتأهيل",shell("الاستقدام والتأهيل","Employees › Onboarding › Mobilization",body)))

# 4 ATTENDANCE LIVE
rows=[("Bir Bahadur","مشروع A · وزارة الصحة","06:58","—","حاضر","green"),("Gita Devi","مشروع A","07:02","15:30","انصرف","slate"),("Ramesh","مشروع B","—","—","غائب","red"),("Anil","مشروع C","07:10","—","حاضر","green")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td><span class='badge {r[5]}'>{r[4]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>الحضور اللحظي — جهاز بصمة + موبايل + جماعي، كلهم في مصدر واحد</div>
<div class='card' style='width:560px'><div class='ct'>الخريطة الحيّة (من مبصّم وأين)</div><div style='height:260px;background:#dbeafe;border-radius:10px;position:relative'><span style='position:absolute;top:40px;left:60px'>📍A 312</span><span style='position:absolute;top:120px;left:200px'>📍B 98</span><span style='position:absolute;top:180px;left:120px'>📍C 47</span><span style='position:absolute;top:80px;left:330px'>📍D 156</span></div></div>
<div class='card' style='width:620px'><div class='ct'>السجل اللحظي</div><table><tr><th>الموظف</th><th>الموقع/المشروع</th><th class='center'>دخول</th><th class='center'>خروج</th><th>الحالة</th></tr>{tr}</table>
<div class='idea'>💡 منع التكرار/التعارض: الموبايل+الجهاز+الجماعي يكتبوا في نفس hr.attendance؛ الإذن/الإجازة تمنع بصمة متعارضة.</div></div>"""
S.append(("04_attendance","الحضور اللحظي + الخريطة",shell("الحضور والانصراف","Employees › Time & Attendance › Live",body)))

# 5 MOBILE APP
phone1=f"""<div class='phone'><div class='screen'>
<div style='text-align:center;color:#0b1220'><div style='font-weight:bold'>CARE — الحضور</div><div class='small'>مشروع A · وزارة الصحة</div></div>
<div style='background:#fff;border-radius:12px;margin-top:10px;padding:12px;text-align:center'>
<div style='width:120px;height:120px;border-radius:50%;background:#e0e7ff;margin:6px auto;line-height:120px;font-size:34px'>🤳</div>
<div class='small'>سيلفي + تحقق وجه ✓</div>
<div style='margin-top:6px'><span class='badge green'>داخل النطاق (Geofence) ✓</span></div>
<div style='margin-top:10px;background:#16a34a;color:#fff;border-radius:10px;padding:12px;font-weight:bold'>تسجيل دخول</div>
</div>
<div class='small' style='text-align:center;margin-top:8px'>📍 GPS · 🕗 06:58 · Offline ✓</div></div></div>"""
phone2=f"""<div class='phone'><div class='screen'>
<div style='font-weight:bold;color:#0b1220'>المشرف — بصمة الفريق</div>
<div style='background:#fff;border-radius:10px;margin-top:8px;padding:8px;font-size:12px'>
<div>☑ Bir Bahadur</div><div>☑ Gita Devi</div><div>☑ Ramesh</div><div>☐ Anil (غائب)</div><div>☑ +28 عامل</div></div>
<div style='margin-top:8px;background:#4f46e5;color:#fff;border-radius:10px;padding:10px;text-align:center;font-weight:bold'>بصمة جماعية (31)</div>
<div style='font-weight:bold;color:#0b1220;margin-top:12px'>خدمة ذاتية</div>
<div style='font-size:12px;line-height:26px'>🌴 طلب إجازة · ⏱️ إذن · 💰 قسيمة الراتب · 📁 مستنداتي · ✅ موافقاتي (3)</div></div></div>"""
phone3=f"""<div class='phone'><div class='screen'>
<div style='font-weight:bold;color:#0b1220'>السائق — نقل الفريق</div>
<div style='background:#fff;border-radius:10px;margin-top:8px;padding:10px;font-size:12px'>الخط: السكن → مشروع A<br>الركّاب: 31<br>🕕 05:40 ركوب · 🕖 06:50 نزول</div>
<div style='margin-top:8px;background:#16a34a;color:#fff;border-radius:10px;padding:10px;text-align:center;font-weight:bold'>تأكيد الركوب</div>
<div class='small' style='margin-top:8px'>يربط الحضور بالنقل (على حساب الشركة) + التكلفة على المشروع.</div></div></div>"""
body=f"""<div class='sub'>تطبيق الموبايل — عامل · مشرف · سائق (Geofence + سيلفي + offline + بصمة جماعية)</div>{phone1}{phone2}{phone3}
<div class='card' style='width:1198px'><div class='idea'>💡 أفكار: كشف GPS مزيّف · ربط الجهاز بالموظف · النشر للمواقع الحساسة محظور بدون تصريح ساري · QR/NFC للموقع · مهام الموقع مع البصمة.</div></div>"""
S.append(("05_mobile","تطبيق الموبايل للحضور",shell("تطبيق الحضور (موبايل)","Employees › Mobile App",body)))

# 6 TIMESHEET + WORKFLOW
body=f"""<div class='sub'>التايم شيت ومطابقة الحضور الفعلي مقابل المتوقع + workflow الاعتماد</div>
<div style='margin-bottom:10px'><span class='stage done'>إنشاء</span><span class='stage done'>توليد آلي</span><span class='stage on'>مراجعة المشرف</span><span class='stage'>اعتماد HR</span><span class='stage'>ترحيل للرواتب</span></div>
<div class='card' style='width:840px'><div class='ct'>تايم شيت — مشروع A · يونيو 2026</div>
<table><tr><th>الموظف</th><th class='center'>أيام عمل</th><th class='center'>حاضر فعلي</th><th class='center'>إجازة/إذن</th><th class='center'>فرق</th><th class='center'>أوفر تايم</th><th>الحالة</th></tr>
<tr><td>Bir Bahadur</td><td class='center'>26</td><td class='center'>24</td><td class='center'>2</td><td class='center'>0</td><td class='center'>12 س</td><td><span class='badge green'>مطابق</span></td></tr>
<tr><td>Gita Devi</td><td class='center'>26</td><td class='center'>23</td><td class='center'>1</td><td class='center red'>2</td><td class='center'>6 س</td><td><span class='badge amber'>فرق غير مبرّر</span></td></tr>
<tr><td>Ramesh</td><td class='center'>26</td><td class='center'>26</td><td class='center'>0</td><td class='center'>0</td><td class='center'>20 س</td><td><span class='badge green'>مطابق</span></td></tr></table>
<div class='idea'>💡 idempotent (مايكرّرش)؛ يحترم الإجازة/الإذن؛ يفرّق المبرّر من غير المبرّر؛ يغذّي الأوفر تايم بقواعده.</div></div>
<div class='card' style='width:340px'><div class='ct'>workflow الاعتماد</div>
<div style='font-size:13px;line-height:30px'>1) المشرف يراجع ويعتمد<br>2) HR يعتمد نهائياً<br>3) يترحّل لمسيّر الرواتب<br>4) قفل الفترة بعد الترحيل</div>
<div class='ok'>كل خطوة موثّقة في chatter + SLA + تصعيد.</div></div>"""
S.append(("06_timesheet","التايم شيت + الاعتماد",shell("التايم شيت","Employees › Time & Attendance › Timesheets",body)))

# 7 OVERTIME & WORKING HOURS RULES
body=f"""<div class='sub'>محرّك قواعد ساعات العمل والأوفر تايم — لكل إدارة/قسم/عامل، قابل للضبط من الإعدادات</div>
<div class='card' style='width:600px'><div class='sec'>سياسة (Policy) — قابلة للتطبيق على مستوى</div>
<div class='kv'><b>النطاق</b> <span class='chip'>شركة</span><span class='chip'>قطاع</span><span class='chip'>إدارة</span><span class='chip'>قسم</span><span class='chip'>عامل</span> (الأخص يطغى)</div>
<div class='kv'><b>ساعات اليوم</b> <span class='inp'>8</span> · <b style='width:90px'>أسبوع</b> <span class='inp'>48</span> · رمضان <span class='inp'>36</span></div>
<div class='kv'><b>أيام العمل</b> <span class='inp'>الأحد–الخميس</b></span></div>
<div class='kv'><b>فترة سماح تأخير</b> <span class='inp'>10 د</span></div>
<div class='sec' style='margin-top:8px'>قواعد الأوفر تايم (معدلات قابلة للتعديل)</div>
<table><tr><th>الحالة</th><th class='center'>المعدّل</th><th class='center'>الحد الأقصى</th></tr>
<tr><td>أوفر تايم عادي (بعد 8 س)</td><td class='center'>×1.25</td><td class='center'>2 س/يوم</td></tr>
<tr><td>يوم الراحة</td><td class='center'>×1.50</td><td class='center'>—</td></tr>
<tr><td>عطلة رسمية</td><td class='center'>×2.00 + يوم بدل</td><td class='center'>—</td></tr></table>
<div class='small'>* معدلات افتراضية وفق قانون العمل الكويتي — قابلة للضبط بالكامل من الإعدادات.</div></div>
<div class='card' style='width:570px'><div class='sec'>منطق الاحتساب</div>
<div class='kv'><b>سعر الساعة</b> = الأجر الأساسي ÷ (أيام×ساعات)</div>
<div class='kv'><b>أوفر تايم عادي</b> = الساعات × سعر الساعة × 1.25</div>
<div class='kv'><b>أهلية</b> الأوفر تايم لازم متحقّق من الحضور الفعلي (مش طلب فقط)</div>
<div class='idea'>💡 الأوفر تايم يتولّد من الحضور المعتمد، يمرّ بـ workflow موافقة، ثم يغذّي الراتب تلقائياً (Compensation Hub). تصعيد لو تعدّى الحد.</div>
<div class='warn'>تعارض: عامل تعدّى 2 س/يوم → يتطلب موافقة مدير الإدارة.</div></div>"""
S.append(("07_overtime_rules","قواعد الأوفر تايم وساعات العمل",shell("سياسات العمل والأوفر تايم","Employees › Configuration › Work Policies",body)))

# 8 LEAVE ENTITLEMENT (KUWAIT)
body=f"""<div class='sub'>استحقاق الإجازات وفق قانون العمل الكويتي (قابل للضبط)</div>
<div class='card' style='width:600px'><div class='sec'>الإجازة السنوية</div>
<div class='kv'><b>الاستحقاق</b> 30 يوم/سنة مدفوعة (تُستحق بعد 9 أشهر خدمة)</div>
<div class='kv'><b>الترحيل</b> قابل للضبط (مثلاً سنة واحدة)</div>
<div class='kv'><b>بدل نقدي</b> عن الرصيد غير المستخدم عند نهاية الخدمة</div>
<div class='sec' style='margin-top:8px'>الإجازة المرضية (متدرّجة)</div>
<table><tr><th>المدة</th><th class='center'>الأجر</th></tr>
<tr><td>أول 15 يوم</td><td class='center'>كامل</td></tr><tr><td>التالي 10</td><td class='center'>¾</td></tr><tr><td>التالي 10</td><td class='center'>½</td></tr><tr><td>التالي 10</td><td class='center'>¼</td></tr><tr><td>التالي 30</td><td class='center'>بدون أجر</td></tr></table></div>
<div class='card' style='width:570px'><div class='sec'>رصيد الموظف (Bir Bahadur)</div>
{barrow('سنوية مستحقة',100,'30 ي','bar')}{barrow('مستخدمة',40,'12 ي','b4')}{barrow('المتبقي',60,'18 ي','b3')}
<div class='kv' style='margin-top:6px'><b>قيمة الرصيد (بدل)</b> 18 × سعر اليوم = KWD 360</div>
<div class='idea'>💡 محرّك استحقاق قابل للضبط: أنواع إجازات، معدلات، تدرّج، ترحيل، بدل — كله من الإعدادات + احتساب آلي في الراتب ونهاية الخدمة.</div></div>"""
S.append(("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)",shell("استحقاق الإجازات","Employees › Leaves › Entitlement",body)))

# 9 EOS CALCULATOR (KUWAIT)
body=f"""<div class='sub'>حاسبة مكافأة نهاية الخدمة وفق قانون العمل الكويتي (القطاع الخاص)</div>
<div class='card' style='width:600px'><div class='sec'>القاعدة (افتراضي قابل للضبط)</div>
<div class='kv'><b>أول 5 سنوات</b> 15 يوم أجر عن كل سنة</div>
<div class='kv'><b>بعد 5 سنوات</b> شهر أجر عن كل سنة</div>
<div class='kv'><b>الحد الأقصى</b> أجر سنة ونصف</div>
<div class='kv'><b>الاستقالة (عقد غير محدد)</b> &lt;3 سنوات: لا شيء · 3–5: ½ · 5–10: ⅔ · 10+: كامل</div>
<div class='kv'><b>الأساس</b> آخر أجر شامل (أساسي + بدلات ثابتة) + بدل رصيد الإجازة</div></div>
<div class='card' style='width:570px'><div class='sec'>مثال — Bir Bahadur</div>
<table><tr><th>البند</th><th class='right'>القيمة</th></tr>
<tr><td>مدة الخدمة</td><td class='right'>6 سنوات 4 أشهر</td></tr>
<tr><td>آخر أجر شامل/شهر</td><td class='right'>180.000</td></tr>
<tr><td>أول 5 سنوات (15 ي×5)</td><td class='right'>450.0</td></tr>
<tr><td>بعد 5 (1 شهر × 1.33)</td><td class='right'>240.0</td></tr>
<tr><td>بدل رصيد الإجازة (18 ي)</td><td class='right'>108.0</td></tr>
<tr style='background:#f8fafc'><td><b>إجمالي المستحق</b></td><td class='right'><b>KWD 798.0</b></td></tr>
<tr><td>سبب الإنهاء</td><td class='right'>انتهاء عقد (كامل)</td></tr></table>
<div class='ok'>محسوبة آلياً عند الاستقالة/الإنهاء — وتظهر تقديرياً في ملف الموظف دائماً.</div></div>"""
S.append(("09_eos","حاسبة نهاية الخدمة (قانون الكويت)",shell("مكافأة نهاية الخدمة","Employees › Payroll › End of Service",body)))

# 10 PAYROLL / COMPENSATION HUB
rows=[("راتب أساسي","earning","180.000","green"),("بدل سكن (مخصّص)","earning","—","slate"),("أوفر تايم (12س)","earning","33.750","green"),("عمولة","earning","25.000","green"),("قرض (قسط)","deduction","-20.000","red"),("غياب/تأخير","deduction","-7.500","red"),("تأمينات (GOSI)","deduction","-12.500","red")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge {('green' if r[1]=='earning' else 'red')}'>{r[1]}</span></td><td class='right'>{r[2]}</td></tr>" for r in rows])
body=f"""<div class='sub'>قسيمة الراتب — تُبنى من <b>Compensation Hub</b> (كل المستحقات والخصومات في مصدر واحد)</div>
<div class='card' style='width:600px'><div class='ct'>قسيمة يونيو 2026 — Bir Bahadur</div>
<table><tr><th>البند</th><th>النوع</th><th class='right'>المبلغ</th></tr>{tr}
<tr style='background:#f8fafc'><td colspan='2'><b>الصافي</b></td><td class='right'><b>KWD 198.750</b></td></tr></table></div>
<div class='card' style='width:570px'><div class='ct'>Compensation Hub</div>
<div class='kv'>كل بند (بدل/مكافأة/عمولة/أوفر تايم/قرض/غرامة) → سطر بحالة <span class='badge slate'>draft</span>→<span class='badge amber'>approved</span>→<span class='badge green'>paid</span></div>
<div class='idea'>💡 الراتب يسحب من الـ Hub → أي معتمد ماينساش. يحل أكبر فجوة (البدلات/المكافآت/العمولات/الأوفرتايم مش بتوصل للراتب حالياً).</div>
<div class='kv' style='margin-top:6px'><b>تصدير</b> <span class='chip'>WPS (حماية الأجور)</span><span class='chip'>قيد محاسبي</span><span class='chip'>بنك</span></div></div>"""
S.append(("10_payroll","الرواتب + Compensation Hub",shell("الرواتب والمستحقات","Employees › Payroll › Payslips",body)))

# 11 DOCUMENTS / EXPIRY CENTER
def cell(n,c): return f"<td class='center' style='background:{c};border-radius:4px'>{n}</td>"
body=f"""<div class='sub'>مركز انتهاء المستندات — إقامات/تصاريح/جوازات/رخص لكل الموظفين في مكان واحد</div>
<div class='card' style='width:600px'><div class='ct'>خريطة حرارية (الـ90 يوم القادمة)</div>
<table><tr><th>النوع</th><th class='center'>≤7ي</th><th class='center'>≤15</th><th class='center'>≤30</th><th class='center'>≤60</th><th class='center'>≤90</th></tr>
<tr><td>إقامة</td>{cell('4','#fee2e2')}{cell('9','#fef3c7')}{cell('18','#fef3c7')}{cell('31','#ecfdf5')}{cell('44','#ecfdf5')}</tr>
<tr><td>إذن عمل</td>{cell('2','#fee2e2')}{cell('6','#fef3c7')}{cell('14','#fef3c7')}{cell('22','#ecfdf5')}{cell('30','#ecfdf5')}</tr>
<tr><td>جواز</td>{cell('0','#ecfdf5')}{cell('1','#fef3c7')}{cell('3','#fef3c7')}{cell('8','#ecfdf5')}{cell('12','#ecfdf5')}</tr>
<tr><td>تصريح أمني</td>{cell('1','#fee2e2')}{cell('2','#fef3c7')}{cell('5','#fef3c7')}{cell('7','#ecfdf5')}{cell('9','#ecfdf5')}</tr></table></div>
<div class='card' style='width:570px'><div class='ct'>إجراءات</div>
<div style='font-size:13px;line-height:28px'><span class='badge red'>عاجل</span> 7 مستندات تنتهي خلال أسبوع<br><span class='btn p'>تجديد جماعي</span><span class='btn'>تعيين مسؤول</span></div>
<div class='idea'>💡 تنبيهات <b>قبل</b> الانتهاء (مش بعده) متعددة المراحل + بريد + نشاط؛ تصريح/إقامة منتهية = <b>بوابة</b> تمنع النشر/الراتب. توحيد مستندات الموظف والشهادات والتصاريح.</div></div>"""
S.append(("11_documents","مركز انتهاء المستندات",shell("المستندات والامتثال","Employees › Documents › Expiry Center",body)))

# 12 DISCIPLINE & LEGAL
body=f"""<div class='sub'>الانضباط والإنذارات والقضايا</div>
<div style='margin-bottom:10px'><span class='stage done'>مسودة</span><span class='stage on'>بانتظار الإفادة</span><span class='stage'>اتخاذ إجراء</span><span class='stage'>معتمد</span></div>
<div class='card' style='width:560px'><div class='ct'>إجراء تأديبي DA-0142</div>
<div class='kv'><b>الموظف</b> Ramesh · مشروع B</div><div class='kv'><b>السبب</b> غياب بدون إذن</div><div class='kv'><b>إفادة الموظف</b> (مطلوبة)</div><div class='kv'><b>الإجراء</b> إنذار كتابي</div>
<div class='idea'>💡 workflow بإفادة الموظف + مرفقات + ربط بالحضور/الغياب + سجل في ملف الموظف.</div></div>
<div class='card' style='width:620px'><div class='ct'>القضايا القانونية + المواعيد</div>
<table><tr><th>القضية</th><th>المحكمة</th><th>الجلسة القادمة</th><th>الحالة</th></tr>
<tr><td>LC-0007</td><td>العمالية</td><td>2026-07-02</td><td><span class='badge amber'>جارية</span></td></tr>
<tr><td>LC-0005</td><td>العمالية</td><td>—</td><td><span class='badge green'>كسبناها</span></td></tr></table>
<div class='idea'>💡 تذكير بالمواعيد (نشاط+بريد) + سجل تحديثات + ربط بالموظف/المخالفة.</div></div>"""
S.append(("12_discipline","الانضباط والقانوني",shell("الانضباط والقضايا","Employees › Discipline & Legal",body)))

# 13 HOUSING / HOSTEL
body=f"""<div class='sub'>السكن — هرم (سكن→دور→شقة→غرفة→سرير) + إشغال + تكلفة على المشروع</div>
<div class='card' style='width:560px'><div class='ct'>سكن العمال 1 — الإشغال</div>
{barrow('مشغول',86,'1,940 / 2,250','bar')}{barrow('متاح',14,'310','b3')}
<table style='margin-top:8px'><tr><th>الدور</th><th class='center'>أسرّة</th><th class='center'>مشغول</th><th class='center'>متاح</th></tr>
<tr><td>الدور 1</td><td class='center'>120</td><td class='center'>110</td><td class='center'>10</td></tr>
<tr><td>الدور 2</td><td class='center'>120</td><td class='center'>118</td><td class='center'>2</td></tr></table></div>
<div class='card' style='width:620px'><div class='ct'>تخصيص سرير + تكلفة</div>
<div class='kv'><b>العامل</b> Bir Bahadur → <b>سرير</b> B-12 (دور2/شقة3/غرفة1)</div><div class='kv'><b>من–إلى</b> 2024-03-01 → —</div>
<div class='kv'><b>تكلفة/سرير/شهر</b> KWD 28 → تُحمّل على <b>مشروع A</b></div>
<div class='idea'>💡 إصلاح كراش القسمة على صفر؛ منع تخصيص نفس العامل لأكث1 سرير؛ توزيع تكلفة السكن والصيانة على المشاريع + قيد محاسبي.</div></div>"""
S.append(("13_housing","السكن (Hostel)",shell("السكن واللوجستيات","Employees › Welfare › Housing",body)))

# 14 UNIFORM & TRANSPORT
body=f"""<div class='sub'>الزي والمواصلات (على حساب الشركة) + توزيع التكلفة</div>
<div class='card' style='width:560px'><div class='ct'>صرف الزي/المهمات</div>
<table><tr><th>الموظف</th><th>الصنف</th><th class='center'>عدد</th><th>توقيع</th></tr>
<tr><td>Bir Bahadur</td><td>زي نظافة</td><td class='center'>3</td><td>✍️</td></tr>
<tr><td>فريق A (جماعي)</td><td>قفازات/أحذية</td><td class='center'>31</td><td>✍️</td></tr></table>
<div class='idea'>💡 دورة استبدال + تتبّع الإرجاع/التالف + صرف جماعي + توقيع موثّق.</div></div>
<div class='card' style='width:620px'><div class='ct'>المواصلات</div>
<div class='kv'><b>الخط</b> السكن → مشروع A · <b>السائق</b> John · <b>الركّاب</b> 31</div>
<div class='kv'><b>ركوب/نزول</b> تأكيد من تطبيق السائق</div>
<div class='kv'><b>التكلفة</b> KWD 9/يوم → <b>مشروع A</b></div>
<div class='idea'>💡 ربط النقل بالحضور + توزيع التكلفة على المشروع + تتبّع المركبات (fleet).</div></div>"""
S.append(("14_uniform_transport","الزي والمواصلات",shell("الزي والمواصلات","Employees › Welfare › Uniform & Transport",body)))

# 15 PERFORMANCE & SKILLS
body=f"""<div class='sub'>الأداء (360°) والمهارات</div>
<div class='card' style='width:560px'><div class='ct'>تقييم 360° — Sara (مشرف)</div>
{barrow('المدير',100,'4.5','bar')}{barrow('الزملاء',80,'4.1','b2')}{barrow('المرؤوسون',90,'4.3','b3')}{barrow('تقييم ذاتي',70,'3.9','b4')}
<div class='kv' style='margin-top:6px'><b>الإجمالي</b> 4.2 / 5 <span class='badge green'>عالٍ</span></div></div>
<div class='card' style='width:620px'><div class='ct'>مصفوفة المهارات</div>
<table><tr><th>المهارة</th><th class='center'>المستوى</th><th class='center'>المطلوب</th><th>فجوة</th></tr>
<tr><td>تنظيف معدّات ثقيلة</td><td class='center'>3</td><td class='center'>4</td><td><span class='badge amber'>تدريب</span></td></tr>
<tr><td>السلامة (HSE)</td><td class='center'>4</td><td class='center'>4</td><td><span class='badge green'>مطابق</span></td></tr></table>
<div class='idea'>💡 ربط فجوة المهارة بـ خطة تدريب + شهادات + ترقية المرحلة (stages). أهم للقطاع الخاص (عمالة ماهرة).</div></div>"""
S.append(("15_performance","الأداء والمهارات",shell("الأداء والمهارات","Employees › Performance",body)))

# 16 ACCESS PROFILES
body=f"""<div class='sub'>شجرة الصلاحيات — لكل دور: عرض/تعديل/إخفاء لكل منيو/تبويب/حقل (بدون كود)</div>
<div class='card' style='width:300px'><div class='ct'>الأدوار</div>
<div style='font-size:13px;line-height:30px'><span class='badge indigo'>HR Manager</span><br><span class='badge slate'>HR Officer</span><br><span class='badge slate'>Payroll Officer</span><br><span class='badge slate'>مدير إدارة</span><br><span class='badge slate'>مشرف</span><br><span class='badge slate'>موظف (ESS)</span><br><span class='badge slate'>مدقّق</span><br><span class='btn'>+ دور</span></div></div>
<div class='card' style='width:880px'><div class='ct'>مصفوفة الصلاحيات — الدور: Payroll Officer</div>
<table><tr><th>العنصر</th><th class='center'>عرض</th><th class='center'>تعديل</th><th class='center'>إنشاء</th><th class='center'>حذف</th></tr>
<tr><td>منيو: الرواتب</td><td class='center'>✔</td><td class='center'>✔</td><td class='center'>✔</td><td class='center'>—</td></tr>
<tr><td>حقل: الراتب الأساسي</td><td class='center'>✔</td><td class='center'>✔</td><td class='center'>—</td><td class='center'>—</td></tr>
<tr><td>حقل: تقييم الأداء</td><td class='center'>—</td><td class='center'>—</td><td class='center'>—</td><td class='center'>—</td></tr>
<tr><td>تبويب: الانضباط</td><td class='center'>✔ (قراءة)</td><td class='center'>—</td><td class='center'>—</td><td class='center'>—</td></tr>
<tr><td>منيو: الإعدادات</td><td class='center'>—</td><td class='center'>—</td><td class='center'>—</td><td class='center'>—</td></tr></table>
<div class='idea'>💡 طبقات Odoo (groups + ir.model.access + ir.rule + field/view groups) تحت غطاء واحد سهل. record rules: «قسمي/مشروعي فقط». الداشبورد نفسه محكوم بالمصفوفة.</div></div>"""
S.append(("16_access","شجرة الصلاحيات (Access Profiles)",shell("الصلاحيات","Employees › Configuration › Access Profiles",body)))

# 17 REPORTS CENTER
reps=["بطاقة موظف / ID","التحاق","إخلاء طرف","عودة إجازة","قسيمة راتب","ملخص رواتب","تسوية نهاية الخدمة (EOS)","ملف WPS","طلب عمالة","انتهاء المستندات","إنذار/مكافأة","قضية قانونية","صرف الزي","إشغال وتكلفة السكن","تكلفة المواصلات","كشف حضور بالمشروع","تقرير أوفر تايم","الأعداد والدوران","تقرير الجنسيات/الإقامات","شهادة توجيه","مقابلة خروج"]
chips="".join([f"<span class='chip'>📄 {r}</span>" for r in reps])
body=f"""<div class='sub'>مركز التقارير — كلها per-company branding · عربي/إنجليزي · محكومة بالصلاحيات</div>
<div class='card' style='width:1198px'>{chips}<div class='idea' style='margin-top:10px'>💡 كل تقرير بقالب لكل شركة + ترويسة/تذييل + توقيع/QR، وجدول الأسعار/الحضور يتأقلم حسب نوع الخدمة، وكلها قابلة للتصدير PDF/Excel.</div></div>"""
S.append(("17_reports","مركز التقارير",shell("التقارير","Employees › Reports",body)))

# render + gallery
links=[]
for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);links.append((fn+".png",title));print("rendered",fn)
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}'><img src='{f}' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(links)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل</h1>
<div class='s'>{len(links)} شاشة · اضغط أي صورة لتكبيرها · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("HR gallery:",len(links))
