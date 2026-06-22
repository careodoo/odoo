# hr_reward_warning — Developer Handover Documentation

> **Open HRMS Official Announcements** — a Cybrosys/Open HRMS community module for Odoo 17.
> Despite the directory name `hr_reward_warning`, this module declares itself as
> **"Open HRMS Official Announcements"** (technical model `hr.announcement`). It lets HR
> publish official announcements / circulars to employees, departments or job positions,
> with a draft → approval workflow, automatic expiry, and a stat button on the employee
> form so each employee sees the announcements addressed to them. UI is **English**; no
> Arabic labels are present in this module's code. Read this before touching the code.

> ⚠️ **Name vs. content mismatch (read first):** the folder is `hr_reward_warning` but the
> code, model, menus and sequences are all about **announcements**, not rewards/warnings.
> There is **no reward and no warning model** in this codebase. The "reward/warning" name is
> a leftover; everything ships under `hr.announcement`. Do not look for reward/warning logic
> here — it does not exist.

---

## 1. At a glance

| | |
|---|---|
| Technical name (directory / addon) | `hr_reward_warning` |
| Manifest display name | **Open HRMS Official Announcements** |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| License | LGPL-3 |
| Author / Maintainer | Cybrosys Techno Solutions, Open HRMS |
| Depends | `hr`, `mail` |
| External Python libs | **None** (stdlib only) |
| Application / auto_install | `application=False`, `auto_install=False` |
| Main model | `hr.announcement` |
| Inherited model | `hr.employee` (adds announcement stat button) |
| Reports | **N/A** — no QWeb/PDF reports |
| Wizards | **N/A** — no transient wizard models |
| Assets / JS / OWL | **N/A** — no `web.assets_*` bundles; only static description images |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u hr_reward_warning --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- No external Python dependency to install — `import` only uses `odoo` core.
- No dev mode required; this module ships no JS/SCSS asset bundles, so a plain `-u`
  followed by a service restart is sufficient. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.announcement  (central model — mail.thread, mail.activity.mixin)
├── audience targeting (one of):
│     ├── is_announcement = True            → general announcement (everyone)
│     └── announcement_type:
│           ├── 'employee'      → employee_ids   (M2m hr.employee)
│           ├── 'department'    → department_ids (M2m hr.department)
│           └── 'job_position'  → position_ids   (M2m hr.job)
├── workflow: draft → to_approve → approved / rejected
├── expiry: approved → expired   (driven by daily ir.cron)
├── name (Code No) auto-filled from ir.sequence on create
│     ├── general  → code 'hr.announcement.general'  (prefix GA)
│     └── targeted → code 'hr.announcement'          (prefix AN)
└── attachment_id (M2m ir.attachment), announcement (Html letter), date_start/date_end

hr.employee (inherited)
└── announcement_count (computed, non-stored) + fa-bullhorn stat button
      → action_open_announcements() opens the announcements addressed to that employee

ir.cron  "HR Announcement Expiry Date"  (daily) → model.get_expiry_state()
ir.rule  multi-company global rule on hr.announcement
Menus    "Announcements" root (web_icon) → "Announcements" list/form
```

**Design notes**
- A single model (`hr.announcement`) covers both *general* announcements (to everyone) and
  *targeted* ones (by employee / department / job position). The split is governed by
  `is_announcement` and `announcement_type`; the form shows/hides the relevant M2m via
  `invisible` expressions.
- The employee-side `announcement_count` is a **non-stored compute** that runs four
  `search_count` queries each time it is read (general + per-employee + per-department +
  per-job). Same logic is duplicated in `action_open_announcements()` as `search` calls.

---

## 3. Data model

### 3.1 `hr.announcement` (`models/hr_announcement.py`)
`_name = 'hr.announcement'` · `_inherit = ['mail.thread', 'mail.activity.mixin']`

| Field | Type | Notes |
|---|---|---|
| `name` | Char | "Code No:" — set from `ir.sequence` on create (not user-entered); shown readonly |
| `announcement_reason` | Text (required) | labelled **"Title"** in the UI — the announcement subject |
| `state` | Selection | `draft` / `to_approve` ("Waiting For Approval") / `approved` / `rejected` ("Refused") / `expired`; default `draft`; `track_visibility='always'` |
| `requested_date` | Date | defaults to today (via `fields.Datetime.now().strftime(...)`); readonly create date |
| `attachment_id` | M2m `ir.attachment` | relation table `doc_warning_rel` — attach supporting docs |
| `company_id` | M2o `res.company` | default = login user's company; readonly |
| `is_announcement` | Boolean | "Is general Announcement?" — when True, audience = everyone |
| `announcement_type` | Selection | `employee` / `department` / `job_position` — only relevant when **not** a general announcement |
| `employee_ids` | M2m `hr.employee` | relation `hr_employee_announcements`; audience when type = employee |
| `department_ids` | M2m `hr.department` | relation `hr_department_announcements`; audience when type = department |
| `position_ids` | M2m `hr.job` | relation `hr_job_position_announcements`; audience when type = job_position |
| `announcement` | Html | "Letter" — the announcement body |
| `date_start` | Date (required) | default today; gates visibility on the employee side (`date_start <= today`) |
| `date_end` | Date (required) | default today; once passed, the cron flips state to `expired` |

**Constraints**
- `_check_date_start` (`@api.constrains('date_start','date_end')`): raises `ValidationError`
  if `date_start > date_end` ("The Start Date must be earlier than the End Date").

**Overrides / methods**
- `create(vals)` (`@api.model`): assigns `name` from a sequence —
  `hr.announcement.general` (prefix **GA**) if `is_announcement`, else `hr.announcement`
  (prefix **AN**). Then calls super.
  > Note: this is the old-style single-`vals` `create` signature, not the v17
  > `@api.model_create_multi` batch form. It works for single creates but would only take
  > the first dict in a multi-create batch — keep in mind if you ever batch-create records.
- `action_sent_announcement()` → sets `state = 'to_approve'` (button "Send For Approval").
- `action_approve_announcement()` → sets `state = 'approved'` (button "Approve").
- `action_reject_announcement()` → sets `state = 'rejected'` (button "Refuse").
- `get_expiry_state()`: cron entrypoint — searches all announcements where
  `state != 'rejected'` and writes `state = 'expired'` for any whose `date_end < today`.

### 3.2 `hr.employee` (inherited — `models/hr_employee.py`)
`_inherit = 'hr.employee'`

| Field | Type | Notes |
|---|---|---|
| `announcement_count` | Integer (compute, **non-stored**) | "# Announcements" visible to this employee |

**Methods**
- `_compute_announcement_count()`: sums four `sudo().search_count` queries —
  (1) general approved announcements, (2) those targeting `self.id` via `employee_ids`,
  (3) those targeting `self.department_id` via `department_ids`, (4) those targeting
  `self.job_id` via `position_ids`. All four filter `state in ('approved','done')` and
  `date_start <= today`.
- `action_open_announcements()`: rebuilds the same four sets with `search` and opens an
  `ir.actions.act_window` on `hr.announcement` — list+form if more than one, single form
  (`hr_reward_warning.hr_announcement_view_form`) if exactly one. Returns `None` if there
  are no announcements (the stat button is hidden in that case via `invisible="announcement_count == 0"`).

> ⚠️ **`'done'` state gotcha:** both employee-side methods filter on
> `state in ('approved','done')`, but the `state` Selection on `hr.announcement` has **no
> `'done'` value** (it is `draft/to_approve/approved/rejected/expired`). So `'done'` never
> matches anything — effectively only `approved` announcements are counted/shown. Harmless
> today, but don't rely on a `'done'` state existing.

---

## 4. Views (`views/`)

### 4.1 `hr_announcement_views.xml`
- **Form** (`hr_announcement_view_form`): header with workflow buttons —
  - "Send For Approval" (`action_sent_announcement`, group `hr.group_hr_user`, visible only in `draft`),
  - "Approve" / "Refuse" (`action_approve_announcement` / `action_reject_announcement`, group `hr.group_hr_manager`, visible only in `to_approve`),
  - `state` statusbar (`statusbar_visible="draft,to_approve,approved"`).
  Body: `name` (readonly), `is_announcement` toggle (readonly once `name` is set),
  `announcement_reason` and `announcement` (Html) readonly outside `draft`, the three
  audience M2m fields shown conditionally on `announcement_type`, `attachment_id`
  (`many2many_binary`), `company_id` (multi-company group only), plus a chatter.
- **Tree** (`hr_announcement_view_tree`): `name`, `announcement_reason`, `state`.
- **Search** (`hr_announcement_view_search`): search on name / is_announcement /
  announcement_reason / state; filters **"Approved Letters"** (`state = approved`) and
  **"General Announcements"** (`is_announcement = True`); group-by **Status** (`state`).
- **Action** (`hr_announcement_action`): window action on `hr.announcement`, `view_mode = tree,form`.

### 4.2 `hr_employee_views.xml`
- Inherits `hr.view_employee_form` and injects a `fa-bullhorn` `oe_stat_button` into the
  button box, bound to `action_open_announcements`, hidden when `announcement_count == 0`.

### 4.3 `hr_reward_warning_menus.xml`
- Root menu `hr_announcement_menu_root` **"Announcements"** with
  `web_icon="hr_reward_warning,static/description/icon.png"`, `sequence="-6"` (so it sorts
  high in the top menu), restricted to `hr.group_hr_user,hr.group_hr_manager`.
- Child `hr_announcement_menu_view_announcements` **"Announcements"** → `hr_announcement_action`.

### Wizards / Reports
**N/A** — this module ships no wizard (TransientModel) and no report (QWeb/PDF/AbstractModel).

---

## 5. Automation — cron (`data/ir_cron_data.xml`)

| Cron record | Schedule | Action |
|---|---|---|
| `ir_cron_hr_announcement_expiry_date` ("HR Announcement Expiry Date") | every **1 day**, `numbercall=-1`, `doall=False` | `model.get_expiry_state()` on `hr.announcement` |

`get_expiry_state()` flips every non-rejected announcement whose `date_end < today` to
`state = 'expired'`. There are **no other crons** and **no mail templates** in this module.

---

## 6. Sequences (`data/ir_sequence_data.xml`)

| Record | Code | Prefix | Padding |
|---|---|---|---|
| `seq_general_announcement` ("General Announcement") | `hr.announcement.general` | `GA` | 4 |
| `seq_announcement` ("Announcement") | `hr.announcement` | `AN` | 4 |

The `create()` override picks the sequence by `is_announcement`. Codes look like `GA0001`
(general) or `AN0001` (targeted).

---

## 7. Settings
**N/A** — no `res.config.settings` inheritance and no `config_parameter` records. Behaviour
is not configurable from the UI; all logic is hard-coded (audience rules, expiry, states).

---

## 8. Security (`security/`)

### `ir.model.access.csv`
| Access id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|
| `access_hr_announcement_admin` | `hr.announcement` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `access_hr_announcement_user` | `hr.announcement` | `hr.group_hr_user` | ✓ | ✓ | ✓ | ✓ |
| `access_hr_announcement_employee` | `hr.announcement` | `base.group_user` | ✓ | — | — | — |

So **any internal user** can read announcements (read-only), HR Officers and HR Managers
get full CRUD. The approval/refuse buttons are additionally gated to `hr.group_hr_manager`
at the **view** level (not by record rules), and "Send For Approval" to `hr.group_hr_user`.

### `hr_announcement_security.xml`
- `hr_announcement_rule_company` — a **global** `ir.rule` enforcing multi-company scoping:
  `['|',('company_id','=',False),('company_id','child_of',[user.company_id.id])]`.

> Note: there is no record rule restricting employees to only the announcements addressed to
> them at the ORM level. The "addressed to me" filtering is done in
> `action_open_announcements()` (Python domains), not by security rules — a user with read
> access can still query other announcements via the model. The employee stat button is a UX
> convenience, not an access boundary.

---

## 9. Assets / JS
**N/A** — no `web.assets_backend` / `web.assets_frontend` bundles, no OWL components, no
JavaScript or SCSS. The `static/description/` tree is purely the Cybrosys store listing
(`index.html`, `icon.png`, `banner.jpg`, screenshots, marketing icons) — **not loaded by
Odoo at runtime** other than `icon.png` referenced as the menu `web_icon`.

---

## 10. Gotchas & notes (read before debugging)

- **Directory name lies.** `hr_reward_warning` contains the *Announcements* module. There is
  no reward and no warning model. If a ticket mentions "reward/warning", confirm whether they
  mean this module (announcements) or something else entirely.
- **`'done'` state never matches.** Employee-side counting/opening filters on
  `state in ('approved','done')`, but `'done'` is not a defined state — only `approved`
  records ever surface. See §3.2.
- **`announcement_count` is non-stored.** It runs four `search_count` queries per employee
  per read. It cannot be searched/grouped/sorted on, and on large employee lists it adds
  query load. Don't add it to a tree view's default columns expecting it to be cheap.
- **Old-style `create`.** Uses the single-`vals` `@api.model create` signature, not
  `@api.model_create_multi`. Multi-record creates would mis-assign the sequence — keep
  single-record creation, or migrate the override if you batch-create.
- **`requested_date` default is computed at import time** via
  `fields.Datetime.now().strftime('%Y-%m-%d')` evaluated once when the class is defined,
  rather than a `default=fields.Date.today` callable. In a long-running worker this is the
  process start date, not necessarily "today". `date_start`/`date_end` correctly use
  `fields.Date.today()` (also evaluated at import — same caveat). Set these explicitly on
  records if exact create-day accuracy matters.
- **`track_visibility='always'`** on `state` is the legacy attribute name; v17 prefers
  `tracking=True`. It still works but flag it if migrating further.
- **Approval is view-gated, not rule-gated.** The Approve/Refuse buttons are hidden from
  non-managers, but CRUD access (write) is granted to `hr.group_hr_user` too — an HR Officer
  could change `state` directly via the ORM/import. Tighten with a record rule if real
  segregation of duties is required.
- **No reports, no wizards, no settings, no assets** — keep expectations aligned; this is a
  small CRUD + workflow + cron module.

---

## 11. File map
```
__manifest__.py                      depends (hr, mail) / data list
README.rst                           Cybrosys store readme
doc/RELEASE_NOTES.md                 v17.0.1.0.0 initial commit note
models/
  __init__.py                        imports hr_employee, hr_announcement
  hr_announcement.py                 hr.announcement (model, workflow, cron entry, create)
  hr_employee.py                     hr.employee (announcement_count + stat-button action)
data/
  ir_cron_data.xml                   daily expiry cron → get_expiry_state()
  ir_sequence_data.xml               GA / AN sequences
security/
  hr_announcement_security.xml       multi-company ir.rule
  ir.model.access.csv                manager/user CRUD + base.group_user read
views/
  hr_announcement_views.xml          form / tree / search / action
  hr_employee_views.xml              employee-form stat button (inherits hr.view_employee_form)
  hr_reward_warning_menus.xml        root + child "Announcements" menus
i18n/
  ar_001.po                          Arabic translations (UI strings; no Arabic in code)
static/description/                  store listing assets (icon.png used as menu web_icon)
```

> **i18n note:** an `i18n/ar_001.po` Arabic translation file ships with the module, so the
> Announcements UI can render in Arabic when that language is active — but all field labels,
> selection labels and strings in the **code/views are English**. No Arabic literals exist in
> the Python or XML source.
