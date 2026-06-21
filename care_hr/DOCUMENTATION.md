# care_hr — Developer Handover Documentation

> **Care HR** — the client's custom HR module for Odoo 17, tailored to **Kuwait
> government-style HR paperwork**. It extends the standard `hr.employee` / `hr.leave`
> and adds four official "HR Action" documents (Joining, Clearance, Absence, Leave
> Return), each with a barcode + QR code, a draft→submit→approve workflow, and
> printable Arabic/Kuwait-letterhead PDF reports. UI mixes English labels with
> Arabic/official content. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `care_hr` |
| Display name | Care HR |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Depends | `base`, `hr`, `hr_holidays`, `hr_skills`, `care`, `purchase_report` |
| External Python lib | **`qrcode`** (QR generation) + `base64`, `io` |
| Core inherited models | `hr.employee`, `hr.leave`, `hr.department`, `hr.skill`, `hr.skill.level` |
| New models | `hr.action.joining`, `hr.action.clearance` (+ line), `hr.action.absence`, `hr.action.leave.return`, `hr.employee.suspend` (wizard) |
| Reports | 5 document reports (each with plain + letterhead variant) + employee badge |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u care_hr --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
> ⚠️ Requires the `qrcode` Python package in the Odoo venv. If `import qrcode`
> fails, QR computes raise — install it in `/home/odoo/.pyenv/versions/odoo-17-env`.

---

## 2. Architecture overview

```
hr.employee (inherited)
├── category_ids, joining_ids → hr.action.joining
├── suspend workflow (suspend_date/reason/by) via hr.employee.suspend wizard
└── can_print_reports / can_edit (permission helper flags)

Official HR documents — all mail.thread, all carry barcode + QR, all draft→submit→approve:
├── hr.action.joining        (التحاق / joining order; assign department; delay, salary date)
├── hr.action.clearance      (إخلاء طرف / exit clearance)  +  hr.action.clearance.line
├── hr.action.absence        (غياب / absence report; last work date)
└── hr.action.leave.return   (عودة من إجازة / leave-return; late days/fees; links hr.leave)

hr.leave (inherited)     barcode/QR, department+employee domains, leave-return link, returned flag, self_time_off
hr.department (inherited) allowed_user_ids
hr.skill / hr.skill.level (inherited) employee_ids/_count + "view employees" action

Helpers:  qr_generator.generateQrCode  ·  reports/hr_reports.py (badge AbstractModel)
```

**Recurring design patterns** (every `hr.action.*` model follows the same shape):
- `_inherit = ['mail.thread','mail.activity.mixin']`, `_rec_name = 'employee_id'`.
- `employee_id` (required) + related-stored mirror fields (`image_1920`, `job_title`,
  `employee_barcode`, `department_id`, `civil_code`) so reports/print read one record.
- `barcode` (Char, default from `generate_barcode`) + `qr_image`/`qr_url`
  (computed via `_generate_qr_code`).
- `state` Selection state machine: `draft → submitted → approved` driven by
  `button_submit()` / `button_approve()`.
- `button_print_report()` / `button_print_report_header()` → plain vs. letterhead PDF.
- `active` (Boolean) for archiving.

---

## 3. Data model

### 3.1 `hr.employee` (inherited — `models/hr_employee.py`)
| Field | Type | Notes |
|---|---|---|
| `category_ids` | M2m `hr.employee.category` | tracked tags |
| `joining_ids` | O2m `hr.action.joining` | joining orders for this employee |
| `joining_date` | Date (computed `compute_joining_date`, stored) | earliest/approved joining |
| `suspend_date`, `suspend_reason`, `suspend_by` | Date/Text/M2o users | suspension state (tracked) |
| `can_print_reports`, `can_edit` | Boolean | permission helper flags used to gate buttons in views |

Methods: `write()` override (tracking/permission logic), `button_suspend()` /
`button_unsuspend()` (open/apply the suspend wizard), `compute_joining_date()`,
`_mail_track()` override (custom chatter tracking).

### 3.2 `hr.action.joining` (`models/hr_action_joining.py`)
Official **joining order**. Key fields: `employee_id`, `join_date` (required), `delay`
(Integer), `salary_date`, `department_id`, related `job_title`/`employee_barcode`/`image_1920`,
`barcode`+`qr_image`/`qr_url`, `state` (draft/submitted/approved), `active`.
Methods: `button_submit`, `button_approve`, `button_print_report(_header)`,
`action_assign_department()` (sets the employee's department from the order),
`_generate_qr_code`.

### 3.3 `hr.action.clearance` + `hr.action.clearance.line` (`models/hr_action_clearance.py`)
Exit-clearance document. Header carries `employee_id`, related `department_id`/`image_1920`/
`employee_barcode`, barcode+QR, `state`, `active`, and `line_ids` →
`hr.action.clearance.line` (`name`, `remarks`, `sequence`). `get_default_lines()` seeds the
standard clearance checklist rows on create. Same submit/approve/print methods.

### 3.4 `hr.action.absence` (`models/hr_action_absence.py`)
Absence report. `employee_id` + related `job_title`/`civil_code`/`employee_barcode`/
`department_id`, `last_work_date` (computed `compute_last_work_date`, stored),
`absence_reason` (Text, required), `work_location`, barcode+QR, `state`, `active`.
Submit/approve/print as above.

### 3.5 `hr.action.leave.return` (`models/hr_action_leave_return.py`)
Tracks an employee's **return from leave** and any lateness. Links the employee's last
leave via `last_leave_id` (computed) and derives `last_leave_from/to`, `leave_return_date`,
`leave_request_days` (`compute_last_leave_dates`). `start_work_date` (actual return) feeds
`actual_leave_days` (`compute_actual_leave_days`) and `late_days` (`compute_late_days`);
`late_fees` (Float, manual), `notes`. barcode+QR, `state`, `active`. Created from / linked
back to `hr.leave` (see 3.7).

### 3.6 `hr.employee.suspend` (wizard — `wizards/hr_employee_suspend.py`)
TransientModel: `employee_id`, `reason` (Text), `date`, `unsuspend` (Boolean),
`can_print_reports`, `can_edit`. `button_suspend()` writes the suspend/unsuspend state back
to the employee. Launched from the employee form buttons.

### 3.7 `hr.leave` (inherited — `models/hr_leave.py`)
Adds: `barcode` (+ `generate_barcode` default), `qr_image`/`qr_url` (`_generate_qr_code`),
`original_return_date`, `available_department_ids` (default from
`_default_available_department_ids`), `hr_department_id` + `hr_employee_id` (domain-filtered
pickers), `leave_return_ids` → `hr.action.leave.return`, `leave_return_count` (computed),
`returned` Selection (computed `has_returned`), `self_time_off` (Boolean).
Methods: `onchange_self_time_off`, `onchange_hr_employee_id`, `_check_date_state`
(constraint), `action_view_leave_return()`.
Also inherits **`hr.department`** here to add `allowed_user_ids` (M2m users) used by the
leave department domain.

### 3.8 `hr.skill` / `hr.skill.level` (inherited — `models/hr_skills.py`)
Both add `employee_ids` (M2m, computed `compute_employee_ids`) + `employee_count`, and an
`action_view_employees()` to drill from a skill/level to the employees who have it.

### 3.9 `qr_generator.py`
Module-level helper `generateQrCode.generate_qr_code(url)` — builds a QR PNG with the
`qrcode` lib (version 4, ERROR_CORRECT_L, box 20, border 4) and returns base64. Used by all
`_generate_qr_code` computes across the models above.

---

## 4. Reports (`reports/*.xml` + `reports/hr_reports.py`)
Each official document has **two** QWeb-PDF variants — plain (printed on pre-printed
letterhead) and **"with Header"** (renders the Kuwait emblem/police letterhead itself).
Images live in `static/src/img/` (`Emblem_of_Kuwait.svg.png`, `kuwait_police.png`,
`header.png`, `footer.png`, `stamp.png`, `logo.jpeg`).

| Report record (name) | Document |
|---|---|
| Joining Report / Joining with Header | `hr.action.joining` |
| Clearance Report / Clearance with Header | `hr.action.clearance` (landscape paperformat `paperformat_clearance_landscape`) |
| Absence Report / Absence with Header | `hr.action.absence` |
| Leave Return / Leave Return with Header | `hr.action.leave.return` |
| Leave Request Report / …Header | `hr.leave` |
| `report.hr.print_employee_badge` (AbstractModel, `reports/hr_reports.py`) | employee badge — custom `_get_report_values` |

The `button_print_report` vs `button_print_report_header` methods on each model choose the
plain vs letterhead variant.

---

## 5. Security (`security/`)
- `groups.xml` declares a **User / Approver** pair per workflow (Joining, Absence, Leave
  Return — module category "HR Joining") plus a suspend-user group, and record rules
  (`hr_joining_rule_user_own` = users see their own, `hr_joining_rule_manager` = approvers
  see all).
- `ir.model.access.csv`:
  - `hr.action.joining` / `…absence` / `…leave.return` → CRUD for their `*_user` and
    `*_approver` groups.
  - `hr.action.clearance` + `…line` → CRUD for `base.group_user`.
  - `hr.employee.suspend` → CRUD for `group_hr_suspend_user`.

The **approval gate** is enforced by the group on `button_approve` + the record rules, not
by field-level locks — keep that in mind when changing the workflow.

---

## 6. Views (`views/*.xml`)
One view file per model: `hr_employee.xml` (adds suspend buttons, joining tab, permission
flags), `hr_leave.xml` (QR, return link, self-time-off, department/employee domains),
`hr_skills.xml` (employee count + drill-down), and one each for the four `hr.action.*`
documents (form with state header buttons, barcode/QR, print buttons; list/search).
`wizards/hr_employee_suspend.xml` is the suspend wizard dialog.

---

## 6b. HR 360 Dashboard (OWL client action)

A powerful HR home dashboard, **gated to a group** and used as the **landing screen**
for its members.

**Backend** — `hr.employee.get_hr_dashboard_data()` (`@api.model`, in `models/hr_employee.py`)
returns one plain dict: KPIs (total employees, joiners this year, on-leave today,
present today, pending approvals, suspended, departments, active loans), aggregates
(`by_department`, `by_job`, `by_gender`, `by_category`, `joiners_trend` = 12-month line,
`by_leave_type`), and lists (`upcoming_leaves` next 7 days, `new_joiners`, `pending_docs`).
Optional models are read through `self.env.get(...)` so it works whether or not
`hr.attendance` / `hr.loan` are installed (present-today and loans degrade to 0).
`read_group` counts use a `__count` → `<field>_count` fallback (this build exposes the
latter).

**Frontend** — OWL component `care_hr.HrDashboard` in
`static/src/hr_dashboard/hr_dashboard.{js,xml,scss}`, registered as client action
**`care_hr_dashboard`**. Lazy-loads Chart.js via `loadBundle("web.chartjs_lib")`,
animations off, charts rendered from a plain-data copy (decoupled from the OWL proxy).
KPI/cards link into the employees list. Declared in `__manifest__.py` →
`assets/web.assets_backend`.

**Landing + permissions**
- Group `care_hr.group_hr_dashboard` (security/groups.xml) — implies `hr.group_hr_user`
  so members can read HR data. Assign users to it later (the "specific users").
- Client action `care_hr.action_hr_dashboard` + a top-level app menu
  (`menu_hr_dashboard_root` → `menu_hr_dashboard`), both restricted to the group.
- `res.users` override (`models/res_users.py`): `_sync_dashboard_home_action()` sets each
  group member's **Home Action** (`action_id`) to the dashboard, so they land on it at
  login; removing a user from the group clears it (only if it still points at our
  dashboard), so they fall back to the normal app menu. Runs from `create()` and from
  `write()` when group keys change (`groups_id` / `in_group_*` / `sel_groups_*`), guarded
  against recursion via the `care_hr_sync` context flag.

> To make the dashboard someone's home: tick them into **Dashboard User**
> (category "HR Dashboard"). To revert: untick — their home returns to the normal menu.

## 7. Gotchas & notes
- **`qrcode` dependency** is hard — every document's `_generate_qr_code` calls
  `qr_generator`. A missing lib breaks form rendering of any action document.
- **Two report variants per document** — when editing a report, update *both* the plain
  and the "with Header" template, or printouts diverge.
- **Related-stored mirror fields** (`job_title`, `civil_code`, `employee_barcode`,
  `image_1920`, `department_id`) are denormalised onto each action document so the PDF and
  approval record stay correct even if the employee later changes — don't replace them with
  live `related` (non-stored) without checking the reports.
- **Barcodes** are auto-generated on create (`generate_barcode` default); don't assume
  uniqueness constraints beyond what's defined.
- Depends on the client's base **`care`** module and **`purchase_report`** — load order
  matters; update `care` first if both changed.
- `_mail_track` on `hr.employee` is overridden — custom chatter behaviour; test tracking
  after any change there.

---

## 8. File map
```
__manifest__.py
models/   hr_employee.py · hr_leave.py · hr_skills.py · qr_generator.py
          hr_action_joining.py · hr_action_clearance.py
          hr_action_absence.py · hr_action_leave_return.py
wizards/  hr_employee_suspend.py (+ .xml)
reports/  hr_reports.py (badge AbstractModel)
          joining_/clearance_/absence_/leave_return_/leave_request_report.xml
security/ groups.xml · ir.model.access.csv
views/    hr_employee · hr_leave · hr_skills · hr_action_{joining,clearance,absence,leave_return}.xml
static/src/img/  Kuwait emblem / police / header / footer / stamp / logo
```
