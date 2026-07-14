# -*- coding: utf-8 -*-
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__))
accent='#1a9f6d'
rows=[('المرجع','Care/2026/7/1788'),('الموضوع','خطاب تعريف براتب — محمد عبده'),('الاتجاه','صادر'),
('الحالة','ممسوح'),('الجهة','الهيئة العامة للقوى العاملة'),('التصنيف','حكومي'),('القسم','الشؤون الحكومية'),
('تاريخ الإصدار','2026-06-22'),('المندوب','خالد سالم'),('سُلّم للمندوب','2026-06-22'),
('مسؤول المتابعة','عبدالله الخالدي'),('مُقدّم الطلب','سارة'),('رسوم غير مدفوعة','150.000 د.ك')]
tr=''
for l,v in rows:
    tr+=('<tr><td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#8a93a8;font-weight:bold;font-size:12px;width:38%%;">%s</td>'
         '<td style="padding:7px 12px;border-bottom:1px solid #eef1f6;color:#1d2433;font-weight:bold;font-size:13px;">%s</td></tr>'%(l,v))
html=('<html><head><meta charset="utf-8"></head><body style="background:#eef1f6;padding:24px;">'
'<div style="max-width:620px;margin:auto;font-family:Tahoma,Arial,sans-serif;direction:rtl;border:1px solid #e4e8f0;border-radius:14px;overflow:hidden;background:#fff;">'
'<div style="background:#1e2a44;padding:16px 22px;"><span style="color:#e8564e;font-weight:bold;font-size:20px;">CARE</span>'
'<span style="color:#aeb8cc;font-size:12px;font-weight:bold;"> · إدارة المراسلات</span></div>'
'<div style="background:%s;height:6px;"></div>'
'<div style="padding:22px;">'
'<h2 style="margin:0 0 6px;color:#1e2a44;font-size:19px;">كتابك جاهز للاستلام ✅</h2>'
'<p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 14px;">تم توقيع كتابك ومسحه ضوئياً، وهو الآن جاهز للاستلام من إدارة المراسلات.</p>'
'<table style="width:100%%;border-collapse:collapse;border:1px solid #eef1f6;border-radius:8px;overflow:hidden;">%s</table>'
'<div style="text-align:center;margin-top:20px;"><a href="#" style="display:inline-block;background:#2f6df6;color:#fff;padding:11px 26px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">فتح الكتاب في النظام ←</a></div>'
'</div><div style="background:#f6f8fc;padding:13px 22px;color:#8a93a8;font-size:11px;text-align:center;">رسالة آلية من نظام إدارة المراسلات · CARE — يرجى عدم الرد على هذا البريد</div>'
'</div></body></html>')%(accent,tr)
open(os.path.join(OUT,'letter_email_preview.html'),'w').write(html)
subprocess.run(['wkhtmltoimage','--enable-local-file-access','--quality','92','--width','680','--encoding','utf-8',
 os.path.join(OUT,'letter_email_preview.html'),os.path.join(OUT,'letter_email_preview.png')],capture_output=True)
print('rendered email preview')
