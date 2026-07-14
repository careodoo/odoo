# -*- coding: utf-8 -*-
"""CARE Project & Tasks Management System — mockups (wkhtmltoimage friendly, table-cell layout)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__))
CSS="""<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;font-family:'Cairo',Tahoma,sans-serif}
body{background:#eef1f6;color:#1d2433;direction:rtl}
.wrap{width:1180px;margin:0 auto;padding:18px}
.top{background:#15213b;color:#fff;border-radius:12px;padding:12px 18px;margin-bottom:14px}
.top .logo{font-weight:800;color:#f0663c;font-size:19px}
.top .crumb{color:#9fb0d0;font-weight:700;font-size:13px}
.h{font-size:22px;font-weight:800;margin:2px 0}
.sub{color:#7b8499;font-weight:700;font-size:13px;margin-bottom:14px}
.kpis{display:table;width:100%;border-spacing:10px 0;margin:0 -10px 14px}
.kpi{display:table-cell;width:16.6%;background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:12px;vertical-align:top;text-align:center}
.kpi .v{font-size:24px;font-weight:800}.kpi .l{color:#7b8499;font-weight:700;font-size:12px;margin-top:2px}
.kpi.red .v{color:#e2513f}.kpi.amber .v{color:#e08a00}.kpi.green .v{color:#1a9f6d}.kpi.blue .v{color:#2f6df6}.kpi.purple .v{color:#7a5cf0}.kpi.teal .v{color:#017e84}
.card{background:#fff;border:1px solid #e4e8f0;border-radius:14px;padding:16px;margin-bottom:14px}
.card h3{font-size:15px;margin-bottom:12px}
.row{display:table;width:100%;border-spacing:12px 0;margin:0 -12px}
.col{display:table-cell;vertical-align:top}
.alert{background:#fff4f2;border:1px solid #ffd4cc;color:#c0392b;border-radius:10px;padding:11px 14px;font-weight:700;font-size:13px;margin-bottom:12px}
.alert.info{background:#eef4ff;border-color:#cfe0ff;color:#2a5bd7}.alert.ok{background:#effaf3;border-color:#bfe8d2;color:#12945f}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f6f8fc;color:#66708a;text-align:right;padding:9px 10px;font-weight:800;font-size:12px;border-bottom:2px solid #e4e8f0}
td{padding:9px 10px;border-bottom:1px solid #eef1f6;font-weight:600}
.badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:800}
.b-red{background:#fdeceb;color:#c0392b}.b-amber{background:#fff3e0;color:#c47f00}.b-green{background:#e6f7ef;color:#12945f}
.b-blue{background:#e9f0ff;color:#2f6df6}.b-grey{background:#eef1f6;color:#66708a}.b-purple{background:#f0ebff;color:#6a45e0}.b-teal{background:#e1f5f5;color:#017e84}
.pcard{background:#fff;border:1px solid #e7ebf3;border-radius:12px;padding:12px;margin-bottom:10px;border-top:4px solid #2f6df6}
.pcard .pt{font-weight:800;font-size:14px;color:#15213b}
.pcard .pd{color:#7b8499;font-size:12px;font-weight:700;margin:2px 0 8px}
.mini{display:table;width:100%;text-align:center}.mini>div{display:table-cell}
.mini .mv{font-weight:800;font-size:16px}.mini .ml{font-size:10px;color:#8a93a8;font-weight:700}
.cols{display:table;width:100%;border-spacing:8px 0}
.kcol{display:table-cell;width:20%;background:#f6f8fc;border:1px solid #e4e8f0;border-radius:12px;padding:8px;vertical-align:top}
.kcol .ch{font-weight:800;font-size:12px;margin-bottom:8px;display:flex;justify-content:space-between}
.tc{background:#fff;border:1px solid #e7ebf3;border-radius:9px;padding:8px;margin-bottom:7px}
.tc .r{font-weight:800;font-size:11.5px;color:#2f3a57}.tc .t{font-size:11px;color:#7b8499;font-weight:700;margin-top:2px}
.tc .m{font-size:10px;margin-top:6px;color:#8a93a8;font-weight:700;display:flex;justify-content:space-between}
.av{width:22px;height:22px;border-radius:50%;background:#dfe5ef;display:inline-block;text-align:center;line-height:22px;font-size:10px;font-weight:800;color:#5a6b8c}
.step{display:table-cell;width:20%;text-align:center;position:relative;vertical-align:top;padding:0 4px}
.step .n{width:38px;height:38px;border-radius:50%;background:#2f6df6;color:#fff;font-weight:800;line-height:38px;margin:0 auto 6px}
.step.done .n{background:#1a9f6d}.step.wait .n{background:#c9d2e3;color:#5a6b8c}
.step .lb{font-weight:800;font-size:11.5px}.step .ds{color:#7b8499;font-size:10.5px;font-weight:700}
.tl{border-right:3px solid #2f6df6;padding-right:14px;margin-right:6px}
.tl .it{margin-bottom:12px}.tl .it .tt{font-weight:800;font-size:12.5px}.tl .it .td{color:#8a93a8;font-size:11px;font-weight:700}
.pill{display:inline-block;padding:4px 10px;border-radius:8px;background:#eef1f6;font-weight:800;font-size:11.5px}
.fld{margin-bottom:8px}.fld .k{color:#8a93a8;font-weight:700;font-size:11px}.fld .val{font-weight:800;font-size:13px}
.btn{display:inline-block;padding:7px 14px;border-radius:8px;font-weight:800;font-size:12px;margin-left:6px}
.btn.p{background:#2f6df6;color:#fff}.btn.g{background:#1a9f6d;color:#fff}.btn.r{background:#e2513f;color:#fff}.btn.s{background:#fff;border:1px solid #d4dae6;color:#3a4a66}
</style>"""
def top(c):
    return f"<div class='top'><span class='logo'>CARE • Projects</span> <span class='crumb'>· {c}</span><span style='float:left' class='crumb'>◐ نظام إدارة المشاريع والتاسكات</span></div>"
def render(name, inner, h=None):
    html=f"<html><head><meta charset='utf-8'>{CSS}</head><body><div class='wrap'>{inner}</div></body></html>"
    p=os.path.join(OUT,name+'.html');open(p,'w').write(html)
    cmd=['wkhtmltoimage','--enable-local-file-access','--quality','90','--width','1180','--encoding','utf-8']
    if h:cmd+=['--height',str(h)]
    cmd+=[p,os.path.join(OUT,name+'.png')];subprocess.run(cmd,capture_output=True);print('rendered',name)
def bar(pct,color):
    return f"<div style='background:#eef1f6;border-radius:6px;height:8px;margin-top:4px'><div style='background:{color};width:{pct}%;height:8px;border-radius:6px'></div></div>"

# 1) Command center
def pcard(t,d,w,v,tk,ov,badge,color):
    return f"<div class='pcard' style='border-top-color:{color}'><div class='pt'>{t}</div><div class='pd'>{d}</div><div class='mini'><div><div class='mv' style='color:#2f6df6'>{w}</div><div class='ml'>عامل</div></div><div><div class='mv' style='color:#017e84'>{v}</div><div class='ml'>سيارة</div></div><div><div class='mv' style='color:#7a5cf0'>{tk}</div><div class='ml'>تاسك</div></div><div><div class='mv' style='color:#e2513f'>{ov}</div><div class='ml'>متأخر</div></div></div><div style='margin-top:8px'>{badge}</div></div>"
render('pms_01_center', top('مركز المشاريع') + """
<div class='h'>مركز إدارة المشاريع والعقود</div>
<div class='sub'>كل مشروع مربوط بإدارة وعقد (Experience) — نظرة شاملة على العمال والسيارات والتاسكات</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>114</div><div class='l'>المشاريع</div></div>
<div class='kpi teal'><div class='v'>38</div><div class='l'>عقود نشطة</div></div>
<div class='kpi'><div class='v'>1,240</div><div class='l'>عمال موزّعون</div></div>
<div class='kpi purple'><div class='v'>96</div><div class='l'>سيارات</div></div>
<div class='kpi amber'><div class='v'>412</div><div class='l'>تاسكات مفتوحة</div></div>
<div class='kpi red'><div class='v'>47</div><div class='l'>متأخرة</div></div>
</div>
<div class='row'>
<div class='col'>""" +
pcard("مشروع نظافة بلدية الكويت","إدارة النظافة · عقد EXP-2026-014","210","18","32","5","<span class='badge b-blue'>نشط</span>","#2f6df6") +
pcard("حراسة المنشآت الحكومية","إدارة الأمن · عقد EXP-2025-041","88","6","14","2","<span class='badge b-green'>نشط</span>","#1a9f6d") + "</div><div class='col'>" +
pcard("صيانة وتنظيف المستشفيات","إدارة العمليات · عقد EXP-2026-007","145","12","21","9","<span class='badge b-amber'>يحتاج متابعة</span>","#e08a00") +
pcard("مشروع الزراعة التجميلية","إدارة الزراعة · عقد EXP-2025-033","64","9","11","1","<span class='badge b-blue'>نشط</span>","#017e84") + "</div><div class='col'>" +
pcard("نظافة مرافق التعليم","إدارة النظافة · عقد EXP-2026-022","96","7","18","6","<span class='badge b-red'>متأخر</span>","#e2513f") +
pcard("عقد قيد التجهيز","بانتظار ربط العقد","0","0","3","0","<span class='badge b-grey'>مسودة</span>","#9aa3b5") + "</div></div>",720)

# 2) Project 360
render('pms_02_project', top('بطاقة المشروع') + """
<div class='h'>مشروع نظافة بلدية الكويت</div>
<div class='sub'>إدارة النظافة · العقد: EXP-2026-014 · مدير المشروع: عبدالله الخالدي</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>210</div><div class='l'>عامل</div></div>
<div class='kpi teal'><div class='v'>18</div><div class='l'>سيارة</div></div>
<div class='kpi purple'><div class='v'>32</div><div class='l'>تاسك مفتوح</div></div>
<div class='kpi red'><div class='v'>5</div><div class='l'>متأخر</div></div>
<div class='kpi green'><div class='v'>92%</div><div class='l'>الإنجاز</div></div>
<div class='kpi amber'><div class='v'>3</div><div class='l'>طلبات معلّقة</div></div>
</div>
<div class='row'>
<div class='col'><div class='card'><h3>🔗 العقد المرتبط (Experience)</h3>
<div class='fld'><div class='k'>رقم العقد</div><div class='val'>EXP-2026-014</div></div>
<div class='fld'><div class='k'>العميل</div><div class='val'>بلدية الكويت</div></div>
<div class='fld'><div class='k'>العرض المصدر</div><div class='val'>Proposal PR-2026-088</div></div>
<div class='fld'><div class='k'>المدة</div><div class='val'>2026-01-01 → 2028-12-31</div></div>
<div class='fld'><div class='k'>القيمة</div><div class='val'>1,450,000 د.ك</div></div>
<div style='margin-top:6px'><span class='btn s'>فتح العقد ←</span></div></div></div>
<div class='col'><div class='card'><h3>🚗 السيارات (18)</h3>
<table><tr><th>اللوحة</th><th>النوع</th><th>الحالة</th></tr>
<tr><td>1-23456</td><td>بيك أب</td><td><span class='badge b-green'>يعمل</span></td></tr>
<tr><td>2-98765</td><td>كنس آلي</td><td><span class='badge b-green'>يعمل</span></td></tr>
<tr><td>3-45612</td><td>نقل عمال</td><td><span class='badge b-amber'>صيانة</span></td></tr></table>
<div style='margin-top:6px'><span class='btn s'>كل السيارات ←</span></div></div></div>
<div class='col'><div class='card'><h3>👷 العمال (210)</h3>
<div class='fld'><div class='k'>حسب المهنة</div><div class='val'>عامل نظافة 180 · سائق 18 · مشرف 12</div></div>
<div class='fld'><div class='k'>الحضور اليوم</div><div class='val'>198 / 210 (94%)</div></div>
<div class='fld'><div class='k'>الورديات</div><div class='val'>صباحي 120 · مسائي 90</div></div>
<div class='alert' style='margin-top:8px'>⚠️ 12 غياب اليوم — بحاجة تغطية</div>
<div><span class='btn s'>كشف العمال ←</span></div></div></div>
</div>
<div class='card'><h3>📋 آخر التاسكات في المشروع</h3>
<table><tr><th>التاسك</th><th>النوع</th><th>المسند إليه</th><th>البند</th><th>الاستحقاق</th><th>الحالة</th></tr>
<tr><td>استبدال ماكينة كنس معطلة</td><td><span class='badge b-blue'>مهمة</span></td><td>م. سالم</td><td>معدات</td><td>2026-07-03</td><td><span class='badge b-amber'>جارية</span></td></tr>
<tr><td>مذكرة نقص عمالة وردية مسائية</td><td><span class='badge b-purple'>مذكرة</span></td><td>الإدارة</td><td>موارد بشرية</td><td>2026-07-02</td><td><span class='badge b-red'>متأخرة</span></td></tr>
<tr><td>طلب صرف مواد تنظيف</td><td><span class='badge b-teal'>طلب داخلي</span></td><td>المخزن</td><td>مشتريات</td><td>2026-07-05</td><td><span class='badge b-green'>معتمد</span></td></tr></table></div>
""",860)

# 3) Task kanban
def tcard(r,t,who,cat,due,tag,tagc):
    return f"<div class='tc'><div class='r'>{r} <span class='badge {tagc}'>{tag}</span></div><div class='t'>{t}</div><div class='m'><span><span class='av'>{who}</span> {cat}</span><span>{due}</span></div></div>"
render('pms_03_kanban', top('لوحة التاسكات') + """
<div class='h'>لوحة التاسكات — كانبان محسّن</div>
<div class='sub'>أنواع متعددة (مهمة · مذكرة · كتاب داخلي · طلب داخلي · مراسلة) مع المسند والأولوية والبند</div>
<div class='cols'>
<div class='kcol'><div class='ch'><span>📥 جديدة</span><span class='pill'>8</span></div>""" +
tcard("T-1042","استبدال ماكينة كنس","م.س","معدات","اليوم","مهمة","b-blue") +
tcard("T-1043","طلب صرف مواد","أ.ع","مشتريات","غداً","طلب داخلي","b-teal") + """</div>
<div class='kcol'><div class='ch'><span>🏃 جارية</span><span class='pill'>14</span></div>""" +
tcard("T-1020","جدولة وردية مسائية","خ.س","موارد بشرية","2026-07-04","مهمة","b-blue") +
tcard("T-1021","مذكرة نقص عمالة","الإدارة","موارد بشرية","متأخر","مذكرة","b-purple") + """</div>
<div class='kcol'><div class='ch'><span>⏸️ معلّقة</span><span class='pill'>5</span></div>""" +
tcard("T-1009","طلب موافقة ميزانية","م.إ","مالية","بانتظار","طلب داخلي","b-teal") + """</div>
<div class='kcol'><div class='ch'><span>👀 مراجعة</span><span class='pill'>6</span></div>""" +
tcard("T-0998","كتاب داخلي للإدارة","الأمن","إداري","2026-07-02","كتاب داخلي","b-amber") + """</div>
<div class='kcol'><div class='ch'><span>✅ منجزة</span><span class='pill'>42</span></div>""" +
tcard("T-0980","صيانة سيارة 3-45612","الورشة","معدات","تم","مهمة","b-blue") + """</div>
</div>
<div class='alert info' style='margin-top:12px'>💡 كل تاسك يحمل: <b>النوع</b> · <b>المشروع/الإدارة</b> · <b>البند/الفئة</b> · <b>المسند إليه</b> · <b>الأولوية</b> · <b>الاستحقاق</b> — قابل للفرز والتجميع بأي منها.</div>
""",560)

# 4) Task form + Forward accept/reject + tracking
render('pms_04_forward', top('التاسك والإحالة') + """
<div class='h'>T-1021 — مذكرة نقص عمالة وردية مسائية</div>
<div class='sub'>المشروع: نظافة بلدية الكويت · البند: موارد بشرية · الأولوية: عالية</div>
<div style='margin-bottom:12px'><span class='btn g'>✅ إنجاز</span><span class='btn p'>➡️ إحالة (Forward)</span><span class='btn s'>💬 تعليق</span><span class='btn s'>🖇️ مرفق</span></div>
<div class='row'>
<div class='col'><div class='card'><h3>البيانات</h3>
<div class='fld'><div class='k'>أنشأها</div><div class='val'>خالد سالم (مشرف)</div></div>
<div class='fld'><div class='k'>المسند إليه حالياً</div><div class='val'>عبدالله الخالدي (مدير)</div></div>
<div class='fld'><div class='k'>النوع / البند</div><div class='val'>مذكرة · موارد بشرية</div></div>
<div class='fld'><div class='k'>الاستحقاق</div><div class='val' style='color:#c0392b'>2026-07-02 (متأخر يومان)</div></div>
</div>
<div class='card' style='background:#eef4ff;border-color:#cfe0ff'><h3>➡️ طلب إحالة معلّق</h3>
<div style='font-weight:700;font-size:12.5px;line-height:1.9'>أحال إليك <b>خالد سالم</b> هذا التاسك.<br/>السبب: «يتطلب موافقتك على التعيين».</div>
<div style='margin-top:8px'><span class='btn g'>قبول ✅</span><span class='btn r'>رفض ✖</span></div>
</div></div>
<div class='col'><div class='card'><h3>🧭 تتبّع كامل للتاسك</h3>
<div class='tl'>
<div class='it'><div class='tt'>أُنشئ بواسطة خالد سالم</div><div class='td'>2026-06-28 · أُسند إلى وحدة الموارد</div></div>
<div class='it'><div class='tt'>إحالة → عبدالله الخالدي</div><div class='td'>2026-06-30 · «للموافقة» — <span class='badge b-amber'>بانتظار القبول</span></div></div>
<div class='it'><div class='tt'>تعليق: بحاجة ميزانية إضافية</div><div class='td'>2026-06-30 · بواسطة الإدارة</div></div>
<div class='it'><div class='tt'>تصعيد تلقائي (متأخر)</div><div class='td'>2026-07-02 · إشعار للمدير</div></div>
</div></div></div>
</div>
<div class='alert info'>💡 عند الإحالة: يصل إشعار للمستلم يقبل/يرفض. القبول ينقل الملكية ويُسجَّل في التتبّع؛ الرفض يعيده مع السبب. كل خطوة موثّقة.</div>
""",760)

# 5) Department private task groups
render('pms_05_groups', top('مجموعات الإدارة') + """
<div class='h'>مجموعات التاسكات الخاصة بالإدارة</div>
<div class='sub'>مدير الإدارة ينشئ مجموعة يراها الأعضاء فقط — خصوصية كاملة</div>
<div class='row'>
<div class='col'><div class='card' style='border-top:4px solid #7a5cf0'><h3>🔒 لجنة السلامة — إدارة العمليات</h3>
<div class='pd' style='color:#7b8499;font-size:12px;font-weight:700;margin-bottom:8px'>٥ أعضاء · خاصة (لا يراها غيرهم)</div>
<div><span class='av'>ع</span> <span class='av'>م</span> <span class='av'>س</span> <span class='av'>ف</span> <span class='av'>ن</span></div>
<table style='margin-top:8px'><tr><th>التاسك</th><th>المسند</th><th>الحالة</th></tr>
<tr><td>تدقيق معدات الإطفاء</td><td>م.ع</td><td><span class='badge b-amber'>جارية</span></td></tr>
<tr><td>تدريب سلامة جديد</td><td>س.ف</td><td><span class='badge b-blue'>جديدة</span></td></tr></table></div></div>
<div class='col'><div class='card' style='border-top:4px solid #017e84'><h3>🔒 متابعة العقود — إدارة المشاريع</h3>
<div class='pd' style='color:#7b8499;font-size:12px;font-weight:700;margin-bottom:8px'>٤ أعضاء · خاصة</div>
<div><span class='av'>خ</span> <span class='av'>ع</span> <span class='av'>ر</span> <span class='av'>ط</span></div>
<table style='margin-top:8px'><tr><th>التاسك</th><th>المسند</th><th>الحالة</th></tr>
<tr><td>تجديد عقد EXP-2025-041</td><td>خ.ع</td><td><span class='badge b-red'>متأخرة</span></td></tr>
<tr><td>مراجعة غرامات مشروع</td><td>ر.ط</td><td><span class='badge b-amber'>جارية</span></td></tr></table></div></div>
</div>
<div class='alert info'>💡 المجموعة الخاصة: صلاحية الرؤية محصورة بالأعضاء فقط عبر قواعد سجل (Record Rules). المدير يضيف/يزيل الأعضاء ويحدد صلاحياتهم.</div>
""",560)

# 6) Manager overdue analytics
render('pms_06_overdue', top('لوحة المدير') + """
<div class='h'>لوحة المدير — التاسكات المتأخرة</div>
<div class='sub'>تفصيل المتأخرات حسب البند/الفئة والإدارة والمسند إليه</div>
<div class='kpis'>
<div class='kpi red'><div class='v'>47</div><div class='l'>متأخرة إجمالاً</div></div>
<div class='kpi amber'><div class='v'>18</div><div class='l'>تستحق خلال ٣ أيام</div></div>
<div class='kpi purple'><div class='v'>6</div><div class='l'>إحالات معلّقة</div></div>
<div class='kpi blue'><div class='v'>4.2</div><div class='l'>متوسط أيام التأخّر</div></div>
<div class='kpi teal'><div class='v'>9</div><div class='l'>إدارات متأثرة</div></div>
<div class='kpi green'><div class='v'>78%</div><div class='l'>الإنجاز في الموعد</div></div>
</div>
<div class='row'>
<div class='col'><div class='card'><h3>حسب البند / الفئة</h3>
<table><tr><th>البند</th><th>متأخر</th><th>النسبة</th></tr>
<tr><td>موارد بشرية</td><td>14</td><td><span class='badge b-red'>30%</span></td></tr>
<tr><td>معدات وصيانة</td><td>11</td><td><span class='badge b-amber'>23%</span></td></tr>
<tr><td>مشتريات</td><td>9</td><td><span class='badge b-amber'>19%</span></td></tr>
<tr><td>مالية</td><td>7</td><td><span class='badge b-blue'>15%</span></td></tr>
<tr><td>إداري</td><td>6</td><td><span class='badge b-grey'>13%</span></td></tr></table></div></div>
<div class='col'><div class='card'><h3>حسب الإدارة</h3>
<table><tr><th>الإدارة</th><th>متأخر</th><th>المسؤول</th></tr>
<tr><td>النظافة</td><td>16</td><td>ع.الخالدي</td></tr>
<tr><td>الأمن</td><td>9</td><td>م.العتيبي</td></tr>
<tr><td>العمليات</td><td>12</td><td>س.المطيري</td></tr>
<tr><td>الزراعة</td><td>5</td><td>ف.ناصر</td></tr></table></div></div>
</div>
<div class='alert'>🚨 «موارد بشرية» أعلى بند متأخّر (١٤) — يتركّز في مشروعَي النظافة والتعليم. اضغط للتفصيل.</div>
""",640)

# 7) Internal memos/letters/requests
render('pms_07_internal', top('الداخلية') + """
<div class='h'>المذكرات والكتب والطلبات الداخلية</div>
<div class='sub'>أنواع خاصة من التاسكات بسير اعتماد — بين الإدارات والأفراد</div>
<div class='row'>
<div class='col'><div class='card'><h3>📝 مذكرة داخلية</h3>
<div style='font-size:12px;font-weight:700;line-height:1.9'>من: مشرف موقع<br/>إلى: إدارة الموارد<br/>الموضوع: نقص عمالة<br/>الحالة: <span class='badge b-amber'>بانتظار الرد</span></div></div></div>
<div class='col'><div class='card'><h3>📄 كتاب داخلي</h3>
<div style='font-size:12px;font-weight:700;line-height:1.9'>من: إدارة الأمن<br/>إلى: الإدارة العامة<br/>مرجع: INT-2026-051<br/>الحالة: <span class='badge b-blue'>قيد المراجعة</span></div></div></div>
<div class='col'><div class='card'><h3>📥 طلب داخلي</h3>
<div style='font-size:12px;font-weight:700;line-height:1.9'>النوع: صرف مواد<br/>مقدّم من: موقع البلدية<br/>الاعتماد: مدير المشروع<br/>الحالة: <span class='badge b-green'>معتمد</span></div></div></div>
</div>
<div class='card'><h3>سير الاعتماد</h3><div style='display:table;width:100%'>
<div class='step done'><div class='n'>1</div><div class='lb'>إنشاء</div><div class='ds'>المُقدّم ينشئ الطلب</div></div>
<div class='step done'><div class='n'>2</div><div class='lb'>مراجعة الإدارة</div><div class='ds'>المشرف/المدير</div></div>
<div class='step'><div class='n'>3</div><div class='lb'>اعتماد</div><div class='ds'>صاحب الصلاحية</div></div>
<div class='step wait'><div class='n'>4</div><div class='lb'>تنفيذ</div><div class='ds'>الجهة المنفّذة</div></div>
<div class='step wait'><div class='n'>5</div><div class='lb'>إغلاق وأرشفة</div><div class='ds'>يُوثّق ويُرشّف</div></div>
</div></div>
<div class='alert info'>💡 كل نوع له مرجع تلقائي وسير اعتماد قابل للتخصيص، ويظهر ضمن التاسكات مع فلترة بالنوع.</div>
""",600)

# 8) Portal
render('pms_08_portal', top('البورتال') + """
<div class='h'>بورتال المشاريع — لمستخدمين خاصين</div>
<div class='sub'>كل مستخدم يرى فقط مشروعه وتاسكاته حسب صلاحيته — عملاء/شركاء/مشرفو مواقع</div>
<div class='row'>
<div class='col'><div class='card' style='border-top:4px solid #2f6df6'><h3>👤 المستخدم: مشرف موقع البلدية</h3>
<div style='font-size:12px;font-weight:700;line-height:2'>المشاريع المتاحة: <b>نظافة بلدية الكويت فقط</b><br/>الصلاحية: عرض + إنشاء طلبات + تحديث تاسكاته<br/>لا يرى: باقي المشاريع أو بيانات الشركة</div>
<table style='margin-top:8px'><tr><th>تاسكاتي</th><th>الحالة</th></tr>
<tr><td>رفع تقرير الحضور اليومي</td><td><span class='badge b-amber'>مطلوب</span></td></tr>
<tr><td>طلب صرف مواد تنظيف</td><td><span class='badge b-green'>معتمد</span></td></tr></table></div></div>
<div class='col'><div class='card' style='border-top:4px solid #017e84'><h3>🏛️ المستخدم: ممثل العميل (بلدية)</h3>
<div style='font-size:12px;font-weight:700;line-height:2'>يرى: تقدّم مشروعه · مؤشرات الأداء (SLA)<br/>يقدّم: ملاحظات/شكاوى كطلبات<br/>الصلاحية: قراءة + فتح طلب</div>
<div class='alert ok' style='margin-top:8px'>✅ رضا الخدمة هذا الشهر: 96% · SLA ملتزم</div></div></div>
</div>
<div class='card'><h3>🔑 مصفوفة صلاحيات البورتال</h3>
<table><tr><th>الدور</th><th>المشاريع</th><th>عرض</th><th>إنشاء طلب</th><th>تحديث تاسك</th><th>تقارير</th></tr>
<tr><td>مشرف موقع</td><td>مشروعه</td><td>✓</td><td>✓</td><td>✓ (تاسكاته)</td><td>—</td></tr>
<tr><td>ممثل عميل</td><td>مشروعه</td><td>✓</td><td>✓ (شكاوى)</td><td>—</td><td>✓ SLA</td></tr>
<tr><td>مقاول باطن</td><td>نطاقه</td><td>✓</td><td>✓</td><td>✓</td><td>—</td></tr></table></div>
<div class='alert info'>💡 يُبنى على بورتال أودو: كل مستخدم بورتال يُربط بمشروع/إدارة عبر قواعد سجل، فلا يرى إلا ما يخصّه.</div>
""",680)

# 9) Comprehensive Project 360
def tab(t,act=False):
    c="background:#15213b;color:#fff" if act else "background:#eef1f6;color:#5a6b8c"
    return f"<span style='display:inline-block;padding:6px 12px;border-radius:8px;font-weight:800;font-size:12px;margin:0 0 6px 6px;{c}'>{t}</span>"
render('pms_09_project360', top('بطاقة المشروع الشاملة') + """
<div class='h'>مشروع نظافة بلدية الكويت — نظرة شاملة</div>
<div class='sub'>إدارة النظافة · العقد EXP-2026-014 · مدير المشروع: عبدالله الخالدي</div>
<div style='margin-bottom:12px'>""" +
tab("نظرة عامة",True)+tab("العقد")+tab("العمال والمهارات")+tab("الحضور والانصراف")+tab("السيارات")+tab("طلبات الشراء")+tab("سندات التسليم/المواد")+tab("الطلبات الداخلية")+tab("التاسكات")+tab("المستندات")+tab("المالية/الربحية") + """
</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>210</div><div class='l'>عامل</div></div>
<div class='kpi green'><div class='v'>198</div><div class='l'>حاضر اليوم</div></div>
<div class='kpi teal'><div class='v'>18</div><div class='l'>سيارة</div></div>
<div class='kpi purple'><div class='v'>32</div><div class='l'>تاسك مفتوح</div></div>
<div class='kpi red'><div class='v'>7</div><div class='l'>إقامات تنتهي قريباً</div></div>
<div class='kpi amber'><div class='v'>19%</div><div class='l'>هامش الربح</div></div>
</div>
<div class='row'>
<div class='col'><div class='card'><h3>⏱️ حضور اليوم</h3>
<div class='fld'><div class='k'>حاضر / إجمالي</div><div class='val'>198 / 210 (94%)</div></div>
<div class='fld'><div class='k'>متأخر · غياب</div><div class='val'>6 · 12</div></div>
<div class='fld'><div class='k'>الورديات</div><div class='val'>صباحي 120 · مسائي 90</div></div>
<span class='btn s'>سجل البصمة ←</span></div></div>
<div class='col'><div class='card'><h3>🧰 المهارات (أعلى)</h3>
<table><tr><th>المهارة</th><th>عدد</th></tr>
<tr><td>تشغيل ماكينة كنس</td><td>24</td></tr>
<tr><td>تنظيف واجهات</td><td>15</td></tr>
<tr><td>قيادة شاحنة</td><td>18</td></tr></table>
<span class='btn s'>مصفوفة المهارات ←</span></div></div>
<div class='col'><div class='card'><h3>💰 المالية</h3>
<div class='fld'><div class='k'>إيراد شهري</div><div class='val'>120,800 د.ك</div></div>
<div class='fld'><div class='k'>تكلفة (أجور+أسطول+مواد)</div><div class='val'>97,850 د.ك</div></div>
<div class='fld'><div class='k'>الهامش</div><div class='val' style='color:#1a9f6d'>22,950 د.ك (19%)</div></div>
<span class='btn s'>P&L المشروع ←</span></div></div>
</div>
<div class='alert'>🛂 <b>7 عمال</b> تنتهي إقاماتهم خلال 30 يوماً في هذا المشروع — أُنشئت تاسكات تجديد تلقائياً.</div>
""",760)

# 10) Procurement & materials
render('pms_10_procurement', top('المشتريات والمواد') + """
<div class='h'>طلبات الشراء وسندات التسليم والمواد</div>
<div class='sub'>كل ما يخص المشروع من نظام المشتريات والمخزون والمبيعات في مكان واحد</div>
<div class='card'><h3>🧾 طلبات الشراء (Purchase Requests)</h3>
<table><tr><th>الطلب</th><th>البند</th><th>الكمية</th><th>المُقدّم</th><th>الاعتماد</th><th>الحالة</th></tr>
<tr><td>PR-2026-231</td><td>مواد تنظيف</td><td>200 كرتون</td><td>مشرف الموقع</td><td>مدير المشروع</td><td><span class='badge b-green'>معتمد</span></td></tr>
<tr><td>PR-2026-244</td><td>قفازات وكمامات</td><td>500 علبة</td><td>المخزن</td><td>—</td><td><span class='badge b-amber'>بانتظار الاعتماد</span></td></tr>
<tr><td>PR-2026-251</td><td>قطع غيار ماكينة</td><td>3</td><td>الورشة</td><td>مدير المشروع</td><td><span class='badge b-blue'>أمر شراء صادر</span></td></tr></table></div>
<div class='row'>
<div class='col'><div class='card'><h3>📦 سندات التسليم (Delivery Notes)</h3>
<table><tr><th>السند</th><th>المصدر</th><th>التاريخ</th><th>الاستلام</th></tr>
<tr><td>WH/OUT/0912</td><td>المخزن الرئيسي</td><td>2026-06-29</td><td><span class='badge b-green'>مستلم</span></td></tr>
<tr><td>PO/IN/0455</td><td>مورّد: النخبة</td><td>2026-06-30</td><td><span class='badge b-amber'>جزئي</span></td></tr>
<tr><td>SO/DEL/0771</td><td>عبر المبيعات → الموقع</td><td>2026-07-01</td><td><span class='badge b-grey'>بالطريق</span></td></tr></table></div></div>
<div class='col'><div class='card'><h3>🧴 استهلاك المواد مقابل الميزانية</h3>
<div class='fld'><div class='k'>مواد التنظيف</div><div class='val'>مستهلك 3,200 / ميزانية 4,000 د.ك</div>
<div style='background:#eef1f6;border-radius:6px;height:10px;margin-top:4px'><div style='background:#1a9f6d;width:80%;height:10px;border-radius:6px'></div></div></div>
<div class='fld' style='margin-top:8px'><div class='k'>قطع الغيار</div><div class='val'>مستهلك 1,850 / 2,000 د.ك</div>
<div style='background:#eef1f6;border-radius:6px;height:10px;margin-top:4px'><div style='background:#e08a00;width:92%;height:10px;border-radius:6px'></div></div></div>
<div class='alert' style='margin-top:10px'>⚠️ قطع الغيار قاربت الميزانية (92%)</div></div></div>
</div>
<div class='alert info'>💡 يُربط تلقائياً عبر الحساب التحليلي/المشروع: كل PR وPO وسند تسليم وحركة مخزون تحمل «المشروع» فتظهر هنا.</div>
""",720)

# 11) Attendance & Skills
render('pms_11_attendance', top('الحضور والمهارات') + """
<div class='h'>الحضور والانصراف + مهارات عمالة المشروع</div>
<div class='sub'>مباشر من نظام البصمة + مصفوفة مهارات العمال</div>
<div class='kpis'>
<div class='kpi green'><div class='v'>198</div><div class='l'>حاضر اليوم</div></div>
<div class='kpi red'><div class='v'>12</div><div class='l'>غياب</div></div>
<div class='kpi amber'><div class='v'>6</div><div class='l'>تأخير</div></div>
<div class='kpi blue'><div class='v'>94%</div><div class='l'>نسبة الحضور</div></div>
<div class='kpi purple'><div class='v'>1,240</div><div class='l'>ساعات الشهر</div></div>
<div class='kpi teal'><div class='v'>88</div><div class='l'>إضافي (ساعة)</div></div>
</div>
<div class='row'>
<div class='col'><div class='card'><h3>⏱️ سجل الحضور (اليوم)</h3>
<table><tr><th>العامل</th><th>دخول</th><th>خروج</th><th>الحالة</th></tr>
<tr><td>محمد عبده</td><td>06:02</td><td>14:10</td><td><span class='badge b-green'>حاضر</span></td></tr>
<tr><td>حسام خالد</td><td>06:48</td><td>—</td><td><span class='badge b-amber'>متأخر</span></td></tr>
<tr><td>راجيش كومار</td><td>—</td><td>—</td><td><span class='badge b-red'>غياب</span></td></tr>
<tr><td>أنيل جاريش</td><td>13:58</td><td>—</td><td><span class='badge b-blue'>وردية مسائية</span></td></tr></table></div></div>
<div class='col'><div class='card'><h3>🧰 مصفوفة المهارات</h3>
<table><tr><th>العامل</th><th>كنس آلي</th><th>واجهات</th><th>قيادة</th><th>سلامة</th></tr>
<tr><td>محمد عبده</td><td>★★★</td><td>★★</td><td>—</td><td>★★</td></tr>
<tr><td>حسام خالد</td><td>★★</td><td>★★★</td><td>★</td><td>★★★</td></tr>
<tr><td>راجيش كومار</td><td>—</td><td>★</td><td>★★★</td><td>★★</td></tr></table>
<div class='alert info' style='margin-top:8px'>💡 التعيين الذكي: يقترح العامل الأنسب للتاسك حسب مهارته وتوفره وحضوره.</div></div></div>
</div>
""",640)

# 12) Settings & per-manager permissions
def prow2(role, att,pur,fin,wrk,veh,tsk):
    def m(x): return "<span style='color:#1a9f6d;font-weight:800'>✓</span>" if x else "<span style='color:#d0d5e0'>—</span>"
    return f"<tr><td style='font-weight:800'>{role}</td><td style='text-align:center'>{m(att)}</td><td style='text-align:center'>{m(pur)}</td><td style='text-align:center'>{m(fin)}</td><td style='text-align:center'>{m(wrk)}</td><td style='text-align:center'>{m(veh)}</td><td style='text-align:center'>{m(tsk)}</td></tr>"
render('pms_12_settings', top('الإعدادات والصلاحيات') + """
<div class='h'>الإعدادات وصلاحيات مدير المشروع</div>
<div class='sub'>إعدادات لكل شيء + تحكّم دقيق: كل مدير يرى ما يخصّه فقط، قسماً بقسم</div>
<div class='row'>
<div class='col'><div class='card'><h3>⚙️ إعدادات الموديول</h3>
<div style='font-weight:700;font-size:12.5px;line-height:2.1'>
📁 أنواع التاسكات (مهمة/مذكرة/كتاب/طلب/مراسلة)<br/>
🏷️ البنود والفئات<br/>
🪜 مراحل التاسكات (Kanban)<br/>
📋 قوالب التاسكات المتكررة<br/>
⏫ قواعد التصعيد والمهل<br/>
🌐 صلاحيات البورتال<br/>
🔗 ربط العقود (Experience) والحسابات التحليلية</div></div></div>
<div class='col'><div class='card'><h3>🔒 خصوصية البيانات</h3>
<div style='font-weight:700;font-size:12.5px;line-height:2.1'>
• كل مدير مشروع يرى <b>مشاريعه فقط</b> (Record Rules).<br/>
• <b>البيانات المالية/الهوامش</b> مخفية عن المشرفين الميدانيين.<br/>
• التاسكات <b>السرّية</b> للمصرّح لهم فقط.<br/>
• المجموعات الخاصة للأعضاء فقط.</div>
<div class='alert ok' style='margin-top:8px'>✅ كل خانة قابلة للتفعيل/الإخفاء لكل دور</div></div></div>
</div>
<div class='card'><h3>👁️ مصفوفة رؤية مدير المشروع (قابلة للضبط)</h3>
<table><tr><th>الدور</th><th>الحضور</th><th>المشتريات</th><th>المالية</th><th>العمال</th><th>السيارات</th><th>التاسكات</th></tr>""" +
prow2("مدير المشروع",1,1,1,1,1,1) +
prow2("مشرف الموقع",1,1,0,1,0,1) +
prow2("منسّق المشتريات",0,1,0,0,0,1) +
prow2("محاسب المشروع",0,1,1,0,1,0) +
prow2("ممثل العميل (بورتال)",0,0,0,0,0,1) + """
</table></div>
""",640)

# 13) Labor compliance (iqamas/permits)
render('pms_13_compliance', top('امتثال العمالة') + """
<div class='h'>امتثال العمالة — الإقامات والتصاريح لكل مشروع</div>
<div class='sub'>جوهر عملك كـ«كفيل» — تنبيه مبكر يمنع الغرامات + ربط بملف الحصة</div>
<div class='kpis'>
<div class='kpi red'><div class='v'>7</div><div class='l'>إقامات تنتهي ≤30 يوم</div></div>
<div class='kpi amber'><div class='v'>14</div><div class='l'>تصاريح عمل تنتهي</div></div>
<div class='kpi blue'><div class='v'>3</div><div class='l'>بطاقات مدنية</div></div>
<div class='kpi purple'><div class='v'>210/230</div><div class='l'>المنشور/الحصة</div></div>
<div class='kpi green'><div class='v'>198</div><div class='l'>تأمين GOSI ساري</div></div>
<div class='kpi teal'><div class='v'>20</div><div class='l'>حصة متاحة</div></div>
</div>
<div class='card'><h3>🛂 وثائق تنتهي قريباً (تُولّد تاسك تجديد تلقائياً)</h3>
<table><tr><th>العامل</th><th>الوثيقة</th><th>الانتهاء</th><th>المتبقي</th><th>الحالة</th></tr>
<tr><td>محمد عبده</td><td>الإقامة</td><td>2026-07-18</td><td><b style='color:#c0392b'>17 يوم</b></td><td><span class='badge b-red'>تاسك تجديد</span></td></tr>
<tr><td>راجيش كومار</td><td>تصريح عمل</td><td>2026-07-25</td><td>24 يوم</td><td><span class='badge b-amber'>قيد المتابعة</span></td></tr>
<tr><td>أنيل جاريش</td><td>البطاقة المدنية</td><td>2026-08-05</td><td>35 يوم</td><td><span class='badge b-blue'>مجدول</span></td></tr>
<tr><td>سونيل راج</td><td>الإقامة</td><td>2026-07-12</td><td><b style='color:#c0392b'>11 يوم</b></td><td><span class='badge b-red'>عاجل</span></td></tr></table></div>
<div class='alert info'>💡 مربوط بملف القوى العاملة (PAM/الشؤون): الحصة مقابل المنشور فعلاً + تنبيه عند تجاوز الحصة أو قرب انتهاء التأشيرات.</div>
""",620)


# 14) Project materials ledger
render('pms_14_materials', top('مخزون المشروع') + """
<div class='h'>مخزون المشروع — الاستلام والسحب التدريجي</div>
<div class='sub'>يُزوَّد شهرياً حسب طلبه · يسحب تدريجياً · لا يتجاوز المتاح</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>24</div><div class='l'>صنف</div></div>
<div class='kpi teal'><div class='v'>4,180</div><div class='l'>قيمة المخزون د.ك</div></div>
<div class='kpi red'><div class='v'>3</div><div class='l'>تحت الحد الأدنى</div></div>
<div class='kpi amber'><div class='v'>68%</div><div class='l'>استهلاك الشهر</div></div>
<div class='kpi purple'><div class='v'>6</div><div class='l'>مواقع فرعية</div></div>
<div class='kpi green'><div class='v'>~9</div><div class='l'>أيام حتى النفاد</div></div>
</div>
<div class='card'><h3>📦 أرصدة الأصناف (مستلَم − مسحوب = المتاح)</h3>
<table><tr><th>الصنف</th><th>مستلَم</th><th>مسحوب</th><th>المتاح الآن</th><th>الحد الأدنى</th><th>الحالة</th></tr>
<tr><td>سائل تنظيف أرضيات</td><td>200 لتر</td><td>150</td><td><b>50</b></td><td>40</td><td><span class='badge b-green'>جيد</span></td></tr>
<tr><td>أكياس قمامة كبيرة</td><td>500 كرتون</td><td>470</td><td><b style='color:#c0392b'>30</b></td><td>60</td><td><span class='badge b-red'>أعِد الطلب</span></td></tr>
<tr><td>قفازات</td><td>300 علبة</td><td>120</td><td><b>180</b></td><td>50</td><td><span class='badge b-green'>جيد</span></td></tr>
<tr><td>مطهّر مركّز</td><td>120 لتر</td><td>96</td><td><b style='color:#c47f00'>24</b></td><td>25</td><td><span class='badge b-amber'>قارب الحد</span></td></tr></table>
<div style='margin-top:8px'><span class='btn p'>سحب / توزيع</span><span class='btn s'>إصدار سند تسليم</span><span class='btn s'>طلب تزويد شهري</span></div></div>
<div class='alert'>⚠️ «أكياس القمامة» تحت الحد الأدنى — النظام يقترح طلب تزويد تلقائي بناءً على استهلاك آخر ٣ أشهر.</div>
""",620)

# 15) Constrained delivery note
render('pms_15_delivery_note', top('سند التسليم') + """
<div class='h'>سند تسليم مواد — مقيّد بالرصيد المتاح</div>
<div class='sub'>يُحدّد الكميات ويطبع — والنظام يمنع تجاوز المتاح فعلياً</div>
<div class='row'>
<div class='col'><div class='card'><h3>بيانات السند</h3>
<div class='fld'><div class='k'>رقم السند</div><div class='val'>DN-2026-0342</div></div>
<div class='fld'><div class='k'>المشروع</div><div class='val'>نظافة بلدية الكويت</div></div>
<div class='fld'><div class='k'>الموقع المستلِم</div><div class='val'>موقع حولي — فرع 2</div></div>
<div class='fld'><div class='k'>التاريخ</div><div class='val'>2026-07-01</div></div>
<div class='fld'><div class='k'>المستلِم + التوقيع</div><div class='val'>م. العنزي · ✍️</div></div>
</div></div>
<div class='col' style='width:62%'><div class='card'><h3>الأصناف</h3>
<table><tr><th>الصنف</th><th>المتاح</th><th>الكمية المطلوبة</th><th>الحالة</th></tr>
<tr><td>سائل تنظيف أرضيات</td><td>50 لتر</td><td>30</td><td><span class='badge b-green'>✓ ضمن المتاح</span></td></tr>
<tr><td>قفازات</td><td>180 علبة</td><td>40</td><td><span class='badge b-green'>✓ ضمن المتاح</span></td></tr>
<tr style='background:#fff4f2'><td>أكياس قمامة</td><td>30 كرتون</td><td style='color:#c0392b;font-weight:800'>50</td><td><span class='badge b-red'>✖ يتجاوز المتاح — مرفوض</span></td></tr></table>
<div class='alert' style='margin-top:8px'>🚫 لا يمكن إصدار السند: الكمية المطلوبة من «أكياس القمامة» (50) تتجاوز المتاح (30). صحّح الكمية أو اطلب تزويداً.</div>
<div style='margin-top:6px'><span class='btn p'>🖨️ طباعة السند</span><span class='btn s'>حفظ مسودة</span></div></div></div>
</div>
<div class='alert info'>💡 كل سحب ينقص الرصيد فوراً، وكل سند يُحفظ في سجل المشروع بمرجع وباركود.</div>
""",600)

# 16) Assets & custody
render('pms_16_assets', top('الأصول والعُهدة') + """
<div class='h'>أصول ومعدات المشروع (عُهدة على المدير)</div>
<div class='sub'>تُقيّد في نظام الأصول (المالية) + عُهدة — إرجاع/استبدال/إخلاء طرف</div>
<div class='kpis'>
<div class='kpi blue'><div class='v'>14</div><div class='l'>أصل</div></div>
<div class='kpi teal'><div class='v'>28,400</div><div class='l'>القيمة د.ك</div></div>
<div class='kpi purple'><div class='v'>12</div><div class='l'>في عهدتي</div></div>
<div class='kpi amber'><div class='v'>1</div><div class='l'>للصيانة</div></div>
<div class='kpi green'><div class='v'>1</div><div class='l'>مُرجَع</div></div>
<div class='kpi red'><div class='v'>0</div><div class='l'>مفقود/تالف</div></div>
</div>
<div class='card'><h3>🧰 سجل الأصول</h3>
<table><tr><th>الأصل</th><th>باركود</th><th>القيمة</th><th>الحالة</th><th>إجراء</th></tr>
<tr><td>ماكينة كنس آلية</td><td>AST-0912</td><td>6,500</td><td><span class='badge b-blue'>في عهدتي</span></td><td><span class='btn s'>إرجاع</span> <span class='btn s'>استبدال</span></td></tr>
<tr><td>مولّد كهرباء</td><td>AST-0913</td><td>3,200</td><td><span class='badge b-amber'>صيانة</span></td><td><span class='btn s'>متابعة</span></td></tr>
<tr><td>جهاز ضغط ماء</td><td>AST-0914</td><td>1,800</td><td><span class='badge b-green'>مُرجَع للشركة</span></td><td><span class='btn s'>إخلاء طرف ✓</span></td></tr></table></div>
<div class='alert info'>💡 عند نقل/إنهاء مدير المشروع: يُولّد النظام <b>كشف إخلاء طرف تلقائي</b> بكل الأصول والعُهد المفتوحة، يوقّعه المدير الجديد فتُنقل المسؤولية. كل أصل له QR للجرد الميداني.</div>
""",600)

# 17) Petty cash + cover
render('pms_17_pettycash', top('العُهدة النقدية') + """
<div class='h'>العُهدة النقدية والنثريات</div>
<div class='sub'>يصرف بتوثيق كامل · يرى المتبقّي · يغلق ويطبع الكفر للمالية</div>
<div class='kpis'>
<div class='kpi teal'><div class='v'>1,500</div><div class='l'>قيمة العهدة د.ك</div></div>
<div class='kpi amber'><div class='v'>1,130</div><div class='l'>مصروف</div></div>
<div class='kpi green'><div class='v'>370</div><div class='l'>المتبقّي</div></div>
<div class='kpi blue'><div class='v'>مفتوحة</div><div class='l'>الحالة</div></div>
<div class='kpi purple'><div class='v'>9</div><div class='l'>مستندات</div></div>
<div class='kpi red'><div class='v'>18</div><div class='l'>يوم منذ الفتح</div></div>
</div>
<div class='row'>
<div class='col' style='width:64%'><div class='card'><h3>🧾 بنود المصروف (بصور المستندات)</h3>
<table><tr><th>البيان</th><th>التصنيف</th><th>المبلغ</th><th>المستند</th></tr>
<tr><td>صيانة ماكينة كنس</td><td>صيانة</td><td>220</td><td><span class='badge b-green'>🖼️ مرفق</span></td></tr>
<tr><td>وقود احتياطي</td><td>محروقات</td><td>150</td><td><span class='badge b-green'>🖼️ مرفق</span></td></tr>
<tr><td>أدوات نثرية</td><td>نثريات</td><td>90</td><td><span class='badge b-green'>🖼️ مرفق</span></td></tr>
<tr><td>مواصلات طارئة</td><td>مواصلات</td><td>70</td><td><span class='badge b-amber'>بلا مستند</span></td></tr></table>""" +
bar(75,'#e08a00') + """<div style='font-size:12px;font-weight:700;color:#8a93a8;margin-top:4px'>صُرف 1,130 من 1,500 (75%)</div>
<div style='margin-top:8px'><span class='btn p'>+ إضافة مصروف</span><span class='btn g'>إغلاق العهدة</span><span class='btn s'>🖨️ طباعة الكفر والبيان</span></div></div></div>
<div class='col'><div class='card'><h3>📑 الكفر (غلاف البيان)</h3>
<div style='border:2px solid #d7deea;border-radius:8px;padding:12px;text-align:center'>
<div style='font-weight:800;color:#f0663c'>CARE — بيان عُهدة نقدية</div>
<div style='width:70px;height:70px;border:3px solid #000;margin:8px auto'></div>
<div style='font-weight:800'>PC-2026-058</div>
<div style='font-size:12px;font-weight:700;line-height:1.9;margin-top:6px'>المشروع: نظافة البلدية<br/>المدير: ع. الخالدي<br/>العهدة: 1,500 · مصروف: 1,130<br/>المتبقّي: 370 د.ك</div>
<div style='margin-top:6px'><span class='badge b-amber'>بانتظار اعتماد المالية</span></div>
</div></div></div>
</div>
<div class='alert info'>💡 لا صرف فوق المتبقّي · تنبيه العهدة المفتوحة طويلاً · ربط بالحساب التحليلي للمشروع · اعتماد مالي + تدقيق عشوائي.</div>
""",720)

# 18) Fuel
render('pms_18_fuel', top('المحروقات') + """
<div class='h'>المحروقات واستهلاك سيارات المشروع</div>
<div class='sub'>تعبئة · استهلاك · كفاءة · كشف شذوذ</div>
<div class='kpis'>
<div class='kpi teal'><div class='v'>3,240</div><div class='l'>لتر هذا الشهر</div></div>
<div class='kpi blue'><div class='v'>1,180</div><div class='l'>تكلفة د.ك</div></div>
<div class='kpi green'><div class='v'>8.4</div><div class='l'>كم/لتر (متوسط)</div></div>
<div class='kpi red'><div class='v'>2</div><div class='l'>تنبيه شذوذ</div></div>
<div class='kpi amber'><div class='v'>18</div><div class='l'>سيارة</div></div>
<div class='kpi purple'><div class='v'>92%</div><div class='l'>ضمن الحد</div></div>
</div>
<div class='card'><h3>⛽ استهلاك حسب السيارة</h3>
<table><tr><th>السيارة</th><th>تعبئة (لتر)</th><th>المسافة (كم)</th><th>الكفاءة</th><th>الحالة</th></tr>
<tr><td>1-23456 بيك أب</td><td>420</td><td>3,700</td><td>8.8</td><td><span class='badge b-green'>طبيعي</span></td></tr>
<tr><td>2-98765 كنس آلي</td><td>560</td><td>2,100</td><td>3.8</td><td><span class='badge b-blue'>معدّة ثقيلة</span></td></tr>
<tr style='background:#fff4f2'><td>3-45612 نقل عمال</td><td>640</td><td>1,900</td><td>3.0</td><td><span class='badge b-red'>🚩 استهلاك مرتفع</span></td></tr></table></div>
<div class='alert'>🚩 السيارة 3-45612: استهلاك مرتفع مقابل مسافة قليلة — تحقّق (تسريب/استخدام غير مصرّح). كشف الشذوذ يقارن التعبئة بسعة الخزان والمسافة.</div>
""",560)

print("ALL DONE")
