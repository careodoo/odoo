# employee_orientation — Developer Handover Documentation

> **Employee Orientation & Training** — a third-party (Cybrosys) Odoo 17 HR add-on
> for onboarding new hires and running training programs. It drives a new employee
> through a department-specific **orientation checklist** (each line dispatched as an
> **orientation request** to a responsible user), and separately runs **training
> programs** that print participation certificates. UI is **English** (no Arabic in
> this module). Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `employee_orientation` |
| Display name | Employee Orientation & Training |
| Version | `17.0.1.0.0` |
| Category | Human Resources |
| License | AGPL-3 |
| Author | Cybrosys Techno Solutions (third-party OCA-style module) |
| Depends | `base`, `hr` |
| External Python libs | stdlib only — `datetime`, `dateutil.relativedelta` (no extra pip installs) |
| New models | `employee.orientation`, `orientation.request`, `orientation.checklist`, `checklist.line`, `employee.training`, `orientation.force.complete` (wizard) |
| Inherited models | `hr.employee` (adds `certificates`) |
| Reports | 1 QWeb-PDF — training **Certificate of Participation** |
| Menus | English labels; root menus `Orientations` + `Training Program` under HR, config under HR → Configuration |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u employee_orientation --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. This module has **no JS/SCSS assets**, so a module `-u` followed by a
  restart is sufficient for any change. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
Configuration (HR managers set up once per department)
  checklist.line               (a single onboarding task + its responsible user)
  orientation.checklist        (M2m of checklist.line, scoped to one hr.department)
        │
        ▼  picked on an orientation
employee.orientation  (mail.thread)  ── the onboarding record for ONE new hire
  ├─ employee_id        → hr.employee   (related: department_id, job_id, parent_id)
  ├─ orientation_id     → orientation.checklist  (domain-filtered by department)
  └─ orientation_request_ids → orientation.request   (one per checklist line, on Confirm)
        │
        ▼  on action_complete_orientation, if any request still 'new'
  orientation.force.complete  (TransientModel wizard) ── lists pending lines, force-closes

employee.training  (mail.thread)  ── a department training program (independent flow)
  └─ training_ids  (computed) → hr.employee of that department
       prints  →  report.employee_orientation.print_pack_template  (AbstractModel)
                  → "Certificate of Participation" QWeb-PDF (one page per employee)

hr.employee (inherited) ── adds `certificates` Boolean (print-or-not flag)
```

**Design notes**
- Two largely **independent** flows live in one module: **Orientation** (checklist-driven
  onboarding with email dispatch) and **Training** (program + certificate printing).
- Orientation requests are **generated** from the chosen checklist's lines at Confirm
  time (`action_confirm_orientation`) — they are not entered by hand.
- `employee.training.training_ids` is a **computed, non-stored** O2m derived purely from
  the program's department; it is not a real relation (see Gotchas).

---

## 3. Data model

### 3.1 `employee.orientation` (`models/employee_orientation.py`)
The onboarding record for one new hire. `_inherit = 'mail.thread'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | sequence code `employee.orientation`, prefix `OR`, default `'New'`, set in `create()` |
| `employee_id` | M2o `hr.employee` | required — the new hire |
| `department_id` | M2o `hr.department` | `related='employee_id.department_id'`, required |
| `date` | Datetime | orientation date; copied to each generated request's `request_date` |
| `responsible_user_id` | M2o `res.users` | overall responsible user |
| `employee_company_id` | M2o `res.company` | required, default = current user's company |
| `parent_id` | M2o `hr.employee` | `related='employee_id.parent_id'` (manager) |
| `job_id` | M2o `hr.job` | `related='employee_id.job_id'`, domain by department |
| `orientation_id` | M2o `orientation.checklist` | required; domain = checklists of the same department |
| `note` | Text | free description |
| `orientation_request_ids` | O2m `orientation.request` | the generated request lines |
| `state` | Selection | `draft → confirm → complete` (+ `cancel`); readonly, indexed, default `draft` |

**Methods / workflow:**
- `create(vals)` — assigns the `OR###` sequence to `name` (NB: classic single-record
  signature, not `@api.model_create_multi`; see Gotchas).
- `action_confirm_orientation()` — state → `confirm`; **iterates the chosen checklist's
  `checklist_line_ids`** and creates one `orientation.request` per line, copying
  `line_name → request_name`, `responsible_user_id → partner_id`, `date → request_date`,
  and the employee.
- `action_cancel_orientation()` — cancels every child request, then state → `cancel`.
- `action_complete_orientation()` — if **any** child request is still `'new'`, opens the
  `orientation.force.complete` wizard (target `new`, `default_orientation_id` in context);
  otherwise state → `complete`.

### 3.2 `orientation.request` (`models/orientation_request.py`)
One dispatched onboarding task for a responsible user. `_inherit = 'mail.thread'`,
`_rec_name = 'request_name'`.

| Field | Type | Notes |
|---|---|---|
| `request_name` | Char | line title (from `checklist.line.line_name`) |
| `request_orientation_id` | M2o `employee.orientation` | parent onboarding record |
| `employee_company_id` | M2o `res.company` | required, default current company |
| `partner_id` | M2o `res.users` | "Responsible User" (the assignee) — emailed |
| `request_date` | Date | from the orientation `date` |
| `employee_id` | M2o `hr.employee` | the new hire |
| `request_expected_date` | Date | editable target date |
| `attachment_ids` | M2m `ir.attachment` (rel `orientation_rel_1`) | supporting documents |
| `note` | Text | notes |
| `user_id` | M2o `res.users` | default current user (used as mail `email_from`) |
| `company_id` | M2o `res.company` | required, default current company |
| `state` | Selection | `new → complete` (+ `cancel`); readonly, indexed, default `new` |

**Methods:**
- `action_confirm_send_mail()` — opens the standard `mail.compose.message` wizard
  pre-loaded with the orientation-request email template (see §6 Gotcha — template
  xmlid mismatch).
- `action_confirm_request()` — state → `complete`.
- `action_cancel_request()` — state → `cancel`.

### 3.3 `orientation.checklist` (`models/orientation_checklist.py`)
Reusable, department-scoped checklist template. `_inherit = 'mail.thread'`,
`_rec_name = 'checklist_name'`.

| Field | Type | Notes |
|---|---|---|
| `checklist_name` | Char | required |
| `checklist_department_id` | M2o `hr.department` | required — scopes which orientations may pick it |
| `active` | Boolean | default `True` (archivable) |
| `checklist_line_ids` | M2m `checklist.line` (rel `checklist_line_rel`) | the tasks in this checklist |

> Note: `checklist_line_ids` is a **Many2many**, so the same `checklist.line` can be
> shared across multiple checklists.

### 3.4 `checklist.line` (`models/checklist_line.py`)
A single reusable onboarding task. `_rec_name = 'line_name'`. **Not** a `mail.thread`.

| Field | Type | Notes |
|---|---|---|
| `line_name` | Char | required — the task title |
| `responsible_user_id` | M2o `res.users` | required — default assignee for generated requests |

### 3.5 `employee.training` (`models/employee_training.py`)
A department training program. `_inherit = 'mail.thread'`, `_rec_name = 'program_name'`.

| Field | Type | Notes |
|---|---|---|
| `program_name` | Char | required |
| `program_department_id` | M2o `hr.department` | required |
| `program_convener_id` | M2o `res.users` | required — "Responsible User", emailed |
| `training_ids` | O2m `hr.employee` | **computed, non-stored** (`_compute_employee_details`) — employees of the program's department |
| `note_id` | Text | description |
| `date_from`, `date_to` | Datetime | program window |
| `user_id` | M2o `res.users` | default current user |
| `company_id` | M2o `res.company` | required, default current company |
| `state` | Selection | `new → confirm → complete` (+ `cancel`, `print`); readonly, indexed, default `new` |

**Methods / workflow:**
- `_compute_employee_details()` (`@api.depends('program_department_id')`) — searches
  `hr.employee` by department and assigns the recordset to `training_ids`.
- `action_confirm_event()` → `confirm`; `action_complete_event()` → `complete`;
  `action_cancel_event()` → `cancel`.
- `print_event()` — computes a duration from `create_date`/`write_date`, builds a `data`
  dict, and calls `report_action` on the `print_pack_certificates` report (see §5).
- `action_confirm_send_mail()` — opens the mail composer with the training email template
  `employee_orientation.orientation_training_mailer`.

### 3.6 `orientation.force.complete` (wizard — `wizard/orientation_force_complete.py`)
`TransientModel`. Lets a manager close an orientation even when requests are still open.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | — |
| `orientation_id` | M2o `employee.orientation` | seeded via `default_orientation_id` |
| `orientation_lines` | O2m `orientation.request` | **computed** (`_compute_pending_lines`) — the still-`new` requests |

- `_compute_pending_lines()` (`@api.onchange('orientation_id')`) — collects child requests
  in state `new`.
- `force_complete()` — sets each non-cancelled pending line to `complete`, then sets the
  parent orientation to `complete`.

### 3.7 `hr.employee` (inherited — `models/hr_employee.py`)
Adds a single field:

| Field | Type | Notes |
|---|---|---|
| `certificates` | Boolean | default `True` — "Certificates": flag for whether the employee should receive a certificate. Shown on the employee form (after `parent_id`) and in the training Employee Details tab. |

> Note: `print_event` / the report do **not** currently filter on `certificates`; the
> field is exposed in the UI but not yet used to gate certificate generation (see Gotchas).

---

## 4. Workflows summary

**Orientation (onboarding):**
```
draft ──action_confirm_orientation──▶ confirm  (generates orientation.request per checklist line)
confirm ──action_complete_orientation──▶ complete   (or → force-complete wizard if any request still 'new')
draft/confirm ──action_cancel_orientation──▶ cancel  (cancels all child requests)

orientation.request:  new ──action_confirm_request──▶ complete
                      new ──action_cancel_request──▶ cancel
                      (action_confirm_send_mail emails the responsible user)
```

**Training:**
```
new ──action_confirm_event──▶ confirm ──action_complete_event──▶ complete
confirm ──action_cancel_event──▶ cancel
complete ──print_event──▶ Certificate of Participation PDF (one page per dept employee)
```

---

## 5. Reports
**One** QWeb-PDF report. (No badges, no letterhead variants — unlike `care_hr`.)

| | |
|---|---|
| `ir.actions.report` xmlid | `employee_orientation.print_pack_certificates` ("Certificates") |
| Bound model | `employee.training` |
| `report_name` / `report_file` | `employee_orientation.print_pack_template` |
| Report values model | `report.employee_orientation.print_pack_template` (AbstractModel, `models/employee_orientation_report.py`) |
| Templates | `report/print_pack_certificates_templates.xml` — `certificate_layout` + `print_pack_template` |

**How it renders:** `print_event()` passes a `data` dict (department id, program name,
convener, company, dates, duration/hours/minutes). `_get_report_values(docids, data)`
**ignores `docids`** and re-searches `hr.employee` by `data['dept_id']`, building one
certificate entry per employee in that department. The template loops `data` and emits a
**"Certificate of Participation"** page per employee, with a page break after each.

> Gotcha: certificate recipients are derived from the **department at print time**, not
> from a stored list, and not filtered by the `certificates` flag.

---

## 6. Data files, sequences & email templates

### 6.1 Sequence (`data/employee_orientation_data.xml`, `noupdate=1`)
`ir.sequence` code `employee.orientation`, prefix `OR`, padding 3 → `OR001`, `OR002`…
(company-independent: `company_id = False`). Consumed by `employee.orientation.create()`.

### 6.2 Email templates (`mail.template`, both `noupdate=1`, `auto_delete=True`)
| File | xmlid | Model | To |
|---|---|---|---|
| `data/orientation_request_data.xml` | **`orientation_request_view`** | `orientation.request` | `partner_id.work_email` |
| `data/employee_training_data.xml` | `orientation_training_mailer` | `employee.training` | `program_convener_id.login` |

> ⚠️ **Template xmlid mismatch (latent bug).** `orientation.request.action_confirm_send_mail`
> looks up `employee_orientation.orientation_request_mailer`, but the record in
> `orientation_request_data.xml` is declared as **`orientation_request_view`**. The lookup
> therefore fails its `_xmlid_lookup`, `template_id` falls back to `False`, and the composer
> opens **without** the pre-filled template (the user still gets a blank compose window).
> The training side is consistent (`orientation_training_mailer` matches). To restore the
> templated email, rename either the record id or the lookup string to match. There is also a
> leftover `print(template_id)` debug statement in that method.

---

## 7. Security (`security/ir.model.access.csv`)
No custom groups are defined; access is granted to standard HR groups.

| Model | `hr.group_hr_user` | `base.group_user` (all internal users) |
|---|---|---|
| `employee.orientation` | CRUD | — |
| `orientation.request` | CRUD | read/write only |
| `orientation.checklist` | CRUD (x2 lines in CSV) | — |
| `checklist.line` | CRUD | — |
| `employee.training` | CRUD | read/write only |
| `orientation.force.complete` | CRUD | — |

- **No record rules** are defined (no multi-company / ownership isolation in this module).
- **Menu visibility** is the practical gate: orientation/training menus are limited to
  `hr.group_hr_manager` / `hr.group_hr_user`; configuration menus (Orientation Program,
  Checklist Line) are `hr.group_hr_manager` only.

---

## 8. Views & menus

| View file | Models / contents |
|---|---|
| `views/employee_orientation_views.xml` | tree/form/search + action + menu. Form has header workflow buttons (Confirm / Mark Done / Cancel), statusbar, fields readonly once confirmed, an "Orientation Checklists Lines" tab (editable inline `orientation_request_ids`, visible only in confirm/complete), Notes, and chatter. |
| `views/orientation_request_views.xml` | tree/form/search + action + menu. Form (`create=0`) header: Send by Email / Complete / Cancel; Documents tab (`many2many_binary`), Notes, chatter. |
| `views/orientation_checklist_views.xml` | tree/form/search + action + menu (manager-only). Form has inline editable `checklist_line_ids`; action defaults `search_default_active`. |
| `views/checklist_line_views.xml` | tree/form/search + action. **Declares the two root menus**: `employee_orientation_menu_root` ("Orientations", under `hr.menu_hr_root`) and `orientation_checklist_menu_root` ("Orientation Program", under HR Configuration), plus the Checklist Line menu. |
| `views/employee_training_views.xml` | tree/form/search + action + "Training Program" menu. Form header: Send by Email / Confirm / Complete / Cancel / Print Certificates; Employee Details tab (`training_ids`), Notes, chatter. **Also inherits `hr.view_employee_form`** to add the `certificates` field after `parent_id`. |
| `wizard/orientation_force_complete_views.xml` | the Force Complete dialog (lists pending lines, Force Complete / Cancel buttons). |

**Menu tree:**
```
HR (hr.menu_hr_root)
├── Orientations (employee_orientation_menu_root, seq 90)
│     ├── Employee Orientation   → employee.orientation
│     └── Orientation Request     → orientation.request
└── Training Program (seq 91)     → employee.training
HR ▸ Configuration (hr.menu_human_resources_configuration)
└── Orientation Program (manager only)
      ├── Orientation Checklist        → orientation.checklist (seq 10)
      └── Orientation Checklist Line   → checklist.line (seq 20)
```

---

## 9. Crons / automation — **N/A**
No `ir.cron` records, no scheduled actions, no server actions. All transitions are
button-driven.

## 10. Settings / config_parameters — **N/A**
No `res.config.settings` inheritance and no `ir.config_parameter` usage. Behaviour is
not configurable through Settings; defaults come from field definitions and data files.

## 11. Assets / JS / OWL — **N/A**
No `static/src` JS, SCSS, or OWL components, and no `assets` key in the manifest. The
only `static/` content is the App Store description page (`static/description/`) and its
images — **not loaded by Odoo at runtime**.

---

## 12. Gotchas & notes (read before debugging)
- **Email template xmlid mismatch** on the orientation-request side — the "Send by Email"
  button opens a blank composer instead of the templated mail. See §6.2. (Training email
  is fine.)
- **`certificates` flag is decorative** — defined on `hr.employee` and shown in views, but
  the certificate report iterates **all** department employees regardless of the flag.
  If the client wants opt-out, filter on `certificates` in `_get_report_values` and/or
  `print_event`.
- **`training_ids` is computed & non-stored** and depends only on `program_department_id`;
  it cannot be edited per-program and won't persist. The training form's "Employee Details"
  tab is effectively a live department roster, not a curated attendee list. The tree-view
  `domain` on `program_convener_id` (`[('department_id.name','=','program_department.name')]`)
  is a **bug** — it compares against the literal string, not the selected department.
- **Legacy `create` signature** — `employee.orientation.create(self, vals)` uses the old
  single-dict, `@api.model` style. It still works in 17 but won't batch; if you ever import
  orientations in bulk, migrate to `@api.model_create_multi` with a list of vals.
- **Report ignores `docids`** — `_get_report_values` re-queries by department, so printing
  from any one training record yields the same department-wide certificate set.
- **Leftover debug `print()`** in `orientation.request.action_confirm_send_mail` — remove it.
- **Third-party Cybrosys module** — keep it loosely coupled to the `care_*` custom modules;
  it only depends on `base` + `hr`. Re-applying a fresh Cybrosys release will overwrite local
  fixes (the template-xmlid fix in particular). Track local edits.
- **`noupdate="1"`** on the sequence and both mail templates — a module `-u` will **not**
  overwrite them once installed; edit those records in the DB or bump/duplicate the xmlid
  if you need the data reloaded.
- **Odoo shell doesn't auto-commit** — call `env.cr.commit()` for data fixes run via
  `odoo-bin shell`, or use SQL; otherwise the change rolls back on exit.

---

## 13. File map
```
__manifest__.py                  depends base, hr · data manifest (no assets)
README.rst · doc/RELEASE_NOTES.md
models/
  employee_orientation.py        employee.orientation (onboarding + sequence + workflow)
  orientation_request.py         orientation.request (dispatched task + mail composer)
  orientation_checklist.py       orientation.checklist (department-scoped template)
  checklist_line.py              checklist.line (reusable task + responsible user)
  employee_training.py           employee.training (program + cert printing + mail)
  employee_orientation_report.py report.employee_orientation.print_pack_template (AbstractModel)
  hr_employee.py                 hr.employee inherit (+certificates Boolean)
wizard/
  orientation_force_complete.py  orientation.force.complete (TransientModel) + _views.xml
data/
  employee_orientation_data.xml  OR### ir.sequence (noupdate)
  orientation_request_data.xml   orientation_request_view mail.template (noupdate)
  employee_training_data.xml     orientation_training_mailer mail.template (noupdate)
report/
  print_pack_certificates_report.xml      ir.actions.report (Certificates)
  print_pack_certificates_templates.xml   certificate_layout + print_pack_template
security/
  ir.model.access.csv            HR-user / internal-user ACLs (no custom groups, no rules)
views/   employee_orientation · orientation_request · orientation_checklist ·
         checklist_line (declares root menus) · employee_training (+ hr.employee inherit)
static/description/              App Store page + images (NOT loaded by Odoo)
```
