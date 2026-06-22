# hr_overtime_compensation — Developer Handover Documentation

> **HR Overtime Compensation** — a custom Odoo 17 module that lets a project manager
> raise a request to pay employees a **compensation for extra/overtime work**
> («طلب صرف تعويض عن عمل اضافي»), route it through a configurable **multi-approver
> sign-off chain**, and print an official **Arabic (RTL) PDF letter** with barcode + QR.
> UI labels are English; the printed document and its headings are Arabic. Read this
> before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_overtime_compensation` |
| Display name | HR Overtime Compensation |
| Version | `17.0` (manifest) — runs on Odoo 17 |
| License | Other proprietary |
| Category | Uncategorized |
| Depends | `hr`, `project`, `mail` |
| External Python lib | **`qrcode`** (QR generation) + stdlib `base64`, `io`, `datetime` |
| Key models | `overtime.request` (central), `overtime.request.line`, `overtime.request.approval`, `overtime.approver` (config), `overtime.reject` (wizard) |
| Inherited models | none (no `_inherit` of core models — only `mail.thread`/`mail.activity.mixin` mixins) |
| Reports | 1 QWeb-PDF: «طلب صرف تعويض عن عمل اضافي» (Arabic letter) |
| Menus | Top-level app "Overtime Compensation" |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u hr_overtime_compensation --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- No dev mode. After editing XML/report templates, a module `-u` regenerates the
  registry; a restart serves them. Log file: `/var/log/odoo/odoo-17.log`.
- > ⚠️ Requires the **`qrcode`** Python package in the Odoo venv. If `import qrcode`
  > fails, the QR compute (`_generate_qr_code`) raises and the request form fails to
  > render. Install it in `/home/odoo/.pyenv/versions/odoo-17-env`.

---

## 2. Architecture overview

```
overtime.request   (central document — mail.thread, mail.activity.mixin)
├── many2one  → project.project          (project_id, required)
├── related   → res.users                (project_manager_id = project_id.user_id)
├── one2many  → overtime.request.line     (request_line_ids — one row per employee)
│                 └── many2one → hr.employee (employee_id; hours, value, reason)
├── one2many  → overtime.request.approval (approval_ids — the sign-off chain)
│                 └── many2one → res.users (user_id, approved/rejected flags)
├── computed  → approver_users (m2m res.users), approver_users_str (csv emails)
├── barcode (Char) + qr_image / qr_url    (qr_generator.generateQrCode)
└── state: draft → submit → waiting → approve   (+ reject / cancel)

overtime.approver  (CONFIG master — ordered list of default approver users)
   └── seeds approval_ids on every new request via get_default_approvers()

overtime.reject    (TransientModel wizard — capture a reject reason)

Helpers:  models/qr_generator.py  (generateQrCode.generate_qr_code)
Report:   report/overtime_request_printout.xml  (Arabic RTL PDF + header/footer png)
Data:     data/mail_template.xml (approval email) · data/activity_type.xml (activity)
```

**Workflow in one line:** PM creates a request → fills employee lines (hours, reason)
→ Submit → each configured approver gets an email/activity and clicks **Approve** (or
**Reject** with a reason) → once *every* approver has approved, the request flips to
`approve`. Approver order comes from the `overtime.approver` config list.

---

## 3. Data model

### 3.1 `overtime.request` (central — `models/overtime_request.py`)
`_inherit = ['mail.thread', 'mail.activity.mixin']` · `_description = 'Overtime Request'`

| Field | Type | Notes |
|---|---|---|
| `project_id` | M2o `project.project` | required; the project the overtime is for |
| `project_manager_id` | M2o `res.users` | `related='project_id.user_id'`, required |
| `request_date` | Date | required; printed as «التاريخ» on the letter |
| `request_line_ids` | O2m `overtime.request.line` | employee rows (hours/value/reason) |
| `state` | Selection | `draft`(New) / `submit`(Submitted) / `waiting`(Waiting Approval) / `approve`(Approved) / `reject`(Rejected) / `cancel`(Cancel); `tracking=True` |
| `user_confirmed` | Boolean (computed, **non-stored**) | true if the *current* user already approved their line — hides their Approve/Reject buttons |
| `approval_ids` | O2m `overtime.request.approval` | the sign-off chain; **default = `get_default_approvers`** (seeded from `overtime.approver`) |
| `approver_users` | M2m `res.users` (computed, **stored**) | the set of users in `approval_ids`; drives record rules + button visibility |
| `approver_users_str` | Char (computed, stored) | comma-joined approver emails |
| `barcode` | Char | default `generate_barcode` = current unix timestamp as string |
| `qr_image` | Binary (computed, non-stored) | QR PNG (base64) via `qr_generator` |
| `qr_url` | Char (computed, non-stored) | deep-link URL encoded into the QR |

**Computed logic**
- `compute_approver_users` (`@api.depends('approval_ids','approval_ids.user_id')`) —
  collects `user_id` of every approval line into `approver_users` (stored).
- `compute_approver_users_str` (`@api.depends('approver_users')`) — csv of approver
  emails (stored).
- `compute_user_confirmed` (no `@api.depends` — recomputed each read) — true when the
  current `env.uid` is an approver **and** has an `approved` line. Used to hide the
  Approve/Reject buttons once you've acted.
- `_generate_qr_code` (no `@api.depends`) — builds a `/web#id=...&action=...&model=overtime.request&...&menu_id=...`
  deep link to *this* record (resolving `action_overtime_request` and
  `overtime_request_menu` via `self.env.ref`) and renders it to a QR PNG.

**Key methods / workflow**
| Method | Effect |
|---|---|
| `get_default_approvers()` | returns `(0,0,{sequence,user_id})` tuples built from **all** `overtime.approver` records — used as the default for `approval_ids` and on Reset-to-Draft |
| `generate_barcode()` (`@api.model`) | `str(int(datetime.now().timestamp()))` — the document barcode |
| `name_get()` | display name = `"{project name}-{request_date}"` |
| `button_submit()` | `state → 'submit'` |
| `button_approve()` | marks the **current user's** approval line `approved=True`+timestamp; if any line is still un-approved → `state='waiting'`; once **all** approved → `state='approve'` |
| `button_reject()` | opens the `overtime.reject` wizard (passes `default_overtime_request_id`) |
| `button_cancel()` | `state → 'cancel'` |
| `button_draft()` | `state → 'draft'`, **wipes** `approval_ids` (`(5,0,0)`) and re-seeds them from `get_default_approvers()` |

> **Approval gate detail:** approval is **unanimous** — the request only reaches
> `approve` when *no* approval line is left un-approved. A single Reject sets the whole
> request to `reject` (see wizard, §3.5).

### 3.2 `overtime.request.line` (`models/overtime_request.py`)
One employee row on a request. `_description = 'Overtime Request Line'`.

| Field | Type | Notes |
|---|---|---|
| `request_id` | M2o `overtime.request` | parent |
| `project_id` | M2o `project.project` | `related='request_id.project_id'` |
| `employee_ids` | M2m `hr.employee` | **default = `get_default_employee_ids`** = employees whose `parent_id` is the current user's employee (i.e. *the manager's direct reports*); used only to scope the `employee_id` domain (column hidden in the UI) |
| `employee_id` | M2o `hr.employee` | the worker; `domain="[('id','in',employee_ids)]"`; labelled **Name** |
| `job_title` | Char | `related='employee_id.job_title'` |
| `barcode` | Char | `related='employee_id.barcode'` — the employee's HR barcode («الرقم الوظيفي» on the letter) |
| `num_hours` | Float | overtime hours («عدد الساعات») |
| `compensation_value` | Float | compensation amount («قيمة التعويض» — "filled by HR") |
| `overtime_reason` | Text | reason («سبب العمل الاضافي») |

> **Gotcha:** `employee_ids` defaults to *the current user's direct reports* via
> `parent_id`. If the logged-in user has no `employee_id`, or no subordinates, the
> `employee_id` domain is empty and no employee can be picked on a new line.

### 3.3 `overtime.request.approval` (`models/overtime_request.py`)
One approver's sign-off line. `_inherit = ['mail.thread','mail.activity.mixin']` ·
`_order = 'sequence'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | default `'Ask To Approve Overtime Request'` |
| `overtime_request_id` | M2o `overtime.request` | parent |
| `sequence` | Integer | default 10; defines approver order |
| `user_id` | M2o `res.users` | the approver |
| `approved` | Boolean | set by `button_approve` on the parent |
| `date_approved` | Datetime | timestamp |
| `rejected` | Boolean | set by the reject wizard |
| `date_rejected` | Datetime | timestamp |
| `reject_reason` | Char | captured in the wizard |

Method `send_approve_request()` — sends the `email_template_approve_request_approval`
mail to this approver (force-send, light layout) **and** schedules an
`hr_overtime_compensation.mail_act_hr_overtime` activity on the parent request for that
user. Triggered from the **"Request For Approve"** button in the Approvals tab.

### 3.4 `overtime.approver` (CONFIG — `models/overtime_approver.py`)
`_description = 'Overtime Approver'` · `_order = 'sequence'`. The **master list** of
default approvers applied to every new request.

| Field | Type | Notes |
|---|---|---|
| `sequence` | Integer | default 10; handle-sortable in the UI |
| `user_id` | M2o `res.users` | an approver |

Maintained under **Overtime Compensation → Configuration → Overtime Compensation
Approvers** (manager-only). `overtime.request.get_default_approvers()` reads every row
here to seed `approval_ids`.

### 3.5 `overtime.reject` (wizard — `wizards/overtime_reject.py`)
TransientModel `overtime.reject`. Fields: `overtime_request_id` (M2o, required),
`reason` (Char, required). `button_reject()` finds the **current user's** approval line
on the request, stamps `rejected=True` + `date_rejected` + `reject_reason`, and sets the
request `state='reject'`. Opened from `overtime.request.button_reject()`.

### 3.6 `qr_generator.py` (helper — `models/qr_generator.py`)
Module-level helper class `generateQrCode` with a static-style
`generate_qr_code(url)` — builds a QR PNG via the `qrcode` lib (version 4,
`ERROR_CORRECT_L`, box_size 20, border 4) and returns base64. Imported by
`overtime_request.py` and used in `_generate_qr_code`.

---

## 4. Views (`views/*.xml`)

### 4.1 `overtime_request_views.xml`
- **Tree** (`overtime_request_view_tree`): `project_id`, `project_manager_id`,
  `request_date`, `state` (badge — muted/info/warning/success/danger per state).
- **Form** (`overtime_request_view_form`):
  - Header buttons gated by `state` and approver identity:
    - **Submit** (visible only in `draft`), **Cancel** (hidden in `cancel`),
      **Reset to Draft** (hidden in `draft`).
    - **Approve** / **Reject** — visible only when
      `approver_users not in [uid] is False` (i.e. you *are* an approver), you have not
      yet confirmed (`not user_confirmed`), and `state in ('submit','waiting')`.
    - `state` statusbar (`draft,submit,approve` visible).
  - Body group: `project_id`, `project_manager_id`, `request_date`, `barcode`
    (all read-only unless `state == 'draft'`).
  - **Employees** tab — editable `request_line_ids` tree (barcode, employee, job_title,
    hours, compensation, reason; `employee_ids`/`project_id` columns hidden). Read-only
    unless draft.
  - **Approvals** tab — `approval_ids` tree (`create=0 edit=0 delete=0`, all fields
    read-only) with the **"Request For Approve"** button (hidden once `approved`).
  - Chatter (followers / activities / messages).
- **Kanban** (`hr_kanban_view_hr_overtime`): card showing project, project manager,
  request date.
- **Action** `action_overtime_request` — "Overtime Requests", `view_mode=tree,kanban,form`.

### 4.2 `overtime_approval_views.xml`
- **Tree** (`overtime_approval_view_tree`) on `overtime.approver` — editable, `sequence`
  handle + `user_id`.
- **Action** `overtime_approver_action` — "Overtime Approvers", `view_mode=tree`.

### 4.3 `overtime_menuitem.xml`
Top-level app **"Overtime Compensation"** (`menu_overtime_compensation`, uses the module
icon):
- **Requests** (`overtime_request_menu` → `action_overtime_request`).
- **Configuration** (manager-group only) → **Overtime Compensation Approvers**
  (`overtime_approval_menu` → `overtime_approver_action`, manager-group only).

> Note: `overtime_request_menu` is referenced by name in `_generate_qr_code` to build
> the QR deep-link `menu_id` — don't rename/remove it without updating that method.

### 4.4 Wizard view — `wizards/overtime_reject.xml`
`overtime_reject_view_form` — simple dialog: `overtime_request_id` (shown) + `reason`,
with **Reject** (danger) and **Cancel** (`special="cancel"`) buttons.

---

## 5. Reports (`report/overtime_request_printout.xml`)

One QWeb-PDF report — **"Print Overtime Request"** (`action_report_overtime_request`,
`report_name = hr_overtime_compensation.report_overtime_request`), bound to
`overtime.request` (`binding_model_id` → appears in the Print menu).

- Custom layout template `overtime_internal_layout` wraps the body with header/footer
  images: `/hr_overtime_compensation/static/img/header.png` and `.../footer.png`.
- Body (`report_overtime_request`): a **Code128 barcode** (top-left, from `o.barcode`)
  and a **QR image** (top-right, rendered via `/report/barcode/?barcode_type=QR&value=o.qr_url+str(o.id)`).
- The document is rendered **`with_context(lang='ar_001')`** and `dir="rtl"` — an Arabic
  letter titled **«طلب صرف تعويض عن عمل اضافي»** addressed to «اﻹدارة التنفيذية»,
  from the project management, with the project + manager names.
- Main table («الرقم الوظيفي / اسم العامل / الوظيفة / عدد الساعات / قيمة التعويض / سبب
  العمل الاضافي») iterates `request_line_ids` and computes **total hours** and **total
  compensation** footer rows.
- Approval table («يعتمد») iterates `approval_ids`: job title
  (`user_id.employee_id.job_id.name`), accept/reject check marks, signature column,
  reject reason.

> **Gotcha:** the QR in the PDF uses `o.qr_url + str(o.id)` (id appended), whereas the
> screen/email QR uses `qr_url` alone — the two QR payloads differ slightly.

> **Static images:** `static/img/header.png`, `footer.png` are used by the report;
> `care_header_logo_1.png`, `care_header_logo_2.png` exist in `static/img/` but are not
> referenced by any loaded template. `static/description/icon.png` is the app icon.

---

## 6. Automation & data

### 6.1 Mail template (`data/mail_template.xml`)
`email_template_approve_request_approval` — model `overtime.request.approval`. Subject
"Ask To Approve Overtime Request {{project name}}"; sent **to**
`object.user_id.employee_id.work_email`, **from** the current user. Body greets the
approver, asks them to approve, and includes a purple **"Overtime Approval"** button
linking to `overtime_request_id.qr_url`. Sent by `send_approve_request()`.

### 6.2 Activity type (`data/activity_type.xml`)
`mail_act_hr_overtime` — a `mail.activity.type` named "Overtime" (icon `fa-sun-o`) on
`overtime.request`. Scheduled by `send_approve_request()` for each approver.

> ⚠️ **Gotcha:** `data/activity_type.xml` is **NOT listed in `__manifest__.py`'s `data`
> list** — so the `mail_act_hr_overtime` record is **not loaded by `-u`**. Because
> `send_approve_request()` calls `activity_schedule('hr_overtime_compensation.mail_act_hr_overtime', …)`,
> the **"Request For Approve"** button will raise a missing-external-id error unless this
> XML is added to the manifest (or the record already exists in the DB from a prior
> load). **Add `'data/activity_type.xml'` to the manifest `data` list before
> `data/mail_template.xml`** to fix.

### 6.3 Crons / scheduled actions
**N/A** — no `ir.cron` records in this module.

---

## 7. Settings / config parameters
**N/A** — no `res.config.settings` inheritance and no `ir.config_parameter` keys of its
own. The only config surface is the **Overtime Approvers** master list
(`overtime.approver`, §3.4). `_generate_qr_code` reads the standard `web.base.url`
parameter to build the QR deep-link.

---

## 8. Security (`security/`)

### 8.1 Groups & rules (`security/security.xml`)
- Module category **"Overtime"** (`module_hr_overtime`).
- Group **Manager** (`group_hr_overtime_manager`) — controls the Configuration menu /
  approver master list.
- Record rules on `overtime.request`:
  - `hr_overtime_rule_user_own` (`base.group_user`): a user sees a request if they
    **created it** (`create_uid = user.id`) **or** they are one of its approvers
    (`approver_users in user.ids`).
  - `hr_overtime_rule_manager_all` (`group_hr_overtime_manager`): managers see **all**
    requests (`[(1,'=',1)]`).

### 8.2 Access rights (`security/ir.model.access.csv`)
All five models grant full **CRUD to `base.group_user`** (every internal user):
`overtime.request`, `overtime.request.line`, `overtime.request.approval`,
`overtime.approver`, `overtime.reject`.

> **Gotcha:** access is wide open (every internal user has CRUD on every model,
> including the `overtime.approver` config table). Visibility is narrowed only by the
> **record rules** above for `overtime.request`; the other models have no record rules.
> The manager group gates the Configuration **menu** but not table-level CRUD on
> `overtime.approver`.

---

## 9. Assets / JS
**N/A** — no `web.assets_*` bundles, no OWL components, no SCSS/JS. UI is standard
backend views + a QWeb-PDF report only.

---

## 10. Gotchas & notes (read before debugging)
- **`qrcode` dependency is hard** — `_generate_qr_code` runs on every form read of a
  request; a missing lib breaks the form. Install in the Odoo venv.
- **`activity_type.xml` not in manifest** (§6.2) — the "Request For Approve" button can
  raise a missing-XML-id error. Add the file to the manifest `data` list.
- **Approval is unanimous** — `button_approve` only flips the request to `approve` once
  *every* approval line is approved; any single Reject sets the whole request to
  `reject`. There is no "majority" or per-stage gating beyond `sequence` ordering.
- **Approve/Reject button visibility** depends on `approver_users` (stored m2m) and
  `user_confirmed` (non-stored). If `compute_approver_users` hasn't re-run after editing
  `approval_ids`, button visibility can look stale until the form reloads.
- **`employee_ids` default = current user's direct reports** (`parent_id`). A user with
  no `employee_id` or no subordinates can't pick an employee on a new line.
- **Reset to Draft wipes approvals** and re-seeds them from the *current*
  `overtime.approver` master list — changing the master list after a request was created
  only affects it after a Reset-to-Draft (or a fresh request).
- **QR payload differs** between the PDF (`qr_url + str(id)`) and the screen/email
  (`qr_url`). Keep that in mind if you scan-test.
- **QR/menu coupling** — `_generate_qr_code` resolves `action_overtime_request` and
  `overtime_request_menu` by external id; renaming either breaks QR generation.
- **`name_get` (not `_compute_display_name`)** — the v16-style `name_get` override is
  still used here; works on 17 but is the deprecated path.
- **Wide access rights** — every internal user has CRUD on all five models (§8.2); rely
  on record rules for `overtime.request` visibility only.

---

## 11. File map
```
__manifest__.py                         depends (hr/project/mail) + data list
README.rst
__init__.py                             → models, wizards
models/
  __init__.py                           → overtime_request, overtime_approver
  overtime_request.py                   overtime.request (+ .line, + .approval) [central]
  overtime_approver.py                  overtime.approver (config master list)
  qr_generator.py                       generateQrCode helper (qrcode lib)
wizards/
  __init__.py                           → overtime_reject
  overtime_reject.py                    overtime.reject (TransientModel)
  overtime_reject.xml                   reject dialog form
views/
  overtime_request_views.xml            tree / form / kanban / action
  overtime_approval_views.xml           overtime.approver tree + action
  overtime_menuitem.xml                 app menu + Configuration submenu
report/
  overtime_request_printout.xml         Arabic RTL PDF (barcode + QR) + layout
security/
  security.xml                          category, Manager group, 2 record rules
  ir.model.access.csv                   CRUD for base.group_user on all 5 models
data/
  mail_template.xml                     approver request email (LOADED)
  activity_type.xml                     "Overtime" activity type (NOT in manifest!)
static/
  description/icon.png                  app icon
  img/header.png · footer.png           report header/footer (used)
  img/care_header_logo_1.png · _2.png   present but unreferenced
```
