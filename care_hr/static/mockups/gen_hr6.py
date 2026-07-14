# -*- coding: utf-8 -*-
"""Care HR — residency workflow, deployment, quality, requests hub, payroll controls. Rebuilds index."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=160):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:150px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
def kol(h,items):
    return f"<div class='kol' style='width:135px'><div class='h'>{h}</div>"+"".join([f"<div class='kc'>{i}</div>" for i in items])+"</div>"
S=[]

# 39 RESIDENCY TRANSACTION (start->finish)
chk="".join([f"<div class='kv'><span class='badge {c}' style='width:20px;text-align:center'>{m}</span> {n}</div>" for n,m,c in [
 ("صورة الجواز","✔","green"),("صورة شخصية","✔","green"),("الكشف الطبي","✔","green"),("نسخة العقد","✔","green"),("شهادة راتب","●","amber")]])
body=f"""<div class='sub'>معاملة إقامة TX-0231 — تجديد · Ramesh — من البدء للإغلاق (محكم + سهل)</div>
<div style='margin-bottom:10px'><span class='stage done'>بدء</span><span class='stage done'>مستندات</span><span class='stage done'>رسوم</span><span class='stage on'>عهدة المندوب</span><span class='stage'>تقديم حكومي</span><span class='stage'>معالجة</span><span class='stage'>إصدار</span><span class='stage'>تسوية</span><span class='stage'>إغلاق</span></div>
<div class='card' style='width:520px'><div class='ct'>حزمة المستندات (مجمّعة تلقائياً من ملف العامل)</div>{chk}
<div class='kv' style='margin-top:6px'><b>المندوب</b> Khaled &nbsp; <b style='width:90px'>الرسوم</b> KWD 20</div>
<div class='kv'><b>رقم حكومي</b> — (يُدخل عند التقديم)</div>
<div class='kv'><b>الإقامة بعد الإصدار</b> ستُحدّث تلقائياً + OCR</div></div>
<div class='card' style='width:300px'><div class='ct'>الإحكام (Controls)</div>
<div style='font-size:13px;line-height:25px'>🔒 لا تتعدّى مرحلة<br>⏰ مهلة حكومية: 18 يوم<br>🚫 إقامة منتهية → منع نشر/راتب<br>💼 العهدة لازم تتسوّى<br>📝 audit كامل</div></div>
<div class='card' style='width:300px'><div class='ct'>السهولة (Ease)</div>
<div style='font-size:13px;line-height:25px'>📦 حزمة مستندات تلقائية<br>🔁 تجديد بالدفعات<br>📱 المندوب يحدّث من الموبايل<br>🔍 OCR لتاريخ الإقامة<br>⚡ بدء تلقائي قبل الانتهاء</div></div>"""
S.append(("39_residency_tx","معاملة الإقامة (Workflow)",shell("معاملة إقامة","Employees › Residency › Transaction",body)))

# 40 RESIDENCY BOARD + BATCH
body=f"""<div class='sub'>لوحة معاملات الإقامة — كل المعاملات بمراحلها + تجديد بالدفعات بضغطة</div>
{kol('بدء (6)',['تجديد ×4','جديدة ×2'])}{kol('مستندات (5)',['Ramesh','+4'])}{kol('عهدة (8)',['دفعة A (40)'])}
{kol('تقديم (4)',['ref#...'])}{kol('معالجة (12)',['متوقّع 5ي'])}{kol('إصدار (3)',['✓ OCR'])}{kol('تسوية (2)',['بانتظار مستند'])}
<div class='card' style='width:560px;margin-top:4px'><div class='ct'>تجديد بالدفعات (من مركز الانتهاء)</div>
<div class='kv'><b>المنتهية ≤30 يوم</b> 31 إقامة</div>
<div style='margin:6px 0'><span class='btn p'>توليد دفعة تجديد (31) بضغطة</span></div>
<div class='ok'>ينشئ 31 معاملة + طلب صرف بالإجمالي + عهدة واحدة — بدل 31 معاملة يدوية.</div></div>
<div class='card' style='width:560px;margin-top:4px'><div class='ct'>الإحصائيات</div>
{bar('متوسط زمن التجديد',60,'9 أيام','bar')}{bar('التزام SLA',85,'88%','b3')}{bar('معاملات متأخرة',20,'3','b4')}</div>"""
S.append(("40_residency_board","لوحة الإقامات + الدفعات",shell("لوحة الإقامات","Employees › Residency › Board",body)))

# 41 DEPLOYMENT ENGINE
rows=[("Bir Bahadur","A","نظافة·HSE✓","نيبال","صالح","مطابق تماماً","green"),
      ("Sunil","B","نظافة","بنجلاديش","—","مطابق (بدون تصريح)","amber"),
      ("Anil","C","عام","الهند","—","أقل من المطلوب","red")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'><span class='badge {('green' if r[1]=='A' else 'amber' if r[1]=='B' else 'slate')}'>{r[1]}</span></td><td class='small'>{r[2]}</td><td>{r[3]}</td><td class='center'>{r[4]}</td><td><span class='badge {r[6]}'>{r[5]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>محرّك تمركز العمال — يطابق العامل بمتطلبات المشروع (مهارة/تصنيف/تصريح/جنسية)</div>
<div class='card' style='width:400px'><div class='ct'>متطلبات مشروع A (وزارة الصحة)</div>
<div class='kv'><b>المطلوب</b> 8 عمّال نظافة</div><div class='kv'><b>التصنيف الأدنى</b> B</div><div class='kv'><b>إلزامي</b> HSE ساري</div><div class='kv'><b>موقع حساس؟</b> نعم → تصريح أمني</div><div class='kv'><b>نسبة جنسية</b> نيبال ≤ 60%</div></div>
<div class='card' style='width:730px'><div class='ct'>أفضل المرشّحين للنشر (مع البوابات)</div>
<table><tr><th>العامل</th><th class='center'>تصنيف</th><th>مهارات</th><th>الجنسية</th><th class='center'>تصريح</th><th>المطابقة</th></tr>{tr}</table>
<div class='warn'>🚫 لا يُنشر بدون تصريح للموقع الحساس · بدون HSE · لو في إجازة/مستند منتهٍ.</div>
<div class='idea'>💡 لوحة سحب للتمركز + كشف تعارض + قاعدة تدوير (مدة قصوى بالموقع) + تغطية لحظية.</div></div>"""
S.append(("41_deployment","تمركز العمال في المشاريع",shell("تمركز العمال","Employees › Operations › Deployment",body)))

# 42 WORKER QUALITY GRADE
body=f"""<div class='sub'>جودة العامل — تصنيف مركّب A/B/C يقود أهلية النشر</div>
<div class='card' style='width:560px'><div class='ct'>مكوّنات التصنيف — Bir Bahadur</div>
{bar('المهارات',90,'4.5','bar')}{bar('الأداء (360)',84,'4.2','b2')}{bar('انتظام الحضور',96,'96%','b3')}{bar('تقييم العميل',86,'4.3','b6')}{bar('الانضباط (خصم)',10,'0 مخالفات','b4')}
<div class='kv' style='margin-top:6px'><b>التصنيف النهائي</b> <span class='badge green' style='font-size:14px'>A</span> · أهلية: <b>عملاء مميّزون</b></div></div>
<div class='card' style='width:560px'><div class='ct'>توزيع الجودة (القوى العاملة)</div>
{bar('A (ممتاز)',45,'540','b3')}{bar('B (جيد)',75,'1,210','b2')}{bar('C (يحتاج تطوير)',55,'668','b4')}
<div class='idea'>💡 التصنيف يحدّد النشر (A للخاص/المميّز)، الترقية، مراجعة الراتب، خطة التطوير لـC، وتنبّؤ بالترك.</div></div>"""
S.append(("42_quality","جودة العامل (التصنيف)",shell("جودة العامل","Employees › Performance › Worker Grade",body)))

# 43 ADMIN REQUESTS HUB
rows=[("إجازة سنوية","Bir Bahadur","مدير الإدارة","green","معتمد"),("سلفة راتب","Gita","HR","amber","قيد الاعتماد"),
      ("شهادة راتب","Ramesh","HR","blue","قيد التوليد"),("إذن خروج","Anil","المشرف","green","معتمد"),("شكوى سكن","Sunil","رعاية العمال","amber","مفتوحة")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td><span class='badge {r[3]}'>{r[4]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>مركز الطلبات الإدارية الموحّد — كل الطلبات + صندوق موافقات واحد + مصفوفة وتفويض</div>
<div class='card' style='width:300px'><div class='ct'>أنواع الطلبات (مكان واحد)</div>
<div style='font-size:13px;line-height:29px'>🌴 إجازة · ⏱️ إذن · 💵 سلفة · 🏦 قرض<br>📄 شهادة/مستند · 🛠️ صيانة سكن<br>📣 شكوى · ✈️ تذكرة · 🔁 نقل</div></div>
<div class='card' style='width:560px'><div class='ct'>صندوق الموافقات (موحّد)</div>
<table><tr><th>الطلب</th><th>الموظف</th><th>المعتمِد</th><th>الحالة</th></tr>{tr}</table></div>
<div class='card' style='width:300px'><div class='ct'>التحكّم</div>
<div style='font-size:13px;line-height:25px'>🧩 مصفوفة اعتماد لكل نوع<br>👤 تفويض عند الإجازة<br>⏰ SLA + تصعيد<br>📝 كله في الشتر</div>
<div class='idea'>💡 الموظف من الموبايل؛ المدير يعتمد الكل من مكان واحد.</div></div>"""
S.append(("43_requests_hub","مركز الطلبات الإدارية",shell("الطلبات الإدارية","Employees › Self-Service › Requests",body)))

# 44 PAYROLL RUN CONTROLS
body=f"""<div class='sub'>تشغيل الرواتب بضغطة — مع فحوصات قبلية تمنع الصرف لو في خلل (محكم + سهل)</div>
<div class='card' style='width:560px'><div class='ct'>الفحوصات القبلية — دورة يونيو 2026</div>
<div class='kv'><span class='badge green' style='width:20px;text-align:center'>✔</span> كل التايم شيت معتمدة (12 مشروع)</div>
<div class='kv'><span class='badge green' style='width:20px;text-align:center'>✔</span> كل بنود Compensation Hub معتمدة</div>
<div class='kv'><span class='badge green' style='width:20px;text-align:center'>✔</span> الأوفر تايم متحقّق من الحضور</div>
<div class='kv'><span class='badge red' style='width:20px;text-align:center'>✗</span> 3 عمّال إقامتهم منتهية → <b>محظور صرفهم</b></div>
<div class='kv'><span class='badge amber' style='width:20px;text-align:center'>!</span> 5 عمّال بفرق تايم شيت غير مبرّر</div>
<div class='warn'>الصرف لكل القوى ممنوع حتى حل الحظر (أو استثناؤهم بقرار موثّق).</div></div>
<div class='card' style='width:560px'><div class='ct'>التشغيل</div>
<div class='kv'><b>الموظفون</b> 2,415 / 2,418 (3 محظورون)</div><div class='kv'><b>إجمالي الصافي</b> KWD 610,900</div>
<div style='margin:8px 0'><span class='btn p'>تشغيل الرواتب</span><span class='btn'>تصدير WPS</span><span class='btn'>قيد محاسبي</span></div>
<div class='ok'>فصل المهام: طالب ≠ معتمِد ≠ صارف. قفل الفترة بعد الصرف.</div>
<div class='idea'>💡 بضغطة بعد الفحوصات؛ كشف مستحقات لكل عامل (إجازة/EOS/قروض/عهد) متاح قبل الصرف.</div></div>"""
S.append(("44_payroll_run","تشغيل الرواتب (محكم)",shell("تشغيل الرواتب","Employees › Payroll › Run",body)))

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
