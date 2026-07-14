# -*- coding: utf-8 -*-
"""Care HR — additional mockup screens (employee suggestions + business-model ideas)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read() if os.path.exists(os.path.join(OUT,'_css.txt')) else """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DejaVu Sans',Arial,sans-serif;background:#eef2f7;color:#0f172a;width:1280px}
.top{background:#0b1220;color:#fff;height:52px;padding:0 20px;line-height:52px}
.top .b{font-weight:bold;font-size:17px;color:#7dd3fc;display:inline-block}.top .c{color:#94a3b8;font-size:13px;margin-left:14px}.top .u{float:right;color:#cbd5e1;font-size:13px}
.wrap{padding:18px 22px}.h1{font-size:22px;font-weight:bold}.sub{color:#64748b;font-size:13px;margin-bottom:14px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 1px 3px rgba(15,23,42,.05);padding:15px;margin:0 13px 13px 0}
.ct{color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:7px}
.kpi .v{font-size:25px;font-weight:bold}.kpi .d{font-size:12px;margin-top:3px}.up{color:#16a34a}.dn{color:#dc2626}.mut{color:#94a3b8}
.btn{display:inline-block;border-radius:8px;padding:7px 13px;font-size:13px;border:1px solid #cbd5e1;background:#fff;margin-right:7px}.btn.p{background:#4f46e5;border-color:#4f46e5;color:#fff;font-weight:bold}.btn.g{background:#16a34a;border-color:#16a34a;color:#fff}
.badge{display:inline-block;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:bold}
.green{background:#dcfce7;color:#166534}.amber{background:#fef3c7;color:#92400e}.red{background:#fee2e2;color:#991b1b}.blue{background:#dbeafe;color:#1e40af}.slate{background:#e2e8f0;color:#334155}.indigo{background:#e0e7ff;color:#3730a3}.teal{background:#ccfbf1;color:#115e59}
table{border-collapse:collapse;width:100%}th{background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase;text-align:left;padding:8px 9px;border-bottom:1px solid #e2e8f0}td{padding:9px;border-bottom:1px solid #eef2f7;font-size:13px}
.bar{height:13px;border-radius:7px;background:#4f46e5;display:inline-block;vertical-align:middle}.b2{background:#0ea5e9}.b3{background:#10b981}.b4{background:#f59e0b}.b5{background:#64748b}.b6{background:#8b5cf6}
.barbg{background:#eef2f7;border-radius:7px;display:inline-block;width:150px;height:13px;vertical-align:middle;margin-right:7px}.barbg .bar{display:block}
.stage{display:inline-block;padding:5px 13px;border-radius:20px;background:#e2e8f0;color:#475569;font-size:12px;margin-right:5px}.stage.on{background:#4f46e5;color:#fff}.stage.done{background:#10b981;color:#fff}
.kv{font-size:13px;line-height:25px}.kv b{color:#475569;display:inline-block;width:160px;font-weight:600}
.panel{background:#0b1220;color:#e2e8f0;border-radius:12px;padding:13px 15px}.panel .big{font-size:21px;font-weight:bold;color:#fff}.panel .s{font-size:11px;color:#94a3b8}
.chip{display:inline-block;background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;border-radius:7px;padding:3px 9px;font-size:12px;margin:2px}
.sec{font-weight:bold;font-size:13px;color:#334155;margin:4px 0 8px;border-bottom:1px solid #eef2f7;padding-bottom:5px}
.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.ok{background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.idea{background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;border-radius:8px;padding:8px 11px;font-size:12px;margin-top:8px}
.right{text-align:right}.center{text-align:center}.small{font-size:12px;color:#64748b}
.inp{display:inline-block;border:1px solid #cbd5e1;border-radius:7px;padding:5px 9px;font-size:12px;background:#fbfdff;min-width:70px}
.phone{width:300px;background:#0b1220;border-radius:26px;padding:12px;margin:0 16px 0 0;display:inline-block;vertical-align:top}.screen{background:#f4f7fb;border-radius:16px;padding:12px;min-height:480px}
"""
def shell(title,crumb,body):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{crumb}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{title}</div>{body}</div></body></html>"""
def bar(l,p,v,c="bar",w=150):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:130px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
def panel(items):
    tds="".join([f"<td style='border:none'><div class='s'>{s}</div><div class='big'>{v}</div></td>" for s,v in items])
    return f"<div class='panel' style='width:1150px;margin-top:6px'><table style='color:#e2e8f0'><tr>{tds}</tr></table></div>"
S=[]

# 18 PROFITABILITY
rows=[("مشروع A · وزارة الصحة","حكومي","312","58,400","41,200","30%","green"),
      ("مشروع B · بنك الخليج","خاص","98","22,000","18,900","14%","amber"),
      ("مشروع C · مجمع تجاري","خاص","47","9,600","9,950","-4%","red")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge {'indigo' if r[1]=='حكومي' else 'slate'}'>{r[1]}</span></td><td class='center'>{r[2]}</td><td class='right'>{r[3]}</td><td class='right'>{r[4]}</td><td class='center'><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>ربحية كل عقد لحظياً = قيمة العقد − <b>التكلفة المحمّلة الفعلية للعمالة</b> (يقفل الـ loop مع التسعير)</div>
<div class='card' style='width:760px'><div class='ct'>P&amp;L حسب المشروع (الشهر)</div>
<table><tr><th>المشروع</th><th>القطاع</th><th class='center'>عمالة</th><th class='right'>إيراد</th><th class='right'>تكلفة</th><th class='center'>هامش</th></tr>{tr}</table>
<div class='warn'>⚠ مشروع C خاسر (-4%) — التغطية أعلى من المطلوب أو السعر منخفض → مراجعة.</div></div>
<div class='card' style='width:400px'><div class='ct'>تكلفة العامل المحمّلة الكاملة</div>
{bar('راتب',100,'180','bar')}{bar('سكن',16,'28','b2')}{bar('مواصلات',12,'21','b3')}{bar('زي+تأمين',9,'15','b4')}{bar('إطفاء استقدام/فيزا',14,'25','b6')}{bar('مخصّص نهاية خدمة',10,'18','b5')}
<div class='kv' style='margin-top:6px'><b>الإجمالي/عامل/شهر</b> <b>KWD 287</b></div></div>
{panel([('إجمالي الإيراد','90k'),('التكلفة المحمّلة','70k'),('الهامش','20k · 22%'),('عمالة على البنش (تكلفة بدون إيراد)','KWD 6,400')])}
<div class='idea' style='width:1150px'>💡 مخصّص نهاية الخدمة يُحتسب شهرياً (مش صدمة كاش)؛ تكلفة «البنش» تُرصد؛ السعر المعروض (Proposal) يُقارَن بالتكلفة الفعلية.</div>"""
S.append(("18_profitability","ربحية العقد/المشروع (P&L)",shell("ربحية العقود","Employees › Analytics › Profitability",body)))

# 19 WORKFORCE PLANNING
rows=[("مشروع A","نظافة","320","312","-8","شاغر 8 → طلب استقدام","amber"),
      ("مشروع B","أمن","100","100","0","مكتمل","green"),
      ("مشروع D (جديد)","ضيافة","60","0","-60","عقد جديد → خطة استقدام","red")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center {'red' if r[4].startswith('-') else ''}'>{r[4]}</td><td><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>تخطيط مدفوع بالعقود: المطلوب لكل عقد مقابل المتاح + إحلال تلقائي عشان مفيش موقع يفضى</div>
<div class='card' style='width:760px'><div class='ct'>العرض مقابل الطلب (Demand vs Supply)</div>
<table><tr><th>المشروع</th><th>الخدمة</th><th class='center'>مطلوب</th><th class='center'>متاح</th><th class='center'>الفجوة</th><th>الإجراء</th></tr>{tr}</table>
<div class='ok'>الفجوة تولّد <b>طلب استقدام تلقائي</b> → recruitment → mobilization.</div></div>
<div class='card' style='width:400px'><div class='ct'>خطة الإحلال (Backfill)</div>
<div style='font-size:13px;line-height:27px'><span class='badge amber'>7</span> سيخرجون قريباً (إجازة/إقامة)<br><span class='badge red'>3</span> استقالات<br>→ بدلاء من <b>Pool الاحتياطي</b> أو استقدام</div>
<div class='sec' style='margin-top:8px'>حصة الفيزا (Quota)</div>{bar('مستخدم',78,'780','bar')}{bar('متاح',22,'220','b3')}</div>
<div class='idea' style='width:1150px'>💡 العقد الجديد يولّد خطة استقدام تلقائياً (مع زمن الوصول الطويل)؛ نسب الجنسيات تُراقَب؛ مفيش موقع تحت المطلوب (SLA).</div>"""
S.append(("19_workforce_planning","تخطيط القوى العاملة والإحلال",shell("تخطيط القوى العاملة","Employees › Planning › Workforce",body)))

# 20 SPONSORSHIP COMPLIANCE
rows=[("Bir Bahadur","سارية","2026-09","سارٍ","لا","—","green"),
      ("Ramesh","تنتهي ≤22ي","2026-07","ينتهي قريباً","لا","تجديد قيد التنفيذ","amber"),
      ("Kamal","منتهية","2026-05","منتهٍ","نعم","بلاغ هروب مقدّم","red")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge {('green' if 'سارية' in r[1] else ('amber' if '≤' in r[1] else 'red'))}'>{r[1]}</span></td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td>{r[5]}</td></tr>" for r in rows])
body=f"""<div class='sub'>امتثال العمالة المكفولة (خليجي) — إقامة · إذن عمل · هروب · نقل كفالة · حصص</div>
<div class='card' style='width:830px'><div class='ct'>لوحة الامتثال</div>
<table><tr><th>العامل</th><th>الإقامة</th><th class='center'>تنتهي</th><th class='center'>إذن العمل</th><th class='center'>هروب؟</th><th>إجراء</th></tr>{tr}</table>
<div class='warn'>⚠ Kamal: إقامة منتهية + بلاغ هروب → <b>محظور النشر</b> وإيقاف الراتب تلقائياً.</div></div>
<div class='card' style='width:320px'><div class='ct'>إجراءات الكفالة</div>
<div style='font-size:13px;line-height:30px'>🔄 تجديد إقامة (رسوم+موعد)<br>🏃 بلاغ هروب (مهلة قانونية)<br>↔️ نقل كفالة<br>✈️ تذكرة إجازة/نهاية خدمة</div></div>
<div class='idea' style='width:1150px'>💡 الإقامة/الإذن المنتهي = بوابة تمنع النشر والراتب؛ بلاغ الهروب كـ workflow بمهلة قانونية؛ حصة الفيزا ونسب الجنسيات تُدار مركزياً.</div>"""
S.append(("20_sponsorship","امتثال العمالة المكفولة",shell("الكفالة والامتثال","Employees › Compliance › Sponsorship",body)))

# 21 SLA + CLIENT PORTAL
body=f"""<div class='sub'>SLA وبوابة العميل — تغطية الموقع + اعتماد العميل لكشف الحضور (أساس الفوترة)</div>
<div class='card' style='width:560px'><div class='ct'>تغطية المواقع اليوم</div>
{bar('مشروع A (مطلوب 312)',100,'312 ✓','b3')}{bar('مشروع B (مطلوب 100)',92,'92 ⚠','b4')}{bar('مشروع C (مطلوب 47)',100,'47 ✓','b3')}
<div class='warn'>⚠ مشروع B تحت المطلوب بـ8 → مخاطرة خرق SLA/غرامة → إحلال عاجل.</div></div>
<div class='card' style='width:620px'><div class='ct'>بوابة العميل (وزارة الصحة)</div>
<div style='font-size:13px;line-height:27px'>👁️ يشوف تغطية موقعه اللحظية<br>✍️ <b>يعتمد كشف الحضور الشهري رقمياً</b> → يفتح الفوترة<br>📝 يرفع طلب/شكوى → تذكرة<br>📄 يحمّل حزمة مستندات العمال/التصاريح</div>
<div class='ok'>اعتماد العميل = أساس الفوترة (يربط HR بالمبيعات/المحاسبة).</div></div>"""
S.append(("21_sla_client","SLA وبوابة العميل",shell("SLA والعميل","Employees › Operations › SLA & Client",body)))

# 22 ROSTER
def cell(v,c): return f"<td class='center' style='background:{c};border-radius:4px'>{v}</td>"
body=f"""<div class='sub'>جدولة الورديات (Roster) لكل موقع + Pool احتياطي — يقلّل الأوفر تايم ويغطّي الغياب</div>
<div class='card' style='width:830px'><div class='ct'>روستر مشروع A — الأسبوع</div>
<table><tr><th>العامل</th><th class='center'>سبت</th><th class='center'>أحد</th><th class='center'>إثنين</th><th class='center'>ثلاثاء</th><th class='center'>أربعاء</th></tr>
<tr><td>Bir</td>{cell('☀️','#dcfce7')}{cell('☀️','#dcfce7')}{cell('🌙','#dbeafe')}{cell('R','#f1f5f9')}{cell('☀️','#dcfce7')}</tr>
<tr><td>Gita</td>{cell('🌙','#dbeafe')}{cell('R','#f1f5f9')}{cell('☀️','#dcfce7')}{cell('☀️','#dcfce7')}{cell('🌙','#dbeafe')}</tr>
<tr><td>Ramesh</td>{cell('L','#fef3c7')}{cell('L','#fef3c7')}{cell('☀️','#dcfce7')}{cell('☀️','#dcfce7')}{cell('☀️','#dcfce7')}</tr></table>
<div class='small'>☀️ نهاري · 🌙 ليلي · R راحة · L إجازة</div></div>
<div class='card' style='width:320px'><div class='ct'>Pool الاحتياطي</div>
<div style='font-size:13px;line-height:28px'>غياب Ramesh اليوم → <b>إحلال آلي</b>:<br>✅ Sunil (احتياطي)<br><span class='badge green'>الموقع مغطّى</span></div>
<div class='idea'>💡 كشف فجوات التغطية + تقليل الأوفر تايم + إحلال آلي من الـ pool.</div></div>"""
S.append(("22_roster","جدولة الورديات + الاحتياطي",shell("الورديات والروستر","Employees › Operations › Roster",body)))

# 23 AGENCY PERFORMANCE
rows=[("ABC Recruitment","نيبال","120","18 يوم","4%","6%","green"),
      ("XYZ Manpower","بنجلاديش","85","31 يوم","12%","19%","amber"),
      ("Global Hire","الهند","40","26 يوم","8%","9%","green")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td class='center'><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>أداء وكالات الاستقدام — قرار مبني على البيانات</div>
<div class='card' style='width:830px'><div class='ct'>مقارنة الوكالات</div>
<table><tr><th>الوكالة</th><th>الدولة</th><th class='center'>عمّال</th><th class='center'>زمن الوصول</th><th class='center'>رسوب طبي</th><th class='center'>تسرّب 1 سنة</th></tr>{tr}</table>
<div class='warn'>⚠ XYZ: تسرّب 19% + رسوب طبي 12% + بطيئة → مراجعة العقد.</div></div>
<div class='card' style='width:320px'><div class='ct'>تكلفة لكل وصول</div>{bar('ABC',60,'420','bar')}{bar('XYZ',85,'610','b4')}{bar('Global',70,'500','b2')}</div>
<div class='idea' style='width:1150px'>💡 تقييم آلي: التكلفة/الزمن/الرسوب الطبي/التسرّب لكل وكالة → اختيار أفضل مصدر للاستقدام.</div>"""
S.append(("23_agency","أداء وكالات الاستقدام",shell("وكالات الاستقدام","Employees › Recruitment › Agencies",body)))

# 24 PROBATION ENGINE
rows=[("Anil S.","2026-04-01","90 يوم","2026-06-30","6 أيام","تقييم مطلوب","amber"),
      ("Sunil R.","2026-05-15","90 يوم","2026-08-13","51 يوم","جارية","green"),
      ("Hari B.","2026-03-20","90 يوم","2026-06-18","منتهية","تثبيت/إنهاء","red")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>محرّك فترة التجربة (مقترح الموظفين #3) — احتساب آلي + إشعار قبل الانتهاء + تقرير</div>
<div class='card' style='width:1150px'><div class='ct'>الموظفون تحت فترة التجربة</div>
<table><tr><th>الموظف</th><th class='center'>البداية</th><th class='center'>المدة</th><th class='center'>تنتهي</th><th class='center'>المتبقي</th><th>الإجراء</th></tr>{tr}</table>
<div class='warn'>⚠ Anil: تنتهي خلال 6 أيام → إشعار للمدير لاتخاذ قرار (تثبيت/تمديد/إنهاء).</div>
<div class='idea'>💡 احتساب آلي من تاريخ الالتحاق (قابل للضبط لكل عقد) + إشعار قبل الانتهاء + تقرير «تحت التجربة» + ربط بمراحل الموظف (test_period).</div></div>"""
S.append(("24_probation","محرّك فترة التجربة",shell("فترة التجربة","Employees › Onboarding › Probation",body)))

# 25 LETTERS / CERTIFICATES
reps=["شهادة راتب","شهادة خبرة","تعريف بالراتب للبنك","تعريف للسفارة","خطاب عدم ممانعة (NOC)","تعريف بالإقامة","خطاب كفالة سكن"]
chips="".join([f"<span class='chip'>📄 {r}</span>" for r in reps])
body=f"""<div class='sub'>مركز الخطابات والشهادات (مقترح الموظفين #6) — طلب ذاتي + توليد فوري</div>
<div class='card' style='width:560px'><div class='ct'>طلب من الموظف (خدمة ذاتية)</div>
<div class='kv'><b>نوع الخطاب</b> شهادة راتب ▾</div><div class='kv'><b>الموجّه إلى</b> بنك الخليج</div><div class='kv'><b>اللغة</b> عربي/إنجليزي</div>
<div style='margin-top:8px'><span class='btn p'>طلب → توليد PDF</span></div>
<div class='ok'>workflow اعتماد بسيط → توليد بقالب الشركة + توقيع/QR + سجل.</div></div>
<div class='card' style='width:620px'><div class='ct'>قوالب جاهزة</div>{chips}
<div class='idea' style='margin-top:8px'>💡 يبني على موديول الخطابات (sp_letter)؛ الموظف يطلب من الموبايل؛ توليد آلي بقالب لكل شركة وبياناته الفعلية.</div></div>"""
S.append(("25_letters","مركز الخطابات والشهادات",shell("الخطابات والشهادات","Employees › Admin Services › Letters",body)))

# 26 MOVEMENT HISTORY
body=f"""<div class='sub'>سجل حركة الموظف الداخلية (مقترح الموظفين #5) — كل الأقسام/المواقع بتواريخها</div>
<div class='card' style='width:760px'><div class='ct'>الخط الزمني — Bir Bahadur</div>
<table><tr><th>من</th><th>إلى</th><th>القسم</th><th>المشروع/الموقع</th><th>السبب</th></tr>
<tr><td>2024-03</td><td>2024-09</td><td>النظافة</td><td>مشروع B · بنك الخليج</td><td>التحاق</td></tr>
<tr><td>2024-09</td><td>2025-06</td><td>النظافة</td><td>مشروع A · وزارة الصحة</td><td>نقل (طلب عميل)</td></tr>
<tr><td>2025-06</td><td>الآن</td><td>النظافة-VIP</td><td>مشروع A · مبنى الإدارة</td><td>ترقية مهارة</td></tr></table>
<div class='idea'>💡 سجل كامل غير قابل للتلاعب (audit) + تقرير حركة الموظفين الداخلية + يظهر في ملف 360.</div></div>
<div class='card' style='width:400px'><div class='ct'>تقارير الحركة</div>
<div style='font-size:13px;line-height:28px'>📊 حركة حسب القسم/المشروع<br>📊 معدل دوران داخلي<br>📊 أكثر المواقع استقبالاً/فقداً</div></div>"""
S.append(("26_movement","سجل حركة الموظف الداخلية",shell("الحركة الداخلية","Employees › Employee › Movement History",body)))

# 27 ATTRITION
body=f"""<div class='sub'>تحليل التسرّب (Attrition) + تنبّؤ — يقلّل تكلفة الاستقدام المتكرر</div>
<div class='card' style='width:560px'><div class='ct'>معدل التسرّب حسب البُعد</div>
{bar('وكالة XYZ',100,'19%','red')}{bar('مشروع C',75,'14%','b4')}{bar('مشرف: Khan',60,'11%','b4')}{bar('جنسية: X',40,'8%','b2')}{bar('المتوسط',50,'9.5%','b5')}</div>
<div class='card' style='width:620px'><div class='ct'>تنبّؤ بالخطر (مرشّحون للاستقالة/الهروب)</div>
<table><tr><th>العامل</th><th>المؤشرات</th><th class='center'>الخطر</th></tr>
<tr><td>Ramesh</td><td class='small'>غياب متكرر + سلف + شكوى</td><td class='center'><span class='badge red'>عالٍ</span></td></tr>
<tr><td>Kamal</td><td class='small'>تأخر راتب + إقامة منتهية</td><td class='center'><span class='badge amber'>متوسط</span></td></tr></table>
<div class='idea'>💡 يحدّد مصدر المشكلة (وكالة/مشروع/مشرف) + تدخّل مبكر (احتفاظ) → توفير تكلفة استقدام بديل.</div></div>"""
S.append(("27_attrition","تحليل التسرّب (Attrition)",shell("تحليل التسرّب","Employees › Analytics › Attrition",body)))

# render new + rebuild combined index
for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("03_mobilization","رحلة الاستقدام والتأهيل"),
("04_attendance","الحضور اللحظي + الخريطة"),("05_mobile","تطبيق الموبايل للحضور"),("06_timesheet","التايم شيت + الاعتماد"),
("07_overtime_rules","قواعد الأوفر تايم وساعات العمل"),("08_leave_kuwait","استحقاق الإجازات (قانون الكويت)"),("09_eos","حاسبة نهاية الخدمة (قانون الكويت)"),
("10_payroll","الرواتب + Compensation Hub"),("11_documents","مركز انتهاء المستندات"),("12_discipline","الانضباط والقانوني"),
("13_housing","السكن (Hostel)"),("14_uniform_transport","الزي والمواصلات"),("15_performance","الأداء والمهارات"),
("16_access","شجرة الصلاحيات (Access Profiles)"),("17_reports","مركز التقارير"),
("18_profitability","ربحية العقد/المشروع (P&L) ⭐"),("19_workforce_planning","تخطيط القوى العاملة والإحلال ⭐"),
("20_sponsorship","امتثال العمالة المكفولة ⭐"),("21_sla_client","SLA وبوابة العميل"),("22_roster","جدولة الورديات + الاحتياطي"),
("23_agency","أداء وكالات الاستقدام"),("24_probation","محرّك فترة التجربة (مقترح موظفين)"),("25_letters","مركز الخطابات والشهادات (مقترح موظفين)"),
("26_movement","سجل حركة الموظف الداخلية (مقترح موظفين)"),("27_attrition","تحليل التسرّب (Attrition)")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية للبيزنس · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL),"screens")
