# -*- coding: utf-8 -*-
"""Adaptive Pricing Wizard — visual mockups (wkhtmltoimage friendly)."""
import os, subprocess
OUT = os.path.dirname(os.path.abspath(__file__)); W = 1200

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DejaVu Sans',Arial,sans-serif;background:#eef2f7;color:#0f172a;width:1200px}
.top{background:#0b1220;color:#fff;height:50px;padding:0 20px;line-height:50px}
.top .b{font-weight:bold;color:#7dd3fc;font-size:16px}
.top .x{float:right;color:#94a3b8;font-size:20px}
.wrap{padding:20px 24px}
.h1{font-size:22px;font-weight:bold;margin-bottom:2px}
.sub{color:#64748b;font-size:13px;margin-bottom:16px}
.steps{margin-bottom:18px}
.st{display:inline-block;color:#94a3b8;font-size:13px;margin-right:8px}
.st .n{display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;border-radius:50%;background:#e2e8f0;color:#64748b;margin-right:5px;font-size:12px}
.st.on{color:#4f46e5;font-weight:bold}.st.on .n{background:#4f46e5;color:#fff}
.st.done .n{background:#10b981;color:#fff}
.st .ar{color:#cbd5e1;margin:0 4px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 1px 3px rgba(15,23,42,.05);padding:16px;margin:0 14px 14px 0}
.model{width:265px;padding:18px;cursor:pointer}
.model.on{border:2px solid #4f46e5;background:#f5f6ff}
.model .ic{font-size:26px}.model .t{font-weight:bold;font-size:15px;margin:8px 0 3px}.model .d{color:#64748b;font-size:12px;line-height:1.5}
.model .bf{margin-top:8px;font-size:11px;color:#4338ca;background:#eef2ff;border-radius:6px;padding:3px 7px;display:inline-block}
table{border-collapse:collapse;width:100%}
th{background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase;text-align:left;padding:8px 10px;border-bottom:1px solid #e2e8f0}
td{padding:9px 10px;border-bottom:1px solid #eef2f7;font-size:13px}
.inp{display:inline-block;border:1px solid #cbd5e1;border-radius:7px;padding:6px 10px;font-size:13px;background:#fbfdff;min-width:90px}
.lbl{font-size:12px;color:#475569;font-weight:600;display:block;margin:10px 0 4px}
.btn{display:inline-block;border-radius:8px;padding:9px 16px;font-size:13px;border:1px solid #cbd5e1;background:#fff;color:#0f172a;margin-right:8px}
.btn.p{background:#4f46e5;border-color:#4f46e5;color:#fff;font-weight:bold}
.chip{display:inline-block;background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;border-radius:7px;padding:3px 9px;font-size:12px;margin:2px}
.badge{display:inline-block;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:bold}
.bg-green{background:#dcfce7;color:#166534}.bg-amber{background:#fef3c7;color:#92400e}.bg-red{background:#fee2e2;color:#991b1b}.bg-blue{background:#dbeafe;color:#1e40af}
.panel{background:#0b1220;color:#e2e8f0;border-radius:12px;padding:14px 16px}
.panel .big{font-size:22px;font-weight:bold;color:#fff}.panel .s{font-size:12px;color:#94a3b8}
.kv{font-size:13px;line-height:26px}.kv b{color:#475569;display:inline-block;width:150px;font-weight:600}
.right{text-align:right}.center{text-align:center}.small{font-size:12px;color:#64748b}
.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:8px;padding:8px 12px;font-size:12px;margin-top:8px}
.radio{display:inline-block;border:1px solid #cbd5e1;border-radius:8px;padding:7px 12px;font-size:13px;margin-right:8px;color:#475569}
.radio.on{border-color:#4f46e5;background:#eef2ff;color:#3730a3;font-weight:bold}
.sec{font-weight:bold;font-size:13px;color:#334155;margin:6px 0 8px;border-bottom:1px solid #eef2f7;padding-bottom:6px}
"""

def shell(title, steps_html, body):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Pricing Wizard</span><span class='x'>×</span></div>
<div class='wrap'><div class='h1'>{title}</div>{steps_html}{body}</div></body></html>"""

def steps(active):
    names = ['Service & model','Pricing inputs','Margin & scenarios','Review & apply']
    out = "<div class='steps'>"
    for i,n in enumerate(names):
        cls = 'on' if i==active else ('done' if i<active else '')
        mark = '✓' if i<active else str(i+1)
        out += f"<span class='st {cls}'><span class='n'>{mark}</span>{n}</span>"
        if i<3: out += "<span class='ar'>→</span>"
    return out+"</div>"

def panel(cost, margin, price, extra=''):
    return (f"<div class='panel' style='width:1150px;margin-top:6px'><table style='color:#e2e8f0'><tr>"
            f"<td style='border:none'><div class='s'>COST</div><div class='big'>{cost}</div></td>"
            f"<td style='border:none'><div class='s'>MARGIN</div><div class='big'>{margin}</div></td>"
            f"<td style='border:none'><div class='s'>PRICE</div><div class='big'>{price}</div></td>"
            f"{extra}</tr></table></div>")

screens=[]

# 1) MODEL PICKER
models=[
 ("👷","Manpower-based","التكلفة على أساس العمال: رواتب + بدلات + إقامة + زي. السعر لكل عامل/شهر.","الأمن · النظافة بعمالة دائمة"),
 ("⏱️","Hourly","تسعير بالساعة: تكلفة الساعة × الساعات. حد أدنى + وقت إضافي.","صيانة · خدمات مؤقتة"),
 ("📍","Per-visit","تسعير بالزيارة: تكلفة الزيارة × عدد الزيارات/شهر + مواد لكل زيارة.","تعقيم · مكافحة حشرات"),
 ("📦","Lump-sum / General","سعر إجمالي ثابت: تجميع التكاليف (عمالة+مواد+معدات+overhead) ثم هامش.","مشروع لمرة · توريد"),
 ("📐","Per-unit","تسعير بالوحدة: م²/قطعة × تكلفة الوحدة. للأعمال المقاسة.","تنظيف واجهات بالم² · غسيل سجاد"),
 ("🔁","Retainer","اشتراك شهري متكرر: باقة ثابتة شهرياً مع نطاق محدد.","عقود إدارة مرافق"),
]
cards="".join([f"<div class='card model {'on' if i==0 else ''}'><div class='ic'>{ic}</div><div class='t'>{t}</div><div class='d'>{d}</div><div class='bf'>مناسب لـ: {bf}</div></div>" for i,(ic,t,d,bf) in enumerate(models)])
body=f"""<div class='sub'>اختر الخدمة ونموذج الفوترة المناسب — كل نموذج بيفتح حقول تسعير مختلفة</div>
<label class='lbl'>الخدمة</label><span class='inp' style='min-width:280px'>Cleaner – day shift ▾</span>
&nbsp;&nbsp;<label class='lbl' style='display:inline'>العميل</label> <span class='inp'>Ministry of Health ▾</span>
<div style='margin-top:14px'>{cards}</div>
<div style='margin-top:6px'><span class='btn'>إلغاء</span><span class='btn p'>التالي → إدخال التسعير</span></div>"""
screens.append(("pw1_model","Pricing Wizard — اختيار نموذج الفوترة", shell("Pricing Wizard", steps(0), body)))

# 2) MANPOWER
rows=[("Cleaner – day",40,"199.0","+12","24%","275.0","11,000"),
      ("Cleaner – night",16,"215.0","+15","20%","287.5","4,600"),
      ("Supervisor",4,"420.0","+6","30%","608.6","2,434")]
tr="".join([f"<tr><td>{r[0]}</td><td class='center'>{r[1]}</td><td class='right'>{r[2]}</td><td class='center small'>{r[3]}</td><td class='center'><span class='badge bg-green'>{r[4]}</span></td><td class='right'>{r[5]}</td><td class='right'><b>{r[6]}</b></td></tr>" for r in rows])
build="".join([f"<div class='kv'><b>{k}</b> {v}</div>" for k,v in [("Salary","155.0"),("Residency","18.0"),("Accommodation","20.0"),("Uniform","6.0"),("Insurance","6.0"),("+ Add-ons (mat/transport)","12.0")]])
body=f"""<div class='sub'>نموذج: <span class='badge bg-blue'>Manpower-based</span> · التكلفة مجمّدة من Cost Book العميل</div>
<div class='card' style='width:730px'>
<div class='sec'>الأدوار والعمالة</div>
<table><tr><th>الدور</th><th class='center'>عدد</th><th class='right'>تكلفة/عامل (مجمّدة)</th><th class='center'>+بدلات</th><th class='center'>هامش</th><th class='right'>سعر/عامل</th><th class='right'>إجمالي/شهر</th></tr>{tr}</table>
<div style='margin-top:8px'><span class='btn'>+ دور</span>
<label class='lbl' style='display:inline-block;margin-right:14px'>نسبة المشرف</label><span class='inp'>1 : 15</span>
<label class='lbl' style='display:inline-block;margin-right:14px'>وقت إضافي</label><span class='inp'>×1.5</span></div>
</div>
<div class='card' style='width:380px'>
<div class='sec'>تفصيل التكلفة (للدور المحدد)</div>{build}
<div class='kv' style='border-top:1px solid #eef2f7;margin-top:6px;padding-top:6px'><b>إجمالي التكلفة/عامل</b> <b>211.0</b></div>
<div class='warn'>ⓘ التكلفة مأخوذة من Cost Book «Ministry of Health» وقت الإنشاء — تعديل الكتالوج لاحقاً مش هيأثر.</div>
</div>
{panel("KWD 9,260","KWD 8,774 (49%)","KWD 18,034 / شهر")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي → الهامش والسيناريوهات</span></div>"""
screens.append(("pw2_manpower","Pricing Wizard — تسعير العمالة", shell("Pricing Wizard", steps(1), body)))

# 3) HOURLY
body=f"""<div class='sub'>نموذج: <span class='badge bg-blue'>Hourly</span> · للخدمات المؤقتة والصيانة</div>
<div class='card' style='width:560px'>
<div class='sec'>مدخلات التسعير بالساعة</div>
<label class='lbl'>تكلفة الساعة (محمّلة)</label><span class='inp'>3.250 KWD</span>
<label class='lbl'>الساعات المقدّرة / شهر</label><span class='inp'>520</span>
<label class='lbl'>حد أدنى للفاتورة (ساعات)</label><span class='inp'>100</span>
<label class='lbl'>مضاعف الوقت الإضافي</label><span class='inp'>×1.5</span>
<label class='lbl'>استراتيجية الهامش</label><span class='radio'>تكلفة+%</span><span class='radio on'>هامش مستهدف 28%</span>
</div>
<div class='card' style='width:540px'>
<div class='sec'>الناتج</div>
<table><tr><th>البند</th><th class='right'>القيمة</th></tr>
<tr><td>تكلفة الساعة</td><td class='right'>3.250</td></tr>
<tr><td>سعر الساعة (هامش 28%)</td><td class='right'><b>4.514</b></td></tr>
<tr><td>ساعات/شهر</td><td class='right'>520</td></tr>
<tr><td>سعر الوقت الإضافي/ساعة</td><td class='right'>6.771</td></tr>
<tr style='background:#f8fafc'><td><b>الإجمالي الشهري</b></td><td class='right'><b>2,347 KWD</b></td></tr></table>
</div>
{panel("3.250 / ساعة","28%","4.514 / ساعة","<td style='border:none'><div class='s'>الشهري</div><div class='big'>2,347</div></td>")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي →</span></div>"""
screens.append(("pw3_hourly","Pricing Wizard — تسعير بالساعة", shell("Pricing Wizard", steps(1), body)))

# 4) PER-VISIT
body=f"""<div class='sub'>نموذج: <span class='badge bg-blue'>Per-visit</span> · للتعقيم ومكافحة الحشرات والزيارات الدورية</div>
<div class='card' style='width:560px'>
<div class='sec'>مدخلات الزيارة</div>
<label class='lbl'>تكلفة الزيارة (عمالة+معدات)</label><span class='inp'>28.0 KWD</span>
<label class='lbl'>مواد لكل زيارة</label><span class='inp'>9.5 KWD</span>
<label class='lbl'>عدد الزيارات / شهر</label><span class='inp'>12</span>
<label class='lbl'>مدة الزيارة</label><span class='inp'>3 ساعات</span>
<label class='lbl'>الهامش المستهدف</label><span class='inp'>30%</span>
</div>
<div class='card' style='width:540px'>
<div class='sec'>الناتج</div>
<table><tr><th>البند</th><th class='right'>القيمة</th></tr>
<tr><td>إجمالي تكلفة الزيارة</td><td class='right'>37.5</td></tr>
<tr><td>سعر الزيارة (هامش 30%)</td><td class='right'><b>53.6</b></td></tr>
<tr><td>زيارات/شهر</td><td class='right'>12</td></tr>
<tr style='background:#f8fafc'><td><b>الإجمالي الشهري</b></td><td class='right'><b>643 KWD</b></td></tr>
<tr><td>الإجمالي السنوي</td><td class='right'>7,716 KWD</td></tr></table>
</div>
{panel("37.5 / زيارة","30%","53.6 / زيارة","<td style='border:none'><div class='s'>سنوي</div><div class='big'>7,716</div></td>")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي →</span></div>"""
screens.append(("pw4_visit","Pricing Wizard — تسعير بالزيارة", shell("Pricing Wizard", steps(1), body)))

# 5) LUMP-SUM
build="".join([f"<tr><td>{k}</td><td class='right'>{v}</td></tr>" for k,v in [("عمالة","4,200"),("مواد","1,850"),("معدات","900"),("نقل","350"),("Overhead 8%","584")]])
body=f"""<div class='sub'>نموذج: <span class='badge bg-blue'>Lump-sum / General</span> · سعر إجمالي ثابت للمشروع</div>
<div class='card' style='width:560px'>
<div class='sec'>تجميع التكلفة</div>
<table><tr><th>المكوّن</th><th class='right'>التكلفة</th></tr>{build}
<tr style='background:#f8fafc'><td><b>إجمالي التكلفة</b></td><td class='right'><b>7,884</b></td></tr></table>
<label class='lbl'>الهامش المستهدف</label><span class='inp'>22%</span>
<label class='lbl'>تقريب السعر</label><span class='inp'>10 KWD</span>
</div>
<div class='card' style='width:540px'>
<div class='sec'>الناتج</div>
<div class='kv'><b>إجمالي التكلفة</b> 7,884 KWD</div>
<div class='kv'><b>الهامش (22%)</b> 2,224 KWD</div>
<div class='kv'><b>السعر الثابت</b> <b style='font-size:18px;color:#4f46e5'>10,110 KWD</b></div>
<div class='warn' style='margin-top:10px'>سعر ثابت واحد للمشروع — مايتجزّأش لكل وحدة.</div>
</div>
{panel("7,884","22% · 2,224","10,110 ثابت")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي →</span></div>"""
screens.append(("pw5_lump","Pricing Wizard — سعر إجمالي", shell("Pricing Wizard", steps(1), body)))

# 6) PER-UNIT
body=f"""<div class='sub'>نموذج: <span class='badge bg-blue'>Per-unit</span> · للأعمال المقاسة (م²، قطعة...)</div>
<div class='card' style='width:560px'>
<div class='sec'>مدخلات الوحدة</div>
<label class='lbl'>نوع الوحدة</label><span class='inp'>متر مربع (م²) ▾</span>
<label class='lbl'>الكمية</label><span class='inp'>12,000</span>
<label class='lbl'>تكلفة الوحدة</label><span class='inp'>0.220 KWD</span>
<label class='lbl'>الهامش المستهدف</label><span class='inp'>26%</span>
<label class='lbl'>حد أدنى للأمر</label><span class='inp'>500 KWD</span>
</div>
<div class='card' style='width:540px'>
<div class='sec'>الناتج</div>
<table><tr><th>البند</th><th class='right'>القيمة</th></tr>
<tr><td>تكلفة/م²</td><td class='right'>0.220</td></tr>
<tr><td>سعر/م² (هامش 26%)</td><td class='right'><b>0.297</b></td></tr>
<tr><td>الكمية</td><td class='right'>12,000 م²</td></tr>
<tr style='background:#f8fafc'><td><b>الإجمالي</b></td><td class='right'><b>3,568 KWD</b></td></tr></table>
</div>
{panel("0.220 / م²","26%","0.297 / م²","<td style='border:none'><div class='s'>الإجمالي</div><div class='big'>3,568</div></td>")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي →</span></div>"""
screens.append(("pw6_unit","Pricing Wizard — تسعير بالوحدة", shell("Pricing Wizard", steps(1), body)))

# 7) MARGIN & SCENARIOS
body=f"""<div class='sub'>طبّق استراتيجية الهامش على كل الخدمات + قارن السيناريوهات</div>
<div style='margin-bottom:10px'>
<span class='radio'>تكلفة + %</span><span class='radio on'>هامش مستهدف</span><span class='radio'>سعر مستهدف</span><span class='radio'>يدوي</span>
<span class='chip'>هامش عام: 24%</span><span class='chip'>تقريب: 1 KWD</span><span class='chip'>حد أدنى للهامش (Guard): 10%</span></div>
<div class='card' style='width:560px'>
<div class='sec'>السيناريوهات</div>
<div class='kv'><span class='radio'>Economy · 15%</span> 196,400 KWD</div>
<div class='kv'><span class='radio on'>Standard · 24%</span> 214,800 KWD</div>
<div class='kv'><span class='radio'>Premium · 32%</span> 233,900 KWD</div>
<div style='margin-top:8px'><span class='btn'>حفظ سيناريو</span><span class='btn'>مقارنة</span></div>
</div>
<div class='card' style='width:540px'>
<div class='sec'>تنبيهات</div>
<div class='kv'><span class='badge bg-red'>⚠ 1</span> خدمة هامشها 18% &lt; الحد 20% → تحتاج موافقة مدير</div>
<div class='kv'><span class='badge bg-green'>✓</span> باقي الخدمات ضمن الحدود</div>
</div>
{panel("KWD 159,600","24% · 50,400","KWD 214,800")}
<div style='margin-top:8px'><span class='btn'>← رجوع</span><span class='btn p'>التالي → المراجعة</span></div>"""
screens.append(("pw7_margin","Pricing Wizard — الهامش والسيناريوهات", shell("Pricing Wizard", steps(2), body)))

# 8) REVIEW & APPLY
rows=[("Cleaner – day/night","Manpower","56 عامل","18,034 / شهر","216,408"),
      ("Façade cleaning","Per-unit","12,000 م²","—","3,568"),
      ("Deep disinfection","Per-visit","12 زيارة","643 / شهر","7,716"),
      ("AC maintenance","Hourly","520 ساعة","2,347 / شهر","28,164")]
tr="".join([f"<tr><td>{r[0]}</td><td><span class='badge bg-blue'>{r[1]}</span></td><td>{r[2]}</td><td class='right'>{r[3]}</td><td class='right'><b>{r[4]}</b></td></tr>" for r in rows])
body=f"""<div class='sub'>مراجعة كل الخدمات بنماذجها المختلفة قبل التطبيق على العرض</div>
<div class='card' style='width:1150px'>
<table><tr><th>الخدمة</th><th>النموذج</th><th>الأساس</th><th class='right'>دوري</th><th class='right'>إجمالي سنوي</th></tr>{tr}
<tr style='background:#f8fafc'><td colspan='4'><b>الإجمالي السنوي</b></td><td class='right'><b style='font-size:16px;color:#4f46e5'>255,856 KWD</b></td></tr></table>
<div style='margin-top:10px'><span class='chip'>التكلفة 194,500</span><span class='chip'>الهامش 61,356 (24%)</span><span class='chip'>عمولة 2,100</span><span class='chip'>القيمة المتوقعة (×60%) 153,513</span></div>
</div>
<div style='margin-top:6px'><span class='btn'>← رجوع</span><span class='btn'>حفظ كمسودة</span><span class='btn p'>تطبيق على العرض ✓</span></div>"""
screens.append(("pw8_review","Pricing Wizard — المراجعة والتطبيق", shell("Pricing Wizard", steps(3), body)))

# render + gallery
links=[]
for fn,title,html in screens:
    hp=os.path.join(OUT,fn+".html"); pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width",
        "--width",str(W),"--quality","92",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp); links.append((fn+".png",title)); print("rendered",fn)
cards="".join([f"<div style='margin:0 0 26px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}'><img src='{f}' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(links)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care — Adaptive Pricing Wizard Mockups</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0}}.w{{max-width:1000px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}</style></head>
<body><div class='w'><h1>Adaptive Pricing Wizard — Mockups</h1>
<div class='s'>{len(links)} screens · نماذج فوترة مختلفة (عمالة/ساعة/زيارة/إجمالي/وحدة) · اضغط أي صورة لتكبيرها · <a href='index.html'>← العروض</a> · <a href='portal.html'>البوابة</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"pricing.html"),"w",encoding="utf-8").write(gal)
print("pricing gallery:",len(links))
