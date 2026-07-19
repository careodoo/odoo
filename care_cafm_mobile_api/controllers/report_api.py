# -*- coding: utf-8 -*-
"""One PDF report route for every record in the system.

Writing a report per model does not scale — there are dozens of models across
the services and each new one arrives without a report until somebody
remembers. So this reads the record's own field definitions and renders what is
actually filled in. A model gets a report the moment it exists.

Curation still matters, so MODELS may name the fields that belong at the top of
the sheet and the child table worth printing; anything not named still prints,
just after them. The record is read through the *caller's* environment, never
sudo — an Odoo access rule that hides a record must hide its report too, or the
report becomes the way around the rules.
"""
import base64
import io as _io

from markupsafe import Markup, escape
from werkzeug import urls

from odoo import http, fields as odoo_fields, _
from odoo.exceptions import AccessError
from odoo.http import request

RED = '#c0392b'
INK = '#14202b'
MUTED = '#6b7785'

# Never useful on a printed sheet.
SKIP = {
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'display_name',
    '__last_update', 'message_ids', 'message_follower_ids', 'message_partner_ids',
    'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id',
    'activity_date_deadline', 'activity_summary', 'activity_exception_decoration',
    'activity_exception_icon', 'website_message_ids', 'message_has_error',
    'message_has_error_counter', 'message_needaction', 'message_needaction_counter',
    'message_attachment_count', 'message_has_sms_error', 'message_is_follower',
    'access_token', 'access_url', 'access_warning', 'rating_ids', 'my_activity_date_deadline',
    'activity_calendar_event_id', 'message_main_attachment_id', 'has_message',
    'company_id', 'active', 'color', 'sequence',
}
SKIP_TYPES = {'binary', 'html', 'json', 'many2many_binary'}


# code -> (model, title, headline fields, child table field)
# Anything absent is still reportable by its model name; this only decides what
# gets pride of place.
MODELS = {
    'workorder': ('care.cafm.workorder', 'أمر عمل',
                  ['name', 'facility_id', 'service_id', 'state', 'priority',
                   'employee_id', 'scheduled_date'], None),
    'stock_count': ('care.cafm.stock.count', 'محضر جرد مخزني',
                    ['name', 'store_id', 'count_date', 'count_type', 'state',
                     'accuracy', 'variance_lines', 'variance_value'], 'line_ids'),
    'stock_request': ('care.cafm.stock.request', 'طلب تعويض مخزون',
                      ['name', 'store_id', 'state', 'urgency', 'needed_by',
                       'total_value'], 'line_ids'),
    'tank_cleaning': ('care.tank.cleaning', 'شهادة تنظيف خزان مياه',
                      ['name', 'certificate_no', 'tank_id', 'clean_date', 'crew_id',
                       'state', 'lab_result', 'completeness'], None),
    'pool_reading': ('care.pool.reading', 'قراءة مياه مسبح',
                     ['name', 'pool_id', 'taken_at', 'taken_by', 'is_safe',
                      'breaches'], None),
    'disinfect_round': ('care.disinfect.round', 'محضر جولة تعقيم',
                        ['name', 'facility_id', 'round_type', 'method', 'done_at',
                         'product_id', 'contact_minutes', 'contact_ok', 'state'], None),
    'pest_visit': ('care.pest.visit', 'تقرير زيارة مكافحة حشرات',
                   ['name', 'program_id', 'visit_date', 'technician_id', 'state'],
                   'station_ids'),
    'valet_ticket': ('care.valet.ticket', 'تذكرة صف سيارات',
                     ['name', 'plate', 'guest_name', 'guest_phone', 'facility_id',
                      'received_at', 'state'], None),
    'observation': ('care.cafm.observation', 'ملاحظة جودة',
                    ['name', 'facility_id', 'service_id', 'state', 'severity'], None),
    'asset': ('care.cafm.asset', 'بطاقة أصل',
              ['name', 'code', 'facility_id', 'category_id', 'state'], None),
    'invoice': ('care.cafm.invoice', 'فاتورة',
                ['name', 'client_id', 'date', 'amount_total', 'state'], 'line_ids'),
}


def _fmt(rec, fname, field):
    """One field as printable text, or '' when there is nothing to print."""
    try:
        val = rec[fname]
    except Exception:
        return ''
    if val is False or val is None or val == '':
        return ''
    t = field.type
    if t == 'boolean':
        return _('نعم') if val else _('لا')
    if t == 'selection':
        try:
            sel = dict(field._description_selection(rec.env))
        except Exception:
            sel = dict(field.selection or [])
        return str(sel.get(val, val))
    if t == 'many2one':
        try:
            return val.sudo().display_name or ''
        except Exception:
            return ''
    if t in ('one2many', 'many2many'):
        return ''
    if t == 'datetime':
        try:
            return odoo_fields.Datetime.context_timestamp(rec, val).strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(val)[:16]
    if t == 'date':
        return str(val)
    if t == 'float':
        return ('%.2f' % val).rstrip('0').rstrip('.') if val else '0'
    if t == 'monetary':
        return '%.3f' % val
    if t == 'integer':
        return str(val)
    return str(val)


def _printable_fields(rec, first):
    """(label, value) pairs: the named fields first, then whatever else is
    filled in. Empty fields are dropped — a sheet of dashes reads as a broken
    report, not a thorough one."""
    out, seen = [], set()
    for fname in first:
        f = rec._fields.get(fname)
        if not f:
            continue
        v = _fmt(rec, fname, f)
        seen.add(fname)
        if v:
            out.append((f.string or fname, v))
    for fname, f in sorted(rec._fields.items(), key=lambda kv: kv[1].string or kv[0]):
        if fname in seen or fname in SKIP or f.type in SKIP_TYPES:
            continue
        if f.type in ('one2many', 'many2many'):
            continue
        v = _fmt(rec, fname, f)
        if v:
            out.append((f.string or fname, v))
    return out


def _child_table(rec, lines_field):
    """The child table, if there is one worth printing."""
    if not lines_field or lines_field not in rec._fields:
        return None
    lines = rec[lines_field]
    if not lines:
        return None
    cols = []
    for fname, f in lines._fields.items():
        if fname in SKIP or f.type in SKIP_TYPES or f.type in ('one2many', 'many2many'):
            continue
        if f.type == 'many2one' and f.comodel_name == rec._name:
            continue          # the back-reference — same on every row
        if any(_fmt(l, fname, f) for l in lines):
            cols.append((fname, f))
    cols = cols[:7]
    if not cols:
        return None
    return ([f.string or n for n, f in cols],
            [[_fmt(l, n, f) for n, f in cols] for l in lines])


def _qr_data_uri(text):
    try:
        import qrcode
        buf = _io.BytesIO()
        qrcode.make(text, box_size=6, border=1).save(buf, format='PNG')
        return 'data:image/png;base64,%s' % base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _render(rec, title, pairs, table, verify_url):
    company = rec.env.company
    qr = _qr_data_uri(verify_url) if verify_url else None
    rows = Markup('').join(
        Markup('<tr><td class="k">%s</td><td class="v">%s</td></tr>') % (k, v)
        for k, v in pairs)
    tbl = Markup('')
    if table:
        heads, body = table
        tbl = Markup('<h3>%s</h3><table class="grid"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>') % (
            _('البنود'),
            Markup('').join(Markup('<th>%s</th>') % h for h in heads),
            Markup('').join(
                Markup('<tr>%s</tr>') % Markup('').join(Markup('<td>%s</td>') % c for c in r)
                for r in body))
    return Markup("""<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"/>
<title>%(title)s</title><style>
*{box-sizing:border-box}
body{font-family:'Tajawal','Segoe UI',Arial,sans-serif;color:%(ink)s;margin:0;padding:22px;font-size:12.5px}
.hd{display:flex;justify-content:space-between;align-items:flex-start;
    border-bottom:3px solid %(red)s;padding-bottom:12px;margin-bottom:16px}
.hd h1{margin:0 0 3px;font-size:19px;color:%(red)s}
.hd .co{font-size:12px;color:%(muted)s}
.hd .qr img{width:78px;height:78px}
table{width:100%%;border-collapse:collapse}
.kv td{padding:6px 9px;border-bottom:1px solid #e8ecf1;vertical-align:top}
.kv .k{width:34%%;color:%(muted)s;font-weight:600}
.kv .v{font-weight:600}
h3{margin:20px 0 7px;font-size:14px;color:%(red)s}
.grid th{background:#f4f6fa;text-align:right;padding:7px 8px;border:1px solid #dfe5ec;font-size:11.5px}
.grid td{padding:6px 8px;border:1px solid #e8ecf1;font-size:11.5px}
.ft{margin-top:22px;padding-top:9px;border-top:1px solid #e8ecf1;
    color:%(muted)s;font-size:10.5px;display:flex;justify-content:space-between}
</style></head><body>
<div class="hd">
  <div><h1>%(title)s</h1><div class="co">%(company)s</div>
       <div class="co">%(ref)s</div></div>
  %(qr)s
</div>
<table class="kv">%(rows)s</table>
%(tbl)s
<div class="ft"><span>%(printed)s %(now)s</span><span>%(by)s</span></div>
</body></html>""") % {
        'title': escape(title), 'ink': INK, 'red': RED, 'muted': MUTED,
        'company': escape(company.name or ''),
        'ref': escape(rec.display_name or ''),
        'qr': Markup('<div class="qr"><img src="%s"/></div>') % qr if qr else Markup(''),
        'rows': rows, 'tbl': tbl,
        'printed': _('طُبع في'),
        'now': odoo_fields.Datetime.context_timestamp(
            rec, odoo_fields.Datetime.now()).strftime('%Y-%m-%d %H:%M'),
        'by': escape(rec.env.user.name or ''),
    }


class RecordReport(http.Controller):

    def _user(self, token):
        tok = token or request.httprequest.args.get('token')
        if tok:
            return request.env['care.cafm.mobile.token'].sudo().resolve(tok)
        return request.env.user if request.env.user and not request.env.user._is_public() else None

    def _resolve(self, code, rid, user):
        """Return (record-in-caller's-env, title, headline, lines-field)."""
        spec = MODELS.get(code)
        model = spec[0] if spec else code.replace('_', '.')
        env = request.env(user=user.id)
        if model not in env:
            return None, None, None, None
        # Caller's env, not sudo: whatever the access rules hide stays hidden.
        rec = env[model].browse(rid).exists()
        if not rec:
            return None, None, None, None
        rec.check_access_rights('read')
        rec.check_access_rule('read')
        title = spec[1] if spec else (rec._description or model)
        return rec, title, (spec[2] if spec else []), (spec[3] if spec else None)

    @http.route(['/api/v1/report/<string:code>/<int:rid>',
                 '/api/v1/report/<string:code>/<int:rid>/pdf'],
                type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def record_pdf(self, code, rid, token=None, **kw):
        user = self._user(token)
        if not user:
            return request.make_response(_('غير مصرّح'), status=401)
        try:
            rec, title, first, lines_field = self._resolve(code, rid, user)
        except AccessError:
            return request.make_response(_('لا تملك صلاحية عرض هذا السجل.'), status=403)
        if not rec:
            return request.not_found()
        try:
            pairs = _printable_fields(rec, first or [])
            table = _child_table(rec, lines_field)
            base = request.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', '').rstrip('/')
            html = _render(rec, title, pairs, table,
                           '%s/api/v1/report/%s/%s' % (base, code, rid) if base else None)
            pdf = request.env['ir.actions.report'].sudo()._run_wkhtmltopdf(
                [str(html)], landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 8, 'data-report-margin-bottom': 8,
                    'data-report-margin-left': 8, 'data-report-margin-right': 8,
                })
        except AccessError:
            return request.make_response(_('لا تملك صلاحية عرض هذا السجل.'), status=403)
        # HTTP headers are latin-1, and almost every display_name here is
        # Arabic. Send an ASCII-safe name plus the real one per RFC 5987.
        raw = (rec.display_name or code).replace('/', '-').replace(' ', '_')[:60]
        ascii_name = raw.encode('ascii', 'ignore').decode().strip('_-') or '%s-%s' % (code, rid)
        quoted = urls.url_quote(raw + '.pdf')
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition',
             "inline; filename=\"%s.pdf\"; filename*=UTF-8''%s" % (ascii_name, quoted)),
        ])
