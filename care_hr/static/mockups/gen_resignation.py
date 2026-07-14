# -*- coding: utf-8 -*-
"""Mockup: enhanced Employee Resignation printable report + unified barcode/QR header."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=920

# deterministic barcode bars (Code128-like look)
def barcode(seed=7):
    widths=[]
    v=seed
    for i in range(46):
        v=(v*1103515245+12345)>>3 & 7
        widths.append(1+(v%4))
    bars=""
    for i,w in enumerate(widths):
        col="#111" if i%2==0 else "#fff"
        bars+=f"<span style='display:inline-block;width:{w}px;height:46px;background:{col}'></span>"
    return f"<div style='display:inline-flex;align-items:flex-end'>{bars}</div>"

# deterministic QR-like grid 21x21
def qr(seed=13):
    n=21; v=seed; cells=""
    def finder(r,c):
        return (1<=r<=7 and 1<=c<=7) or (1<=r<=7 and n-7<=c<=n-1) or (n-7<=r<=n-1 and 1<=c<=7)
    grid=""
    for r in range(n):
        row=""
        for c in range(n):
            v=(v*1103515245+12345)>>5 & 0xFFFF
            on = finder(r,c) and not (2<=r<=5 and 2<=c<=5) and not (2<=r<=5 and n-6<=c<=n-3) and not (n-6<=r<=n-3 and 2<=c<=5)
            if (1<=r<=7 and 1<=c<=7) or (1<=r<=7 and n-7<=c<=n-1) or (n-7<=r<=n-1 and 1<=c<=7):
                on = finder(r,c) and (r in (1,7) or c in (1,7) or (3<=r<=5 and 3<=c<=5) or (3<=r<=5 and n-6<=c<=n-4) or (n-6<=r<=n-4 and 3<=c<=5))
            else:
                on = (v%100)<45
            row+=f"<td style='width:5px;height:5px;background:{'#111' if on else '#fff'}'></td>"
        grid+=f"<tr>{row}</tr>"
    return f"<table style='border-collapse:collapse;border:4px solid #fff'>{grid}</table>"

CSS="""
body{margin:0;background:#e2e8f0;font-family:'Cairo','Segoe UI',Arial,sans-serif}
.page{width:880px;margin:14px auto;background:#fff;padding:0 0 22px;box-shadow:0 3px 14px rgba(0,0,0,.15)}
.hdr{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #714B67;padding:14px 22px;background:#faf7f9}
.hdr .side{text-align:center;font-size:10px;color:#475569}
.hdr .mid{text-align:center}
.hdr .mid .co{font-size:19px;font-weight:bold;color:#714B67}
.hdr .mid .ti{font-size:14px;color:#334155;margin-top:2px}
.hdr .mid .sn{font-size:11px;color:#64748b;margin-top:3px;direction:ltr}
.body{padding:16px 26px;direction:rtl}
.sec{margin:14px 0}
.sec h3{font-size:13px;color:#fff;background:#714B67;padding:5px 11px;border-radius:6px;margin:0 0 8px}
table.f{width:100%;border-collapse:collapse;font-size:12.5px}
table.f td{border:1px solid #e2e8f0;padding:6px 9px}
table.f td.l{background:#f8fafc;font-weight:bold;width:130px;color:#334155}
.appr{width:100%;border-collapse:collapse;font-size:12px}
.appr th{background:#f1f5f9;border:1px solid #e2e8f0;padding:6px}
.appr td{border:1px solid #e2e8f0;padding:9px 6px;text-align:center;height:34px}
.chk span{display:inline-block;font-size:12px;margin:3px 10px}
.badge{display:inline-block;border-radius:20px;padding:1px 9px;font-size:11px;color:#fff}
.g{background:#21b07b}.r{background:#e25563}.b{background:#3a7afe}
.sign{display:flex;justify-content:space-between;margin-top:26px;font-size:12px;color:#334155}
.sign div{text-align:center;width:30%}
.sign .ln{border-top:1px solid #94a3b8;margin-top:30px;padding-top:4px}
.foot{font-size:10px;color:#94a3b8;text-align:center;margin-top:14px;direction:ltr}
.note{background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#075985}
"""

def header(serial):
    return f"""<div class='hdr'>
      <div class='side'>{barcode()}<div style='direction:ltr;font-size:11px;margin-top:3px;letter-spacing:2px'>{serial}</div><div>الرقم التسلسلي · Serial</div></div>
      <div class='mid'><div class='co'>CARE — شركة كِير للخدمات</div><div class='ti'>نموذج استقالة / Employee Resignation</div><div class='sn'>{serial}</div></div>
      <div class='side'>{qr()}<div style='margin-top:3px'>امسح للوصول للسجل · Scan</div></div>
    </div>"""

report=f"""<div class='page'>
  {header('RES/2026/00007')}
  <div class='body'>
    <div class='sec'><h3>بيانات الموظف · Employee</h3>
      <table class='f'>
        <tr><td class='l'>الاسم</td><td>سونام باهادور</td><td class='l'>الكود</td><td>EMP-1042</td></tr>
        <tr><td class='l'>القسم</td><td>النظافة</td><td class='l'>الوظيفة / الدرجة</td><td>عامل نظافة · درجة 6</td></tr>
        <tr><td class='l'>المشروع</td><td>مشروع A</td><td class='l'>ملف القوى العاملة</td><td>12345</td></tr>
        <tr><td class='l'>تاريخ التعيين</td><td>2023-02-01</td><td class='l'>الإقامة</td><td>سارية حتى 2027-03</td></tr>
      </table>
    </div>
    <div class='sec'><h3>تفاصيل الاستقالة · Details</h3>
      <table class='f'>
        <tr><td class='l'>النوع</td><td>استقالة <span class='badge b'>Resignation</span></td><td class='l'>تاريخ التقديم</td><td>2026-06-10</td></tr>
        <tr><td class='l'>آخر يوم عمل</td><td>2026-07-10</td><td class='l'>مدة الإشعار</td><td>30 يوم ✓</td></tr>
        <tr><td class='l'>السبب</td><td colspan='3'>ظروف عائلية — العودة للوطن.</td></tr>
      </table>
    </div>
    <div class='sec'><h3>سلسلة الاعتماد · Approval Trail</h3>
      <table class='appr'>
        <tr><th>المرحلة</th><th>المسؤول</th><th>التاريخ</th><th>التوقيع</th></tr>
        <tr><td>تقديم الموظف</td><td>سونام باهادور</td><td>2026-06-10</td><td></td></tr>
        <tr><td>المدير المباشر</td><td>مشرف الموقع</td><td>2026-06-11</td><td></td></tr>
        <tr><td>الموارد البشرية</td><td>أحمد (HR)</td><td>2026-06-12</td><td></td></tr>
        <tr><td>الإدارة المالية</td><td>خالد (Finance)</td><td>2026-06-14</td><td></td></tr>
        <tr><td>الاعتماد النهائي</td><td>مدير العمليات</td><td>2026-06-15</td><td></td></tr>
      </table>
    </div>
    <div class='sec'><h3>التسوية المالية (نهاية الخدمة) · Final Settlement</h3>
      <table class='f'>
        <tr><td class='l'>مدة الخدمة</td><td>3 سنوات 5 أشهر</td><td class='l'>مكافأة نهاية الخدمة</td><td>258.000 د.ك</td></tr>
        <tr><td class='l'>رصيد الإجازات</td><td>14 يوم = 39.000</td><td class='l'>سلف/خصومات</td><td>−25.000</td></tr>
        <tr><td class='l'>آخر راتب مستحق</td><td>85.000</td><td class='l'><b>الصافي النهائي</b></td><td><b>357.000 د.ك</b></td></tr>
      </table>
    </div>
    <div class='sec'><h3>إخلاء الطرف · Clearance</h3>
      <div class='chk'>
        <span>العُهد <span class='badge g'>مُعادة</span></span>
        <span>السكن <span class='badge g'>تم الإخلاء</span></span>
        <span>الزي <span class='badge g'>مُعاد</span></span>
        <span>بطاقات الدخول <span class='badge r'>غير مُعادة</span></span>
        <span>إلغاء الإقامة <span class='badge b'>قيد الإجراء</span></span>
      </div>
    </div>
    <div class='note'>📌 صدر هذا المستند آلياً من النظام. الباركود أعلى اليمين = الرقم التسلسلي للسجل · رمز QR أعلى اليسار يفتح السجل مباشرة في النظام عند مسحه.</div>
    <div class='sign'>
      <div><div class='ln'>توقيع الموظف</div></div>
      <div><div class='ln'>مدير الموارد البشرية</div></div>
      <div><div class='ln'>الإدارة المالية</div></div>
    </div>
    <div class='foot'>Generated by Care HR · 2026-06-25 · hr.employee.resignation/7 · القالب موحّد لكل التقارير</div>
  </div>
</div>"""

html=f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{report}</body></html>"
hp=os.path.join(OUT,"resignation_report.html");pp=os.path.join(OUT,"resignation_report.png")
open(hp,"w",encoding="utf-8").write(html)
subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","92",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.remove(hp);print("rendered resignation_report.png")
