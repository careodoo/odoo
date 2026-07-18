# -*- coding: utf-8 -*-
"""A password-protected page listing the demo/test app users (one per job
function on مستشفى لوذان) so the team can log in and exercise every role.

Gated by ?key=<password>; the credentials live in ir.config_parameter."""
import json
from odoo.http import request, Controller, route

PAGE_KEY = 'care-test-2026'  # the page password (share this to open the page)


class TestUsersPage(Controller):

    @route('/care/test-users', type='http', auth='public', methods=['GET'], csrf=False)
    def test_users(self, key=None, **kw):
        env = request.env
        if key != PAGE_KEY:
            html = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>محمي</title>
<style>body{font-family:sans-serif;background:#0E3A5F;color:#fff;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0}form{background:#fff;color:#0E3A5F;padding:28px;border-radius:16px;
box-shadow:0 12px 40px rgba(0,0,0,.3);text-align:center;max-width:320px}input{width:100%;padding:12px;
border:1px solid #cbd5e1;border-radius:10px;margin:12px 0;box-sizing:border-box;font-size:15px}
button{width:100%;padding:12px;background:#C0392B;color:#fff;border:0;border-radius:10px;font-weight:800;font-size:15px}</style>
</head><body><form method="get"><h3>🔒 صفحة محمية</h3><p style="font-size:13px;color:#64748b">أدخل كلمة مرور الصفحة</p>
<input name="key" type="password" placeholder="كلمة المرور" autofocus/><button>دخول</button></form></body></html>"""
            return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

        raw = env['ir.config_parameter'].sudo().get_param('care.test_users', '[]')
        pw = env['ir.config_parameter'].sudo().get_param('care.test_users_pw', 'Care@2026')
        try:
            users = json.loads(raw)
        except Exception:
            users = []
        role_ar = {
            'cleaning': 'النظافة 🧹', 'security': 'الأمن 🛡️', 'agriculture': 'الزراعة 🌿',
            'facade': 'الواجهات 🏙️', 'maintenance': 'الصيانة 🔧', 'waste': 'نقل النفايات ♻️',
            'quality': 'مراقبة الجودة ✅', 'supervisor': 'مشرف 👔', 'worker': 'عامل عام 👷',
        }
        rows = ''.join(
            '<tr><td>%s</td><td><b>%s</b></td><td class="mono">%s</td>'
            '<td class="mono">%s</td></tr>' % (
                role_ar.get(u.get('role'), u.get('role') or ''), u.get('name') or '',
                u.get('login') or '', pw)
            for u in users)
        html = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>مستخدمو التجربة — لوذان</title>
<style>*{box-sizing:border-box}body{font-family:'Segoe UI',Tahoma,sans-serif;background:#F6F7F9;margin:0;color:#0E3A5F}
.hd{background:linear-gradient(135deg,#E24A3B,#C0392B,#8E241B);color:#fff;padding:26px 18px;border-radius:0 0 22px 22px}
.hd h1{margin:0 0 4px;font-size:22px}.hd p{margin:0;opacity:.9;font-size:13px}
.wrap{max-width:760px;margin:0 auto;padding:16px}
.note{background:#fff;border-radius:14px;padding:14px 16px;margin:14px 0;box-shadow:0 4px 14px rgba(0,0,0,.05);font-size:13.5px}
.note b{color:#C0392B}
table{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,.06)}
th{background:#0E3A5F;color:#fff;padding:11px;font-size:13px;text-align:right}
td{padding:11px;border-bottom:1px solid #eef2f5;font-size:13px}
tr:last-child td{border-bottom:0}.mono{font-family:ui-monospace,Menlo,monospace;direction:ltr;text-align:left;color:#334}
.pw{background:#0E3A5F;color:#fff;border-radius:12px;padding:12px 16px;margin:12px 0;display:flex;justify-content:space-between;align-items:center}
.pw span{font-family:ui-monospace,monospace;font-size:18px;font-weight:800;letter-spacing:1px}</style>
</head><body>
<div class="hd"><h1>مستخدمو التجربة — مستشفى لوذان</h1><p>شركة حمد الطبية · لتجربة كل الأدوار وتحسين التطبيق</p></div>
<div class="wrap">
<div class="pw"><span>🔑 كلمة المرور الموحّدة</span><span>%(pw)s</span></div>
<div class="note">كل المستخدمين أدناه يستخدمون <b>نفس كلمة المرور</b> الظاهرة أعلاه. سجّل الدخول في التطبيق باسم المستخدم (البريد) وكلمة المرور، وسيفتح التطبيق تلقائياً على واجهة الدور المناسب (نظافة/أمن/زراعة/…).</div>
<table><thead><tr><th>الدور</th><th>الاسم</th><th>اسم المستخدم (تسجيل الدخول)</th><th>كلمة المرور</th></tr></thead>
<tbody>%(rows)s</tbody></table>
<div class="note" style="margin-top:16px;color:#64748b">عدد المستخدمين: %(n)d · المنشأة: مستشفى لوذان</div>
</div></body></html>""" % {'pw': pw, 'rows': rows, 'n': len(users)}
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
