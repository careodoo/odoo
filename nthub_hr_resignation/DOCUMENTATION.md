# nthub_hr_resignation — Developer Handover Documentation

> **HR Resignation** — a third-party (Neoteric Hub) Odoo module that manages the
> **employee resignation / termination / death** off-boarding workflow. An HR record
> (`hr.employee.resignation`) carries a multi-stage approval lifecycle
> (draft → HR → Finance → Done), archives the employee on completion, and exposes a
> **website/portal form** so employees can file a resignation request themselves.
> UI labels are English. This file is the single source of truth for handover — read it
> before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `nthub_hr_resignation` |
| Display name | HR Resignation |
| Manifest version | `15.0` (string in manifest — **module runs on Odoo 17 on this server**) |
| Author / company | Neoteric Hub (`https://www.neoterichub.com`) |
| License | LGPL-3 |
| Category | Human Resources |
| `application` | `False` (it is a feature module, not a top-level app) |
| Declared depends | `hr`, `account`, `website` |
| **Undeclared runtime deps** | `hr_contract` (uses `hr.contract`), `portal` (controller imports `CustomerPortal`), and `nthub_hr_eos` (referenced in `action_open_eos_request`) — see Gotchas |
| External Python libs | stdlib `time`, `base64`, `datetime.date`; `dateutil.relativedelta` (ships with Odoo) |
| New model | `hr.employee.resignation` |
| Inherited model | `hr.employee` (adds resignation flags) |
| Controller | `PortalAccount(CustomerPortal)` — website resignation form |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u nthub_hr_resignation --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. Log file: `/var/log/odoo/odoo-17.log`.
- After editing the QWeb website templates, a module `-u` re-imports the templates; a
  restart serves them.

---

## 2. Architecture overview

```
hr.employee.resignation   (central model — mail.thread)
├── many2one → hr.employee        (employee_id; default = current user's employee)
├── related  → hr.department      (department_id, stored)
├── many2one → res.company        (company_id)
├── many2one → res.users          (approved_by)
├── many2many→ ir.attachment      (attachment_ids — supporting docs)
└── state machine: draft → submit → hr_dept → finance_dept → done   (+ refuse)
                     │        │         │            │
                  Submit   HR Appr.  Finance Appr.  Done → archives employee

hr.employee (inherited)
├── resigned (Boolean)            set True when a resignation reaches "done"
├── resignation_type (Selection)  resignation / termination / death
├── date_of_leave (Date)          set from the request's leave_date on Submit
├── get_employee()                @api.model — current user's employee (used as default)
└── get_active_contracts(date)    finds the single active hr.contract (raises if >1)

Website / Portal (controllers/main.py → PortalAccount)
├── GET  /my/resignation              show the user's latest non-done request
├── GET  /create/resignation/request  render the create form
└── POST /resignation/request         create/update request + attach files
    Templates: portal_resignation, thankyou_resignation
    Website menu: "Resignation Request" → /create/resignation/request

Backend menu: HR → Employee Resignation  (group hr.group_hr_user)
Sequence: code "hr.employee.resignation", prefix "RES/", padding 4, date-ranged
```

**Design notes**
- The approval gate is enforced purely by **`groups="…"` on the header buttons** (HR user →
  HR manager → account manager → HR manager). There are no field-level locks beyond the
  view's `readonly="state != 'draft'"` rules.
- `name` is allocated from an `ir.sequence` in `create()` (prefix `RES/`), defaulting to
  `'New'` if the sequence is missing.
- Record visibility is split by two `ir.rule`s: regular users see only their own / their
  reports', while HR users and account managers see everything.

---

## 3. Module-level constants (`models/hr_employee_resignation.py`)

| Constant | Value |
|---|---|
| `resignation_states` | the 6 lifecycle states used by the `state` Selection (see §4.1) |

```python
resignation_states = [
    ('draft',        'Draft'),
    ('submit',       'Waiting HR Approval'),
    ('hr_dept',      'Waiting Finance Approval'),
    ('finance_dept', 'Waiting Done'),
    ('done',         'Done'),
    ('refuse',       'Refused'),
]
```
> Note the labels are off-by-one relative to the button that produces them: e.g.
> `action_hr_approve()` (HR manager) moves `submit → hr_dept`, and `hr_dept`'s label is
> "Waiting Finance Approval". The **state keys** are the stable contract; labels are
> descriptive only.

---

## 4. Data model

### 4.1 `hr.employee.resignation` (central — `models/hr_employee_resignation.py`)
`_inherit = 'mail.thread'` · `_description = "Employee Resignation"` · `_rec_name = 'employee_name'`

| Field | Type | Purpose |
|---|---|---|
| `name` | Char (default `'New'`) | reference; set from sequence `hr.employee.resignation` in `create()` (e.g. `RES/0001`) |
| `employee_id` | Many2one `hr.employee` (required) | the resigning employee; default = `hr.employee.get_employee()` (current user's employee) |
| `employee_name` | Char (related `employee_id.name`) | display name; the model's `_rec_name` |
| `department_id` | Many2one `hr.department` (related, **stored**) | employee's department |
| `company_id` | Many2one `res.company` (readonly, default = user's company) | owning company |
| `approved_date` | Datetime (readonly) | set to `now()` when the request reaches `done` |
| `leave_date` | Date | requested last working / leave date; **drives Submit logic** |
| `ticket_date` | Date (default today) | request filing date |
| `approved_by` | Many2one `res.users` (readonly) | declared but **never written** by the code (always empty) — see Gotchas |
| `state` | Selection `resignation_states` (default `draft`) | lifecycle state |
| `resignation_type` | Selection `resignation / termination / death` | off-boarding reason category |
| `reason` | Text | free-text justification (required in views) |
| `attachment_ids` | Many2many `ir.attachment` | supporting documents |

**Workflow methods** (each `ensure_one()`):

| Method | Transition | Group (from view button) | Side effects |
|---|---|---|---|
| `create(vals)` | — | — | allocates `name` from sequence, then `super().create` (single-dict signature, **not** `@api.model_create_multi`) |
| `action_submit()` | `draft → submit` | `hr.group_hr_user` | builds a month window from `leave_date`, calls `employee_id.get_active_contracts(date_to)`; **raises `UserError`** if no active contract; writes `employee_id.date_of_leave = leave_date` |
| `action_hr_approve()` | `submit → hr_dept` | `hr.group_hr_manager` | none |
| `action_finance_approve()` | `hr_dept → finance_dept` | `account.group_account_manager` | none |
| `action_resignation_done()` | `finance_dept → done` | `hr.group_hr_manager` | sets `approved_date = now()`; **archives the employee** (`employee_id.active = False`), sets `employee_id.resigned = True` and copies `resignation_type` onto the employee |
| `action_resignation_refuse()` | `done → refuse` | `hr.group_hr_user` | (button is `invisible` unless `state == 'done'`) |
| `action_set_to_draft()` | `refuse → draft` | `base.group_user` | reset |
| `action_open_eos_request()` | — | — | opens a `hr.employee.eos` form via `self.eos_id` / `nthub_hr_eos.view_employee_eos_form` — **dead/broken** in this module (no `eos_id` field, no menu/button calls it) — see Gotchas |
| `unlink()` | — | — | blocks delete when `state in ['submit','done']` |

> **Submit date math:** `action_submit` computes `date_from = first-of-month(leave_date)`
> and `date_to = date_from + relativedelta(day=leave_date.day)` — effectively
> `date_to == leave_date`. It then requires exactly one active contract on that date
> (`get_active_contracts` raises if it finds more than one).

### 4.2 `hr.employee` (inherited — `models/hr_employee.py`)
| Field | Type | Purpose |
|---|---|---|
| `resigned` | Boolean (default `False`) | set `True` once a resignation is completed (`done`) |
| `resignation_type` | Selection `resignation / termination / death` | mirrors the completed request's type |
| `date_of_leave` | Date (tracked) | set from the request's `leave_date` on Submit |

**Methods:**
- `get_employee()` — `@api.model`; returns the **first** `hr.employee` linked to the current
  user (`user_id = self.env.uid`) or `False`. Used as the default for `resignation.employee_id`.
- `get_active_contracts(date=today)` — searches `hr.contract` for a contract active on
  `date` (running window incl. open `date_end` and trial logic). **Raises `UserError`** if it
  finds more than one. Returns the recordset. > `hr_contract` is not in the manifest depends
  — see Gotchas.

---

## 5. Views / UI

### 5.1 Backend (`views/hr_employee_resignation_view.xml`)
- **Form** (`hr_employee_resignation_form_view1`): header with the 6 workflow buttons (each
  gated by its `groups` + `invisible="state != …"`), a `statusbar` widget
  (`statusbar_visible="draft,done"`, draft=blue / refuse=red). Sheet groups:
  *Employee Information* (`employee_id`, related `department_id`, `company_id` for
  multi-company), `resignation_type`, `ticket_date`, `leave_date`, `approved_date`,
  `attachment_ids` as `many2many_binary`; *Resignation Reason* (`reason`); an
  *Extra Information* page (`group_no_one`) with audit fields; chatter.
  Most inputs are `readonly="state != 'draft'"`.
- **Tree** (`hr_employee_resignation_tree_view`): employee, department, type, ticket/leave
  date (optional cols), approved_date, company, state.
- **Search** (`view_employee_resignation_filter`): search by employee/company/department;
  Group By type / status / company / department.
- **Action** (`hr_employee_resignation_action`): `tree,form`, model `hr.employee.resignation`.
- **Menu** (`views/menu.xml`): `menu_hr_emp_resignation` → "Employee Resignation" under
  `hr.menu_hr_main`, sequence 8, group `hr.group_hr_user`.

### 5.2 Employee form (`views/hr_employee_view.xml`)
Inherits `hr.view_employee_form` to show `resigned` and `resignation_type` after
`company_id` (both `invisible="not resigned"`).

### 5.3 Website / Portal (`views/template/`)
- `portal_menu.xml` — `website.menu` "Resignation Request" →
  `/create/resignation/request?create_from_header=true` (`noupdate="1"`; the optional
  `group_ids` restriction is commented out, so the menu is visible to all).
- `resignation_template.xml` — two QWeb website templates:
  - **`portal_resignation`** — the create/edit form (`POST /resignation/request`,
    `enctype="multipart/form-data"`). Renders an employee `<select>` (populated from
    `employee_ids`), ticket date, type, leave date, reason, a (disabled) resignation date,
    and a multi-file attachment input. Shows a state badge and the portal chatter when
    editing an existing `resignation_id`.
  - **`thankyou_resignation`** — confirmation page linking to `/my/resignation`.
  > These templates carry several copy/paste artifacts from the source module
  > (`trip_id`, `/my/trips` redirect, a `financial_dept` state that doesn't exist) — see
  > Gotchas.

---

## 6. Controller (`controllers/main.py` — `PortalAccount(CustomerPortal)`)

| Route | Methods | Auth | Behaviour |
|---|---|---|---|
| `/my/resignation` | GET (`http`, website) | `user` | finds the current user's latest non-`done` request (`create_uid = uid`, `order id desc`, `limit 1`) and renders `portal_resignation` |
| `/create/resignation/request` | GET (`http`, website, `csrf=False`) | `user` | renders an empty create form; loads **all** employees (`sudo().search([])`) into `employee_ids`, sets `ticket_date = today`, `resignation_id = False` |
| `/resignation/request` | POST (`http`, website) | **`public`** | create-or-update: if `resignation_id` posted → `check_access_rights('write')` + `write(values)`; else `sudo().create(values)`. Attaches uploaded `ufile`s via `btrip_attchcreate`. On exception → `cr.rollback()` and redirects to `/my/trips?error=…` |
| `btrip_attchcreate(ufiles, record)` | helper | — | base64-encodes each uploaded file into an `ir.attachment` linked to the resignation record |

> **Security note:** `/resignation/request` is `auth='public'` and the create path uses
> `sudo()` — anyone who can reach the URL can create a resignation record. The update path
> does call `check_access_rights('write')`. The error redirect points at `/my/trips`
> (leftover from the source module) — see Gotchas.

---

## 7. Reports
**N/A** — this module ships no QWeb-PDF reports or `ir.actions.report` records.

## 8. Crons / automation
**N/A** — no `ir.cron` jobs. State transitions are entirely button/route driven.

## 9. Settings / config parameters
**N/A** — no `res.config.settings` extension and no `ir.config_parameter` usage.

---

## 10. Data / sequence (`data/sequence.xml`)
One `ir.sequence` (`noupdate="1"`):

| Field | Value |
|---|---|
| `name` | Resignation Sequence |
| `code` | `hr.employee.resignation` |
| `prefix` | `RES/` |
| `padding` | 4 |
| `use_date_range` | True |
| `number_next` / `number_increment` | 1 / 1 |

Consumed in `HrEmployeeResignation.create()` → `next_by_code('hr.employee.resignation')`.

---

## 11. Security (`security/`)
- **`ir.model.access.csv`** — two ACL rows on `hr.employee.resignation`:
  - `base.group_user` → read/write/create, **no unlink**.
  - `hr.group_hr_manager` → full CRUD (incl. unlink).
- **`ir_rule.xml`** — two record rules:
  - `employee_resignation_rule_employee` (group `base.group_user`): a user sees a request
    only if they are the employee, the employee's manager (`parent_id`), or the coach
    (`coach_id`).
  - `employee_resignation_rule_other` (groups `hr.group_hr_user`, `account.group_account_manager`):
    domain `[(1,'=',1)]` → see all records.
- **Button-level gating** (in the form view) is the real approval gate:
  Submit → `hr.group_hr_user`; HR Approve / Done → `hr.group_hr_manager`;
  Finance Approve → `account.group_account_manager`; Refuse → `hr.group_hr_user`;
  Set to Draft → `base.group_user`.

## 12. Assets / JS
**N/A** — no OWL components, JS, or SCSS asset bundles. The only front-end is the two
server-rendered QWeb website templates. `static/description/` holds the App-Store listing
page (`index.html`, icon, banner, screenshots) — **not loaded by Odoo at runtime**.

---

## 13. Gotchas & notes (read before debugging)

- **Manifest version string is `15.0`** but the module runs on Odoo 17 here. Don't trust it
  as a compatibility marker; the code is v17-style (`invisible="…"` button attrs, no
  `attrs`/`states`).
- **Undeclared dependencies** — the `depends` list (`hr`, `account`, `website`) is
  incomplete versus what the code actually uses:
  - `hr.contract` is queried in `get_active_contracts` / `action_submit` but **`hr_contract`
    is not in depends**. If `hr_contract` isn't installed, Submit raises. Add it to depends
    or ensure it's installed.
  - The controller imports `from odoo.addons.portal.controllers.portal import CustomerPortal`
    — `portal` is pulled in transitively via `website`, but it is a real dependency.
  - `action_open_eos_request()` references `self.eos_id`, model `hr.employee.eos`, and view
    `nthub_hr_eos.view_employee_eos_form` — **none exist in this module**. There is no
    `eos_id` field defined, no button/menu calls this method, and `nthub_hr_eos` is not a
    dependency. This method is **dead code / a stub for a sibling EOS module**; calling it
    will error.
- **`approved_by` is never set.** The field exists and is shown read-only in the form, but no
  method writes it — it stays empty. (`approved_date` *is* written, in
  `action_resignation_done`.)
- **`create()` is single-dict (`@api.model`), not `@api.model_create_multi`.** Batch creates
  via the ORM will fail or skip the sequence assignment for extra records. The
  `model_create_multi` line is commented out in the source.
- **`unlink()` guard mismatch:** it blocks delete in `['submit','done']`, but the
  CSV already denies unlink to `base.group_user` entirely; only `hr.group_hr_manager` can
  delete, and even they are blocked for `submit`/`done` records.
- **Website template leftovers** (this module was cloned from a "business trip" module):
  - `portal_resignation` references `trip_id.resignation_id` in two state badges and checks a
    `financial_dept` state that **doesn't exist** (real key is `finance_dept`) — those
    badges render blank.
  - The controller's error path redirects to **`/my/trips`**, not a resignation page.
  - `btrip_attchcreate` keeps the trip-era name.
- **Public POST + sudo create:** `/resignation/request` is `auth='public'` and creates via
  `sudo()`. Treat this as an external-facing endpoint; validate/tighten before exposing on a
  public website. The update branch does enforce `check_access_rights('write')`.
- **Archiving is one-way in the UI:** `action_resignation_done` sets `employee.active=False`.
  Refusing afterward (`done → refuse`) does **not** re-activate the employee or clear
  `resigned`/`date_of_leave`. Reverse those manually if a "done" request is undone.
- **`get_active_contracts(date=fields.Date.today())`** uses a mutable default evaluated at
  import time — the default `date` is the day the server started, not "today" at call time.
  In practice `action_submit` always passes an explicit `date_to`, so this only matters if
  the method is called with no argument.

---

## 14. File map
```
__manifest__.py                         depends/data/security/views
__init__.py                             → models, controllers
controllers/  main.py                   PortalAccount — website resignation form (3 routes)
data/         sequence.xml              ir.sequence  RES/####
models/       hr_employee_resignation.py  hr.employee.resignation (workflow + unlink + create)
              hr_employee.py              hr.employee inherit (resigned/type/date_of_leave + helpers)
security/     ir.model.access.csv       2 ACL rows
              ir_rule.xml               2 record rules (own vs. all)
views/        hr_employee_resignation_view.xml  form/tree/search/action
              hr_employee_view.xml      employee form inherit
              menu.xml                  HR → Employee Resignation menu
              template/portal_menu.xml          website.menu "Resignation Request"
              template/resignation_template.xml portal_resignation + thankyou_resignation
static/description/  index.html · icon.png · banner.gif · assets/  (store listing, not loaded)
```
