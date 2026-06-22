# -*- coding: utf-8 -*-

import json
import logging
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# --- Claude (AI) document analysis ---
AI_MODEL = 'claude-opus-4-8'
AI_ENDPOINT = 'https://api.anthropic.com/v1/messages'
AI_VERSION = '2023-06-01'
# Categories the model must classify each extracted item into (kept in sync
# with purchase.tender.requirement.category).
AI_CATEGORIES = ('document', 'equipment', 'tool', 'condition', 'info')
AI_SCHEMA = {
    'type': 'object',
    'properties': {
        'summary': {'type': 'string'},
        'requirements': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category': {'type': 'string', 'enum': list(AI_CATEGORIES)},
                    'name': {'type': 'string'},
                    'detail': {'type': 'string'},
                    'qty': {'type': 'integer'},
                },
                'required': ['category', 'name', 'detail', 'qty'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['summary', 'requirements'],
    'additionalProperties': False,
}
AI_SYSTEM = (
    'أنت خبير في تحليل كراسات الشروط والمناقصات الحكومية في دولة الكويت. '
    'ستتسلّم ملف مناقصة (كراسة الشروط). اقرأه بالكامل واستخرج بدقّة كل ما هو مطلوب '
    'من مُقدّم العطاء، مُصنّفاً ضمن الفئات التالية:\n'
    '- document: المستندات والشهادات والوثائق المطلوب تقديمها (مثل: شهادة تسجيل، '
    'كفالة بنكية، رخصة، سجل تجاري، شهادة عدم ممارسة، إلخ).\n'
    '- equipment: المعدّات والآليات المطلوب توفّرها (مثل: سيارات، رافعات، أجهزة).\n'
    '- tool: الأدوات والمستلزمات الأصغر المطلوبة.\n'
    '- condition: الشروط الجوهرية والإلزامية (مثل: مدّة التنفيذ، الغرامات، نسبة الكفالة، '
    'شروط الأهلية، الخبرة السابقة المطلوبة).\n'
    '- info: المعلومات الأساسية للمناقصة (مثل: الجهة، رقم المناقصة، قيمة وثائق الشراء، '
    'موعد الإغلاق، مكان التسليم، مدّة سريان العطاء).\n\n'
    'لكل بند: ضع اسماً مختصراً واضحاً في name، وتفاصيل دقيقة في detail (انسخ الأرقام '
    'والمواعيد والنِسب كما وردت)، والكمية في qty (0 إن لم تُذكر كمية). كن شاملاً وادقّ '
    'قدر الإمكان ولا تُهمل أي بند جوهري.\n\n'
    'أمّا summary فاكتب فيه ملخّصاً تنفيذياً احترافياً بصيغة HTML بسيطة باللغة العربية '
    '(استخدم <p> و<ul><li> و<strong>) يوضّح: موضوع المناقصة والجهة، أبرز المتطلبات، '
    'الشروط الحرجة والمواعيد، وأي مخاطر أو نقاط يجب الانتباه لها قبل التقديم.'
)

# Lifecycle state groupings (keys kept stable; labels are Arabic on the field)
ACTIVE_STATES = ('new', 'under_study', 'docs_purchased', 'interested', 'preparing', 'participated')
WON_STATES = ('winner', 'purchased', 'in_progress', 'completed')
DEAD_STATES = ('lost', 'excepted', 'cancelled', 'closed')

DEFAULT_CHECKLIST = [
    'شراء كراسة الشروط',
    'دراسة كراسة الشروط والمواصفات',
    'زيارة الموقع (إن وُجدت)',
    'تجهيز الضمان الابتدائي',
    'تجهيز العينات / الكتالوجات',
    'إعداد التسعير',
    'اعتماد الإدارة',
    'تجهيز المستندات القانونية',
    'تقديم العطاء',
]


class PurchaseTender(models.Model):
    _name = 'purchase.tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Tender'
    _order = 'importance desc, id desc'

    name = fields.Char(required=True, tracking=True)
    short_name = fields.Char(string='اسم مختصر', compute='_compute_short_name', store=True,
                             help="Auto-generated concise name (first words of the name) to save space in lists/cards.")
    tender_no = fields.Char(tracking=True)
    organization = fields.Many2one('res.partner', required=True, tracking=True)
    tender_name = fields.Char()
    issue_date = fields.Date(tracking=True)
    closing_date = fields.Date(tracking=True)
    new_closing_date = fields.Date(tracking=True)
    initial_meeting_date = fields.Date()
    bid_type = fields.Many2one('bid.type', string='Bidding Type')
    current_co = fields.Many2one('res.partner')
    price = fields.Float()
    guarantee = fields.Float()
    period = fields.Integer()
    manpower = fields.Integer()
    winner = fields.Many2one('res.partner', compute='compute_winner', store=True)
    winner_price = fields.Float(compute='compute_winner', store=True)
    winner_rate_price = fields.Float(compute='compute_winner', store=True)
    care_rank = fields.Integer(compute='compute_winner', store=True)
    to_win = fields.Float(compute='compute_to_win', store=True)
    our_price = fields.Float(string='سعرنا', compute='_compute_our_price', store=True,
                             help="Our own bid (the company's line in the price analysis), not the tender purchase price.")
    state = fields.Selection(selection=[
        ('new', 'جديدة'),
        ('under_study', 'تحت الدراسة'),
        ('docs_purchased', 'تم شراء الكراسة'),
        ('interested', 'مهتمون'),
        ('excepted', 'لن نشارك'),
        ('preparing', 'جارٍ التحضير'),
        ('participated', 'تم التقديم'),
        ('winner', 'فائزة'),
        ('lost', 'خاسرة'),
        ('postponed', 'مؤجلة'),
        ('purchased', 'تمت الترسية'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'منجزة'),
        ('closed', 'مغلقة'),
        ('cancelled', 'ملغاة'),
    ], default='new', tracking=True)
    image = fields.Binary(related='organization.image_1920', store=True)
    image_128 = fields.Image(related='organization.image_128')

    # --- New analytical fields ---
    days_to_close = fields.Integer(compute='_compute_days_to_close', store=True,
                                   help="Days remaining until the (effective) closing date.")
    price_gap = fields.Float(compute='_compute_price_gap', store=True,
                             help="Our price minus the winner price (positive = we were higher).")
    price_gap_pct = fields.Float(string='Price Gap %', compute='_compute_price_gap', store=True)
    win_probability = fields.Float(string='Win Probability %', compute='_compute_win_probability',
                                   store=True)
    importance = fields.Integer(compute='_compute_importance', store=True,
                                help="Sorting score: purchased & active/urgent tenders rank highest.")
    loss_reason = fields.Selection([
        ('price_high', 'سعرنا أعلى'),
        ('not_qualified', 'عدم استيفاء الشروط'),
        ('late', 'تأخّر التقديم'),
        ('guarantee', 'مشكلة في الضمان'),
        ('scope', 'عدم مطابقة النطاق'),
        ('competitor_relations', 'علاقات المنافس'),
        ('other', 'أخرى'),
    ], string='سبب الخسارة', tracking=True)
    loss_note = fields.Char(string='تفاصيل الخسارة')

    # --- Bank guarantee tracking ---
    guarantee_bank = fields.Char(string='Guarantee Bank')
    guarantee_ref = fields.Char(string='Guarantee Ref.')
    guarantee_status = fields.Selection(selection=[
        ('none', 'لا يوجد'),
        ('valid', 'سارٍ'),
        ('expiring', 'ينتهي قريباً'),
        ('expired', 'منتهٍ'),
    ], string='حالة الضمان', compute='_compute_guarantee_status', store=True)

    price_analysis_ids = fields.One2many('purchase.tender.price.analysis', 'tender_id')
    manpower_analysis_ids = fields.One2many('purchase.tender.manpower.analysis', 'tender_id')
    vehicle_analysis_ids = fields.One2many('purchase.tender.vehicle.analysis', 'tender_id')
    material_info_ids = fields.One2many('purchase.tender.material.info', 'tender_id')
    equipment_analysis_ids = fields.One2many('purchase.tender.equipment.analysis', 'tender_id')
    initial_meeting_ids = fields.One2many('purchase.tender.initial.meeting', 'tender_id')
    checklist_ids = fields.One2many('purchase.tender.checklist', 'tender_id', string='قائمة التحضير')
    checklist_done = fields.Integer(compute='_compute_checklist', store=True)
    checklist_total = fields.Integer(compute='_compute_checklist', store=True)
    checklist_progress = fields.Float(string='نسبة التحضير', compute='_compute_checklist', store=True)
    tender_document = fields.Binary(string='ملف المناقصة')
    tender_document_name = fields.Char(string='اسم الملف')
    requirement_ids = fields.One2many('purchase.tender.requirement', 'tender_id', string='المتطلبات')
    requirement_progress = fields.Float(string='جاهزية المتطلبات', compute='_compute_requirement_progress', store=True)
    requirement_ready = fields.Integer(string='جاهز', compute='_compute_requirement_progress', store=True)
    requirement_total = fields.Integer(string='إجمالي', compute='_compute_requirement_progress', store=True)
    prep_score = fields.Float(string='جاهزية العطاء', compute='_compute_prep_score', store=True,
                              help='مزيج من نسبة التحضير وجاهزية المتطلبات')
    ai_summary = fields.Html(string='الملخّص التنفيذي')
    ai_analyzed = fields.Boolean(string='تم التحليل', readonly=True)
    partner_id = fields.Many2one('res.partner')
    expiry_date = fields.Date()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    active = fields.Boolean(default=True)

    @api.onchange('organization')
    def onchange_organization(self):
        for rec in self:
            if rec.organization:
                rec.partner_id = rec.organization.id

    @api.onchange('period')
    def check_period(self):
        if self.period is not None and self.period <= 0:
            self.period = 1

    @api.onchange('manpower')
    def check_manpower(self):
        if self.manpower is not None and self.manpower <= 0:
            self.manpower = 1

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        checklist_items = self._default_checklist_items()
        for res in records:
            if not res.checklist_ids:
                res.checklist_ids = [(0, 0, {'sequence': (i + 1) * 10, 'name': item})
                                     for i, item in enumerate(checklist_items)]
        email_new = self._email_enabled('new')
        followers = self.env['purchase.tender.follower'].search([]).mapped('followers')
        if followers:
            for res in records:
                for follower in followers:
                    res.sudo().activity_schedule(
                        'purchase_tender.mail_act_tender_create',
                        summary='Purchase Tender',
                        note='New tender has been created',
                        user_id=follower.id)
                    if res.closing_date or res.new_closing_date or res.initial_meeting_date:
                        note = self._build_date_note(
                            res.closing_date, res.new_closing_date, res.initial_meeting_date)
                        res.sudo().activity_schedule(
                            'purchase_tender.mail_act_tender_create',
                            summary='Purchase Tender Date Update',
                            note=note,
                            user_id=follower.id)
        if email_new:
            for res in records:
                res._send_tender_mail('purchase_tender.mail_template_new_tender')
        return records

    def write(self, values):
        res = super().write(values)
        followers = self.env['purchase.tender.follower'].search([]).mapped('followers')
        if followers:
            if values.get('state', False) in ['postponed', 'cancelled']:
                for follower in followers:
                    self.sudo().activity_schedule(
                        'purchase_tender.mail_act_tender_create',
                        summary='Purchase Tender',
                        note='Tender status changed to {}'.format(values['state']),
                        user_id=follower.id)
            if values.get('closing_date') or values.get('new_closing_date') or values.get('initial_meeting_date'):
                for follower in followers:
                    note = self._build_date_note(
                        values.get('closing_date'), values.get('new_closing_date'),
                        values.get('initial_meeting_date'))
                    self.sudo().activity_schedule(
                        'purchase_tender.mail_act_tender_create',
                        summary='Purchase Tender Date Update',
                        note=note,
                        user_id=follower.id)
        if values.get('state') and self._email_enabled('status'):
            for rec in self:
                rec._send_tender_mail('purchase_tender.mail_template_status_change')
        if (values.get('closing_date') or values.get('new_closing_date')) and self._email_enabled('date'):
            for rec in self:
                rec._send_tender_mail('purchase_tender.mail_template_date_change')
        return res

    @staticmethod
    def _build_date_note(closing_date, new_closing_date, initial_meeting_date):
        note = ''
        if closing_date:
            note += 'Tender closing date is {} \n'.format(closing_date)
        if new_closing_date:
            note += 'Tender new closing date is {} \n'.format(new_closing_date)
        if initial_meeting_date:
            note += 'Tender initial meeting date is {}'.format(initial_meeting_date)
        return note

    @api.depends('price', 'winner_price', 'winner',
                 'price_analysis_ids.price', 'price_analysis_ids.contact')
    def compute_to_win(self):
        company_partner = self.env.company.sudo().partner_id
        for rec in self:
            care_bid = rec.price_analysis_ids.filtered(lambda p: p.contact.id == company_partner.id)
            if care_bid and care_bid[0].price and rec.winner_price and rec.winner.id != company_partner.id:
                rec.to_win = care_bid[0].price - rec.winner_price
            else:
                rec.to_win = 0

    @api.depends('price_analysis_ids.price', 'price_analysis_ids.state',
                 'price_analysis_ids.contact', 'price_analysis_ids.rank',
                 'price_analysis_ids.rate')
    def compute_winner(self):
        company_partner = self.env.company.sudo().partner_id
        for rec in self:
            rec.winner = False
            rec.winner_price = False
            rec.winner_rate_price = False
            rec.care_rank = False
            valid_bids = rec.price_analysis_ids.filtered(
                lambda p: p.state != 'excepted' and p.price)
            if valid_bids:
                best = min(valid_bids, key=lambda p: p.price)
                rec.winner = best.contact.id
                rec.winner_price = best.price
                rec.winner_rate_price = best.rate
            care_bid = rec.price_analysis_ids.filtered(lambda p: p.contact.id == company_partner.id)
            if care_bid:
                rec.care_rank = care_bid[0].rank

    @api.depends('price_analysis_ids.price', 'price_analysis_ids.contact', 'company_id')
    def _compute_our_price(self):
        for rec in self:
            partner = rec.company_id.partner_id
            care_bid = rec.price_analysis_ids.filtered(lambda p: p.contact.id == partner.id)
            rec.our_price = care_bid[:1].price if care_bid else 0.0

    @api.depends('to_win', 'winner_price')
    def _compute_price_gap(self):
        for rec in self:
            rec.price_gap = rec.to_win
            rec.price_gap_pct = (rec.to_win / rec.winner_price * 100) if rec.winner_price else 0.0

    @api.depends('closing_date', 'new_closing_date')
    def _compute_days_to_close(self):
        today = fields.Date.context_today(self)
        for rec in self:
            effective = rec.new_closing_date or rec.closing_date
            rec.days_to_close = (effective - today).days if effective else 0

    @api.depends('care_rank', 'state', 'price_analysis_ids')
    def _compute_win_probability(self):
        cp = self.env['ir.config_parameter'].sudo()
        p1 = float(cp.get_param('purchase_tender.winprob_rank1', 85) or 85)
        p2 = float(cp.get_param('purchase_tender.winprob_rank2', 55) or 55)
        p3 = float(cp.get_param('purchase_tender.winprob_rank3', 35) or 35)
        po = float(cp.get_param('purchase_tender.winprob_other', 20) or 20)
        pn = float(cp.get_param('purchase_tender.winprob_norank', 50) or 50)
        for rec in self:
            if rec.state in WON_STATES:
                rec.win_probability = 100.0
            elif rec.state in ('lost', 'cancelled', 'closed', 'excepted'):
                rec.win_probability = 0.0
            elif rec.care_rank == 1:
                rec.win_probability = p1
            elif rec.care_rank == 2:
                rec.win_probability = p2
            elif rec.care_rank == 3:
                rec.win_probability = p3
            elif rec.care_rank:
                rec.win_probability = po
            else:
                rec.win_probability = pn

    # Higher score = shown first on the "All" list (purchased + active/urgent on top).
    _STATE_WEIGHT = {
        'winner': 96, 'docs_purchased': 95, 'preparing': 90, 'participated': 88,
        'purchased': 85, 'interested': 80, 'in_progress': 70, 'under_study': 60,
        'new': 55, 'postponed': 40, 'completed': 30, 'excepted': 15,
        'lost': 12, 'closed': 8, 'cancelled': 5,
    }

    def _importance_weights(self):
        weights = dict(self._STATE_WEIGHT)
        raw = self.env['ir.config_parameter'].sudo().get_param('purchase_tender.importance_weights', '')
        for line in (raw or '').replace(',', '\n').split('\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                try:
                    weights[k.strip()] = float(v.strip())
                except ValueError:
                    pass
        return weights

    @api.depends('state', 'price', 'days_to_close', 'win_probability')
    def _compute_importance(self):
        weights = self._importance_weights()
        cp = self.env['ir.config_parameter'].sudo()
        u3 = int(cp.get_param('purchase_tender.imp_urgent3', 400) or 400)
        u7 = int(cp.get_param('purchase_tender.imp_urgent7', 250) or 250)
        u14 = int(cp.get_param('purchase_tender.imp_urgent14', 120) or 120)
        for rec in self:
            score = weights.get(rec.state, 0) * 1000
            if rec.state in ACTIVE_STATES and rec.days_to_close is not None:
                if 0 <= rec.days_to_close <= 3:
                    score += u3
                elif 0 <= rec.days_to_close <= 7:
                    score += u7
                elif 0 <= rec.days_to_close <= 14:
                    score += u14
            score += int(min(rec.price or 0.0, 100000) / 1000)
            score += int(rec.win_probability or 0.0)
            rec.importance = int(score)

    def action_print_requirements(self):
        self.ensure_one()
        return self.env.ref('purchase_tender.action_tender_requirements_report').report_action(self)

    @api.depends('requirement_ids.is_ready', 'requirement_ids.category')
    def _compute_requirement_progress(self):
        # readiness applies to the actionable items the company must prepare
        actionable = ('document', 'equipment', 'tool')
        for rec in self:
            items = rec.requirement_ids.filtered(lambda r: r.category in actionable)
            total = len(items)
            ready = len(items.filtered('is_ready'))
            rec.requirement_total = total
            rec.requirement_ready = ready
            rec.requirement_progress = (100.0 * ready / total) if total else 0.0

    @api.depends('checklist_progress', 'checklist_ids', 'requirement_progress', 'requirement_total')
    def _compute_prep_score(self):
        # one preparedness number: average of the available signals
        # (pre-bid checklist + extracted-requirements readiness)
        for rec in self:
            parts = []
            if rec.checklist_ids:
                parts.append(rec.checklist_progress or 0.0)
            if rec.requirement_total:
                parts.append(rec.requirement_progress or 0.0)
            rec.prep_score = (sum(parts) / len(parts)) if parts else 0.0

    def action_analyze_document(self):
        self.ensure_one()
        if not self.tender_document:
            raise UserError('يُرجى رفع ملف المناقصة أولاً.')
        key = self.env['ir.config_parameter'].sudo().get_param('purchase_tender.ai_api_key')
        if not key:
            raise UserError('تحليل المستند يتطلب مفتاح الذكاء الاصطناعي (Claude). '
                            'أضِفه من: الإعدادات ← المناقصات ← الذكاء الاصطناعي.')
        return self._run_ai_analysis(key)

    def _document_source(self):
        """Build the Claude content block for the uploaded file (PDF or image)."""
        data = self.tender_document
        if isinstance(data, bytes):
            data = data.decode('ascii', 'ignore')
        data = (data or '').replace('\n', '').replace('\r', '')
        name = (self.tender_document_name or '').lower()
        if name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            media = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                     'gif': 'image/gif', 'webp': 'image/webp'}[name.rsplit('.', 1)[-1]]
            return {'type': 'image',
                    'source': {'type': 'base64', 'media_type': media, 'data': data}}
        # default: treat as PDF (Claude reads PDFs natively)
        return {'type': 'document',
                'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data}}

    def _run_ai_analysis(self, key):
        """Send the tender file to Claude, parse the structured result, and fill
        the requirement tabs + executive summary. Called from the form button."""
        self.ensure_one()
        try:
            import requests
        except ImportError:
            raise UserError('مكتبة requests غير متوفّرة على الخادم.')

        # Claude rejects requests larger than 32MB; base64 inflates ~33%.
        # Guard ~28MB of original file so the whole request stays under the cap.
        if len(self.tender_document or b'') > 38_000_000:  # base64 chars ≈ 28MB file
            raise UserError('حجم الملف كبير جداً للتحليل الآلي (الحد ~28 ميجابايت). '
                            'يُرجى ضغط ملف الـ PDF أو رفع الأجزاء المطلوبة فقط.')

        body = {
            'model': AI_MODEL,
            'max_tokens': 8000,
            'system': AI_SYSTEM,
            'output_config': {'format': {'type': 'json_schema', 'schema': AI_SCHEMA}},
            'messages': [{
                'role': 'user',
                'content': [
                    self._document_source(),
                    {'type': 'text', 'text': 'حلّل ملف المناقصة المرفق واستخرج كل المتطلبات '
                                             'والمعلومات وفق التعليمات.'},
                ],
            }],
        }
        headers = {
            'x-api-key': key,
            'anthropic-version': AI_VERSION,
            'content-type': 'application/json',
        }
        try:
            resp = requests.post(AI_ENDPOINT, headers=headers,
                                 data=json.dumps(body), timeout=180)
        except requests.exceptions.RequestException as e:
            _logger.exception('Tender AI request failed')
            raise UserError('تعذّر الاتصال بخدمة الذكاء الاصطناعي: %s' % e)

        if resp.status_code == 401:
            raise UserError('مفتاح الذكاء الاصطناعي غير صالح. تحقّق منه في الإعدادات.')
        if resp.status_code == 429:
            raise UserError('تم تجاوز حدّ الطلبات مؤقتاً. حاول بعد قليل.')
        if resp.status_code >= 400:
            _logger.error('Tender AI error %s: %s', resp.status_code, resp.text[:500])
            raise UserError('فشل تحليل المستند (رمز %s). راجع السجلّ للتفاصيل.' % resp.status_code)

        payload = resp.json()
        if payload.get('stop_reason') == 'refusal':
            raise UserError('رفض النظام تحليل هذا المستند. تأكّد من أنه ملف مناقصة سليم.')
        try:
            text = next(b['text'] for b in payload.get('content', []) if b.get('type') == 'text')
            data = json.loads(text)
        except (StopIteration, ValueError, KeyError):
            _logger.error('Tender AI: unexpected response %s', json.dumps(payload)[:500])
            raise UserError('تعذّر قراءة نتيجة التحليل. حاول مرّة أخرى.')

        # rebuild the requirement lines from the model output
        cmds = [(5, 0, 0)]
        for i, r in enumerate(data.get('requirements', [])):
            cat = r.get('category')
            if cat not in AI_CATEGORIES:
                cat = 'info'
            name = (r.get('name') or '').strip()
            if not name:
                continue
            cmds.append((0, 0, {
                'sequence': (i + 1) * 10,
                'category': cat,
                'name': name[:255],
                'detail': (r.get('detail') or '').strip()[:255] or False,
                'qty': r.get('qty') or 0,
            }))
        vals = {
            'requirement_ids': cmds,
            'ai_summary': data.get('summary') or '<p>لا يوجد ملخّص.</p>',
            'ai_analyzed': True,
        }
        self.write(vals)

        # seed required documents into the pre-bid checklist (without duplicates)
        existing = {(c.name or '').strip() for c in self.checklist_ids}
        seq = (max(self.checklist_ids.mapped('sequence') or [0])) + 10
        doc_cmds = []
        for r in data.get('requirements', []):
            if r.get('category') == 'document':
                label = ('تجهيز: ' + (r.get('name') or '').strip())[:255]
                if label and label not in existing:
                    doc_cmds.append((0, 0, {'sequence': seq, 'name': label}))
                    existing.add(label)
                    seq += 10
        if doc_cmds:
            self.write({'checklist_ids': doc_cmds})

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _default_checklist_items(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('purchase_tender.default_checklist', '')
        items = [x.strip() for x in (raw or '').split('\n') if x.strip()]
        return items or DEFAULT_CHECKLIST

    def action_seed_checklist(self):
        items = self._default_checklist_items()
        for rec in self:
            if not rec.checklist_ids:
                rec.checklist_ids = [(0, 0, {'sequence': (i + 1) * 10, 'name': item})
                                     for i, item in enumerate(items)]

    @api.depends('checklist_ids.is_done')
    def _compute_checklist(self):
        for rec in self:
            total = len(rec.checklist_ids)
            done = len(rec.checklist_ids.filtered('is_done'))
            rec.checklist_total = total
            rec.checklist_done = done
            rec.checklist_progress = round(done / total * 100.0, 0) if total else 0.0

    @api.depends('expiry_date', 'guarantee')
    def _compute_guarantee_status(self):
        today = fields.Date.context_today(self)
        days = self._cfg_int('guarantee_days', 30)
        for rec in self:
            if not rec.guarantee or not rec.expiry_date:
                rec.guarantee_status = 'none'
            elif rec.expiry_date < today:
                rec.guarantee_status = 'expired'
            elif (rec.expiry_date - today).days <= days:
                rec.guarantee_status = 'expiring'
            else:
                rec.guarantee_status = 'valid'

    @api.depends('name')
    def _compute_short_name(self):
        for rec in self:
            name = (rec.name or '').strip()
            words = name.split()
            short = ' '.join(words[:4])
            if len(short) > 30:
                short = short[:30].rstrip() + '…'
            rec.short_name = short or (rec.tender_no or '—')

    @api.depends('name', 'tender_no', 'organization')
    def _compute_display_name(self):
        for tender in self:
            name = tender.name or ''
            if tender.tender_no:
                name += ' - ' + tender.tender_no
            if tender.organization:
                name += ' - ' + tender.organization.name
            tender.display_name = name

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_set_under_study(self):
        self.write({'state': 'under_study'})

    def action_set_docs_purchased(self):
        self.write({'state': 'docs_purchased'})

    def action_set_declined(self):
        self.write({'state': 'excepted'})

    def action_set_preparing(self):
        self.write({'state': 'preparing'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_completed(self):
        self.write({'state': 'completed'})

    def action_set_participated(self):
        self.write({'state': 'participated'})

    def action_set_interested(self):
        self.write({'state': 'interested'})

    def action_set_winner(self):
        self.write({'state': 'winner'})

    def action_set_purchased(self):
        self.write({'state': 'purchased'})

    def action_set_lost(self):
        self.write({'state': 'lost'})

    def action_set_postponed(self):
        self.write({'state': 'postponed'})

    def action_set_closed(self):
        self.write({'state': 'closed'})

    def action_set_cancelled(self):
        self.write({'state': 'cancelled'})

    def action_reset_new(self):
        self.write({'state': 'new'})

    # ------------------------------------------------------------------
    # Email notifications
    # ------------------------------------------------------------------
    def _tender_follower_partners(self):
        users = self.env['purchase.tender.follower'].sudo().search([]).mapped('followers')
        return users.mapped('partner_id').filtered(lambda p: p.email)

    def _email_enabled(self, key):
        val = self.env['ir.config_parameter'].sudo().get_param('purchase_tender.email_%s' % key, 'True')
        return str(val).lower() not in ('false', '0', '')

    def _cfg_int(self, key, default):
        return int(self.env['ir.config_parameter'].sudo().get_param('purchase_tender.%s' % key, default) or default)

    def _send_tender_mail(self, template_xmlid):
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        partners = self._tender_follower_partners()
        for partner in partners:
            template.sudo().send_mail(
                self.id, force_send=False,
                email_values={'email_to': partner.email})

    @api.model
    def _cron_tender_closing_soon(self):
        if not self._email_enabled('closing'):
            return
        days = self._cfg_int('closing_soon_days', 3)
        for t in self.search([('state', 'in', list(ACTIVE_STATES))]):
            if 0 <= t.days_to_close <= days:
                t._send_tender_mail('purchase_tender.mail_template_closing_soon')

    @api.model
    def _cron_tender_guarantee_expiring(self):
        if not self._email_enabled('guarantee'):
            return
        for t in self.search([('guarantee_status', '=', 'expiring')]):
            t._send_tender_mail('purchase_tender.mail_template_guarantee_expiring')

    @api.model
    def _cron_tender_weekly_digest(self):
        if not self._email_enabled('digest'):
            return
        partners = self._tender_follower_partners()
        if not partners:
            return
        active = self.search([('state', 'in', list(ACTIVE_STATES))])
        closing = active.filtered(lambda t: 0 <= t.days_to_close <= 7)
        won = self.search_count([('state', 'in', list(WON_STATES))])
        rows = ''
        for t in closing.sorted(key=lambda t: t.days_to_close)[:8]:
            rows += (
                '<tr><td style="padding:8px;border-bottom:1px solid #e6e8ef;font-weight:700;">%s</td>'
                '<td style="padding:8px;border-bottom:1px solid #e6e8ef;color:#7b8499;">%s</td>'
                '<td style="padding:8px;border-bottom:1px solid #e6e8ef;color:#e25563;font-weight:800;">%s يوم</td></tr>'
                % (t.name or '', t.organization.name or '', t.days_to_close))
        body = (
            '<div dir="rtl" style="background:#eceef3;padding:16px;font-family:Cairo,Tahoma,sans-serif;">'
            '<table align="center" width="600" style="max-width:600px;margin:auto;background:#fff;border-radius:14px;'
            'overflow:hidden;border:1px solid #e6e8ef;"><tr><td style="height:5px;background:#017e84;"></td></tr>'
            '<tr><td style="background:#714B67;padding:15px 22px;color:#fff;font-weight:800;">🏛️ إدارة المناقصات — Care</td></tr>'
            '<tr><td style="padding:18px 22px 4px;font-size:18px;font-weight:800;">📊 الملخّص الأسبوعي</td></tr>'
            '<tr><td style="padding:6px 22px;">'
            '<table width="100%%" style="text-align:center;font-weight:800;"><tr>'
            '<td style="padding:10px;background:#f7f8fb;border-radius:10px;">نشطة<br/><span style="font-size:22px;">%s</span></td>'
            '<td style="width:8px;"></td>'
            '<td style="padding:10px;background:#f7f8fb;border-radius:10px;">تُغلق خلال أسبوع<br/><span style="font-size:22px;color:#e25563;">%s</span></td>'
            '<td style="width:8px;"></td>'
            '<td style="padding:10px;background:#f7f8fb;border-radius:10px;">فزنا بها<br/><span style="font-size:22px;color:#21b07b;">%s</span></td>'
            '</tr></table>'
            '<div style="font-weight:800;margin:16px 0 4px;">⏰ أقرب المواعيد</div>'
            '<table width="100%%" style="border-collapse:collapse;font-size:13px;">%s</table>'
            '</td></tr>'
            '<tr><td style="padding:14px 22px;background:#fafbfd;border-top:1px solid #e6e8ef;'
            'color:#7b8499;font-size:11px;text-align:center;">نظام إدارة المناقصات · care-kw.com</td></tr>'
            '</table></div>'
            % (len(active), len(closing), won, rows or '<tr><td style="padding:8px;color:#7b8499;">لا مواعيد قريبة</td></tr>'))
        mail_from = self.env.company.email or self.env.user.email_formatted
        for partner in partners:
            self.env['mail.mail'].sudo().create({
                'subject': '📊 الملخّص الأسبوعي للمناقصات',
                'email_from': mail_from,
                'email_to': partner.email,
                'body_html': body,
            })

    @api.model
    def _cron_new_entrants_digest(self):
        if not self._email_enabled('new_entrants'):
            return
        partners = self._tender_follower_partners()
        if not partners:
            return
        entrants = self.env['purchase.tender.competitor'].search(
            [('is_new_entrant', '=', True)], order='total_bids desc')
        if not entrants:
            return
        rows = ''
        for c in entrants[:15]:
            rows += (
                '<tr><td style="padding:8px;border-bottom:1px solid #e6e8ef;font-weight:700;">%s</td>'
                '<td style="padding:8px;border-bottom:1px solid #e6e8ef;color:#7b8499;">%s</td>'
                '<td style="padding:8px;border-bottom:1px solid #e6e8ef;">%s</td>'
                '<td style="padding:8px;border-bottom:1px solid #e6e8ef;font-weight:800;">%s</td></tr>'
                % (c.partner_id.name or '', c.top_ministry_id.name or '—', c.first_seen or '—', c.total_bids))
        body = (
            '<div dir="rtl" style="background:#eceef3;padding:16px;font-family:Cairo,Tahoma,sans-serif;">'
            '<table align="center" width="600" style="max-width:600px;margin:auto;background:#fff;border-radius:14px;'
            'overflow:hidden;border:1px solid #e6e8ef;"><tr><td style="height:5px;background:#8b5cf6;"></td></tr>'
            '<tr><td style="background:#714B67;padding:15px 22px;color:#fff;font-weight:800;">🏛️ إدارة المناقصات — Care</td></tr>'
            '<tr><td style="padding:18px 22px 4px;font-size:18px;font-weight:800;">🆕 منافسون جدد دخلوا السوق</td></tr>'
            '<tr><td style="padding:4px 22px;color:#7b8499;font-weight:700;font-size:13px;">منافسون ظهروا لأول مرة خلال آخر 90 يوماً</td></tr>'
            '<tr><td style="padding:10px 22px;"><table width="100%%" style="border-collapse:collapse;font-size:13px;">'
            '<tr><th style="text-align:right;padding:8px;color:#7b8499;border-bottom:1px solid #e6e8ef;">المنافس</th>'
            '<th style="text-align:right;padding:8px;color:#7b8499;border-bottom:1px solid #e6e8ef;">جهته الأبرز</th>'
            '<th style="text-align:right;padding:8px;color:#7b8499;border-bottom:1px solid #e6e8ef;">أول ظهور</th>'
            '<th style="text-align:right;padding:8px;color:#7b8499;border-bottom:1px solid #e6e8ef;">عطاءات</th></tr>'
            '%s</table></td></tr>'
            '<tr><td style="padding:14px 22px;background:#fafbfd;border-top:1px solid #e6e8ef;'
            'color:#7b8499;font-size:11px;text-align:center;">نظام إدارة المناقصات · care-kw.com</td></tr>'
            '</table></div>' % rows)
        mail_from = self.env.company.email or self.env.user.email_formatted
        for partner in partners:
            self.env['mail.mail'].sudo().create({
                'subject': '🆕 منافسون جدد دخلوا السوق',
                'email_from': mail_from, 'email_to': partner.email, 'body_html': body,
            })

    def _send_watchlist_alert(self, competitor):
        self.ensure_one()
        if not self._email_enabled('watchlist'):
            return
        partners = self._tender_follower_partners()
        if not partners:
            return
        link = '%s/web#id=%s&model=purchase.tender&view_type=form' % (self.get_base_url(), self.id)
        body = (
            '<div dir="rtl" style="background:#eceef3;padding:16px;font-family:Cairo,Tahoma,sans-serif;">'
            '<table align="center" width="600" style="max-width:600px;margin:auto;background:#fff;border-radius:14px;'
            'overflow:hidden;border:1px solid #e6e8ef;"><tr><td style="height:5px;background:#e25563;"></td></tr>'
            '<tr><td style="background:#714B67;padding:15px 22px;color:#fff;font-weight:800;">🏛️ إدارة المناقصات — Care</td></tr>'
            '<tr><td style="padding:20px 22px 6px;"><div style="font-size:18px;font-weight:800;">👁️ منافس مُتابَع دخل المنافسة</div>'
            '<div style="color:#7b8499;font-weight:700;font-size:13px;margin-top:3px;">قدّم <b>%s</b> عطاءً على مناقصة تتابعها</div></td></tr>'
            '<tr><td style="padding:10px 22px 4px;">'
            '<table width="100%%" style="border:1px solid #e6e8ef;border-radius:12px;">'
            '<tr><td style="padding:12px 14px;background:#fafbfd;border-bottom:1px solid #e6e8ef;">'
            '<div style="font-size:12px;font-weight:800;color:#7b8499;">%s</div>'
            '<div style="font-size:15px;font-weight:800;">%s</div>'
            '<div style="font-size:12px;color:#7b8499;font-weight:700;">%s</div></td></tr>'
            '<tr><td style="padding:12px 14px;font-weight:700;font-size:13px;line-height:2;">'
            '👁️ المنافس: <b style="color:#e25563;">%s</b><br/>💲 سعرنا: <b>%.3f</b><br/>'
            '📊 احتمالية فوزنا: <b>%s%%</b></td></tr></table>'
            '<table width="100%%" style="margin:14px 0 8px;"><tr><td align="center" style="background:#e25563;border-radius:10px;">'
            '<a href="%s" style="display:block;padding:12px;color:#fff;text-decoration:none;font-weight:800;font-size:14px;">عرض المناقصة ←</a>'
            '</td></tr></table></td></tr>'
            '<tr><td style="padding:14px 22px;background:#fafbfd;border-top:1px solid #e6e8ef;'
            'color:#7b8499;font-size:11px;text-align:center;">نظام إدارة المناقصات · care-kw.com</td></tr>'
            '</table></div>'
            % (competitor.name or '', self.tender_no or '—', self.name or '', self.organization.name or '',
               competitor.name or '', self.our_price or 0.0, self.win_probability or 0, link))
        mail_from = self.env.company.email or self.env.user.email_formatted
        for partner in partners:
            self.env['mail.mail'].sudo().create({
                'subject': '👁️ منافس مُتابَع دخل المنافسة: %s' % (self.name or ''),
                'email_from': mail_from, 'email_to': partner.email, 'body_html': body,
            })

    # ------------------------------------------------------------------
    # Dashboard data
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, year=None):
        """Aggregate everything the dashboard needs in a single call."""
        domain = []
        if year and str(year) != 'all':
            domain += [('issue_date', '>=', '%s-01-01' % year),
                       ('issue_date', '<=', '%s-12-31' % year)]
        tenders = self.search(domain)
        today = fields.Date.context_today(self)

        won_states = WON_STATES
        active_states = ACTIVE_STATES
        won = tenders.filtered(lambda t: t.state in won_states)
        lost = tenders.filtered(lambda t: t.state == 'lost')
        active = tenders.filtered(lambda t: t.state in active_states)

        decided = len(won) + len(lost)
        win_rate = (len(won) / decided * 100) if decided else 0.0

        ranks = won.mapped('care_rank') + lost.mapped('care_rank')
        ranked = [r for r in tenders.mapped('care_rank') if r]
        avg_rank = (sum(ranked) / len(ranked)) if ranked else 0.0

        gaps = [t.price_gap_pct for t in tenders if t.price_gap_pct]
        avg_gap = (sum(gaps) / len(gaps)) if gaps else 0.0

        guar_recs = tenders.filtered(lambda t: t.guarantee and t.guarantee_status in ('valid', 'expiring'))
        guarantees_value = sum(guar_recs.mapped('guarantee'))
        guarantees_expiring = len(tenders.filtered(lambda t: t.guarantee_status == 'expiring'))
        money_left = sum(t.to_win for t in lost if t.to_win and t.to_win > 0)

        closing_7d = len(active.filtered(lambda t: 0 <= t.days_to_close <= 7))
        win_prob_active = (sum(active.mapped('win_probability')) / len(active)) if active else 0.0

        # --- status distribution ---
        state_labels = dict(self._fields['state'].selection)
        status_dist = {}
        for t in tenders:
            status_dist[t.state] = status_dist.get(t.state, 0) + 1

        # --- monthly trend (by issue_date month) ---
        months = [0] * 12
        trend_won = [0] * 12
        trend_lost = [0] * 12
        trend_active = [0] * 12
        cum_value = [0.0] * 12
        for t in tenders:
            if not t.issue_date:
                continue
            m = t.issue_date.month - 1
            months[m] += 1
            if t.state in won_states:
                trend_won[m] += 1
                cum_value[m] += t.winner_price or 0.0
            elif t.state == 'lost':
                trend_lost[m] += 1
            elif t.state in active_states:
                trend_active[m] += 1
        # cumulative sum
        running = 0.0
        cum_running = []
        for v in cum_value:
            running += v
            cum_running.append(round(running, 2))

        # --- by organization ---
        org_count = {}
        org_won = {}
        org_lost = {}
        for t in tenders:
            org = t.organization.name or 'غير محدد'
            org_count[org] = org_count.get(org, 0) + 1
            if t.state in won_states:
                org_won[org] = org_won.get(org, 0) + 1
            elif t.state == 'lost':
                org_lost[org] = org_lost.get(org, 0) + 1
        top_orgs = sorted(org_count.items(), key=lambda x: x[1], reverse=True)[:6]
        win_rate_by_org = []
        for org, _c in top_orgs:
            d = org_won.get(org, 0) + org_lost.get(org, 0)
            wr = (org_won.get(org, 0) / d * 100) if d else 0
            win_rate_by_org.append({'org': org, 'rate': round(wr, 1)})

        # --- by bid type ---
        bid_dist = {}
        for t in tenders:
            bt = t.bid_type.name or 'غير محدد'
            bid_dist[bt] = bid_dist.get(bt, 0) + 1

        # --- rank distribution ---
        rank_dist = {'1': 0, '2': 0, '3': 0, '4': 0, '5+': 0}
        for r in ranked:
            if r >= 5:
                rank_dist['5+'] += 1
            elif r in (1, 2, 3, 4):
                rank_dist[str(r)] += 1

        # --- funnel ---
        funnel = {
            'listed': len(tenders),
            'participated': len(tenders.filtered(
                lambda t: t.state in ('participated', 'interested', 'winner', 'purchased', 'lost'))),
            'qualified': len(tenders.filtered(
                lambda t: t.state in ('interested', 'winner', 'purchased'))),
            'won': len(won),
            'purchased': len(tenders.filtered(lambda t: t.state == 'purchased')),
        }

        # --- competitors (who beats us) ---
        company_partner = self.env.company.sudo().partner_id
        comp = {}
        for t in tenders:
            if t.winner and t.winner.id != company_partner.id and t.state == 'lost':
                cname = t.winner.name
                rec = comp.setdefault(cname, {'count': 0, 'gap': 0.0})
                rec['count'] += 1
                rec['gap'] += t.to_win or 0.0
        competitors = []
        for cname, rec in sorted(comp.items(), key=lambda x: x[1]['count'], reverse=True)[:5]:
            competitors.append({
                'name': cname,
                'count': rec['count'],
                'avg_gap': round(rec['gap'] / rec['count'], 2) if rec['count'] else 0,
            })

        # --- upcoming closings ---
        upcoming = []
        for t in active.filtered(lambda t: t.days_to_close >= 0).sorted(key=lambda t: t.days_to_close)[:6]:
            upcoming.append({
                'id': t.id, 'name': t.name,
                'org': t.organization.name or '',
                'days': t.days_to_close,
                'date': str(t.new_closing_date or t.closing_date or ''),
            })

        # --- recent (newest first) ---
        oldest = fields.Date.to_date('1900-01-01')
        recent = []
        recent_recs = tenders.sorted(key=lambda t: (t.issue_date or oldest, t.id), reverse=True)[:8]
        for t in recent_recs:
            recent.append({
                'id': t.id, 'name': t.short_name or t.name,
                'org': t.organization.name or '',
                'state': t.state, 'state_label': state_labels.get(t.state, t.state),
                'price': t.our_price,
                'winner': t.winner.name or '',
                'winner_price': t.winner_price,
                'rank': t.care_rank,
                'to_win': t.to_win,
            })

        # --- closest losses ---
        closest = []
        for t in lost.filtered(lambda t: t.to_win and t.to_win > 0).sorted(key=lambda t: t.to_win)[:6]:
            closest.append({
                'id': t.id, 'name': t.name,
                'org': t.organization.name or '',
                'our_price': t.price_analysis_ids.filtered(
                    lambda p: p.contact.id == company_partner.id)[:1].mapped('price'),
                'winner': t.winner.name or '',
                'gap': t.to_win,
            })

        # --- guarantees list ---
        guarantees = []
        for t in tenders.filtered(lambda t: t.guarantee).sorted(key=lambda t: (t.issue_date or oldest, t.id), reverse=True)[:8]:
            guarantees.append({
                'id': t.id, 'name': t.name,
                'value': t.guarantee,
                'expiry': str(t.expiry_date or ''),
                'status': t.guarantee_status,
            })

        # --- stats by company ---
        comp_stats = {}
        for t in tenders:
            c = t.company_id.name or 'غير محدد'
            rec = comp_stats.setdefault(c, {'count': 0, 'won': 0, 'value': 0.0})
            rec['count'] += 1
            if t.state in won_states:
                rec['won'] += 1
                rec['value'] += t.winner_price or 0.0
        by_company = [{'company': k, 'count': v['count'], 'won': v['won'],
                       'rate': round(v['won'] / v['count'] * 100, 1) if v['count'] else 0,
                       'value': round(v['value'], 2)}
                      for k, v in sorted(comp_stats.items(), key=lambda x: x[1]['count'], reverse=True)]

        # --- stats by activity (bidding type) ---
        act_stats = {}
        for t in tenders:
            a = t.bid_type.name or 'غير محدد'
            rec = act_stats.setdefault(a, {'count': 0, 'won': 0, 'value': 0.0})
            rec['count'] += 1
            if t.state in won_states:
                rec['won'] += 1
                rec['value'] += t.winner_price or 0.0
        by_activity = [{'activity': k, 'count': v['count'], 'won': v['won'],
                        'value': round(v['value'], 2)}
                       for k, v in sorted(act_stats.items(), key=lambda x: x[1]['count'], reverse=True)]

        # --- forecast: expected value weighted by win-probability ---
        # Estimate each active tender's CONTRACT value: our actual bid (our_price)
        # if set, otherwise the average winner price of historically decided
        # tenders of the same activity (bid_type), else the overall average.
        # NOTE: `price` is the spec-booklet cost (تكلفة الكراسة), NOT the contract
        # value, so it must never be used as the value basis here.
        decided_all = self.search([('state', 'in', list(won_states) + ['lost'])])
        base_vals = [t.winner_price for t in decided_all if t.winner_price]
        if not base_vals:
            base_vals = [t.our_price for t in self.search([]) if t.our_price]
        overall_avg = (sum(base_vals) / len(base_vals)) if base_vals else 0.0
        bt_acc = {}
        for t in decided_all:
            if t.winner_price:
                acc = bt_acc.setdefault(t.bid_type.id, [0.0, 0])
                acc[0] += t.winner_price
                acc[1] += 1
        bt_avg = {k: (s / n) for k, (s, n) in bt_acc.items() if n}

        def est_value(t):
            if t.our_price:
                return t.our_price, True
            return bt_avg.get(t.bid_type.id, overall_avg), False

        weighted_pipeline = 0.0
        gross_pipeline = 0.0
        priced_n = est_n = 0
        forecast = [0.0] * 12
        for t in active:
            val, is_priced = est_value(t)
            if is_priced:
                priced_n += 1
            else:
                est_n += 1
            gross_pipeline += val
            w = val * (t.win_probability or 0.0) / 100.0
            weighted_pipeline += w
            eff = t.new_closing_date or t.closing_date
            if eff:
                forecast[eff.month - 1] += w
        forecast = [round(x, 2) for x in forecast]
        expected = {
            'weighted': round(weighted_pipeline, 2),
            'gross': round(gross_pipeline, 2),
            'priced': priced_n,
            'estimated': est_n,
            'active': len(active),
            'avg_basis': round(overall_avg, 2),
        }

        # --- loss reasons ---
        loss_labels = dict(self._fields['loss_reason'].selection)
        loss_dist = {}
        for t in lost:
            k = t.loss_reason or 'unspecified'
            loss_dist[k] = loss_dist.get(k, 0) + 1
        loss_reasons = [{'key': k, 'label': loss_labels.get(k, k) if k != 'unspecified' else 'غير محدد', 'value': v}
                        for k, v in loss_dist.items()]

        # --- competitor stats (all-time, from the competitor model) ---
        Comp = self.env['purchase.tender.competitor']
        comp_recs = Comp.search([])
        comp_beat_us = sum(comp_recs.mapped('they_beat_us'))
        comp_we_beat = sum(comp_recs.mapped('we_beat_them'))
        comp_h2h = comp_beat_us + comp_we_beat
        top_threat_rec = comp_recs.sorted(key=lambda c: c.threat_score, reverse=True)[:1]
        competitor_stats = {
            'total': len(comp_recs),
            'beat_us': comp_beat_us,
            'we_beat': comp_we_beat,
            'our_winrate_field': round(comp_we_beat / comp_h2h * 100, 1) if comp_h2h else 0,
            'top_threat': (top_threat_rec.partner_id.name or '—') if top_threat_rec else '—',
        }
        comp_top = [{'name': c.partner_id.name, 'value': c.they_beat_us}
                    for c in comp_recs.sorted(key=lambda c: c.they_beat_us, reverse=True)[:6]
                    if c.they_beat_us]

        # available years
        years = sorted({t.issue_date.year for t in self.search([]) if t.issue_date}, reverse=True)

        return {
            'kpi': {
                'total': len(tenders),
                'won': len(won),
                'win_rate': round(win_rate, 1),
                'awarded_value': round(sum(won.mapped('winner_price')), 2),
                'pipeline_value': round(sum(active.mapped('price')), 2),
                'weighted_pipeline': round(weighted_pipeline, 2),
                'closing_7d': closing_7d,
                'avg_rank': round(avg_rank, 1),
                'guarantees_value': round(guarantees_value, 2),
                'guarantees_expiring': guarantees_expiring,
                'money_left': round(money_left, 2),
                'avg_gap': round(avg_gap, 1),
                'win_prob_active': round(win_prob_active, 1),
                'active': len(active),
                'lost': len(lost),
            },
            'expected': expected,
            'status_dist': [{'key': k, 'label': state_labels.get(k, k), 'value': v} for k, v in status_dist.items()],
            'by_company': by_company,
            'by_activity': by_activity,
            'competitor_stats': competitor_stats,
            'comp_top': comp_top,
            'loss_reasons': loss_reasons,
            'forecast': forecast,
            'trend': {'won': trend_won, 'lost': trend_lost, 'active': trend_active},
            'cumulative': cum_running,
            'top_orgs': [{'org': o, 'count': c} for o, c in top_orgs],
            'win_rate_by_org': win_rate_by_org,
            'bid_dist': [{'label': k, 'value': v} for k, v in bid_dist.items()],
            'rank_dist': rank_dist,
            'funnel': funnel,
            'competitors': competitors,
            'upcoming': upcoming,
            'recent': recent,
            'closest': closest,
            'guarantees': guarantees,
            'years': years,
            'currency': self.env.company.currency_id.symbol or '',
        }

    # ------------------------------------------------------------------
    # Competitor dashboard data
    # ------------------------------------------------------------------
    @api.model
    def get_competitor_dashboard_data(self, competitor_id=None, year=None):
        """Analytics for the competitor dashboard (overview + per-competitor drill-down)."""
        Comp = self.env['purchase.tender.competitor']
        PA = self.env['purchase.tender.price.analysis']
        comps = Comp.search([])
        competitors = [{'id': c.partner_id.id, 'name': c.partner_id.name}
                       for c in comps if c.partner_id]

        def pa_domain(extra=None):
            dom = [('is_ours', '=', False), ('contact', '!=', False)]
            if year and str(year) != 'all':
                dom += [('issue_date', '>=', '%s-01-01' % year),
                        ('issue_date', '<=', '%s-12-31' % year)]
            return dom + (extra or [])

        years = sorted({l.issue_date.year for l in PA.search([('contact', '!=', False)])
                        if l.issue_date}, reverse=True)

        if competitor_id:
            c = comps.filtered(lambda r: r.partner_id.id == competitor_id)[:1]
            partner = self.env['res.partner'].browse(competitor_id)
            lines = PA.search(pa_domain([('contact', '=', competitor_id)]))
            monthly = [0] * 12
            monthly_price_sum = [0.0] * 12
            monthly_cnt = [0] * 12
            mins = {}
            for l in lines:
                if l.issue_date:
                    m = l.issue_date.month - 1
                    monthly[m] += 1
                    if l.price:
                        monthly_price_sum[m] += l.price
                        monthly_cnt[m] += 1
                o = l.organization.name or 'غير محدد'
                mins[o] = mins.get(o, 0) + 1
            monthly_price = [round(monthly_price_sum[i] / monthly_cnt[i], 2) if monthly_cnt[i] else 0
                             for i in range(12)]
            ministries = sorted([{'org': k, 'count': v} for k, v in mins.items()],
                                key=lambda x: x['count'], reverse=True)[:8]
            return {
                'mode': 'one',
                'competitors': competitors,
                'selected': competitor_id,
                'years': years,
                'kpi': {
                    'name': partner.name or '',
                    'total_bids': c.total_bids, 'wins': c.wins, 'win_rate': c.win_rate,
                    'ministries': c.ministries, 'avg_price': c.avg_price,
                    'price_index': c.price_index, 'avg_rank': c.avg_rank,
                    'tenders_vs_us': c.tenders_vs_us, 'we_beat_them': c.we_beat_them,
                    'they_beat_us': c.they_beat_us, 'our_win_rate_vs': c.our_win_rate_vs,
                    'threat': c.threat_score,
                },
                'monthly': monthly,
                'monthly_price': monthly_price,
                'ministries': ministries,
                'head_to_head': {'we_beat': c.we_beat_them, 'they_beat': c.they_beat_us},
            }

        # --- overview ---
        total_bids = sum(comps.mapped('total_bids'))
        they_beat = sum(comps.mapped('they_beat_us'))
        we_beat = sum(comps.mapped('we_beat_them'))
        h2h = they_beat + we_beat
        idx = [c.price_index for c in comps if c.price_index]
        top_threats = comps.sorted(key=lambda c: c.threat_score, reverse=True)[:10]
        top_beat = comps.sorted(key=lambda c: c.they_beat_us, reverse=True)[:10]
        top_wins = comps.sorted(key=lambda c: c.wins, reverse=True)[:10]
        idx_leaders = comps.filtered(lambda c: c.price_index).sorted(
            key=lambda c: c.total_bids, reverse=True)[:10]
        mins = {}
        for l in PA.search(pa_domain()):
            o = l.organization.name or 'غير محدد'
            mins[o] = mins.get(o, 0) + 1
        by_ministry = sorted([{'org': k, 'count': v} for k, v in mins.items()],
                             key=lambda x: x['count'], reverse=True)[:8]
        return {
            'mode': 'all',
            'competitors': competitors,
            'selected': None,
            'years': years,
            'kpi': {
                'total_competitors': len(comps),
                'total_bids': total_bids,
                'they_beat_us': they_beat,
                'we_beat_them': we_beat,
                'our_win_rate': round(we_beat / h2h * 100, 1) if h2h else 0,
                'avg_price_index': round(sum(idx) / len(idx), 1) if idx else 0,
                'top_threat': top_threats[:1].partner_id.name or '—' if top_threats else '—',
                'new_entrants': len(comps.filtered(lambda c: c.is_new_entrant)),
            },
            'top_threats': [{'name': c.partner_id.name, 'value': c.threat_score} for c in top_threats],
            'top_beat_us': [{'name': c.partner_id.name, 'value': c.they_beat_us} for c in top_beat],
            'top_wins': [{'name': c.partner_id.name, 'value': c.wins} for c in top_wins],
            'price_index': [{'name': c.partner_id.name, 'value': c.price_index} for c in idx_leaders],
            'head_to_head': {'we_beat': we_beat, 'they_beat': they_beat},
            'by_ministry': by_ministry,
        }
