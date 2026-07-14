# -*- coding: utf-8 -*-
"""Mockup: Employee RESIGNATION SUBMISSION form on the official CARE letterhead
(header + footer images), trilingual (AR / EN / worker native language),
with unified barcode(right)+title(center)+QR(left) bar."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=900

def barcode(seed=7,h=34):
    v=seed;ws=[]
    for i in range(42):
        v=(v*1103515245+12345)>>3 & 7;ws.append(1+(v%3))
    bars="".join(f"<span style='display:inline-block;width:{w}px;height:{h}px;background:{'#111' if i%2==0 else '#fff'}'></span>" for i,w in enumerate(ws))
    return f"<div style='display:inline-flex;align-items:flex-end'>{bars}</div>"

def qr(seed=29,px=3):
    n=21;v=seed;grid=""
    def fb(r,c): return (1<=r<=7 and 1<=c<=7) or (1<=r<=7 and n-7<=c<=n-1) or (n-7<=r<=n-1 and 1<=c<=7)
    for r in range(n):
        row=""
        for c in range(n):
            v=(v*1103515245+12345)>>5 & 0xFFFF
            on=(r in (1,7) or c in (1,7) or (3<=r<=5 and 3<=c<=5) or (3<=r<=5 and n-6<=c<=n-4) or (n-6<=r<=n-4 and 3<=c<=5)) if fb(r,c) else (v%100)<45
            row+=f"<td style='width:{px}px;height:{px}px;background:{'#111' if on else '#fff'}'></td>"
        grid+=f"<tr>{row}</tr>"
    return f"<table style='border-collapse:collapse;border:3px solid #fff'>{grid}</table>"

NAVY="#0f2b5b"; RED="#d8232a"
CSS=f"""
@page{{size:A4}}
*{{box-sizing:border-box}}
body{{margin:0;background:#9aa3b5;font-family:'Cairo','Noto Sans Devanagari','Noto Sans Bengali','Segoe UI',Arial,sans-serif}}
.page{{width:{W}px;min-height:1180px;margin:18px auto;background:#fff;position:relative;display:flex;flex-direction:column;box-shadow:0 4px 18px rgba(0,0,0,.25)}}
.lh-h img,.lh-f img{{width:100%;display:block}}
.codebar{{display:flex;justify-content:space-between;align-items:center;direction:ltr;padding:8px 40px;border-top:1px solid #eef2f7;border-bottom:2px solid {NAVY};background:#fbfcfe}}
.codebar .c{{flex:1}}
.codebar .mid{{text-align:center}}
.codebar .mid .t{{font-size:17px;font-weight:bold;color:{NAVY}}}
.codebar .mid .e{{font-size:11px;color:#64748b;letter-spacing:1px}}
.cap{{font-size:8px;color:#7b8794;margin-top:2px}}
.sn{{direction:ltr;font-size:10px;letter-spacing:1.5px;color:#334155;margin-top:2px;font-weight:bold}}
.content{{flex:1;padding:14px 44px 8px;direction:rtl;color:#1f2937}}
.meta{{display:flex;justify-content:space-between;font-size:11.5px;color:#64748b;margin-bottom:6px}}
.addr{{font-size:13.5px;line-height:1.9}}
.addr .row{{display:flex;justify-content:space-between}}
.addr b{{color:{NAVY}}}
.greet{{font-size:13px;margin:6px 0}}
.subject{{text-align:center;font-weight:bold;font-size:15px;color:#fff;background:{NAVY};border-radius:6px;padding:7px;margin:12px 0 14px;letter-spacing:.5px}}
.letter p{{font-size:13.5px;line-height:2.1;margin:9px 2px;text-align:justify}}
.letter .en{{direction:ltr;text-align:left}}
.letter .nat{{background:#f5f9ff;border:1px solid #dbeafe;border-right:4px solid {NAVY};border-radius:6px;padding:9px 13px;direction:ltr;text-align:left;font-size:13.5px;line-height:2}}
.natlbl{{font-size:9.5px;color:#1d4ed8;display:block;margin-bottom:3px;font-weight:bold}}
.info{{width:100%;border-collapse:collapse;margin:16px 0;font-size:12.5px}}
.info th{{background:{NAVY};color:#fff;padding:8px;font-weight:600;border:1px solid {NAVY}}}
.info td{{border:1px solid #cbd5e1;padding:11px 8px;text-align:center;background:#fff}}
.applicant{{font-size:13px;margin:14px 2px 4px;font-weight:bold;color:{NAVY}}}
.close{{text-align:center;font-size:12.5px;color:#475569;margin:8px 0 14px}}
.sig{{width:100%;border-collapse:collapse;font-size:12px}}
.sig th{{background:#eef2f7;border:1px solid #cbd5e1;padding:7px;color:{NAVY}}}
.sig td{{border:1px solid #cbd5e1;height:40px;padding:6px 9px}}
.sig td.role{{background:#f8fafc;font-weight:bold;width:210px;color:#334155}}
.office{{margin-top:12px;border:1px dashed {RED};background:#fff7f7;border-radius:6px;padding:7px 12px;font-size:10px;color:#7f1d1d;line-height:1.7}}
.office b{{color:{RED}}}
"""

page=f"""<div class='page'>
  <div class='lh-h'><img src='lh_header.png'/></div>
  <div class='codebar'>
    <div class='c' style='text-align:left'>{qr(px=3)}<div class='cap'>امسح للوصول للسجل · Scan</div></div>
    <div class='c mid'><div class='t'>طلب استقالة</div><div class='e'>RESIGNATION REQUEST</div></div>
    <div class='c' style='text-align:right'>{barcode()}<div class='sn'>RES/2026/00007</div><div class='cap'>الرقم التسلسلي · Serial No.</div></div>
  </div>

  <div class='content'>
    <div class='meta'><span>التاريخ / Date: 2026-06-10</span><span>المرجع / Ref: RES/2026/00007</span></div>

    <div class='addr'>
      <div class='row'><span><b>السادة /</b> شركة الرعاية لمقاولات تنظيف المباني والمدن</span><span><b>المحترمين</b></span></div>
      <div class='row'><span><b>عناية /</b> إدارة المـــوارد البشريــة</span><span><b>المحترمين</b></span></div>
      <div class='greet'>تحية طيبة وبعد ،،،</div>
    </div>

    <div class='subject'>الموضوع / طلب استقالة</div>

    <div class='letter'>
      <p>برجاء الموافقة على إشعار تقديم استقالتي من العمل بشركة الرعاية بوظيفة <b>عامل نظافة</b>، على أن يكون آخر يوم عمل لي هو <b>2026/07/10</b>، وذلك لأسباب خاصة. وأنتهز الفرصة لأعبّر عن خالص شكري وتقديري للشركة على فترة عملي معكم.</p>
      <p class='en'>Kindly accept my resignation from CARE company, job title <b>Cleaning Worker</b>, and my last working day will be <b>10/07/2026</b>, for personal reasons. I take this opportunity to express my sincere thanks and appreciation to the company.</p>
      <p class='nat'><span class='natlbl'>لغة العامل — تلقائياً حسب الجنسية (نيبالي · Nepali)</span>
        कृपया CARE कम्पनीबाट काम छोड्ने मेरो निवेदन स्वीकार गर्नुहोस्। पद: सफाइ कर्मचारी। मेरो कामको अन्तिम दिन <b>10/07/2026</b> हुनेछ, व्यक्तिगत कारणले। यस अवसरमा कम्पनीप्रति हार्दिक आभार व्यक्त गर्दछु।</p>
    </div>

    <table class='info'>
      <tr><th style='width:140px'>الرقم الوظيفي</th><th>الاسم</th><th>المشروع / الإدارة</th><th style='width:130px'>الجنسية</th></tr>
      <tr><td>EMP-1042</td><td>سونام باهادور</td><td>مشروع A / النظافة</td><td>نيبال</td></tr>
    </table>

    <div class='applicant'>توقيع مقدم الطلب / Applicant Signature: ...................................</div>
    <div class='close'>وتفضلوا بقبول فائق الاحترام والتقدير ،،</div>

    <table class='sig'>
      <tr><th class='role' style='background:#eef2f7'>الاعتماد / Approval</th><th>التوقيع / Signature</th><th>الملاحظات / Remarks</th><th style='width:110px'>التاريخ / Date</th></tr>
      <tr><td class='role'>المدير المباشر</td><td></td><td></td><td></td></tr>
      <tr><td class='role'>مدير الإدارة المعني</td><td></td><td></td><td></td></tr>
      <tr><td class='role'>مدير الإدارة المالية</td><td></td><td></td><td></td></tr>
      <tr><td class='role'>مدير الموارد البشرية</td><td></td><td></td><td></td></tr>
    </table>

    <div class='office'><b>🔒 للاستخدام الرسمي فقط (يُملأ من الإدارة):</b> رقم القيد RES/2026/00007 · تاريخ الاستلام: ______ · المسار: مُقدَّمة ← المدير المباشر ← مدير الإدارة ← المالية ← الموارد البشرية ← اعتماد نهائي · يُرفق بعد الاعتماد: كشف نهاية الخدمة وإخلاء الطرف. &nbsp; | &nbsp; الباركود (يمين) = الرقم التسلسلي للسجل · رمز QR (يسار) يفتح السجل مباشرة في النظام عند مسحه.</div>
  </div>

  <div class='lh-f'><img src='lh_footer.png'/></div>
</div>"""

html=f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{page}</body></html>"
hp=os.path.join(OUT,"resignation_submit.html");pp=os.path.join(OUT,"resignation_submit.png")
open(hp,"w",encoding="utf-8").write(html)
subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","94",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.remove(hp);print("rendered resignation_submit.png")
