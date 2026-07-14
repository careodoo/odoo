# -*- coding: utf-8 -*-
"""Letter (Correspondence) module — redesign mockups. wkhtmltoimage friendly."""
import os, subprocess

OUT = os.path.dirname(os.path.abspath(__file__))
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;font-family:'Cairo',Tahoma,sans-serif}
body{background:#eef1f6;color:#1d2433;direction:rtl}
.wrap{width:1180px;margin:0 auto;padding:18px}
.top{background:#1e2a44;color:#fff;border-radius:12px;padding:12px 18px;display:flex;align-items:center;gap:14px;margin-bottom:14px}
.top .logo{font-weight:800;color:#e8564e;font-size:19px}
.top .crumb{color:#aeb8cc;font-weight:700;font-size:13px}
.top .sp{flex:1}
.h{font-size:22px;font-weight:800;margin:4px 0 2px}
.sub{color:#7b8499;font-weight:700;font-size:13px;margin-bottom:14px}
.kpis{display:table;width:100%;border-spacing:10px 0;margin:0 -10px 14px}
.kpi{display:table-cell;width:16.6%;background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:12px;vertical-align:top}
.kpi .v{font-size:24px;font-weight:800}
.kpi .l{color:#7b8499;font-weight:700;font-size:12px;margin-top:2px}
.kpi.red .v{color:#e2513f}.kpi.amber .v{color:#e08a00}.kpi.green .v{color:#1a9f6d}.kpi.blue .v{color:#2f6df6}.kpi.purple .v{color:#7a5cf0}
.card{background:#fff;border:1px solid #e4e8f0;border-radius:14px;padding:16px;margin-bottom:14px}
.card h3{font-size:15px;margin-bottom:12px}
.alert{background:#fff4f2;border:1px solid #ffd4cc;color:#c0392b;border-radius:10px;padding:11px 14px;font-weight:700;font-size:13px;margin-bottom:12px}
.alert.info{background:#eef4ff;border-color:#cfe0ff;color:#2a5bd7}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f6f8fc;color:#66708a;text-align:right;padding:9px 10px;font-weight:800;font-size:12px;border-bottom:2px solid #e4e8f0}
td{padding:9px 10px;border-bottom:1px solid #eef1f6;font-weight:600}
.badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:800}
.b-red{background:#fdeceb;color:#c0392b}.b-amber{background:#fff3e0;color:#c47f00}.b-green{background:#e6f7ef;color:#12945f}
.b-blue{background:#e9f0ff;color:#2f6df6}.b-grey{background:#eef1f6;color:#66708a}.b-purple{background:#f0ebff;color:#6a45e0}
.cols{display:table;width:100%;border-spacing:8px 0}
.col{display:table-cell;width:16.6%;background:#f6f8fc;border:1px solid #e4e8f0;border-radius:12px;padding:10px;min-height:280px;vertical-align:top}
.col .ch{font-weight:800;font-size:12.5px;margin-bottom:8px;display:flex;justify-content:space-between}
.lc{background:#fff;border:1px solid #e7ebf3;border-radius:10px;padding:9px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.lc .r{font-weight:800;font-size:12px;color:#2f3a57}
.lc .t{font-size:11.5px;color:#7b8499;font-weight:700;margin-top:2px}
.lc .m{font-size:11px;margin-top:6px;display:flex;justify-content:space-between;color:#8a93a8;font-weight:700}
.steps{display:table;width:100%;margin:6px 0}
.step{display:table-cell;width:20%;text-align:center;position:relative;padding:0 4px;vertical-align:top}
.step .n{width:40px;height:40px;border-radius:50%;background:#2f6df6;color:#fff;font-weight:800;line-height:40px;margin:0 auto 6px;font-size:15px}
.step.done .n{background:#1a9f6d}.step.wait .n{background:#c9d2e3;color:#5a6b8c}
.step .lb{font-weight:800;font-size:12px}.step .ds{color:#7b8499;font-size:11px;font-weight:700;margin-top:2px}
.step:after{content:'';position:absolute;top:20px;right:-50%;width:100%;height:3px;background:#dfe5ef;z-index:-1}
.step:first-child:after{display:none}
.flex{display:table;width:100%;border-spacing:14px 0;margin:0 -14px}
.grow{display:table-cell;vertical-align:top}
.label{border:2px dashed #b9c2d6;border-radius:12px;padding:14px;text-align:center;width:300px}
.label .qr{width:90px;height:90px;background:conic-gradient(#000 0 25%,#fff 0 50%,#000 0 75%,#fff 0);background-size:18px 18px;margin:8px auto;border:4px solid #000}
.tabs{display:flex;gap:6px;border-bottom:2px solid #eef1f6;margin-bottom:12px}
.tab{padding:8px 14px;font-weight:800;font-size:13px;color:#7b8499}
.tab.act{color:#1e2a44;border-bottom:3px solid #e8564e}
.two{display:table;width:100%;border-spacing:14px 0;margin:0 -14px}
.two>.card{display:table-cell;width:50%;vertical-align:top}
.fld{margin-bottom:9px}.fld .k{color:#8a93a8;font-weight:700;font-size:11.5px}.fld .val{font-weight:800;font-size:13px;margin-top:1px}
.btnrow{margin-bottom:12px}
.btn{display:inline-block;padding:7px 14px;border-radius:8px;font-weight:800;font-size:12.5px;border:1px solid transparent;margin:0 0 6px 6px}
.btn.p{background:#2f6df6;color:#fff}.btn.g{background:#1a9f6d;color:#fff}.btn.s{background:#fff;border-color:#d4dae6;color:#3a4a66}
.btn.s{background:#fff;border:1px solid #d4dae6;color:#3a4a66}
.pill{display:inline-block;padding:5px 12px;border-radius:8px;background:#eef1f6;font-weight:800;font-size:12px}
.dqitem{display:table;width:100%;padding:10px 12px;border:1px solid #eef1f6;border-radius:10px;margin-bottom:8px}
.dqn{font-weight:800;font-size:18px;min-width:60px}
</style>
"""

def top(crumb):
    return f"<div class='top'><div class='logo'>CARE • Letters</div><div class='crumb'>المراسلات › {crumb}</div><div class='sp'></div><div class='crumb'>◐ Sara — إدارة المراسلات</div></div>"

def render(name, inner, h=None):
    html = f"<html><head><meta charset='utf-8'>{CSS}</head><body><div class='wrap'>{inner}</div></body></html>"
    p = os.path.join(OUT, name + '.html'); open(p,'w').write(html)
    cmd = ['wkhtmltoimage','--enable-local-file-access','--quality','92','--width','1180','--encoding','utf-8']
    if h: cmd += ['--height', str(h)]
    cmd += [p, os.path.join(OUT, name + '.png')]
    subprocess.run(cmd, capture_output=True)
    print("rendered", name)

# ---------- 1) Dashboard ----------
render('letter_01_dashboard', top('لوحة المتابعة') + """
<div class='h'>لوحة المراسلات</div>
<div class='sub'>نظرة شاملة على الصادر والوارد وحالة التسليم والتوقيع</div>
<div class='alert'>⚠️ <b>١٧٣٤ كتاباً بلا تاريخ تسليم مُسجَّل</b> — التسليم غير مُتتبَّع. ٤٨ كتاباً مع المندوب لم يرجع إثبات استلامها منذ أكثر من ٧ أيام.</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>1,765</div><div class='l'>إجمالي الكتب</div></div>
<div class='kpi'><div class='v'>1,240</div><div class='l'>صادر</div></div>
<div class='kpi'><div class='v'>525</div><div class='l'>وارد</div></div>
<div class='kpi amber'><div class='v'>63</div><div class='l'>بانتظار التوقيع</div></div>
<div class='kpi purple'><div class='v'>91</div><div class='l'>بانتظار المسح الضوئي</div></div>
<div class='kpi red'><div class='v'>48</div><div class='l'>مع المندوب (متأخّر)</div></div>
</div>
<div class='flex'>
<div class='card grow'><h3>الكتب حسب المرحلة</h3>
<table><tr><th>المرحلة</th><th>العدد</th><th>النسبة</th></tr>
<tr><td>مسودة</td><td>120</td><td><span class='badge b-grey'>7%</span></td></tr>
<tr><td>موقّع</td><td>210</td><td><span class='badge b-blue'>12%</span></td></tr>
<tr><td>ممسوح/مؤرشف رقمياً</td><td>640</td><td><span class='badge b-purple'>36%</span></td></tr>
<tr><td>مع المندوب</td><td>155</td><td><span class='badge b-amber'>9%</span></td></tr>
<tr><td>مُسلَّم ومُستلَم</td><td>640</td><td><span class='badge b-green'>36%</span></td></tr></table></div>
<div class='card grow'><h3>حسب الجهة (الأكثر مراسلة)</h3>
<table><tr><th>الجهة</th><th>صادر</th><th>وارد</th></tr>
<tr><td>وزارة الشؤون</td><td>210</td><td>88</td></tr>
<tr><td>الهيئة العامة للقوى العاملة</td><td>180</td><td>64</td></tr>
<tr><td>بلدية الكويت</td><td>96</td><td>41</td></tr>
<tr><td>التأمينات الاجتماعية</td><td>72</td><td>33</td></tr></table></div></div>
""", 720)

# ---------- 2) Kanban lifecycle ----------
def lcard(ref, title, party, meta1, meta2, tag=None):
    tg = f"<span class='badge b-red'>{tag}</span>" if tag else ""
    return f"<div class='lc'><div class='r'>{ref} {tg}</div><div class='t'>{title}</div><div class='m'><span>{party}</span><span>{meta1}</span></div><div class='m'><span></span><span>{meta2}</span></div></div>"
render('letter_02_kanban', top('كانبان دورة الحياة') + """
<div class='h'>مسار الكتاب — من الإنشاء إلى الإقرار</div>
<div class='sub'>لوحة كانبان بدورة حياة واضحة (بدل مراحل مبعثرة)</div>
<div class='cols'>
<div class='col'><div class='ch'><span>📝 مسودة</span><span class='pill'>120</span></div>""" +
lcard("OUT-2026-0455","طلب تجديد تصاريح","الهيئة العامة للقوى","اليوم","صادر") +
lcard("OUT-2026-0454","خطاب تعريف راتب","بنك الخليج","أمس","صادر") + """</div>
<div class='col'><div class='ch'><span>✍️ بانتظار التوقيع</span><span class='pill'>63</span></div>""" +
lcard("OUT-2026-0450","مخاطبة بشأن عقد","وزارة الشؤون","منذ يومين","صادر","عاجل") +
lcard("OUT-2026-0448","رد على مخالفة","بلدية الكويت","منذ ٣ أيام","صادر") + """</div>
<div class='col'><div class='ch'><span>🖨️ بانتظار المسح</span><span class='pill'>91</span></div>""" +
lcard("OUT-2026-0442","تفويض مندوب","التأمينات","موقّع","بانتظار سكان") + """</div>
<div class='col'><div class='ch'><span>🚚 مع المندوب</span><span class='pill'>155</span></div>""" +
lcard("OUT-2026-0430","تسليم مستندات","الهيئة العامة","المندوب: خالد","منذ ٩ أيام","متأخّر") +
lcard("OUT-2026-0431","طلب موافقة","وزارة التجارة","المندوب: أحمد","منذ يومين") + """</div>
<div class='col'><div class='ch'><span>📬 مُسلَّم</span><span class='pill'>190</span></div>""" +
lcard("OUT-2026-0420","خطاب رسمي","وزارة الشؤون","تم التوصيل","بانتظار الإقرار") + """</div>
<div class='col'><div class='ch'><span>✅ مُستلَم/مؤرشف</span><span class='pill'>640</span></div>""" +
lcard("OUT-2026-0410","مخاطبة","بلدية الكويت","مستلم: م.العتيبي","موقّع ومؤرشف") + """</div>
</div>
""", 560)

# ---------- 3) Delivery tracking ----------
render('letter_03_delivery', top('سجل التسليم والمتابعة') + """
<div class='h'>سجل التسليم والمتابعة</div>
<div class='sub'>كل كتاب صادر يُتابَع حتى إثبات استلامه من الجهة — لا مزيد من كتب ضائعة</div>
<div class='alert'>🚨 <b>٤٨ كتاباً</b> سُلِّمت للمندوب ولم يرجع إثبات الاستلام خلال المدة المسموحة — بحاجة متابعة عاجلة.</div>
<div class='card'><table>
<tr><th>المرجع</th><th>الجهة</th><th>المندوب</th><th>سُلّم للمندوب</th><th>تاريخ التوصيل</th><th>المستلم + التوقيع</th><th>الحالة</th><th>التأخّر</th></tr>
<tr><td>OUT-2026-0430</td><td>الهيئة العامة للقوى</td><td>خالد سالم</td><td>2026-06-22</td><td>—</td><td>—</td><td><span class='badge b-red'>لم يُستلَم</span></td><td><b style='color:#c0392b'>٩ أيام</b></td></tr>
<tr><td>OUT-2026-0431</td><td>وزارة التجارة</td><td>أحمد عادل</td><td>2026-06-29</td><td>—</td><td>—</td><td><span class='badge b-amber'>مع المندوب</span></td><td>يومان</td></tr>
<tr><td>OUT-2026-0420</td><td>وزارة الشؤون</td><td>خالد سالم</td><td>2026-06-25</td><td>2026-06-27</td><td>م. العنزي · ✍️</td><td><span class='badge b-blue'>مُسلَّم — بانتظار الإقرار</span></td><td>—</td></tr>
<tr><td>OUT-2026-0410</td><td>بلدية الكويت</td><td>فهد ناصر</td><td>2026-06-20</td><td>2026-06-21</td><td>س. المطيري · ✍️ مختوم</td><td><span class='badge b-green'>مُستلَم ومؤرشف</span></td><td>—</td></tr>
</table></div>
<div class='alert info'>💡 عند تسليم الكتاب للجهة، يُلتقط <b>اسم المستلم + توقيعه/ختمه</b> (توقيع على الجهاز أو صورة إيصال) ويُرفَع — فيُقفَل الكتاب كـ«مُستلَم». كرون يومي ينبّه على المتأخرات.</div>
""", 640)

# ---------- 4) Letter form ----------
render('letter_04_form', top('نموذج الكتاب') + """
<div class='h'>OUT-2026-0430 — تسليم مستندات</div>
<div class='sub'>الجهة: الهيئة العامة للقوى العاملة · صادر</div>
<div class='btnrow'>
<span class='btn s'>✍️ إرسال للتوقيع</span><span class='btn s'>🖨️ تسجيل المسح الضوئي</span>
<span class='btn p'>🚚 تسليم للمندوب</span><span class='btn s'>📬 تأكيد التوصيل</span>
<span class='btn g'>✅ إقرار الاستلام</span><span class='btn s'>🗄️ أرشفة</span>
</div>
<div class='tabs'><span class='tab act'>التفاصيل</span><span class='tab'>سجل التسليم</span><span class='tab'>المرفقات (النسخة الموقّعة)</span><span class='tab'>المتابعة</span></div>
<div class='two'>
<div class='card'><h3>بيانات الكتاب</h3>
<div class='fld'><div class='k'>المرجع</div><div class='val'>OUT-2026-0430</div></div>
<div class='fld'><div class='k'>الاتجاه</div><div class='val'>صادر</div></div>
<div class='fld'><div class='k'>الجهة</div><div class='val'>الهيئة العامة للقوى العاملة</div></div>
<div class='fld'><div class='k'>القسم</div><div class='val'>الشؤون الحكومية</div></div>
<div class='fld'><div class='k'>تاريخ الإصدار</div><div class='val'>2026-06-22</div></div>
<div class='fld'><div class='k'>التصنيف/الوسم</div><div class='val'><span class='badge b-red'>عاجل</span> <span class='badge b-blue'>حكومي</span></div></div>
<div class='fld'><div class='k'>مسؤول المتابعة</div><div class='val'>عبدالله الخالدي</div></div>
</div>
<div class='card'><h3>حالة التسليم</h3>
<div class='fld'><div class='k'>المرحلة</div><div class='val'><span class='badge b-amber'>مع المندوب — متأخّر ٩ أيام</span></div></div>
<div class='fld'><div class='k'>المندوب</div><div class='val'>خالد سالم</div></div>
<div class='fld'><div class='k'>سُلّم للمندوب</div><div class='val'>2026-06-22</div></div>
<div class='fld'><div class='k'>تاريخ التوصيل</div><div class='val'>— (لم يُسجَّل)</div></div>
<div class='fld'><div class='k'>المستلم بالجهة</div><div class='val'>—</div></div>
<div class='fld'><div class='k'>توقيع/ختم الاستلام</div><div class='val'>— بحاجة رفع</div></div>
<div class='alert' style='margin-top:8px'>⚠️ تجاوز المدة — نبّه المندوب / اطلب إثبات الاستلام</div>
</div></div>
""", 620)

# ---------- 5) Sign & Scan workflow + Label ----------
render('letter_05_signscan', top('آلية التوقيع والمسح') + """
<div class='h'>آلية توقيع الكتاب ومسحه على السيستم</div>
<div class='sub'>من المسودة إلى نسخة موقّعة مؤرشفة رقمياً — بخطوات واضحة</div>
<div class='card'><div class='steps'>
<div class='step done'><div class='n'>1</div><div class='lb'>إنشاء وطباعة</div><div class='ds'>يُنشأ الكتاب ويُطبع بالمرجع والتاريخ</div></div>
<div class='step done'><div class='n'>2</div><div class='lb'>توقيع الإدارة</div><div class='ds'>يوقّع المسؤول على النسخة الورقية</div></div>
<div class='step done'><div class='n'>3</div><div class='lb'>مسح ضوئي (سكان)</div><div class='ds'>تُمسح النسخة الموقّعة</div></div>
<div class='step'><div class='n'>4</div><div class='lb'>رفع على السيستم</div><div class='ds'>ترفع النسخة → الحالة «موقّع وممسوح»</div></div>
<div class='step wait'><div class='n'>5</div><div class='lb'>تسليم للمندوب</div><div class='ds'>يُصرف للمندوب مع تتبّع التسليم</div></div>
</div></div>
<div class='flex'>
<div class='card grow'><h3>📱 مسار سريع عبر الجوال / QR</h3>
<div style='font-weight:700;font-size:13px;line-height:2.1'>
① يمسح المندوب/الموظف <b>QR الكتاب</b> من الليبل<br/>
② يلتقط صورة النسخة الموقّعة أو إيصال الاستلام<br/>
③ يوقّع المستلم على الشاشة (توقيع إلكتروني)<br/>
④ تُرفع تلقائياً وتُقفل مرحلة الكتاب<br/>
⑤ يصل إشعار لمسؤول المتابعة بالإقرار</div>
</div>
<div class='card' style='width:340px'><h3>🏷️ الليبل (مرجع + تاريخ + QR)</h3>
<div class='label' style='margin:0 auto'>
<div style='font-weight:800;font-size:15px'>CARE — مراسلات</div>
<div class='qr'></div>
<div style='font-weight:800;font-size:16px'>OUT-2026-0430</div>
<div style='font-weight:700;color:#555;font-size:13px'>صادر · 2026-06-22</div>
<div style='font-weight:700;color:#555;font-size:12px'>الهيئة العامة للقوى العاملة</div>
<div style='margin-top:6px'><span class='badge b-red'>عاجل</span></div>
</div></div></div>
""", 560)

# ---------- 6) Data quality ----------
def dq(n, txt, impact, cls):
    return f"<div class='dqitem'><div style='display:table-cell;width:90px;vertical-align:middle'><div class='dqn' style='color:{cls}'>{n}</div></div><div style='display:table-cell;vertical-align:middle;padding-right:14px'><div style='font-weight:800;font-size:13px'>{txt}</div><div style='color:#8a93a8;font-weight:700;font-size:11.5px'>{impact}</div></div><div style='display:table-cell;vertical-align:middle;text-align:left;width:90px'><span class='btn s'>إصلاح</span></div></div>"
render('letter_06_quality', top('فحص جودة البيانات') + """
<div class='h'>فحص الكتب — المشاكل المرصودة</div>
<div class='sub'>خانات تحتاج إلى مراجعة قبل الاعتماد على المتابعة والأرشفة</div>
<div class='card'>""" +
dq("1,734","كتب بلا تاريخ تسليم","التسليم غير مُتتبَّع — لا يمكن معرفة المستلَم فعلاً","#c0392b") +
dq("569","كتب بلا نسخة ممسوحة","لا يوجد إثبات رقمي موقّع","#e08a00") +
dq("431","كتب بلا مرحلة","لا تظهر في المسار الصحيح","#e08a00") +
dq("50","كتب بلا جهة (Contact)","لا يمكن المتابعة أو الفرز حسب الجهة","#2f6df6") +
dq("1","مرحلة «TEst» غير صالحة","مرحلة تجريبية يجب حذفها","#6a45e0") + """
</div>
<div class='alert info'>💡 بعد إضافة سير عمل التسليم، تُملأ تواريخ التسليم تلقائياً عند كل تسليم/إقرار — فتُقفل هذه الفجوة تدريجياً.</div>
""", 520)

# ---------- 7) Templates + Letterhead PDF ----------
def tpl(name, desc):
    return f"<div style='padding:10px 12px;border:1px solid #e7ebf3;border-radius:10px;margin-bottom:8px'><div style='font-weight:800;font-size:13px'>{name}</div><div style='color:#8a93a8;font-weight:700;font-size:11.5px'>{desc}</div></div>"
render('letter_07_templates', top('القوالب والترويسة') + """
<div class='h'>القوالب الجاهزة + الترويسة الرسمية</div>
<div class='sub'>أنشئ الكتاب بنقرة واحدة — تُدمج بيانات الموظف/الشركة تلقائياً وتُطبع بالترويسة</div>
<div class='flex'>
<div class='card grow'><h3>📄 قوالب جاهزة (Mail-merge)</h3>""" +
tpl("خطاب تعريف براتب","يُدرج اسم الموظف · الراتب · المسمّى تلقائياً") +
tpl("تفويض مندوب لمعاملة","اسم المندوب · رقم الإقامة · الجهة") +
tpl("طلب تجديد إقامة عامل","بيانات العامل من ملفه مباشرة") +
tpl("طلب تصريح عمل","رقم الملف الحكومي · الحصة") +
tpl("رد على مخالفة بلدية","رقم المخالفة · التاريخ") +
tpl("شهادة راتب للبنك","الراتب · تاريخ الالتحاق") + """
</div>
<div class='card' style='width:430px'><h3>🖨️ معاينة الطباعة (ترويسة رسمية)</h3>
<div style='border:1px solid #d7deea;border-radius:8px;padding:18px;background:#fff'>
<div style='display:table;width:100%;border-bottom:2px solid #e8564e;padding-bottom:8px;margin-bottom:12px'>
<div style='display:table-cell;font-weight:800;color:#e8564e;font-size:16px'>CARE<br/><span style='color:#1e2a44;font-size:10px'>شركة كير للخدمات</span></div>
<div style='display:table-cell;text-align:left;font-size:11px;color:#66708a;font-weight:700'>المرجع: OUT-2026-0455<br/>التاريخ: 2026-07-01</div>
</div>
<div style='text-align:center;font-weight:800;font-size:13px;margin-bottom:10px'>السادة / الهيئة العامة للقوى العاملة المحترمين</div>
<div style='font-size:12px;line-height:2;color:#333;font-weight:600'>تحية طيبة وبعد،،<br/>نفيدكم بأن الموظف <b>[محمد عبده]</b> يعمل لدينا بوظيفة <b>[عامل نظافة]</b> براتب شهري قدره <b>[85 د.ك]</b> منذ <b>[2024-03-01]</b>...</div>
<div style='display:table;width:100%;margin-top:20px'>
<div style='display:table-cell;width:90px;text-align:center'><div style='width:70px;height:70px;border:3px solid #000;margin:0 auto'></div><div style='font-size:10px;color:#888'>QR تحقّق</div></div>
<div style='display:table-cell;text-align:left;font-size:11px;font-weight:700'>مدير الموارد البشرية<br/><br/>....................<br/>التوقيع والختم</div>
</div></div></div></div>
""", 560)

# ---------- 8) Threading + SLA deadlines ----------
render('letter_08_thread', top('السلاسل والمواعيد') + """
<div class='h'>سلاسل الردود + المواعيد النهائية</div>
<div class='sub'>اربط الكتاب بما يردّ عليه — وتابع المهلة المطلوبة للرد</div>
<div class='flex'>
<div class='card grow'><h3>🧵 سلسلة المراسلة مع «الهيئة العامة للقوى العاملة»</h3>
<div style='border-right:3px solid #2f6df6;padding-right:14px'>
<div style='margin-bottom:14px'><span class='badge b-blue'>وارد · 2026-06-10</span><div style='font-weight:800;font-size:13px;margin-top:4px'>IN-2026-0088 — طلب استكمال مستندات ملف الحصة</div><div style='color:#8a93a8;font-size:11.5px;font-weight:700'>الجهة تطلب الرد خلال ١٥ يوماً</div></div>
<div style='margin-bottom:14px'><span class='badge b-green'>صادر (ردّنا) · 2026-06-18</span><div style='font-weight:800;font-size:13px;margin-top:4px'>OUT-2026-0430 — تسليم المستندات المطلوبة</div><div style='color:#8a93a8;font-size:11.5px;font-weight:700'>رد على IN-2026-0088</div></div>
<div><span class='badge b-purple'>وارد · بانتظار</span><div style='font-weight:800;font-size:13px;margin-top:4px'>بانتظار موافقة الجهة النهائية</div></div>
</div></div>
<div class='card' style='width:400px'><h3>⏰ المواعيد النهائية</h3>
<div class='alert'>🔴 <b>علينا الرد</b> — IN-2026-0091<br/>مخالفة بلدية · تبقّى <b>يومان</b> على انتهاء المهلة</div>
<div class='alert info'>🟡 <b>بانتظار رد الجهة</b> — OUT-2026-0430<br/>مضى ٩ أيام دون رد · متابعة مقترحة</div>
<div style='padding:10px;border:1px solid #eef1f6;border-radius:10px'>
<div style='font-weight:800;font-size:12.5px;margin-bottom:6px'>لوحة المهل:</div>
<div style='font-size:12px;font-weight:700;line-height:2'>🔴 متأخّر الرد: <b>3</b><br/>🟡 يستحق خلال ٣ أيام: <b>7</b><br/>🟢 ضمن المهلة: <b>21</b></div>
</div></div></div>
""", 540)

# ---------- 9) Delegate performance ----------
render('letter_09_delegates', top('أداء المندوبين') + """
<div class='h'>لوحة أداء المندوبين</div>
<div class='sub'>مساءلة ومتابعة — من يوصّل بسرعة ومن تتراكم عليه الكتب</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>6</div><div class='l'>مندوبون نشطون</div></div>
<div class='kpi amber'><div class='v'>155</div><div class='l'>كتب قيد التوصيل</div></div>
<div class='kpi red'><div class='v'>48</div><div class='l'>متأخرة</div></div>
<div class='kpi green'><div class='v'>2.3</div><div class='l'>متوسط أيام التوصيل</div></div>
<div class='kpi'><div class='v'>92%</div><div class='l'>نسبة إرجاع الإقرار</div></div>
<div class='kpi purple'><div class='v'>1,240</div><div class='l'>سُلّمت هذا العام</div></div>
</div>
<div class='card'><table>
<tr><th>المندوب</th><th>معه الآن</th><th>متوسط أيام التوصيل</th><th>نسبة إرجاع الإقرار</th><th>متأخرات</th><th>التقييم</th></tr>
<tr><td>أحمد عادل</td><td>12</td><td>1.4 يوم</td><td>98%</td><td>1</td><td><span class='badge b-green'>ممتاز</span></td></tr>
<tr><td>فهد ناصر</td><td>18</td><td>2.1 يوم</td><td>95%</td><td>3</td><td><span class='badge b-green'>جيد</span></td></tr>
<tr><td>خالد سالم</td><td>34</td><td>5.8 يوم</td><td>71%</td><td>22</td><td><span class='badge b-red'>يحتاج متابعة</span></td></tr>
<tr><td>سعود المطيري</td><td>9</td><td>1.9 يوم</td><td>96%</td><td>2</td><td><span class='badge b-green'>جيد</span></td></tr>
</table></div>
<div class='alert'>⚠️ المندوب <b>خالد سالم</b> عليه ٣٤ كتاباً ومتوسط توصيله ٥.٨ يوم و٢٢ متأخرة — إعادة توزيع أو مراجعة مقترحة.</div>
""", 560)

# ---------- 10) Physical archive + OCR search ----------
def hit(ref, snippet):
    return f"<div style='padding:11px 12px;border:1px solid #e7ebf3;border-radius:10px;margin-bottom:8px'><div style='font-weight:800;font-size:12.5px;color:#2f6df6'>{ref}</div><div style='font-size:12px;font-weight:600;color:#444;margin-top:3px'>{snippet}</div></div>"
render('letter_10_archive', top('الأرشيف والبحث') + """
<div class='h'>قراءة المرفق تلقائياً (OCR) + بحث بالنص الكامل</div>
<div class='sub'>بعد المسح: يقرأ النظام محتوى المرفق ويخزّنه — فتبحث داخله لاحقاً</div>
<div class='card'><div style='display:table;width:100%;border:2px solid #2f6df6;border-radius:10px;padding:10px 14px'>
<div style='display:table-cell'>🔎 <b style='font-size:14px'>«تجديد إقامة»</b></div>
<div style='display:table-cell;text-align:left;color:#8a93a8;font-weight:700;font-size:12px'>٣٤ نتيجة داخل نصوص الكتب الممسوحة</div>
</div>
<div style='margin-top:10px;background:#eef4ff;border:1px solid #cfe0ff;border-radius:8px;padding:8px 12px;font-weight:700;font-size:12px;color:#2a5bd7'>⚙️ عند رفع السكان: مسح ← <b>قراءة النص تلقائياً (OCR عربي/إنجليزي)</b> ← تخزين في حقل مفهرس ← جاهز للبحث</div></div>
<div class='flex'>
<div class='card grow'><h3>نتائج داخل الكتب (OCR عربي)</h3>""" +
hit("OUT-2026-0430","...بشأن <span style='background:#fff3b0'>تجديد إقامة</span> العامل محمد عبده رقم...") +
hit("OUT-2026-0388","...نأمل الموافقة على <span style='background:#fff3b0'>تجديد إقامة</span> العمالة المرفقة...") +
hit("IN-2026-0091","...يلزم استكمال رسوم <span style='background:#fff3b0'>تجديد الإقامة</span> خلال...") + """
</div>
<div class='card' style='width:380px'><h3>🗄️ موقع النسخة الورقية</h3>
<div style='text-align:center;padding:12px'>
<div style='width:80px;height:80px;border:3px solid #000;margin:8px auto'></div>
<div style='font-weight:800;font-size:15px'>OUT-2026-0430</div>
<div style='margin-top:10px;font-weight:700;font-size:13px;line-height:2'>
📍 المبنى: الإدارة العامة<br/>🗄️ الخزانة: A-3<br/>📁 الملف: صادر ٢٠٢٦ / حكومي<br/>🔖 الرف: 2</div>
<div style='margin-top:8px'><span class='badge b-green'>النسخة الورقية متوفرة</span></div>
</div></div></div>
""", 560)

# ---------- 11) Smart numbering + cross-module links + fees ----------
render('letter_11_links', top('الترقيم والربط') + """
<div class='h'>الترقيم الذكي + الربط بالمنظومة + الرسوم</div>
<div class='sub'>مرجع منظّم وفريد · ربط الكتاب بالموظف/المناقصة/الملف الحكومي · تتبّع الرسوم</div>
<div class='card'><h3>🔢 نظام الترقيم — يبقى الصادر كما هو</h3>
<div style='display:table;width:100%'>
<div style='display:table-cell;width:50%;text-align:center;border-left:1px solid #eef1f6;padding:6px'>
<div style='font-weight:800;font-size:12px;color:#2f6df6;margin-bottom:4px'>صادر (بدون تغيير)</div>
<div style='font-size:19px;font-weight:800;letter-spacing:1px'><span style='color:#e8564e'>Care</span>/<span style='color:#1a9f6d'>2026</span>/<span style='color:#e08a00'>7</span>/<span style='color:#7a5cf0'>1787</span></div>
<div style='color:#8a93a8;font-weight:700;font-size:11px;margin-top:4px'>Care / السنة / الشهر / التسلسل</div></div>
<div style='display:table-cell;width:50%;text-align:center;padding:6px'>
<div style='font-weight:800;font-size:12px;color:#12945f;margin-bottom:4px'>وارد (مقترح — صغير ومماثل)</div>
<div style='font-size:19px;font-weight:800;letter-spacing:1px'><span style='color:#e8564e'>In</span>/<span style='color:#1a9f6d'>2026</span>/<span style='color:#e08a00'>7</span>/<span style='color:#7a5cf0'>0001</span></div>
<div style='color:#8a93a8;font-weight:700;font-size:11px;margin-top:4px'>In / السنة / الشهر / التسلسل (عدّاد مستقل)</div></div>
</div></div>
<div class='flex'>
<div class='card grow'><h3>🔗 مرتبط بـ</h3>
<div style='font-weight:700;font-size:13px;line-height:2.3'>
👤 الموظف: <b>محمد عبده</b> — يظهر في ملفه ضمن «المراسلات»<br/>
📋 المناقصة: <b>T-2026-014 نظافة البلدية</b><br/>
🏛️ الملف الحكومي: <b>حصة الشؤون رقم 4471</b><br/>
🚗 معاملة مرتبطة: <b>تجديد إقامة عامل</b></div>
</div>
<div class='card' style='width:400px'><h3>💰 الرسوم الحكومية</h3>
<table><tr><th>البند</th><th>المبلغ</th><th>الحالة</th></tr>
<tr><td>رسم تجديد إقامة</td><td>10 د.ك</td><td><span class='badge b-green'>مدفوع</span></td></tr>
<tr><td>رسم تصريح عمل</td><td>150 د.ك</td><td><span class='badge b-amber'>غير مدفوع</span></td></tr>
<tr><td>طابع + تصديق</td><td>5 د.ك</td><td><span class='badge b-green'>مدفوع</span></td></tr></table>
<div style='text-align:left;margin-top:8px;font-weight:800'>الإجمالي: 165 د.ك · <span style='color:#e08a00'>المتبقي 150</span></div>
</div></div>
""", 560)



# ---------- 12) Notifications matrix ----------
def notifrow(trigger, to, channel, msg, cls):
    return f"<tr><td style='font-weight:800'>{trigger}</td><td><span class='badge {cls}'>{to}</span></td><td>{channel}</td><td style='font-size:12px;color:#555'>{msg}</td></tr>"
render('letter_12_notifications', top('الإشعارات والتذكيرات') + """
<div class='h'>الإشعارات والتذكيرات الذكية</div>
<div class='sub'>كل طرف يُخطَر في الوقت المناسب — وتذكيرات تلقائية للمتأخرات</div>
<div class='flex'>
<div class='card grow' style='background:#f0fbf5;border-color:#bfe8d2'><h3>🔔 إشعار طالب الكتاب</h3>
<div style='background:#fff;border-radius:10px;padding:12px;font-size:13px;font-weight:700;line-height:1.9'>
✅ كتابك <b>OUT-2026-0455</b> «خطاب تعريف براتب» <b>تم توقيعه ومسحه</b> وهو الآن <b style='color:#1a9f6d'>جاهز للاستلام</b> من إدارة المراسلات.<br/>
<span style='color:#8a93a8;font-size:11.5px'>→ يصل للموظف الذي طلب الكتاب فور اكتمال التوقيع</span></div></div>
<div class='card grow' style='background:#fff6f4;border-color:#ffd0c6'><h3>⏰ تذكير المندوب</h3>
<div style='background:#fff;border-radius:10px;padding:12px;font-size:13px;font-weight:700;line-height:1.9'>
⚠️ الكتاب <b>OUT-2026-0430</b> المُسلَّم إليك بتاريخ 2026-06-22 <b style='color:#c0392b'>لم تُرجِع نسخة الاستلام</b> من «الهيئة العامة للقوى العاملة».<br/>
<span style='color:#8a93a8;font-size:11.5px'>→ تذكير يتكرر كل يومين حتى رفع إثبات الاستلام</span></div></div>
</div>
<div class='card'><h3>📋 مصفوفة الإشعارات الكاملة</h3>
<table><tr><th>الحدث المُشغِّل</th><th>يُخطَر</th><th>القناة</th><th>الرسالة</th></tr>""" +
notifrow("اكتمل توقيع + مسح الكتاب","طالب الكتاب","تطبيق + بريد","كتابك جاهز للاستلام","b-green") +
notifrow("تسليم الكتاب للمندوب","المندوب","تطبيق + واتساب","استلمت كتاباً — يرجى التوصيل وإرجاع الإقرار","b-blue") +
notifrow("مضى X يوم بلا إقرار","المندوب","تذكير متكرر","لم تُرجِع نسخة الاستلام — ذكّرني","b-red") +
notifrow("تجاوز مهلة الإقرار","مسؤول المتابعة","تطبيق + بريد","كتاب متأخّر مع المندوب — تصعيد","b-red") +
notifrow("وصول كتاب وارد جديد","القسم المعني","تطبيق","كتاب وارد يحتاج إجراءً منك","b-purple") +
notifrow("اقتراب مهلة الرد للجهة","مسؤول المتابعة","تطبيق + بريد","علينا الرد خلال يومين","b-amber") +
notifrow("تم إقرار الاستلام","طالب الكتاب","تطبيق","تم تسليم كتابك واستلامه رسمياً ✅","b-green") +
notifrow("كتاب بانتظار التوقيع","المسؤول المخوّل","تطبيق","كتاب بانتظار توقيعك","b-amber") + """
</table></div>
<div class='alert info'>💡 كل الإشعارات <b>موجّهة للمعنيّ فقط</b> (لا تُرسل للجميع) — عبر تطبيق أودو + البريد + واتساب اختيارياً. التذكيرات تعمل بكرون تلقائي.</div>
""", 660)


# ---------- 13) Permissions / roles ----------
def prow(role, scope, c, r, u, d, extra):
    def m(x): return "<span style='color:#1a9f6d;font-weight:800'>✓</span>" if x else "<span style='color:#d0d5e0'>—</span>"
    return f"<tr><td style='font-weight:800'>{role}</td><td style='font-size:12px;color:#555'>{scope}</td><td style='text-align:center'>{m(c)}</td><td style='text-align:center'>{m(r)}</td><td style='text-align:center'>{m(u)}</td><td style='text-align:center'>{m(d)}</td><td style='font-size:11.5px;color:#8a93a8;font-weight:700'>{extra}</td></tr>"
render('letter_13_permissions', top('الصلاحيات والأدوار') + """
<div class='h'>الصلاحيات والأدوار</div>
<div class='sub'>أدمن بكامل الصلاحيات · وكل مستخدم يرى كتبه فقط — بحسب دوره</div>
<div class='flex'>
<div class='card grow' style='background:#fbf0ff;border-color:#e6ccff'><h3>👑 مدير المراسلات (Admin)</h3>
<div style='font-weight:700;font-size:12.5px;line-height:1.9'>يرى ويعدّل ويحذف <b>كل الكتب</b> · يدير القوالب والتصنيفات والمندوبين · يعتمد الإعدادات · يطّلع على السرّي.</div></div>
<div class='card grow' style='background:#eef7ff;border-color:#cfe4ff'><h3>🙍 المستخدم العادي (مُقدِّم الطلب)</h3>
<div style='font-weight:700;font-size:12.5px;line-height:1.9'>يُنشئ كتباً ويرى <b>كتبه هو فقط</b> التي قدّمها وحالتها · لا يرى كتب غيره.</div></div>
</div>
<div class='card'><h3>📋 مصفوفة الصلاحيات حسب الدور</h3>
<table><tr><th>الدور</th><th>نطاق الرؤية</th><th>إنشاء</th><th>قراءة</th><th>تعديل</th><th>حذف</th><th>ملاحظات</th></tr>""" +
prow("مدير المراسلات","كل الكتب + الإعدادات",1,1,1,1,"صلاحية كاملة + السرّي") +
prow("مُقدِّم الطلب","كتبه التي أنشأها فقط",1,1,0,0,"يتابع حالة كتبه") +
prow("المسؤول المخوّل بالتوقيع","الكتب المنتظرة توقيعه",0,1,1,0,"يوقّع فقط") +
prow("المندوب","الكتب المُسلَّمة إليه",0,1,1,0,"يرفع إثبات الاستلام") +
prow("مسؤول القسم","كتب قسمه",0,1,1,0,"متابعة قسمه") +
prow("مدقّق / قارئ","كل الكتب (قراءة فقط)",0,1,0,0,"للأرشيف والتدقيق") + """
</table></div>
<div class='flex'>
<div class='card grow' style='background:#fff6f4;border-color:#ffd0c6'><h3>🔒 قواعد الخصوصية (Record Rules)</h3>
<div style='font-weight:700;font-size:12px;line-height:1.9'>
• المستخدم العادي: <code>يرى الكتاب فقط إن كان هو مُنشئه أو مُقدّمه أو مسؤول متابعته</code><br/>
• المندوب: يرى فقط الكتب التي <code>delegate_id = مستخدمه</code><br/>
• الكتب المعلَّمة <b>«سرّي»</b>: للأدمن + مَن شورك معه صراحة فقط</div></div>
<div class='card' style='width:380px'><h3>⚙️ مجموعات المستخدمين</h3>
<div style='font-weight:700;font-size:12.5px;line-height:2.1'>
👑 Letters / Admin<br/>✍️ Letters / Signer<br/>🚚 Letters / Delegate<br/>🙍 Letters / User<br/>👁️ Letters / Read-only</div>
<div style='margin-top:6px;color:#8a93a8;font-weight:700;font-size:11.5px'>تُسند من إعدادات المستخدم — كأي موديول أودو</div></div>
</div>
""", 720)

print("ALL DONE")
