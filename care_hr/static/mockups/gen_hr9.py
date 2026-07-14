# -*- coding: utf-8 -*-
"""Care HR — compliance center, AI assistant, client billing, EOS liability, kiosk."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280
CSS=open(os.path.join(OUT,'_css.txt')).read()
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Sara — قطاع المشاريع الخاصة ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def bar(l,p,v,c="bar",w=150):
    return f"<div style='margin:6px 0'><span style='display:inline-block;width:160px;font-size:12px'>{l}</span><span class='barbg' style='width:{w}px'><span class='{c}' style='width:{int(p/100*w)}px'></span></span><span class='small' style='margin-left:7px'>{v}</span></div>"
def cell(v,c): return f"<td class='center' style='background:{c};border-radius:4px;font-weight:bold'>{v}</td>"
S=[]

# 50 COMPLIANCE COMMAND CENTER
rows=[("الإقامة","1,980","18","9","4"),("إذن العمل","1,940","14","6","2"),("الكشف الطبي","2,300","40","12","0"),
      ("التأمين الصحي","2,200","60","8","0"),("شهادة HSE","1,100","30","12","12"),("التصريح الأمني","420","9","5","1"),("العقد","2,418","22","3","0")]
tr="".join([f"<tr><td>{r[0]}</td>{cell(r[1],'#ecfdf5')}{cell(r[2],'#fef3c7')}{cell(r[3],'#fee2e2')}{cell(r[4],'#fecaca')}</tr>" for r in rows])
body=f"""<div class='sub'>مركز قيادة الامتثال — كل أنواع الامتثال في لوحة واحدة بدرجة مخاطرة</div>
<div class='card' style='width:760px'><div class='ct'>مصفوفة الامتثال (كل القوى العاملة)</div>
<table><tr><th>النوع</th><th class='center'>ساري</th><th class='center'>ينتهي ≤30ي</th><th class='center'>منتهٍ</th><th class='center'>محظور نشر</th></tr>{tr}</table></div>
<div class='card' style='width:400px'><div class='ct'>درجة المخاطرة العامة</div>
<div style='text-align:center'><div style='font-size:42px;font-weight:bold;color:#f59e0b'>72<span style='font-size:18px'>/100</span></div><span class='badge amber'>متوسطة</span></div>
<div style='font-size:13px;line-height:24px;margin-top:8px'><span class='badge red'>20</span> عامل محظور النشر (مستند منتهٍ)<br><span class='badge amber'>173</span> تنتهي خلال 30 يوم → دفعات تجديد<br><span class='btn p' style='margin-top:6px'>توليد دفعات التجديد</span></div>
<div class='idea'>💡 درجة مخاطرة + إجراءات تلقائية + بوابات نشر/راتب موحّدة.</div></div>"""
S.append(("50_compliance_center","مركز قيادة الامتثال",shell("الامتثال","Employees › Compliance › Command Center",body)))

# 51 AI ASSISTANT
def q(qt,at): return f"<div style='margin:8px 0'><div style='background:#4f46e5;color:#fff;border-radius:12px 12px 2px 12px;padding:8px 12px;font-size:13px;display:inline-block;float:left;max-width:70%'>{qt}</div><div style='clear:both'></div><div style='background:#f1f5f9;border-radius:12px 12px 12px 2px;padding:8px 12px;font-size:13px;display:inline-block;max-width:80%;margin-top:4px'>{at}</div></div>"
chat=(q("كام عامل نظافة متاح لمشروع A دلوقتي؟","🤖 12 عامل متاح (تصنيف B أو أعلى · HSE ساري · غير منشورين). أقترح: Sunil، Anil، +10. <a href='#'>عرض/نشر</a>")+
 q("مين إقامته تنتهي الشهر ده؟","🤖 18 عامل. الأعجل: Ramesh (≤7ي)، Kamal (منتهية ✖). <a href='#'>توليد دفعة تجديد</a>")+
 q("احسب نهاية الخدمة لـ Bir Bahadur","🤖 المدة 6س4ش · الأساس 180 → المكافأة + بدل الإجازة = <b>KWD 798</b> (قانون الكويت). <a href='#'>التفاصيل</a>")+
 q("(عامل بالنيبالية) कति छुट्टी बाँकी छ?","🤖 तपाईंको वार्षिक बिदा बाँकी: 18 दिन · पेस्लिप तयार छ। 📄"))
body=f"""<div class='sub'>مساعد HR ذكي — تسأله بلغتك، يجاوبك من بيانات النظام (للمدير والموظف)</div>
<div class='card' style='width:760px'><div class='ct'>محادثة</div>{chat}
<div style='margin-top:8px'><input class='inp' style='min-width:520px' value='اكتب سؤالك...'/><span class='btn p'>إرسال</span></div></div>
<div class='card' style='width:400px'><div class='ct'>قدرات</div>
<div style='font-size:13px;line-height:26px'>🔎 استعلامات فورية (توافر/امتثال/أرصدة)<br>🧮 حسابات (EOS/إجازة/أوفر تايم)<br>🌐 متعدد اللغات (عربي/نيبالي/بنغالي)<br>⚡ إجراءات سريعة من المحادثة<br>🔒 محكوم بصلاحيات المستخدم</div>
<div class='idea'>💡 الموظف يسأل عن رصيده/راتبه بلغته؛ المدير يسأل عن قوته العاملة فوراً.</div></div>"""
S.append(("51_ai_assistant","مساعد HR الذكي (AI)",shell("المساعد الذكي","Employees › AI Assistant",body)))

# 52 CLIENT BILLING FROM ATTENDANCE
rows=[("مشروع A · وزارة الصحة","عقد سنوي","312","8,112","7.5/يوم","60,840","معتمد عميل","green"),
      ("مشروع B · بنك الخليج","عقد","98","2,548","9.0","22,932","بانتظار العميل","amber"),
      ("مشروع D · ضيافة","أمر عمل","60","1,440","12.0","17,280","مسوّدة","slate")]
tr="".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td class='center'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td class='right'>{r[5]}</td><td><span class='badge {r[7]}'>{r[6]}</span></td></tr>" for r in rows])
body=f"""<div class='sub'>فوترة العميل من الحضور — أيام-العمل الفعلية × السعر التعاقدي → فاتورة (يربط HR بالإيرادات)</div>
<div class='card' style='width:1170px'><div class='ct'>فوترة يونيو حسب المشروع</div>
<table><tr><th>المشروع</th><th>أساس الفوترة</th><th class='center'>عمالة</th><th class='center'>أيام-عمل</th><th class='center'>السعر</th><th class='right'>المبلغ</th><th>الحالة</th></tr>{tr}
<tr style='background:#f8fafc'><td colspan='5'><b>الإجمالي</b></td><td class='right'><b>KWD 101,052</b></td><td></td></tr></table>
<div class='ok'>كشف الحضور المعتمد من العميل (بوابة العميل) = أساس الفاتورة → تتولّد فاتورة في المبيعات/المحاسبة.</div>
<div class='idea'>💡 يقفل الـ loop: حضور → فوترة → مقارنة بتكلفة العمالة (P&L). خصومات تلقائية لأيام النقص/الغياب حسب العقد.</div></div>"""
S.append(("52_client_billing","فوترة العميل من الحضور",shell("فوترة العميل","Employees › Operations › Client Billing",body)))

# 53 EOS LIABILITY
body=f"""<div class='sub'>التزام نهاية الخدمة (Provisioning) — تخطيط مالي للالتزام المتراكم</div>
<div class='card' style='width:560px'><div class='ct'>إجمالي الالتزام المتراكم</div>
<div style='text-align:center'><div style='font-size:38px;font-weight:bold;color:#4f46e5'>KWD 1.84M</div><span class='small'>مخصّص نهاية خدمة لكل القوى العاملة</span></div>
<div style='margin-top:8px'>{bar('قطاع حكومي',100,'1.18M','bar')}{bar('قطاع خاص',60,'0.66M','b2')}</div>
<div class='kv'><b>مخصّص هذا الشهر</b> KWD 31,400</div></div>
<div class='card' style='width:560px'><div class='ct'>التوقّع والاتجاه</div>
<svg width='520' height='130'><polyline points='10,110 90,100 170,88 250,78 330,66 410,55 500,44' style='fill:none;stroke:#4f46e5;stroke-width:3'/></svg>
<div class='small'>الالتزام بينمو مع الأقدمية — يُرصد شهرياً (مش صدمة كاش عند الإنهاء).</div>
<div class='idea'>💡 توقّع الالتزام السنوي؛ توزيع على المشاريع (P&L)؛ تقرير للـCFO؛ احتساب آلي وفق قانون الكويت.</div></div>"""
S.append(("53_eos_liability","التزام نهاية الخدمة (Provisioning)",shell("التزام EOS","Employees › Payroll › EOS Liability",body)))

# 54 WORKER KIOSK
kiosk=f"""<div style='width:560px;background:#0b1220;border-radius:18px;padding:18px;display:inline-block;vertical-align:top'>
<div style='background:#f4f7fb;border-radius:14px;padding:18px;text-align:center'>
<div style='font-weight:bold;font-size:18px;color:#0b1220'>CARE — كشك العمال (السكن)</div>
<div style='width:90px;height:90px;border-radius:50%;background:#e0e7ff;margin:12px auto;line-height:90px;font-size:34px'>🫆</div>
<div class='small'>ضع إصبعك للدخول · Bir Bahadur</div>
<div style='margin-top:14px'>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>📄<br>قسيمة الراتب</span>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>🌴<br>طلب إجازة</span>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>📁<br>مستنداتي</span>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>📣<br>شكوى</span>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>🔔<br>التعميمات</span>
<span style='display:inline-block;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:6px;font-size:14px'>🌐<br>नेपाली / বাংলা</span></div></div></div>"""
body=f"""<div class='sub'>كشك الخدمة الذاتية للعمال — للعمال بدون هاتف ذكي (في السكن/الموقع) · دخول بالبصمة · بلغته</div>
{kiosk}
<div class='card' style='width:560px'><div class='ct'>الفكرة</div>
<div style='font-size:13px;line-height:26px'>🫆 دخول ببصمة الإصبع (نفس أجهزة الحضور)<br>🌐 واجهة بسيطة بلغة العامل (نيبالي/بنغالي)<br>📄 يطبع/يشوف قسيمته · يطلب إجازة · يرفع شكوى<br>🔔 يشوف التعميمات والإنذارات<br>📱 نفس وظائف تطبيق الموبايل لكن لمن لا يملك هاتفاً</div>
<div class='idea'>💡 يغطّي العمالة الكبيرة بدون هواتف؛ يقلّل الضغط على HR؛ شفافية مع العمال (رفاهية/امتثال).</div></div>"""
S.append(("54_kiosk","كشك الخدمة الذاتية للعمال",shell("كشك العمال","Employees › Self-Service › Kiosk",body)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","90",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

ALL=[("01_dashboard","الداشبورد (رئيسية)"),("02_employee360","ملف الموظف 360°"),("45_employee_kanban","عرض الموظفين (كانبان مطوّر) ⭐"),("03_mobilization","رحلة الاستقدام والتأهيل"),
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
("50_compliance_center","مركز قيادة الامتثال ⭐"),("51_ai_assistant","مساعد HR الذكي (AI) ⭐"),("52_client_billing","فوترة العميل من الحضور ⭐"),("53_eos_liability","التزام نهاية الخدمة ⭐"),("54_kiosk","كشك الخدمة الذاتية للعمال ⭐")]
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}.png'><img src='{f}.png' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(ALL)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care HR — Full System Mockup</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0;direction:rtl}}.w{{max-width:1040px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}a{{color:#4f46e5}}</style></head>
<body><div class='w'><h1>Care HR — موكاب النظام الكامل ({len(ALL)} شاشة)</h1>
<div class='s'>اضغط أي صورة لتكبيرها · ⭐ = مميِّزات أساسية · <a href='../blueprint/blueprint.html'>← مخطط النظام (Blueprint)</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("rebuilt index with",len(ALL))
