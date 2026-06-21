# purchase_tender — Developer Handover Documentation

> Kuwait government **tender (مناقصة) management** module for Odoo 17.
> Tracks tenders end‑to‑end: lifecycle, pricing/competitor intelligence, bid‑preparation
> checklists, AI document analysis, dashboards, e‑mail alerts and PDF reports.
> UI is **Arabic**; code/identifiers are English. This file is the single source of
> truth for handover — read it before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `purchase_tender` |
| Version | `17.0.0.0.0` |
| Odoo | 17.0 Enterprise |
| Depends | `base`, `purchase_requisition` |
| External services | **Anthropic Claude API** (optional — document analysis) |
| Python libs used | `requests` (HTTP), stdlib `json`, `logging`, `datetime` |
| Main model | `purchase.tender` |
| Menus | English labels, Arabic content (per client preference) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u purchase_tender --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. After editing JS/SCSS/XML assets, a module `-u` regenerates the asset
  bundles; a restart serves them. Log file: `/var/log/odoo/odoo-17.log`.
- `limit_time_real = 999999999` in the conf — long synchronous calls (AI) are **not**
  killed by the HTTP worker.

---

## 2. Architecture overview

```
purchase.tender  (central model — mail.thread)
├── one2many → purchase.tender.price.analysis      (competitor bids per tender)
├── one2many → purchase.tender.manpower.analysis
├── one2many → purchase.tender.vehicle.analysis
├── one2many → purchase.tender.material.info
├── one2many → purchase.tender.equipment.analysis
├── one2many → purchase.tender.initial.meeting
├── one2many → purchase.tender.checklist           (pre-bid prep tasks)
├── one2many → purchase.tender.requirement         (AI-extracted requirements)
├── many2one → bid.type                            (activity / نشاط)
└── many2one → res.partner (organization = الجهة, winner, current_co)

purchase.tender.competitor   (_auto=False SQL VIEW — competitor intelligence, read-only)
res.partner                  (inherited: tender_group_id, tender_is_competitor)
res.config.settings          (inherited: all tunables via config_parameter)

UI surfaces:
  • Backend OWL dashboards (client actions): main + competitor
  • List / Kanban / Form views (Arabic)
  • 4 QWeb-PDF reports
  • 5 mail.templates + 4 ir.cron jobs
```

**Design principles**
- Almost every threshold/weight is a **`config_parameter`** exposed in Settings, so business
  users tune behaviour without code changes (`set_values()` recomputes affected fields).
- Stored computed fields back all sorting/filtering/grouping (importance, prep_score, etc.).
- Competitor analytics are a **PostgreSQL view** (`_auto=False`) for speed over 450+ tenders.

---

## 3. Module-level constants (`models/purchase_tender.py` top)

| Constant | Meaning |
|---|---|
| `ACTIVE_STATES` | `new, under_study, docs_purchased, interested, preparing, participated` — live pipeline |
| `WON_STATES` | `winner, purchased, in_progress, completed` |
| `DEAD_STATES` | `lost, excepted, cancelled, closed` |
| `DEFAULT_CHECKLIST` | 9 default Arabic pre-bid task labels (fallback when no setting) |
| `_STATE_WEIGHT` | per-state weight (×1000) feeding the `importance` sort |
| `AI_MODEL` | `claude-opus-4-8` (Claude model id for document analysis) |
| `AI_ENDPOINT` / `AI_VERSION` | `https://api.anthropic.com/v1/messages` / `2023-06-01` |
| `AI_CATEGORIES` | `document, equipment, tool, condition, info` (== requirement categories) |
| `AI_SCHEMA` | JSON Schema forced on Claude via `output_config.format` (structured output) |
| `AI_SYSTEM` | Arabic system prompt: Kuwait-tender expert extraction instructions |

---

## 4. Data model

### 4.1 `purchase.tender` (central)
`_inherit = mail.thread, mail.activity.mixin` · `_order = 'importance desc, id desc'`

**Identity / dates:** `name`, `short_name` (computed, stored), `tender_no`, `organization`
(الجهة, required), `bid_type` (النشاط), `issue_date`, `closing_date`, `new_closing_date`,
`initial_meeting_date`, `current_co`.

**Money / bid:** `price` (purchase-docs price / سعر الشراء), `our_price` (سعرنا, computed from
our row in `price_analysis_ids`), `guarantee`, `guarantee_bank`, `guarantee_ref`,
`period`, `manpower`.

**Computed analytics (all stored):**
| Field | Compute | Notes |
|---|---|---|
| `winner`, `winner_price`, `winner_rate_price`, `care_rank` | `compute_winner` | from price analysis rows (rank 1 = winner; our rank = care_rank) |
| `to_win` | `compute_to_win` | gap we'd need to win |
| `our_price` | `_compute_our_price` | our own bid row (≠ `price`) |
| `price_gap`, `price_gap_pct` | `_compute_price_gap` | our price vs winner |
| `days_to_close` | `_compute_days_to_close` | uses `new_closing_date or closing_date` |
| `win_probability` | `_compute_win_probability` | maps `care_rank`→% via winprob settings |
| `importance` | `_compute_importance` | `state_weight×1000 + urgency + value + win_prob`; drives the default sort & "صفحة الكل" ordering |
| `guarantee_status` | `_compute_guarantee_status` | سارٍ / ينتهي قريباً / منتهٍ / لا يوجد (uses `guarantee_days` setting) |

**Lifecycle:** `state` — 15-value Arabic `Selection`. **Keys are stable; labels are Arabic.**
Notable key→label: `docs_purchased`→«شُريت الكراسة» (buying the spec booklet early),
`excepted`→«لن نشارك», `purchased`→«تمت الترسية» (awarded), `winner`→«فائزة».
Order: `new, under_study, docs_purchased, interested, excepted, preparing, participated,
winner, lost, postponed, purchased, in_progress, completed, closed, cancelled`.

**Loss tracking:** `loss_reason` (Selection), `loss_note`.

**Preparation:**
- `checklist_ids` → `purchase.tender.checklist`; rollup `checklist_done/total/progress`
  (`_compute_checklist`).
- `requirement_ids` → `purchase.tender.requirement` (AI output); rollup
  `requirement_ready/total/progress` over actionable categories
  (`document, equipment, tool`) via `_compute_requirement_progress`.
- `prep_score` (جاهزية العطاء) = **average** of `checklist_progress` and
  `requirement_progress`, each counted only when it has data (`_compute_prep_score`).

**AI document:** `tender_document` (Binary), `tender_document_name`, `ai_summary` (Html),
`ai_analyzed` (Boolean).

**Sub-analyses (one2many):** `price_analysis_ids`, `manpower_analysis_ids`,
`vehicle_analysis_ids`, `material_info_ids`, `equipment_analysis_ids`, `initial_meeting_ids`.

**Misc:** `image`/`image_128` (related to organization logo), `company_id`, `currency_id`,
`active`.

**Key overrides / methods:**
- `create()` / `write()` — auto-build the date-change note (`_build_date_note`),
  seed checklist, fire mail alerts (new / status / date) gated by settings.
- `action_set_*` — one button per state transition (used by list/kanban/form quick actions).
- `action_seed_checklist()` / `_default_checklist_items()` — seed prep tasks from the
  `default_checklist` setting (newline-separated) or `DEFAULT_CHECKLIST`.
- **Dashboards:** `get_dashboard_data(year)` and `get_competitor_dashboard_data(competitor_id, year)`
  — called by the OWL client actions; return plain dicts (KPIs, distributions, trends,
  by-company, by-activity, competitor stats, forecasts, upcoming, guarantees …).
- **AI:** `action_analyze_document`, `_document_source`, `_run_ai_analysis` — see §5.
- **Reports:** `action_print_requirements` → renders the requirements PDF.
- **E-mail:** `_email_enabled`, `_cfg_int`, `_send_tender_mail`, `_send_watchlist_alert`,
  and 4 cron entrypoints `_cron_*` — see §7.

### 4.2 `purchase.tender.price.analysis`
One competitor bid line on a tender. Fields: `name`, `sequence`, `contact` (the bidder),
`price`, `rate` (`compute_rate`), `rank` (`compute_rank`, 1 = lowest/winner), `state`
(مقبول/مستبعد). Related-stored from tender: `organization`, `bid_type`, `issue_date`,
`tender_state`, `winner_price`. Flags (`_compute_flags`, stored): `is_ours`, `is_winner`,
`win_count` (Integer, `group_operator='sum'` — Boolean can't aggregate in pivots),
`gap_vs_winner`. `create()` is overridden to fire **watchlist alerts** when a watched
competitor bids on an active tender.

### 4.3 `purchase.tender.competitor` — SQL VIEW (`_auto=False`)
Read-only competitor intelligence, rebuilt in `init()` (raw SQL `CREATE VIEW`). `init()`
also runs `ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS tender_group_id / tender_is_competitor`
as a **load-order safety net** (the view references those columns before `res_partner.py`
may have created them). Reads settings `new_days`, `w_beat`, `w_win`, `w_bid`.
Fields: `partner_id`, `group_id` (owner/sister-company via `tender_group_id`), `is_watched`,
`total_bids`, `wins`, `win_rate`, `ministries`, `avg_price/gap/rank`, `price_index`,
`first_seen`/`last_seen`, `is_new_entrant` (first seen within `new_days`), `top_ministry_id`
(`mode() WITHIN GROUP`), head-to-head vs us (`tenders_vs_us`, `we_beat_them`,
`they_beat_us`, `our_win_rate_vs`), and `threat_score = they_beat_us·w_beat + wins·w_win +
total_bids·w_bid`. `action_view_bids()` opens that competitor's bid lines.
**Gotcha:** PostgreSQL `round()` needs a `numeric` cast — `round(x::numeric, n)`.

### 4.4 `purchase.tender.checklist`
Pre-bid task: `tender_id` (cascade), `sequence`, `name` (المهمة), `is_done`,
`responsible_id`, `deadline`, `note`, `company_id` (related).

### 4.5 `purchase.tender.requirement`  (AI output)
`tender_id` (cascade), `sequence`, `category` (`document/equipment/tool/condition/info`),
`name`, `detail`, `qty`, `is_ready`, `company_id`. Rendered in the form across 5 category
tabs (same field, filtered by `domain`).

### 4.6 Other sub-models
`bid.type` (نشاط/activity master), `purchase.tender.manpower.analysis`,
`...vehicle.analysis`, `...material.info`, `...equipment.analysis`,
`...initial.meeting`, `purchase.tender.record`, `purchase.tender.follower` — simple
one2many detail lines off the tender.

### 4.7 `res.partner` (inherited)
- `tender_group_id` (Many2one self) — links **sister companies under one owner** so the
  competitor view groups them (علامة تابعة لشركة).
- `tender_is_competitor` (Boolean) — watchlist flag driving alerts & `is_watched`.

---

## 5. AI document analysis (Claude)

**Goal:** upload a tender PDF → Claude extracts required documents/equipment/tools/conditions/
key info into the requirement tabs + an HTML executive summary, and seeds required documents
into the prep checklist. "احترافي جداً" handover deliverable.

**Flow (`_run_ai_analysis`)**
1. Guards: file present, API key present (`config_parameter purchase_tender.ai_api_key`),
   file ≤ ~28 MB (Claude rejects requests > 32 MB; base64 inflates ~33 %).
2. `_document_source()` builds the content block — PDF → `document/application/pdf`
   (Claude reads PDFs natively, **no PyPDF2/OCR needed**); image extensions → `image/*`.
   `tender_document` is already base64 (Odoo Binary); newlines stripped.
3. **Raw HTTPS** `requests.post` to the Messages API (no Anthropic SDK installed in the
   Odoo venv — raw HTTP is the correct choice here). Model `claude-opus-4-8`,
   `output_config.format = {json_schema: AI_SCHEMA}` to force valid structured JSON,
   `system = AI_SYSTEM`, `max_tokens 8000`, `timeout 180s`.
4. Handle `401/429/4xx` and `stop_reason == "refusal"` with friendly Arabic `UserError`s.
5. Parse the first text block's JSON → rebuild `requirement_ids` (5,0,0 then create per
   category), set `ai_summary` + `ai_analyzed`, append required `document` items to
   `checklist_ids` (dedup). Returns `{'type':'ir.actions.client','tag':'reload'}`.

**Turning it on:** paste an Anthropic key in **Settings → المناقصات → الذكاء الاصطناعي →
مفتاح الـ API** (config param `purchase_tender.ai_api_key`, password-masked). Until then the
button raises a friendly "add the key" message — the feature is fully built but dormant.

**Where to change the model / prompt / schema:** the `AI_*` constants at the top of
`models/purchase_tender.py`. Model id must be a current Claude id (`claude-opus-4-8`).

---

## 6. UI

### 6.1 Views (`views/purchase_tender.xml`)
- **List:** image, `short_name`, `tender_no`, organization, `our_price`, `care_rank`,
  `win_probability` (progressbar), `prep_score` (جاهزية العطاء, progressbar),
  `checklist_progress`/`ai_analyzed` (optional cols), close date, `days_to_close`, state
  badge + quick-action buttons. Row decorations by state/urgency.
- **Kanban** (`limit=10`, styled by `static/src/kanban/tender_kanban.scss`): logo, name,
  org, KV grid (سعرنا/ترتيب/إغلاق/الضمان), win-probability bar, **جاهزية العطاء** bar,
  🔍 badge when `ai_analyzed`, state quick-action buttons.
- **Form:** header state buttons; tabs incl. قائمة التحضير (checklist + progress),
  **📎 ملف المناقصة** (upload + «🔍 تحليل المستند آلياً» + «🖨️ طباعة المتطلبات» +
  readiness bar + executive summary), 5 requirement tabs (📄 مستندات / 🛠️ معدات وأدوات /
  📋 شروط / ℹ️ معلومات), price analysis, sub-analyses.
- **Search:** state filters, closing-soon, guarantee-expiring, mine, and AI filters
  «حُلّل آلياً» / «لم يُحلّل» / «جاهز للتقديم (≥٨٠٪)»; group-by state/company/organization.

### 6.2 Dashboards (OWL client actions)
- `static/src/dashboard/` — main dashboard (`tag = purchase_tender_dashboard`). Lazy
  Chart.js (IntersectionObserver, animations off) for performance; data from
  `get_dashboard_data`. Blocks newest-first; upcoming-closings + latest-tenders at top.
  Full Arabic month names; per-state colours keyed by **state key**.
- `static/src/competitor_dashboard/` — competitor dashboard
  (`tag = purchase_tender_competitor_dashboard`); top filter to pick a competitor;
  data from `get_competitor_dashboard_data`.
- **OWL gotcha:** `String()` is not available in QWeb-OWL templates — use loose `==`.

### 6.3 Reports (`reports/`, QWeb-PDF, RTL, Cairo/Amiri font, purple header)
- `tender_summary.xml` — «ملخّص المناقصة» (figures + price analysis).
- `tender_requirements.xml` — «متطلبات المناقصة» (requirements grouped by category +
  executive summary + readiness bar + ✔/○ ready marks). Bound to the model (print menu)
  and the form button.
- `competitor_profile.xml`, `tender_bid_result.xml`, `purchase_tender.xml`.

---

## 7. Automation & settings

### 7.1 Cron jobs (`data/tender_cron.xml`) — all gated by their e-mail setting
| Cron | Method | Setting |
|---|---|---|
| Closing-Soon Reminder | `_cron_tender_closing_soon` | `email_closing` + `closing_soon_days` |
| Guarantee-Expiring Reminder | `_cron_tender_guarantee_expiring` | `email_guarantee` + `guarantee_days` |
| Weekly Digest | `_cron_tender_weekly_digest` | `email_digest` |
| New Competitors Digest | `_cron_new_entrants_digest` | `email_new_entrants` + `new_entrant_days` |

### 7.2 Mail templates (`data/mail_templates.xml`)
5 `mail.template` records (inline HTML, `type="html"` — **no CDATA**, RELAXNG rejects it;
escape `#` inside expressions). Sent via `_send_tender_mail` / `_send_watchlist_alert`.

### 7.3 Settings (`res.config.settings`, all `config_parameter`, prefix `purchase_tender.`)
Groups: e-mail toggles (8), timings (`closing_soon_days`, `guarantee_days`,
`new_entrant_days`), threat weights (`threat_beat/win/bid`), win-probability map
(`winprob_rank1..3/other/norank`), defaults (`default_view` tree/kanban, `page_size`,
`default_checklist`), importance tuning (`imp_urgent3/7/14`, `importance_weights`),
and **AI** (`ai_api_key`). `set_values()` rewrites the tender action's `view_mode`/`limit`
and recomputes `win_probability`, `guarantee_status`, `importance` on all tenders so
changes apply immediately.
> **Constraint:** `res.config.settings` only supports char/int/float/bool/selection/m2o/
> datetime — **no Text**. Multi-line inputs use `Char` + `widget="text"`.

---

## 8. Security (`security/`)
- `groups.xml` — `group_tender_user` (read), `group_tender_manager` (CRUD).
- `ir.model.access.csv` — user = read, manager = CRUD on all models; competitor view is
  read-only for both; checklist & requirement are CRUD for both groups.
- `rules.xml` — record rules (multi-company / ownership).

---

## 9. Gotchas & history (read before debugging)
- **Migrated from v16:** sibling third-party modules had v16 `attrs`/`states` which blocked
  DB updates — converted to v17 `invisible`/`readonly`/`required` Python expressions.
- **SQL view load order:** the `ALTER TABLE … IF NOT EXISTS` in `tender_competitor.init()`
  exists because the view can build before `res_partner` columns are created. Keep it.
- **PG `round`** needs `::numeric`. **Pivot aggregates** need Integer, not Boolean
  (`win_count`).
- **Dashboard "froze"** = client-side; fixed with lazy charts + animations off + plain-data
  copies + `limit=10` kanban. Server side is fast.
- **`our_price` vs `price`:** `price` = cost of the spec booklet; `our_price` = our bid
  (only ~11 % populated). The list shows `our_price` as «سعرنا».
- After settings change, computed fields are re-applied in `set_values()` — don't duplicate
  that logic elsewhere.

---

## 10. File map
```
__manifest__.py                         depends/data/assets
data/        tender.xml · mail_templates.xml · tender_cron.xml
models/      purchase_tender.py (central, ~1100 lines) + 14 sub-models
             res_config_settings.py · res_partner.py
reports/     tender_summary · tender_requirements · competitor_profile
             tender_bid_result · purchase_tender   (all QWeb-PDF)
security/    groups.xml · ir.model.access.csv · rules.xml
static/src/  dashboard/ (OWL+Chart.js)  competitor_dashboard/  kanban/ (scss)
static/mockup/  tenders.html · emails.html   (design mockups, not loaded by Odoo)
views/       purchase_tender.xml (list/kanban/form/search/menus) + per-feature views
```
