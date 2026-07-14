# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import fields, models, api, _


class CareAssistant(models.Model):
    """Deterministic 'smart assistant' (mockup 51): the user asks in plain
    language (or clicks a quick question) and gets an answer computed from
    system data. All queries run as the current user, so answers are governed
    by that user's access rights. An LLM back-end can be plugged into
    `_route()` later without changing the UI."""
    _name = 'care.assistant'
    _description = 'Smart Assistant'

    name = fields.Char(default='Assistant')
    question = fields.Char(string='سؤالك', help='اكتب سؤالك بالعربية أو الإنجليزية.')
    employee_id = fields.Many2one('hr.employee', string='الموظف (لأسئلة نهاية الخدمة/الأرصدة)')
    answer_html = fields.Html(string='الإجابة', readonly=True, sanitize=False)
    last_intent = fields.Char(readonly=True)

    # ---------------- helpers ----------------
    def _wrap(self, html, intent=False):
        self.write({'answer_html': Markup(html), 'last_intent': intent or ''})
        return True

    def _card(self, title, body):
        return ('<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;'
                'margin-top:8px;background:#f8fafc;">'
                '<div style="font-weight:600;color:#15213b;margin-bottom:4px;">%s</div>'
                '<div style="color:#334155;font-size:14px;line-height:1.7;">%s</div></div>') % (title, body)

    # ---------------- intents ----------------
    def _ans_availability(self):
        Emp = self.env['hr.employee']
        total = Emp.search_count([('worker_status', '=', 'active')])
        by_dept = Emp.read_group([('worker_status', '=', 'active')],
                                 ['department_id'], ['department_id'],
                                 orderby='department_id_count desc', limit=5)
        rows = ''.join('<li>%s — <b>%s</b></li>' % (
            (g['department_id'][1] if g['department_id'] else _('بدون قسم')),
            g['department_id_count']) for g in by_dept)
        body = _('يوجد حالياً <b>%s</b> عامل بحالة «نشط».') % total
        if rows:
            body += _('<br/>الأعلى توفراً حسب القسم:') + '<ul>%s</ul>' % rows
        return self._wrap(self._card(_('العمالة المتاحة الآن'), body), 'availability')

    def _ans_residency(self, days=30):
        Emp = self.env['hr.employee']
        today = fields.Date.today()
        limit = fields.Date.add(today, days=days)
        recs = Emp.search([('residency_end_date', '!=', False),
                           ('residency_end_date', '>=', today),
                           ('residency_end_date', '<=', limit)],
                          order='residency_end_date')
        soon = recs[:6]
        rows = ''.join('<li>%s — %s</li>' % (e.name, e.residency_end_date) for e in soon)
        body = _('<b>%s</b> عامل تنتهي إقامته خلال %s يوم.') % (len(recs), days)
        if rows:
            body += _('<br/>الأقرب انتهاءً:') + '<ul>%s</ul>' % rows
            body += _('<br/>يمكنك توليد دفعة تجديد بضغطة من الزر أدناه.')
        return self._wrap(self._card(_('إقامات تقترب من الانتهاء'), body), 'residency')

    def _ans_eos(self):
        if not self.employee_id:
            return self._wrap(self._card(_('حاسبة نهاية الخدمة'),
                              _('اختر الموظف أولاً من حقل «الموظف» ثم اسأل.')), 'eos')
        emp = self.employee_id
        start = emp.first_contract_date or emp.joining_date
        wage = emp.contract_id.wage if emp.contract_id else 0.0
        if not start or not wage:
            return self._wrap(self._card(_('حاسبة نهاية الخدمة'),
                              _('لا توجد بيانات كافية (تاريخ المباشرة أو الراتب الأساسي) لحساب %s.') % emp.name), 'eos')
        today = fields.Date.today()
        days_total = (today - start).days
        years = days_total / 365.25
        y_full = int(years)
        months = int((years - y_full) * 12)
        # Kuwait private-sector indemnity: 15 days/yr first 5y, 1 month/yr after
        eos_days = min(years, 5) * 15 + max(years - 5, 0) * 30
        daily = wage / 26.0
        eos = eos_days * daily
        cur = emp.company_id.currency_id.name or 'KWD'
        body = _('الموظف: <b>%s</b><br/>المدة: <b>%s سنة و%s شهر</b> (من %s)<br/>'
                 'الراتب الأساسي: <b>%s %s</b><br/>'
                 'المستحق (15 يوم/سنة أول 5 سنوات + شهر/سنة بعدها): '
                 '<b>%.0f %s</b><br/>'
                 '<span style="color:#64748b;font-size:12px;">تقدير وفق قانون العمل الكويتي — يُضاف بدل الإجازة المتبقية.</span>') % (
            emp.name, y_full, months, start, wage, cur, eos, cur)
        return self._wrap(self._card(_('حاسبة نهاية الخدمة'), body), 'eos')

    def _fallback(self):
        body = _('لم أتعرّف على السؤال. جرّب مثلاً:'
                 '<ul>'
                 '<li>كم عامل متاح الآن؟</li>'
                 '<li>من تنتهي إقامته هذا الشهر؟</li>'
                 '<li>احسب نهاية الخدمة (بعد اختيار الموظف)</li>'
                 '</ul>أو استخدم الأزرار السريعة بالأعلى.')
        return self._wrap(self._card(_('المساعد الذكي'), body), 'none')

    def _route(self, q):
        t = (q or '').lower()
        if any(k in t for k in ['متاح', 'العمالة', 'كام عامل', 'كم عامل', 'available', 'availab']):
            return self._ans_availability()
        if any(k in t for k in ['إقام', 'اقام', 'تنتهي', 'انتهاء', 'residenc', 'expir', 'iqama']):
            return self._ans_residency()
        if any(k in t for k in ['نهاية الخدمة', 'مكافأ', 'eos', 'end of service', 'indemn', 'gratuit']):
            return self._ans_eos()
        return self._fallback()

    # ---------------- buttons ----------------
    def action_ask(self):
        self.ensure_one()
        return self._route(self.question)

    def action_q_availability(self):
        self.ensure_one()
        self.question = _('كم عامل متاح الآن؟')
        return self._ans_availability()

    def action_q_residency(self):
        self.ensure_one()
        self.question = _('من تنتهي إقامته هذا الشهر؟')
        return self._ans_residency()

    def action_q_eos(self):
        self.ensure_one()
        self.question = _('احسب نهاية الخدمة')
        return self._ans_eos()

    def action_generate_renewals(self):
        """Quick action offered after a residency answer."""
        self.ensure_one()
        if 'care.gov.transaction' in self.env:
            return self.env['care.gov.transaction'].action_generate_due_renewals()
        return True

    def action_show_available(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('العمالة المتاحة'),
            'res_model': 'hr.employee', 'view_mode': 'kanban,tree,form',
            'domain': [('worker_status', '=', 'active')],
        }
