# -*- coding: utf-8 -*-
"""Mockups: Passport Archive system (archive board, bulk scan check-out/in) + printed custody receipt."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1280

def barcode(seed=7,h=26):
    v=seed;ws=[]
    for i in range(34):
        v=(v*1103515245+12345)>>3 & 7;ws.append(1+(v%3))
    return "<div style='display:inline-flex;align-items:flex-end'>"+"".join(f"<span style='display:inline-block;width:{w}px;height:{h}px;background:{'#111' if i%2==0 else '#fff'}'></span>" for i,w in enumerate(ws))+"</div>"

def qr(seed=29,px=3):
    n=21;v=seed;grid=""
    def fb(r,c): return (1<=r<=7 and 1<=c<=7) or (1<=r<=7 and n-7<=c<=n-1) or (n-7<=r<=n-1 and 1<=c<=7)
    for r in range(n):
        row=""
        for c in range(n):
            v=(v*1103515245+12345)>>5 & 0xFFFF
            on=(r in(1,7) or c in(1,7) or (3<=r<=5 and 3<=c<=5) or (3<=r<=5 and n-6<=c<=n-4) or (n-6<=r<=n-4 and 3<=c<=5)) if fb(r,c) else (v%100)<45
            row+=f"<td style='width:{px}px;height:{px}px;background:{'#111' if on else '#fff'}'></td>"
        grid+=f"<tr>{row}</tr>"
    return f"<table style='border-collapse:collapse;border:3px solid #fff'>{grid}</table>"

CSS="""
body{margin:0;background:#f1f5f9;font-family:'Cairo','Segoe UI',Arial,sans-serif}
.top{background:#0f2b5b;color:#fff;padding:12px 20px;font-size:14px;display:flex;justify-content:space-between}
.top .b{font-weight:bold}.top .c{opacity:.85;font-size:12px}
.wrap{padding:18px 26px;direction:rtl}
.h1{font-size:21px;font-weight:bold;color:#0f2b5b;margin:0 0 3px}
.sub{color:#64748b;font-size:13px;margin-bottom:14px}
.tile{display:inline-block;vertical-align:top;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 12px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:21px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px;margin:0 9px 12px 0;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.ct{font-weight:bold;color:#0f2b5b;margin-bottom:9px;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{background:#f1f5f9;border:1px solid #e2e8f0;padding:7px;text-align:right}
td{border:1px solid #e2e8f0;padding:7px;text-align:right}
.center{text-align:center}
.badge{display:inline-block;border-radius:20px;padding:1px 9px;font-size:11px;color:#fff}
.g{background:#21b07b}.r{background:#e25563}.o{background:#f59e0b}.b{background:#3a7afe}.p{background:#8b5cf6}.s{background:#64748b}
.cap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#075985;margin-top:8px;line-height:1.8}
.cap b{color:#0c4a6e}
.kv{font-size:12.5px;padding:4px 0;border-bottom:1px dashed #eef2f7}
.kv b{color:#334155}
.scan{background:#0f172a;color:#5eead4;border-radius:8px;padding:8px 12px;font-family:monospace;font-size:12px;direction:ltr;margin:3px 0}
.idea{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#9a3412;margin:10px 9px 0 0}
.step{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:9px;padding:5px 9px;font-size:12px;margin:2px;font-weight:bold}
.arr{color:#94a3b8;font-weight:bold;margin:0 2px}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span>◐ موظف الأرشيف ▾</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(d): return "".join(f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in d)
S=[]

# ---- Screen 1: Passport Archive board ----
rows=[("PP-001824","سونام باهادور","NP · نيبال","09823xxxx","2027-03","داخل الأرشيف · رف B-12","b","g"),
      ("PP-001825","راج كومار","IN · الهند","K48xxxx","2026-08 ⚠","مع المندوب (إقامات)","p","o"),
      ("PP-001826","محمد علي","BD · بنغلاديش","BX91xxxx","2025-12","خارج — سفر إجازة","o","r"),
      ("PP-001827","جون أوتينو","KE · كينيا","KE77xxxx","2028-01","داخل الأرشيف · رف A-03","b","g"),
      ("PP-001828","عمران خان","PK · باكستان","PK33xxxx","2026-07 ⚠","سفر نهائي (مؤرشف)","s","s")]
tr="".join(f"<tr><td><b>{r[0]}</b> {barcode(seed=i+3,h=16)}</td><td>{r[1]}</td><td class='small'>{r[2]}</td><td class='center'>{r[3]}</td><td class='center'>{r[4]}</td><td><span class='badge {r[6]}'>●</span> {r[5]}</td></tr>" for i,r in enumerate(rows))
b=f"""<div class='sub'>كل جواز له باركود ملصق · حالته وموقعه وسجل حركته · تنبيهات الانتهاء والتجديد لموظف الأرشيف</div>
{tiles([('إجمالي الجوازات','1,284','#0f2b5b'),('داخل الأرشيف','1,061','#21b07b'),('خارج (سفر/إجازة)','142','#f59e0b'),('مع المندوب (إقامات)','61','#8b5cf6'),('تنتهي ≤90 يوم','77','#f59e0b'),('منتهية','9','#e25563')])}
<div class='card' style='width:780px'><div class='ct'>سجل الجوازات (الأرشيف)</div>
<table><tr><th>باركود الجواز</th><th>الموظف</th><th>الجنسية</th><th class='center'>رقم الجواز</th><th class='center'>الانتهاء</th><th>الموقع / الحالة</th></tr>{tr}</table></div>
<div class='card' style='width:400px'><div class='ct'>تنبيهات موظف الأرشيف</div>
<div class='kv'><b>⚠ تنتهي خلال 30 يوم</b> 14 جواز</div><div class='kv'><b>⚠ تنتهي خلال 90 يوم</b> 77 جواز</div><div class='kv'><b>⛔ منتهية</b> 9 — تحتاج تجديد فوري</div><div class='kv'><b>📤 خارجة منذ >30 يوم</b> 6 (متابعة)</div>
<div class='cap'><b>⚙️</b> تذكيرات تلقائية بالتجديد قبل 90/60/30 يوم؛ كل تنبيه قابل للضغط لعرض القائمة. يظهر في ملف كل موظف: حالة الجواز (داخل الأرشيف/مع مَن) وسجله الكامل.</div></div>"""
S.append(("pp_archive","أرشيف الجوازات",shell("نظام أرشيف الجوازات","Employees › Archive › Passports",b)))

# ---- Screen 2: Bulk scan check-out / check-in ----
b=f"""<div class='sub'>سحب/إرجاع بالجملة عبر مسح الباركود — المندوب يسحب عدة جوازات للإقامات، أو إرجاعها بعد العودة/الإنجاز</div>
<div class='card' style='width:560px'><div class='ct'>📷 مسح الباركودات (Bulk Scan)</div>
<div class='scan'>✓ PP-001825 — راج كومار · scanned</div>
<div class='scan'>✓ PP-001830 — بير تامانج · scanned</div>
<div class='scan'>✓ PP-001841 — أنيل ثابا · scanned</div>
<div class='scan' style='color:#fca5a5'>✗ PP-002999 — غير موجود بالأرشيف</div>
<div class='kv' style='margin-top:8px'><b>عدد الجوازات الممسوحة:</b> 3 ✓ / 1 ✗</div></div>
<div class='card' style='width:420px'><div class='ct'>بيانات الحركة</div>
<div class='kv'><b>نوع الحركة:</b> <span class='badge p'>سحب — المندوب (إقامات)</span></div>
<div class='kv'><b>الخيارات:</b> سفر إجازة · سفر نهائي · المندوب/إقامات · إرجاع</div>
<div class='kv'><b>المستلم (العُهدة):</b> أبو محمد (مندوب)</div>
<div class='kv'><b>تاريخ الخروج:</b> 2026-06-25</div>
<div class='kv'><b>العودة المتوقعة:</b> 2026-06-29</div>
<div class='kv'><b>الغرض/الجهة:</b> الإدارة العامة للإقامة</div></div>
<div class='card' style='width:1180px'><div class='ct'>الإجراء</div>
<div>{ '<span class=arr>→</span>'.join(["<span class='step'>مسح الباركودات</span>","<span class='step'>اختيار نوع الحركة</span>","<span class='step'>تحديد المستلم/التواريخ</span>","<span class='step'>حفظ سجل بالجملة</span>","<span class='step'>تحديث حالة كل جواز + ملف الموظف</span>","<span class='step'>طباعة إيصال العُهدة</span>"]) }
<div class='cap'><b>⚙️ كيف يعمل:</b> الموظف يمسح كل الباركودات دفعة واحدة، يختار السبب (سفر/نهائي/مندوب)، يحدد المستلم والتواريخ، فيُنشأ سجل عُهدة جماعي واحد، وتتحدّث حالة كل جواز تلقائياً (خارج/مع المندوب) ويظهر في ملف الموظف. الإرجاع بنفس الطريقة (مسح → إرجاع للأرشيف → تحديد الرف).</div></div>"""
S.append(("pp_bulk","سحب/إرجاع الجوازات بالباركود",shell("سحب/إرجاع بالجملة","Employees › Archive › Bulk Movement",b)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","92",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)

# ---- Screen 3: printed custody receipt on letterhead ----
recs=[("PP-001825","راج كومار · EMP-2231","K48xxxx","IN"),("PP-001830","بير تامانج · EMP-3119","NP991xxx","NP"),("PP-001841","أنيل ثابا · EMP-4655","NP771xxx","NP")]
rr="".join(f"<tr><td style='text-align:center'>{i+1}</td><td>{barcode(seed=i+5,h=22)}<div style='font-size:10px'>{r[0]}</div></td><td>{r[1]}</td><td style='text-align:center'>{r[2]}</td><td style='text-align:center'>{r[3]}</td><td></td></tr>" for i,r in enumerate(recs))
rep=f"""<!doctype html><html><head><meta charset='utf-8'><style>
body{{margin:0;font-family:'Cairo',Arial}}.page{{width:900px;margin:14px auto;background:#fff;box-shadow:0 3px 14px rgba(0,0,0,.2)}}
img.lh{{width:100%;display:block}} .cb{{display:flex;justify-content:space-between;align-items:center;direction:ltr;border-top:1px solid #eef2f7;border-bottom:2px solid #0f2b5b;background:#fbfcfe;padding:7px 36px}}
.cb .m{{text-align:center}}.cb .t{{font-size:16px;font-weight:bold;color:#0f2b5b}}.cb .e{{font-size:10px;color:#64748b;letter-spacing:1px}}.cap{{font-size:8px;color:#7b8794}}
.body{{padding:12px 40px;direction:rtl}} .meta{{display:flex;justify-content:space-between;font-size:11.5px;color:#64748b;margin-bottom:8px}}
.subj{{text-align:center;font-weight:bold;font-size:15px;color:#fff;background:#0f2b5b;border-radius:6px;padding:6px;margin:8px 0 12px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}th{{background:#0f2b5b;color:#fff;border:1px solid #0f2b5b;padding:7px}}td{{border:1px solid #cbd5e1;padding:9px}}
.kv{{font-size:12.5px;margin:4px 0}}.sign{{display:flex;justify-content:space-between;margin-top:26px;font-size:12px}}.sign div{{text-align:center;width:30%}}.ln{{border-top:1px solid #94a3b8;margin-top:28px;padding-top:4px}}
</style></head><body><div class='page'>
<img class='lh' src='lh_header.png'/>
<div class='cb'><div style='text-align:left'>{qr(px=3)}<div class='cap'>امسح للوصول · Scan</div></div>
<div class='m'><div class='t'>إيصال عُهدة جوازات</div><div class='e'>PASSPORT CUSTODY RECEIPT</div></div>
<div style='text-align:right'>{barcode(h=34)}<div style='font-size:10px;font-weight:bold'>PPC/2026/00042</div><div class='cap'>الرقم التسلسلي</div></div></div>
<div class='body'>
<div class='meta'><span>التاريخ: 2026-06-25</span><span>المرجع: PPC/2026/00042</span></div>
<div class='subj'>سحب جوازات — عُهدة المندوب (لأغراض الإقامات)</div>
<div class='kv'><b>المستلم:</b> أبو محمد (مندوب) · <b>الجهة:</b> الإدارة العامة للإقامة · <b>العودة المتوقعة:</b> 2026-06-29</div>
<table><tr><th style='width:35px'>#</th><th>باركود الجواز</th><th>الموظف</th><th style='text-align:center'>رقم الجواز</th><th style='text-align:center'>الجنسية</th><th style='width:120px'>ملاحظات</th></tr>{rr}</table>
<div class='sign'><div><div class='ln'>تسليم: موظف الأرشيف</div></div><div><div class='ln'>استلام: المندوب</div></div><div><div class='ln'>اعتماد: المدير</div></div></div>
</div><img class='lh' src='lh_footer.png'/></div></body></html>"""
hp=os.path.join(OUT,"pp_receipt.html");pp=os.path.join(OUT,"pp_receipt.png")
open(hp,"w",encoding="utf-8").write(rep)
subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(940),"--quality","94",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.remove(hp);print("rendered pp_receipt")
