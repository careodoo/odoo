# oh_hr_lawsuit_management — Developer Handover Documentation

> **Open HRMS Legal Actions** — a Cybrosys / OpenHRMS community module for Odoo 17 that
> tracks **legal cases / lawsuits (الإجراءات القانونية)** raised by the company against an
> employee, a partner, or another party. Each case carries a draft→running→won/loss/cancel
> workflow, dated case "updates", an auto-reminder for the next hearing/appointment, and a
> drill-down button on the employee form. UI labels are **English**; an Arabic translation
> catalogue (`i18n/ar_001.po`) ships with it. This is a third-party module installed
> as-is — read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `oh_hr_lawsuit_management` |
| Display name | Open HRMS Legal Actions |
| Version | `17.0` (manifest) |
| Odoo | 17.0 |
| Depends | `base`, `hr` |
| External Python libs | **None** (stdlib `datetime` only) |
| Author / origin | Cybrosys Techno Solutions / OpenHRMS (AGPL-3) |
| New models | `hr.lawsuit`, `hr.lawsuit.update` |
| Inherited model | `hr.employee` (adds `legal_count` + drill-down button) |
| Reports | **N/A** — no QWeb/PDF reports in this module |
| Assets / JS | **N/A** — no backend asset bundles; `static/` is store-listing artwork only |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u oh_hr_lawsuit_management --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`). Log file:
  `/var/log/odoo/odoo-17.log`.
- No external packages required — this module installs cleanly against a stock venv.
- **Demo data** (`data/demo_data.xml`) is only loaded when the database is created with the
  demo flag; it is **not** in the `data` list, so a normal `-u` does not (re)create the
  sample company/employee/lawsuit records.

---

## 2. Architecture overview

```
hr.lawsuit  (central model — mail.thread, mail.activity.mixin)
├── name (Code, auto from ir.sequence 'hr.lawsuit', prefix "LC", padding 4)
├── party1  → res.company   (always the company; required, readonly)
├── party2  = Selection(employee | partner | other)
│      ├── employee → hr.employee   (employee_id)
│      ├── partner  → res.partner   (partner_id)
│      └── other    → other_name (Char)
│   └── party2_name (computed mirror of the chosen party's name, stored)
├── lawyer  → res.partner
├── one2many → hr.lawsuit.update   (dated case updates / log)
├── next_appointment (computed from latest update.datetime, stored)
└── state: draft → running → {delay, cancel, fail(Loss), won}

hr.employee (inherited)
└── legal_count (computed)  +  "Legal Actions" stat button → legal_view()

Automation:
  ir.cron  "Legal Case: Next Appointment"  (daily)
     → hr.lawsuit.cron_notify_next_appointment()
     → schedules mail.activity 'mail_act_legal_case_reminder' on cases
       whose next_appointment is today, assigned to the case creator.
```

**Design notes**
- This is a small, classic OpenHRMS CRUD-plus-workflow module: one main record, one child
  log model, a state machine driven by header buttons, and a single daily cron.
- The "next appointment" is **not a separate field you set** — it is computed as the most
  recent `datetime` among the case's `update_ids` (see Gotchas: the naming is misleading).
- Everything is gated behind a single **Manager** group (`lawsuit_group_manager`); there is
  no separate end-user UI menu (see §8).

---

## 3. Data model

### 3.1 `hr.lawsuit` (central — `models/legal_action.py`)
`_inherit = ['mail.thread', 'mail.activity.mixin']`

| Field | Type | Notes |
|---|---|---|
| `name` | Char (`Code`) | auto-filled on create from sequence `hr.lawsuit` → `LCxxxx`; `copy=False`, readonly in form |
| `ref_no` | Char | free-text Reference Number |
| `company_id` | Many2one `res.company` | default = current user's company, readonly |
| `requested_date` | Date | the "Date" / start date; `copy=False`, readonly except in `draft` |
| `hearing_date` | Date | upcoming hearing date (purely informational; cron uses `next_appointment`, not this) |
| `court_name` | Char | tracked; readonly when `state=won` |
| `judge` | Char | tracked; readonly when `state=won` |
| `lawyer` | Many2one `res.partner` | tracked; readonly when `state=won` |
| `party1` | Many2one `res.company` | first party; **required, readonly** (always the company) |
| `party2` | Selection | `employee` / `partner` / `other`; default `employee`; required, readonly in form metadata |
| `employee_id` | Many2one `hr.employee` | shown/required only when `party2=employee` |
| `partner_id` | Many2one `res.partner` | shown/required only when `party2=partner` |
| `other_name` | Char | shown/required only when `party2=other` |
| `party2_name` | Char (computed `set_party2`, **stored**) | mirror of the second party's name |
| `case_details` | Html | tracked free-form case description |
| `state` | Selection | `draft / running / delay / cancel / fail (Loss) / won`; default `draft`; tracked |
| `update_ids` | One2many `hr.lawsuit.update` | dated case-update log |
| `next_appointment` | Datetime (computed `compute_next_appointment`, **stored**) | latest `update_ids.datetime` |
| `active` | Boolean | default `True` (archiving) |

**Computed logic**
- `set_party2()` — `@api.depends('party2','employee_id')`. **Only sets `party2_name` when
  `party2 == 'employee'`** (copies `employee_id.name`). For `partner`/`other` it leaves
  `party2_name` unset — see Gotchas.
- `compute_next_appointment()` — `@api.depends('update_ids.datetime')`. Sets
  `next_appointment` to the **most recent** (`reverse=True` sort) update's datetime, else
  `False`.

**Workflow methods** (one per header button, each just flips `state`):
`process()`→running, `delay()`→delay, `won()`→won, `loss()`→fail, `cancel()`→cancel.

**Overrides / model methods**
- `create(vals)` — `@api.model`; assigns `vals['name']` from the `hr.lawsuit` sequence
  before super. (Single-record signature; see Gotchas re: batch create.)
- `cron_notify_next_appointment()` — `@api.model`; see §7.

### 3.2 `hr.lawsuit.update` (child log — `models/legal_action.py`)
`_order = 'datetime desc, id desc'`

| Field | Type | Notes |
|---|---|---|
| `lawsuit_id` | Many2one `hr.lawsuit` | parent case (no explicit ondelete/cascade declared) |
| `name` | Char | **required** — the update title |
| `partner_id` | Many2one `res.partner` | optional related contact |
| `details` | Text | free-form notes |
| `datetime` | Datetime | **required** — drives the parent's `next_appointment` |

Edited inline (`editable="bottom"`) in the case form's **Updates** tab.

### 3.3 `hr.employee` (inherited — `models/legal_action.py`, class `HrLegalEmployeeMaster`)
- `legal_count` — Integer, computed by `_legal_count()` (searches `hr.lawsuit` where
  `employee_id == self`, counts). **Not stored** and **no `@api.depends`** — recomputed on
  each form load.
- `legal_view()` — returns an `ir.actions.act_window` opening the `hr.lawsuit` list/form
  filtered to this employee's cases. Bound to the "Legal Actions" stat button injected into
  the employee form's button box.

---

## 4. Views (`views/legal_action_view.xml`)

| View / record | Type | Notes |
|---|---|---|
| `lawsuit_seq` | `ir.sequence` | code `hr.lawsuit`, prefix `LC`, padding 4 |
| `hr_lawsuit_form_view` | form | header state buttons (Process/Delay/Won/Loss/Cancel) + statusbar; party1/party2 group; party-type-conditional `employee_id`/`partner_id`/`other_name`; court/judge/lawyer; dates; **Case Details** + **Updates** notebook tabs; chatter (followers/activities/messages) |
| `hr_lawsuit_tree_view` | tree | code, parties, court, judge, lawyer, date, `state` badge (won=success, delay=warning, fail=danger, cancel=muted, draft/running=info) |
| `hr_lawsuit_search_view` | search | filters on name/parties/court/judge/lawyer/date/state; **Group By** Status and Employee |
| `action_hr_lawsuit` | act_window | "Legal Management"; `res_model=hr.lawsuit`; bound to the search view |
| `legal_hr_employee_inherit_form_view` | inherited form | injects the "Legal Actions" stat button (`fa-exclamation-circle`, `legal_count` statinfo, calls `legal_view`) into `hr.view_employee_form` |
| `hr_lawsuit_sub_menu` | menuitem | parent `hr.menu_hr_root`, action `action_hr_lawsuit`, sequence 10, **restricted to `lawsuit_group_manager`** ("Legal Actions" under the HR app) |

**Button visibility (v17 `invisible` expressions, no `attrs`/`states`):**
- Process: only in `draft`. Delay/Cancel: in `draft` or `running`. Won/Loss: only in
  `running`. The form's `readonly` rules still use the legacy **`states={...}`** dict on
  several field definitions in Python (`court_name`, `judge`, `lawyer`, `employee_id`,
  `requested_date`, `party1`/`party2` via `readonly` attrs) — see Gotchas.

**Wizards:** N/A — no wizard/TransientModel in this module.

---

## 5. Reports
**N/A** — this module defines no QWeb templates, no `ir.actions.report`, and no
`reports/` directory. The `static/description/` PNG/GIF assets are Apps-store listing
artwork only and are not rendered anywhere in the backend.

---

## 6. Assets / JS
**N/A** — there is no `assets` key in the manifest, no OWL component, no SCSS/JS bundle.
`static/` contains only `description/` (store images + `index.html` listing page) and
`static/image/images.jpeg` (referenced by the demo employee photo).

---

## 7. Automation — cron & activities

### 7.1 Cron (`data/cron.xml`)
| Cron | Schedule | Method |
|---|---|---|
| **Legal Case: Next Appointment** (`ir_cron_hrlawsuit`) | every **1 day**, `numbercall=-1`, `doall=False` | `model.cron_notify_next_appointment()` |

`cron_notify_next_appointment()` searches all lawsuits with a `next_appointment`, filters to
those whose `next_appointment.date() == today`, and for each calls
`activity_schedule('oh_hr_lawsuit_management.mail_act_legal_case_reminder', …)` with summary
**"Legal Case Reminder"**, a per-case note, and `user_id = lawsuit.create_uid` — i.e. the
reminder activity lands on the **case creator's** to-do list.

### 7.2 Mail activity type (`data/mail_activity_data.xml`)
`mail_act_legal_case_reminder` — `mail.activity.type` named **"Legal Case Remainder"** (note
the typo in the stored label), icon `fa-sun-o`, `res_model=hr.lawsuit`. This is the activity
type the cron schedules.

---

## 8. Security (`security/security.xml` + `ir.model.access.csv`)

**Module category:** `module_lawsuit_category` ("Lawsuit", sequence 18).

**Group:** `lawsuit_group_manager` — display name **"Manager"** under the Lawsuit category.
- `implied_ids` → `base.group_user` (so any HR Lawsuit Manager is also an internal user).
- `users` seeded with **root** and **admin** at install.

**Access rights (`ir.model.access.csv`):**
| Model | Group | R | W | C | U |
|---|---|---|---|---|---|
| `hr.lawsuit` | `lawsuit_group_manager` | ✔ | ✔ | ✔ | ✔ |
| `hr.lawsuit` | *(no group — all users)* | ✔ | ✘ | ✘ | ✘ |
| `hr.lawsuit.update` | `lawsuit_group_manager` | ✔ | ✔ | ✔ | ✔ |
| `hr.lawsuit.update` | *(no group — all users)* | ✔ | ✘ | ✘ | ✘ |

> Every internal user has **read** access to all lawsuits/updates; only Managers can
> create/edit/delete. Note the two "users" ACL rows reuse the manager's `name`
> (`hr.access_hr_lawsuit_manager` / `…_update_manager`) — harmless duplicate display names,
> distinct `id`s.

**Record rule:** `lawsuit_comp_rule` — global multi-company rule on `hr.lawsuit`:
`['|', ('company_id','=',False), ('company_id','child_of',[user.company_id.id])]`.

**Menu visibility:** the only menu (`hr_lawsuit_sub_menu`) is restricted to
`lawsuit_group_manager`, so non-managers can read records (via ACL) but have no menu entry
to reach them except the employee-form stat button.

---

## 9. Settings / config parameters
**N/A** — no `res.config.settings` extension and no `ir.config_parameter` usage. All
behaviour is fixed in code/XML.

---

## 10. Gotchas & notes (read before debugging)

- **`create()` is single-record / legacy signature.** It is decorated `@api.model` and does
  `vals['name'] = …` on a single dict, then `super().create(vals)`. It is **not**
  `@api.model_create_multi`, so a batched/list create (e.g. import, `create([{...},{...}])`)
  will break or skip sequence assignment. If you touch create, modernise it carefully.
- **`party2_name` only fills for employees.** `set_party2()` copies the name only when
  `party2 == 'employee'`. For `partner`/`other` cases the stored `party2_name` stays blank,
  so the tree's "Name" column and any grouping on it will be empty for those rows. Extend the
  compute if partners/others need a visible name.
- **Legacy `states={...}` on field definitions.** Several Python field defs still use the
  Odoo ≤15 `states={'draft':[('readonly',False)]}` / `states={'won':[('readonly',True)]}`
  syntax (`requested_date`, `court_name`, `judge`, `lawyer`, `employee_id`, `partner_id`).
  Odoo 17 ignores `states` on fields (it was removed in favour of view-level `readonly`
  expressions). The **form view** already drives readonly via `readonly="state != 'draft'"`
  attributes, so behaviour is correct — but don't trust the Python `states=` to do anything.
- **`next_appointment` is derived, not the hearing date.** It is the latest `update_ids`
  datetime, *not* `hearing_date`. The daily cron reminder fires off `next_appointment`, so a
  case with no Updates rows never triggers a reminder even if `hearing_date` is today. If the
  client expects hearing-date reminders, the cron filter must be changed.
- **Mislabelled strings to leave alone (or fix deliberately):** the activity type is stored
  as "Legal Case Remainder" (typo) and the cron note says "Reminder". Changing the activity
  type's `name` is fine, but the XML id `mail_act_legal_case_reminder` is referenced from
  code — keep the id stable.
- **`legal_count` is unstored + un-depended.** It recomputes by SQL search on every employee
  form read. Fine at this scale; if you ever sort/group employees by it, it won't work
  (not stored).
- **No PDF/report, no JS** — if a handover ticket asks to "print the case", there is nothing
  to print; a report must be built from scratch.
- **Demo data is gated** behind the demo flag (`demo` key, not `data`) and `noupdate="1"`,
  so it won't reappear on `-u`. It creates a `MyCompany` company, an employee "Roshan
  Andrews", three partner "lawyers", and one sample lawsuit.
- **Cybrosys upstream module** — when updating from a newer OpenHRMS release, diff against
  this tree; local edits (if any) are not tracked separately.

---

## 11. File map
```
__manifest__.py                         depends [base, hr]; data + demo lists
__init__.py  →  models/__init__.py  →  models/legal_action.py
models/
  legal_action.py     hr.lawsuit (central) · hr.lawsuit.update (log) · hr.employee (inherit)
data/
  cron.xml            ir.cron "Legal Case: Next Appointment" (daily)
  mail_activity_data.xml   mail.activity.type 'mail_act_legal_case_reminder'
  demo_data.xml       sample company/employee/lawyers/lawsuit (demo flag only, noupdate)
security/
  security.xml        module category · lawsuit_group_manager · multi-company rule
  ir.model.access.csv ACLs (manager CRUD; all-users read) for both models
views/
  legal_action_view.xml   ir.sequence · form/tree/search · action · employee stat button · menu
i18n/
  ar_001.po           Arabic translation catalogue (shared OpenHRMS suite catalogue)
static/
  description/        Apps-store listing artwork + index.html (NOT loaded by Odoo runtime)
  image/images.jpeg   demo employee photo
doc/RELEASE_NOTES.md · README.md   upstream Cybrosys docs
```
