# hr_employee_shift — Developer Handover Documentation

> **Employee Request for Shifting** — a department-transfer (**طلب نقل**) workflow
> module for Odoo 17. An employee's move from one `hr.department` to another goes
> through a configurable multi-step approval chain (old-manager submit → up to three
> approvers → new-manager final shift), driven by `mail.template` e-mails and chatter
> activities. Crucially it also **locks down direct department edits** on `hr.employee`
> so transfers can only happen via an approved request. The actual move only happens
> after approval, then a bilingual (English/Arabic) Kuwait HR transfer PDF can be
> printed. UI labels are English; the report and some content are bilingual. Read this
> before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_employee_shift` |
| Display name | Employee Request for Shifting |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Depends | `base`, `hr`, `hr_holidays` |
| External Python libs | **None** (pure Odoo ORM; stdlib only) |
| New models | `employee.shift.request`, `employee.shift.request.record`, `request.refuse.reason` (wizard) |
| Inherited models | `hr.employee`, `hr.department`, `res.config.settings` |
| Reports | 1 QWeb-PDF (bilingual Kuwait HR transfer form) |
| Crons | **None** (N/A) |
| Assets / JS | **None** — only static images used by the report (N/A for OWL/JS) |

> **Author/website in manifest are placeholder defaults** (`My Company`,
> `http://www.yourcompany.com`) and the summary/description are scaffold stubs left
> unedited. Cosmetic only — does not affect behaviour.

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u hr_employee_shift --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- No dev mode. No JS/SCSS assets to rebuild — only XML/Python `-u`.

---

## 2. Architecture overview

```
employee.shift.request   (central workflow — mail.thread + mail.activity.mixin)
│   _order = 'id desc'
├── employee_id        → hr.employee     (who is moving)
├── current_department → hr.department   (Old Department; auto-filled from employee)
├── new_department     → hr.department   (target; domain != current)
├── approver_1/2/3     → res.users       (chain; from dept override OR global settings)
├── old_department_manager / new_department_manager → res.users (dept manager's user)
├── working_hours_modifier → res.users   (related from current_department)
├── working_hours      → resource.calendar (related from employee, editable)
└── state machine: draft → sent → confirm → approval_1/2/3 → done
                              ↘ refuse_1 / refuse_2 / refuse_3  (via wizard)

        on each step → creates an employee.shift.request.record audit row
        on each step → sends a mail.template + schedules a chatter activity
        on 'done'    → writes employee.department_id (context shift_request=True)

employee.shift.request.record   (immutable history line — one per workflow transition)
└── shown read-only on the employee form ("Employee Shift Request History" tab)

hr.employee (inherited)
├── shift_request_records → employee.shift.request.record (O2m)
└── write() GUARD: blocks direct department_id changes unless
    group_direct_shift_user OR context shift_request=True

hr.department (inherited)
└── per-department approver overrides + approval-gate booleans + working_hours_modifier

res.config.settings (inherited)
└── 3 global default approvers (config_parameter, prefix hr_employee_shift.)

request.refuse.reason (TransientModel wizard)
└── captures refuse reason, sets the right refuse_N state on the active request
```

**Design principles**
- The approval chain is **dynamic**: at any step the workflow checks how many
  approvers/manager-gates are configured and either advances to the next approver or
  short-circuits straight to the shift. Steps with no approver are skipped.
- Approvers resolve **per-department first** (`hr.department.employee_shift_approval_*`),
  falling back to **global `config_parameter` defaults**.
- The real enforcement is the `hr.employee.write()` guard — without it the whole
  request workflow could be bypassed by editing the department directly.

---

## 3. Data model

### 3.1 `employee.shift.request` (central — `models/employee_shift_request.py`)
`_inherit = ['mail.thread', 'mail.activity.mixin']` · `_order = 'id desc'`

| Field | Type | Purpose |
|---|---|---|
| `employee_id` | M2o `hr.employee` (required) | the employee being transferred |
| `image_128` / `avatar_128` | Image (related, `compute_sudo`) | from `employee_id` — kanban/form display |
| `current_department` | M2o `hr.department` | **"Old Department"** — auto-set from employee on change |
| `new_department` | M2o `hr.department` (required, domain `!= current`) | target department |
| `date` | Date | **"Request Date"** (also used as transfer date on the PDF) |
| `state` | Selection (required, tracked, default `draft`) | workflow state — see below |
| `approver_1/2/3` | M2o `res.users` | approval chain (defaults from settings, overridable per dept) |
| `old_department_manager` | M2o `res.users` | current dept's `manager_id.user_id` |
| `new_department_manager` | M2o `res.users` | target dept's `manager_id.user_id` |
| `company_id` | M2o `res.company` (required, default current) | multi-company |
| `refuse_reason` | Char | filled by the refuse wizard; shown read-only on refused states |
| `working_hours_modifier` | M2o `res.users` (related, stored) | from `current_department.working_hours_modifier`; the user allowed to edit working hours |
| `working_hours` | M2o `resource.calendar` (related, stored, **readonly=False**) | employee's `resource_calendar_id` — editable by the modifier at the `confirm` step |
| `active` | Boolean (default True) | archiving |
| `show_shift_department` | Boolean | UI flag toggled when the request reaches the new-manager final step |

**State selection (keys → labels):**
`draft` → Draft · `sent` → Sent to Manager · `confirm` → Submitted ·
`approval_1` → First Approved · `refuse_1` → First Refused ·
`approval_2` → Second Approved · `refuse_2` → Second Refused ·
`approval_3` → Third Approved · `refuse_3` → Third Refused · `done` → Shifted.

**Approver default helpers** (`_default_approver_1/2/3`): read the global config
parameters `hr_employee_shift.employee_shift_approval_1/2/3` and browse the
`res.users`. Used both as field defaults and as fallback in `onchange_employee_id`.

**Key methods / workflow** (see §4 for the full state diagram):
- `create(vals)` — **duplicate guard**: raises `ValidationError` if an *open*
  (not in `refuse_1/2/3` or `done`) request already exists for the same
  employee + current + new department.
- `onchange_employee_id` — sets `current_department`, resolves
  `old_department_manager`; **raises** if the dept has no manager or the manager has
  no linked user. Loads per-department approvers if `employee_shift_approval_1` is set,
  else the global defaults.
- `onchange_new_department` — sets `new_department_manager`; same manager/user
  validation as above.
- `_prepare_request_record(approver)` — builds the dict for an audit
  `employee.shift.request.record`. **Note:** uses key `old_department` (not
  `current_department`) to match the record model's field name.
- `send_to_manager()` — if the current dept does **not** require old-manager approval
  (`old_manager_approval` False), jumps straight to `shift_confirm()`. Otherwise sets
  state `sent`, emails the old manager, schedules an activity for them.
- `shift_confirm()` — state `confirm`, logs an audit record, emails approver_1,
  schedules their activity.
- `first_approve()` / `second_approve()` / `third_approve()` — advance the chain. Each
  checks: next approver exists? → advance to next approval state + email/activity.
  Else if `current_department.new_manager_approval` → set the matching `approval_N`
  state, set `show_shift_department=True`, email the **new** dept manager. Else →
  call `shift_department()` directly.
- `first_refuse()` — returns the `request.refuse.reason` wizard action (the **same
  method is reused** for all three Refuse buttons; the wizard figures out which
  refuse_N applies from the current state).
- `shift_department()` — **the actual move**: writes the employee's `department_id`
  to `new_department` using `with_context(shift_request=True)` (to bypass the employee
  guard), sets state `done`, `show_shift_department=False`, logs a final audit record,
  and schedules "completed" activities for the request followers
  (`get_request_followers()` = new manager + approver_2/3 if present).

### 3.2 `employee.shift.request.record` (`models/hr_employee.py`)
Immutable **history/audit line**, one created per workflow transition.
`_description = 'Employee Shift Request History'` (no `mail.thread`).

| Field | Type | Purpose |
|---|---|---|
| `employee_id` | M2o `hr.employee` | who |
| `old_department` | M2o `hr.department` | from |
| `new_department` | M2o `hr.department` | to |
| `state` | Selection | snapshot of the request state at that step |
| `approver` | M2o `res.users` | who acted at that step |

Exposed read-only on the employee form via `hr.employee.shift_request_records`
(O2m, inverse `employee_id`). `create_date` is the timeline.

### 3.3 `hr.employee` (inherited — `models/hr_employee.py`)
- `shift_request_records` — O2m → `employee.shift.request.record`.
- **`write()` override (the enforcement core):** after the super write, if `department_id`
  is in `vals` and the user is **not** in `group_direct_shift_user` and the context flag
  `shift_request` is **not** set, it raises:
  `"You are not allowed to modify department directly, you should create shift request"`.
  > ⚠️ The guard runs **after** `super().write()` — the change is technically applied
  > then rolled back by the raise. Functionally correct (transaction aborts) but be
  > aware when reasoning about side effects.

### 3.4 `hr.department` (inherited — `models/hr_department.py`)
| Field | Type | Purpose |
|---|---|---|
| `employee_shift_approval_1/2/3` | M2o `res.users` (Approver#1/2/3) | per-department approver override (beats global settings) |
| `old_manager_approval` | Boolean | "Required Old Manager Approval" — if False, the `send_to_manager` step is skipped |
| `new_manager_approval` | Boolean | "Required New Manager Approval" — if True, the new manager performs the final shift |
| `working_hours_modifier` | M2o `res.users` | who may edit `working_hours` on the request; **domain limited** to the three approver fields |

### 3.5 `res.config.settings` (inherited — `models/res_config_settings.py`)
Three global default approvers, all `config_parameter` (prefix `hr_employee_shift.`):
`employee_shift_approval_1/2/3`. These are the fallback chain when a department has no
per-department approvers configured.

### 3.6 `request.refuse.reason` (wizard — `wizards/request_refuse_reason.py`)
TransientModel. Single field `reason` (Char, required). `action_refuse()` reads the
active request (`active_id`), maps current state → refuse state + approver
(`confirm`→`refuse_1`/approver_1, `approval_1`→`refuse_2`/approver_2, else
`refuse_3`/approver_3), writes the state + `refuse_reason`, and logs an audit record.
> A commented-out `activity_schedule` block (referencing a non-existent
> `hr_attendance_approval` activity) is dead code — leftover from a copy-paste origin.

---

## 4. Workflow / state machine

```
                 send_to_manager()
   [draft] ───────────────────────────────────────────────┐
      │                                                    │
      │ old_manager_approval = True        old_manager_approval = False
      ▼                                                    │
   [sent] ── shift_confirm() (old mgr) ──► [confirm] ◄─────┘
                                              │
                                  first_approve() by approver_1
                ┌─────────────────────────────┼───────────────────────────────┐
       approver_2 set                 no approver_2,                  no approver_2,
                │                  new_manager_approval=True       new_manager_approval=False
                ▼                             ▼                             │
          [approval_1] ──second_approve()──► [approval_1]                   │
                │  (approver_2)              show_shift_department=True      │
       (same branch logic at each level: approver_3? new mgr? else shift)   │
                ▼                             ▼                             ▼
          [approval_2/3] ───────────► (new_department_manager)        shift_department()
                                       shift_department() button             │
                                              │                             │
                                              ▼                             ▼
                                          [done]  ◄───────────────────────[done]
                                   employee.department_id := new_department

   At [confirm]/[approval_1]/[approval_2] an approver may instead press Refuse
   → request.refuse.reason wizard → [refuse_1] / [refuse_2] / [refuse_3]
```

**Branching rule (repeated at each approval level):** advance to the next approver if
one is configured; otherwise, if the **current** department's `new_manager_approval`
is set, hand off to the new department manager for the final shift; otherwise perform
the shift immediately. So a department with zero approvers and both manager-approval
flags off results in `draft → confirm → done` in two clicks.

---

## 5. Views (`views/*.xml`)

- **`employee_shift_request.xml`** — the main UI:
  - **Kanban** (`o_hr_employee_kanban`, priority 10): employee photo + name, From/To
    departments, date, state badge.
  - **Form**: header with the full button set, each gated by `invisible` expressions on
    `state` + the acting user (`uid`) — *Send to Manager* (draft), *Submit* (old mgr,
    sent), *Approve* ×3 (approver_N at the matching state), *Shift* (new mgr when
    `show_shift_department`), *Refuse* ×3 (all call `first_refuse`). Statusbar shows
    `draft,confirm,done`. `working_hours` is only visible to the
    `working_hours_modifier` at the `confirm` step.
  - **Tree**: date, employee, departments, company, colour-decorated state badge.
  - **Actions / menus**: root menu **"Request for Shifting"** (seq 11) →
    `employee_shift_request_action` ("Request for Shifting", kanban/tree/form) and
    `wait_shift_request_action` (**"Waiting Approval"** — domain matches requests where
    the current user is the manager/approver expected at the request's current state).
- **`hr_employee.xml`** — adds an **"Employee Shift Request History"** form tab
  (read-only `shift_request_records` tree), visible only to
  `group_shift_request_manager`.
- **`hr_department.xml`** — adds a **"Shift Approvers"** group to the department form
  (the 3 approvers, both manager-approval booleans, working-hours modifier).
- **`res_config_settings.xml`** — adds an **"Approval List"** app/settings page with the
  3 global default approvers; plus a `Settings` action + menu (under the root menu,
  `base.group_system` only).

## 5b. Wizard (`wizards/request_refuse_reason.xml`)
Simple dialog: a `reason` field + **Refuse** (calls `action_refuse`) / Cancel buttons.

---

## 6. Reports (`reports/shift_report.xml`)

One `ir.actions.report` — **"Request for Shift Report"** (`qweb-pdf`,
`report_name = hr_employee_shift.shift_report`), bound to `employee.shift.request`
(form print menu). The template `shift_report` renders a **bilingual (English + Arabic,
RTL via `.rtl-row`) Kuwait HR "Transfer Form Temp / Perm" (طلب نقل مؤقت / دائم)** with:
- Logo header (`static/src/img/logo.jpeg`), Human Resources Department title.
- Employee block: name (`employee_id.english_name` + Arabic name), Employee ID
  (`employee_id.barcode`), from/to locations (`current_department`/`new_department`),
  position (`employee_id.job_title`), transfer period, transfer date (`doc.date`).
- Signature blocks for current-location manager, new-location manager, personnel
  supervisor notes, HR manager — all blank for wet signatures.
- Footer: `REF.: HR-FORMS 007`.

> ⚠️ The report reads **`employee_id.english_name`** — that field comes from another
> installed HR module (e.g. the client's `care_hr`/custom employee extension), **not**
> from this module or stock `hr`. If `english_name` is absent the PDF will error. Keep
> this dependency in mind. The other static images
> (`Emblem_of_Kuwait.svg.png`, `header.png`, `footer.png`, `kuwait_police.png`,
> `stamp.png`) ship in `static/src/img/` but are **not referenced** by this template.

---

## 7. Automation & settings

### 7.1 Crons — **N/A**. No `ir.cron` records exist. All automation is synchronous,
triggered by the approval buttons (e-mails + chatter activities).

### 7.2 E-mail templates (`data/mail_templates.xml`)
5 `mail.template` records on `employee.shift.request`, each `auto_delete=0`, inline HTML
table layout, `email_from` = acting user, sent via
`mail.template.send_mail(..., force_send=True)`:
| XML id | Recipient | Sent at step |
|---|---|---|
| `dept_shift_send_to_manager_template` | `old_department_manager` | `send_to_manager` |
| `dept_shift_send_to_1_approve_template` | `approver_1` | `shift_confirm` |
| `dept_shift_send_to_2_approve_template` | `approver_2` | `first_approve` |
| `dept_shift_send_to_3_approve_template` | `approver_3` | `second_approve` |
| `dept_shift_send_to_new_dept_approve_template` | `new_department_manager` | first/second/third_approve (new-mgr branch) |

### 7.3 Activity type (`data/activity.xml`)
One `mail.activity.type` **`mail_act_shift_create`** ("Shift Request", icon `fa-sun-o`,
model `employee.shift.request`). Every workflow step `activity_schedule`s this type for
the next actor; the final shift schedules it for all followers.

### 7.4 Config parameters (`res.config.settings`)
`hr_employee_shift.employee_shift_approval_1` / `_2` / `_3` — global default approver
user ids. Set via **Settings → Approval List**. Only char/m2o supported as usual for
`res.config.settings`.

---

## 8. Security (`security/`)

### 8.1 Groups (`security/security.xml`)
- Category **"Direct Employee Shifting"** → `group_direct_shift_user` — members may edit
  `hr.employee.department_id` **directly** (bypassing the request workflow guard).
- Category **"Request for Shifting"** → `group_shift_request_user` (User),
  `group_shift_request_approver` (Approver), `group_shift_request_manager` (Manager).

### 8.2 Record rules (`security/security.xml`)
| Rule | Group | Domain |
|---|---|---|
| `shift_request_rule_user_own` | User | `[('create_uid','=',user.id)]` — own requests only |
| `ir_rule_shift_request_approver` | Approver | own OR old/new manager OR approver_1/2/3 = user |
| `shift_request_rule_manager` | Manager | `[(1,'=',1)]` — all requests |

### 8.3 Multi-company rule (`security/rules.xml`)
Global rule `employee_shift_request_comp_rule`:
`['|',('company_id','=',False),('company_id','in',company_ids)]`.

### 8.4 Access (`security/ir.model.access.csv`)
> ⚠️ **All three model ACLs grant full CRUD (read/write/create/unlink) with `group_id`
> left blank — i.e. to every user.** Access is effectively governed by the **record
> rules** above (and the employee write-guard), not the ACL. The menus themselves are
> restricted to the three shift groups, so non-members simply don't see the app.
- `access_employee_shift_request` → `employee.shift.request` — CRUD, no group.
- `access_employee_shift_request_record` → `employee.shift.request.record` — CRUD, no group.
- `access_request_refuse_reason` → `request.refuse.reason` — CRUD, no group.

---

## 9. Assets / JS — **N/A**
No `web.assets_*` bundles, no OWL components, no SCSS/JS. The only `static/` content is
the report image set under `static/src/img/`.

---

## 10. Gotchas & notes (read before debugging)

- **The employee write-guard is the real lock.** `hr.employee.write()` blocks any direct
  `department_id` change unless the user is in `group_direct_shift_user` **or** the
  context carries `shift_request=True` (only `shift_department()` sets it). If transfers
  "silently fail" with a ValidationError, this is why — add the user to *Direct Employee
  Shifting* or route through a request. The guard raises **after** super().write(); the
  transaction rollback undoes the change.
- **Manager/user wiring is mandatory.** `onchange_employee_id` / `onchange_new_department`
  **raise** if a department has no `manager_id` or the manager has no linked `res.users`.
  Every department in the chain must have a manager whose `Related User` is set.
- **Approver resolution order:** per-department `employee_shift_approval_1` *(if set)*
  overrides the global settings — but only when slot 1 is filled (slots 2/3 are read
  from the department only in that branch). If a department fills only slot 2, it is
  ignored and the global defaults are used.
- **`first_refuse` is reused for all three Refuse buttons** — the wizard derives the
  correct `refuse_N` from the request's current state, not from which button was pressed.
- **Audit record field name mismatch:** the request model uses `current_department` but
  the history record uses `old_department`; `_prepare_request_record` maps between them.
  Don't "fix" one without the other.
- **`create()` override uses the old single-dict signature** (`def create(self, vals)`,
  `@api.model`) rather than the v17 batch `@api.model_create_multi`. It works for
  single-record creation (the UI path) but **will break on multi-record / batch
  `create([...])`** (e.g. imports). Migrate to `model_create_multi` if batch creation
  is ever needed.
- **Report depends on `english_name`** on `hr.employee`, supplied by another module —
  not declared in this module's `depends`. Implicit cross-module coupling.
- **Manifest metadata is scaffold-default** (author "My Company", stub summary). Cosmetic.
- **ACLs are group-less full-CRUD** (see §8.4). Security relies on record rules + menu
  group restriction, not on the access table.
- **Migrated-DB context:** this addon set was migrated from v16; views here already use
  v17 `invisible="..."` expressions (no `attrs`/`states`).

---

## 11. File map
```
__manifest__.py                       depends: base, hr, hr_holidays
__init__.py                           imports models, wizards
data/        mail_templates.xml (5 templates) · activity.xml (1 activity type)
models/      employee_shift_request.py  (central workflow, ~256 lines)
             hr_employee.py             (write-guard + employee.shift.request.record)
             hr_department.py           (approver overrides + gate booleans)
             res_config_settings.py     (3 global default approvers)
wizards/     request_refuse_reason.py (+ .xml)   refuse-reason dialog
reports/     shift_report.xml           bilingual Kuwait HR transfer PDF
security/    security.xml (groups + record rules) · rules.xml (multi-company)
             ir.model.access.csv  (group-less full CRUD on the 3 models)
views/       employee_shift_request.xml (kanban/tree/form/actions/menus)
             hr_employee.xml · hr_department.xml · res_config_settings.xml
static/src/img/  logo.jpeg (used by report) + Kuwait emblem/police/header/footer/stamp
```
