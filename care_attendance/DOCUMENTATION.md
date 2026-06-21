# care_attendance — Developer Handover Documentation

> **Care Attendance** — a custom Odoo 17 add-on that bolts a **bulk
> attendance / absence workflow** onto standard `hr.attendance`. A department
> manager marks a whole department present (or absent) for a given day in one
> record; an approver signs off; the module then **auto-creates real
> `hr.attendance` check-in/check-out rows** for every affected employee, using
> their working-calendar hours. It also adds **multi-department ("Extra
> Departments")** support per employee, locks down employee create/delete behind
> custom groups, and ships a multi-sheet **XLSX attendance matrix** report
> (Management / Day-Shift Male / Day-Shift Female) plus a nightly auto check-out
> cron. UI labels are English. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `care_attendance` |
| Display name | `care_attendance` (manifest `name`) |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Depends | `base`, `hr`, `hr_attendance`, `report_xlsx` (OCA) |
| External Python libs | `pytz`, `python-dateutil` (`dateutil.relativedelta`); XLSX via `report_xlsx` (xlsxwriter) |
| New models | `bulk.attendance`, `hr.employee.extra.department` |
| Inherited models | `hr.attendance`, `hr.employee`, `res.config.settings` |
| Wizards (TransientModel) | `attendance.refuse.reason`, `hr.attendance.xlsx` |
| Reports | `report.care_attendance.care_attendance_xlsx_report` (3-sheet XLSX) |
| Crons | `Bulk Attendance: check out` (daily) |
| Mail templates | 3 (`send_to_approver`, `approved`, `refused`) |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u care_attendance --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
> ⚠️ **Hard dependency on OCA `report_xlsx`.** The XLSX report inherits
> `report.report_xlsx.abstract`; if `report_xlsx` is not installed/loaded, the
> module fails to load. Update load order: `report_xlsx` must be present first.
> The XLSX builder also requires `xlsxwriter` in the Odoo venv (pulled in by
> `report_xlsx`).

---

## 2. Architecture overview

```
bulk.attendance  (mail.thread, mail.activity.mixin — the workflow record)
│  draft → confirm(Submitted) → approved / refuse
│  type = attendance | absence
├── department_manager (res.users)   ── creator / submitter
├── approver           (res.users)   ── default from config_parameter
├── original_department_ids (m2m hr.department)  default = depts this user manages
├── department_ids          (m2m hr.department)  subset chosen on the record
├── employee_ids            (m2m hr.employee)    present employees (type=attendance)
├── absent_employee_ids     (m2m hr.employee)    absent employees (type=absence)
├── extra_department_ids    (m2m hr.employee.extra.department)
│
└── on Approve  ───────────────►  creates hr.attendance rows (check_in/out)
                                   tagged with bulk_id (+ extra_department_id)

hr.attendance (inherited)
├── bulk_id              → bulk.attendance        (origin of an auto-created row)
└── extra_department_id  → hr.employee.extra.department

hr.employee (inherited)
├── extra_department_ids → hr.employee.extra.department   (works in 2nd dept on a 2nd calendar)
├── create() gated by group_create_employee_user
└── unlink() gated by group_delete_employee_user

hr.employee.extra.department   (an employee's secondary department + calendar)
├── employee_id, employee_department_id (related), employee_calendar_id (related)
├── department_id  (≠ employee's own dept), calendar_id (resource.calendar)

Wizards:
  attendance.refuse.reason  → writes refuse + reason back to bulk.attendance
  hr.attendance.xlsx        → date range + departments → triggers XLSX report

Cron:  bulk.attendance.cron_bulk_check_out()  — fills missing check_out
```

**Core idea.** A `bulk.attendance` record is a request/approval wrapper. On
**approve**, the module reads each employee's `resource_calendar_id` (working
hours) for the bulk date's weekday, converts the calendar `hour_from`/`hour_to`
floats into timezone-correct UTC datetimes, and creates one `hr.attendance` row
per employee. "Extra department" employees get a second row computed from their
extra-department calendar. A daily cron later closes any row whose `check_out`
is still empty once that day's working hours have elapsed.

---

## 3. Data model

### 3.1 `bulk.attendance` (`models/bulk_attendance.py`)
`_inherit = ['mail.thread','mail.activity.mixin']` · `_order = 'id desc'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | sequence-generated (`bulk.attendance`), default `'New'`, readonly |
| `type` | Selection | `attendance` / `absence` (default `attendance`) — drives which employee list & which approve logic is used |
| `department_manager` | M2o `res.users` | default = current user; the submitter/owner |
| `approver` | M2o `res.users` | default `_default_approver` → reads config param `care_attendance.bulk_attendance_approval` |
| `original_department_ids` | M2m `hr.department` | default `get_original_department_ids` = departments whose `manager_id` is this user's employee; used only to constrain the `department_ids` domain |
| `department_ids` | M2m `hr.department` | default `get_department_ids` (same logic); `domain=[('id','in',original_department_ids)]` |
| `employee_ids` | M2m `hr.employee` | present list (type `attendance`); `domain=[('department_id','in',department_ids)]` |
| `absent_employee_ids` | M2m `hr.employee` | absent list (type `absence`); same domain |
| `bulk_date` | Date | default today; the attendance date |
| `state` | Selection | `draft` / `confirm` (Submitted) / `approved` / `refuse`; tracked |
| `company_id` | M2o `res.company` | readonly, default current company |
| `refuse_reason` | Char | set by the refuse wizard |
| `extra_department_ids` | M2m `hr.employee.extra.department` | `domain=[('department_id','in',department_ids)]` |
| `active` | Boolean | default True (archiving) |

**Default helpers**
- `get_original_department_ids()` / `get_department_ids()` — identical: find the
  `hr.employee` linked to `self.env.user`, then the `hr.department`s where that
  employee is `manager_id`. So a manager's record auto-scopes to their own
  departments. (Note: both default methods are non-decorated instance methods
  used as field defaults — Odoo calls them on an empty recordset.)
- `_default_approver()` — reads `ir.config_parameter` `care_attendance.bulk_attendance_approval`
  (set in Settings) and returns that user.

**Workflow methods**
- `button_confirm()` — sets `state='confirm'`, sends the
  `bulk_attendance_send_to_approver_template` mail to the approver, and schedules
  a `mail_act_bulk_attendance_create` activity ("Ask To Approve") on the approver.
  > Note: the old guard that required selecting employees is **commented out** —
  > an empty bulk can currently be submitted.
- `button_draft()` — back to `state='draft'`.
- `button_approve()` — **the core logic** (see §3.1.1).
- `button_refuse()` — opens the `attendance.refuse.reason` wizard (`target='new'`).
- `create()` override — assigns `name` from the `bulk.attendance` sequence when
  it is still `'New'`.

#### 3.1.1 `button_approve()` — how real attendance is generated
1. `t = datetime.combine(bulk_date, min.time())` (or today if no date).
2. Pick the employee set:
   - `type == 'absence'` → all employees in `department_ids` **minus**
     `absent_employee_ids` (i.e. everyone not marked absent is recorded present).
   - else (`attendance`) → exactly `employee_ids`.
3. For each employee:
   - Find that day's `resource_calendar_id.attendance_ids` lines where
     `int(dayofweek) == t.isoweekday() - 1` (Odoo dayofweek is `0`=Mon).
   - **If none → `ValidationError`** "working hours for {name} has no {Weekday} lines".
   - Compute the TZ offset from `pytz.timezone(emp.tz)` and build
     `check_in = datetime(y,m,d, int(hour_from)) - offset hours` (stored UTC).
   - `check_out` only set when **`bulk_date < today`** (past days are fully
     closed): from the single line's `hour_to`, or the 2nd line's `hour_to` when
     the calendar has split shifts (>1 line). For today/future, `check_out` is
     left empty and the cron closes it later.
   - Create `hr.attendance` with `employee_id`, `check_in`, `check_out`, `bulk_id`.
4. **Extra departments:** for each `extra_department_ids` line, repeat the same
   calendar math using `extra.calendar_id` (the extra-department working hours),
   and create a **second** `hr.attendance` row tagged with `extra_department_id`.
5. Send `bulk_attendance_approved_template` to `department_manager`, schedule an
   "Approved" activity, set `state='approved'`.

> **Gotchas in this method:**
> - `int(hour_from)` **truncates** the float calendar hour (e.g. 8.5 → 8). Half-hour
>   start/end times are lost. Known behaviour — change to a proper float→time
>   conversion if minutes matter.
> - The TZ offset uses `tz.utcoffset(t).seconds / 3600`; for negative UTC offsets
>   `.seconds` is not negative-safe. Fine for Kuwait (UTC+3), watch out elsewhere.
> - No dedup: re-approving (or re-creating) can create duplicate `hr.attendance`
>   rows for the same day.

### 3.2 `hr.employee.extra.department` (`models/hr_employee.py`)
A secondary department + working calendar for an employee (e.g. someone who also
covers another department on a different shift).

| Field | Type | Notes |
|---|---|---|
| `employee_id` | M2o `hr.employee` | owner |
| `employee_department_id` | M2o `hr.department` | related (stored) to `employee_id.department_id` |
| `employee_calendar_id` | M2o `resource.calendar` | related (stored) to `employee_id.resource_calendar_id` |
| `department_id` | M2o `hr.department` | required; `domain=[('id','!=',employee_department_id)]` — must differ from the employee's own department |
| `calendar_id` | M2o `resource.calendar` | required; the working hours used for this extra department's attendance |

### 3.3 `hr.employee` (inherited — `models/hr_employee.py`)
- Adds `extra_department_ids` (O2m `hr.employee.extra.department`).
- `create(vals)` override — raises `UserError("You are not allowed to create an
  employee!")` unless the user is in `care_attendance.group_create_employee_user`.
- `unlink()` override — raises `UserError("You are not allowed to delete an
  employee!")` unless the user is in `care_attendance.group_delete_employee_user`.

> **Gotcha:** `create` is the legacy single-dict signature (`def create(self, vals)`),
> not `@api.model_create_multi`. It works under Odoo 17's compatibility shim but
> blocks batched creates from getting a list. Keep in mind if you refactor.

### 3.4 `hr.attendance` (inherited — `models/hr_attendance.py`)
Adds two link fields so an auto-generated row knows where it came from:
- `bulk_id` → `bulk.attendance` (the approval that produced this row).
- `extra_department_id` → `hr.employee.extra.department` (set only for
  extra-department rows). The cron uses this to pick the right calendar.

### 3.5 `res.config.settings` (inherited — `models/res_config_settings.py`)
- `bulk_attendance_approval` (M2o `res.users`, `config_parameter`
  `care_attendance.bulk_attendance_approval`) — the default approver.
- `set_values()` override — after saving, ensures the chosen user is a member of
  the **`Bulk Attendance / Approver`** group (looked up by `full_name`), replacing
  the group's user list with `[(6,0,[user])]`.
  > **Gotcha:** this **resets** the Approver group to exactly that one user every
  > time settings are saved — any other manually-added approvers get removed.
  > Also `full_name` lookup is locale/label-sensitive; renaming the group breaks it.

---

## 4. Wizards (TransientModel)

### 4.1 `attendance.refuse.reason` (`wizards/attendance_refuse.py` / `.xml`)
- Field: `reason` (Char, required).
- `action_refuse()` — browses the active `bulk.attendance` (`active_id`), writes
  `state='refuse'` + `refuse_reason`, sends `bulk_attendance_refused_template`,
  and schedules a "Refused" activity on the `department_manager`.
- Form: single reason input + **Refuse** (danger) / **Cancel** buttons. Opened by
  `bulk.attendance.button_refuse()`.

### 4.2 `hr.attendance.xlsx` (`wizards/attendance_xlsx.py` / `.xml`)
- Fields: `date_from`, `date_to` (Dates, required in the form),
  `department_ids` (M2m `hr.department`, optional filter).
- `print_report()` — returns `report_action(self)` for
  `action_approval_print_xlsx_report`.
- Menu: **HR Attendance → Export Attendance** (`care_attendance_xlsx_menu`,
  parent `hr_attendance.menu_hr_attendance_root`). The wizard form is the
  `care_attendance_xlsx_action` dialog (`target='new'`).

---

## 5. Reports

### `report.care_attendance.care_attendance_xlsx_report` (`reports/care_attendance_xlsx.py`)
`AbstractModel`, `_inherit = report.report_xlsx.abstract`. Bound by
`action_approval_print_xlsx_report` (`report_type=xlsx`,
`report_name=care_attendance.care_attendance_xlsx_report`) and triggered from the
`hr.attendance.xlsx` wizard.

`generate_xlsx_report(workbook, data, objs)` builds an **attendance matrix** —
employees as rows, each day in `[date_from, date_to]` as a column — across **three
worksheets**:
1. **Management** — one row per `hr.department.manager_id`.
2. **Day-Shift Male** — `hr.employee` with `gender='male'`, minus managers.
3. **Day-Shift Female** — `hr.employee` with `gender='female'`, minus managers.

Per employee/day cell:
- `P` (present) if the employee has an `hr.attendance.check_in` on that date
  (optionally filtered by `objs.department_ids`).
- `OFF` (yellow) if that weekday is **not** in the employee's
  `resource_calendar_id` working days.
- `A` (purple "absent" style) otherwise; the daily/weekly absent counters and a
  per-row `ABSENTS` total accumulate. Footer rows give per-day present/absent
  totals (yellow) and, on the female sheet, "Total Present/Absent Staff".

Columns: `S.No.`, `EID` (employee `barcode`), `Name`, then one per day (day
number + weekday abbr in the 2-row header), then `ABSENTS`.

> **Hard requirement:** an `hr.leave.type` named **exactly `'Sick Time Off'`** must
> exist, else every sheet raises `UserError("please set sick time off type!")`.
> (The sick-leave handling beyond that lookup is currently commented out, so the
> type is required but its leaves don't yet affect the matrix.)
>
> **Note:** the three sheets are near-identical copy-paste blocks. Edit all three
> when changing cell logic, or they diverge.

---

## 6. Automation (cron)

### `Bulk Attendance: check out` (`data/cron.xml` → `bulk_check_out_cron`)
- Runs `model.cron_bulk_check_out()` on `bulk.attendance`, **every 1 day**,
  `numbercall=-1`, first run ~5 min after install.
- `cron_bulk_check_out()` finds all `hr.attendance` with `bulk_id` set and
  `check_out = False`, and for each computes the expected `check_out` from the
  relevant calendar (the **extra-department** calendar if `extra_department_id`
  is set, otherwise the employee's `resource_calendar_id`) for the bulk date's
  weekday. If `datetime.now() >= computed check_out`, it fills `check_out`.
  Split-shift calendars (>1 line) use the second line's `hour_to`.

This closes the rows that `button_approve` left open (today/future bulks) once
the working day has actually ended.

---

## 7. Settings / config parameters

| Config parameter | Set via | Used by |
|---|---|---|
| `care_attendance.bulk_attendance_approval` | Settings → HR Attendance → **Bulk Attendance → Bulk Attendance Approver** (`views/res_config_settings.xml`, injected into the `hr_attendance` settings app) | `bulk.attendance._default_approver` (default approver) and `res_config_settings.set_values` (syncs the Approver group) |

---

## 8. Security (`security/`)

### Groups (`security.xml`)
| Group (xml id) | Category | Notes |
|---|---|---|
| `group_bulk_attendance_user` (User) | Bulk Attendance | implies `hr_attendance.group_hr_attendance_own_reader`; submitters |
| `group_bulk_attendance_approver` (Approver) | Bulk Attendance | approvers; the group `res_config_settings` syncs |
| `group_create_employee_user` (User) | Create Employee | required to create `hr.employee` |
| `group_delete_employee_user` (User) | Delete Employee | required to delete `hr.employee` |

### Record rules (`security.xml`)
- `bulk_attendance_rule_user_own` — `group_bulk_attendance_user` sees only records
  where `create_uid = user.id`.
- `bulk_attendance_rule_manager` — `group_bulk_attendance_approver` sees all
  (`[(1,'=',1)]`).

### Access (`ir.model.access.csv`)
All four custom/transient models get full CRUD with **no group** set (so any
internal user satisfies model-level ACL; visibility is then narrowed by the
record rules above):
`bulk.attendance`, `hr.employee.extra.department`, `attendance.refuse.reason`,
`hr.attendance.xlsx`.

> **Gotcha:** because the ACL rows have an empty `group_id`, model-level access is
> effectively open to all internal users; the **record rules** (and the view-level
> `groups=`/`invisible=` button guards) are what actually scope the workflow.
> The Submit/Approve/Refuse buttons in the form are gated by `department_manager
> != uid` / `approver != uid` and group membership.

---

## 9. Views (`views/*.xml`)

### `bulk.attendance` (`views/bulk_attendance.xml`)
- **Kanban** (`hr_kanban_view_bulk_attendance`) — name, type, departments tags,
  state badge.
- **Tree** `bulk_attendance_view_tree` (priority 1) — name, departments, date,
  state badge (success=approved, info=draft/confirm, danger=refuse).
- **Tree** `absence_view_tree` (priority 2) — same plus `absent_employee_ids`.
- **Form** `bulk_attendance_view_form` — header Submit/Approve/Refuse/Reset
  buttons (visibility by user role + state), statusbar, fields, and a notebook
  with **Attendance** (present employees, shown when `type=attendance`),
  **Absence** (absent employees, when `type=absence`) and **Extra Departments**
  pages; chatter.
- **Actions/menus:** `Bulk Attendance` (tree/kanban/form), `Bulk Attendance
  Waiting Approval` (domain `approver=uid, state=confirm`, approver-only),
  `Absence` (domain `type=absence`). Root menu `Bulk Attendance` visible to both
  user & approver groups.

> **Note:** the form header has a stray malformed line (a duplicated
> `invisible="..."` fragment after `button_draft`) — harmless leftover; tidy if
> editing the header.

### `hr.employee` (`views/hr_employee.xml`)
Adds an **Extra Departments** page (editable tree of `extra_department_ids`) to
the standard employee form (`hr.view_employee_form`), plus standalone form/tree
views for `hr.employee.extra.department`.

### `hr.attendance` (`views/hr_attendance.xml`)
Inherits `hr_attendance.view_attendance_tree` to add a `department_id` column.

### `res.config.settings` (`views/res_config_settings.xml`)
Injects the **Bulk Attendance Approver** setting into the HR Attendance settings
app.

---

## 10. Assets / JS
None. No `static/src` JS/SCSS; only `static/description/icon.png` (module icon).

---

## 11. Gotchas & notes (read before debugging)

- **`report_xlsx` (OCA) is a hard dependency** and so is `xlsxwriter` in the venv.
  Missing either breaks module load / report generation.
- **`'Sick Time Off'` leave type must exist** or the XLSX report raises for every
  sheet. Its leaves are not yet wired into the matrix (commented-out branch).
- **`set_values()` resets the Approver group** to exactly the one configured user
  on every settings save — don't rely on manually-added approvers persisting.
- **Calendar-hour truncation:** `int(hour_from/hour_to)` drops minutes in both
  `button_approve` and `cron_bulk_check_out`. Half-hour shifts are not honoured.
- **No duplicate guard** when generating `hr.attendance` rows — re-approving or
  overlapping bulks can double-book a day.
- **`button_confirm` no longer validates** that employees are selected (guard
  commented out) — empty submissions are possible.
- **TZ offset math** assumes a positive UTC offset (`utcoffset().seconds`). Correct
  for Kuwait (UTC+3); revisit for negative-offset deployments.
- **Default-method scoping:** `get_original_department_ids` / `get_department_ids`
  resolve departments from the *current user's* employee → managed departments; a
  user with no linked employee or no managed department gets an empty default.
- **`hr.employee.create` legacy signature** (`def create(self, vals)`), not
  `model_create_multi` — fine today, mind it on refactor.
- The manifest `name`/`summary`/`author` are still the scaffold placeholders
  ("My Company", template summary) — cosmetic, but worth fixing for the apps list.

---

## 12. File map
```
__manifest__.py                       depends: base, hr, hr_attendance, report_xlsx
models/
  bulk_attendance.py                  bulk.attendance (workflow, approve→hr.attendance, cron)
  hr_employee.py                      hr.employee (create/unlink guards) + hr.employee.extra.department
  hr_attendance.py                    hr.attendance (bulk_id, extra_department_id)
  res_config_settings.py              bulk_attendance_approval config + group sync
wizards/
  attendance_refuse.py / .xml         attendance.refuse.reason (refuse + reason)
  attendance_xlsx.py / .xml           hr.attendance.xlsx (date range → XLSX) + menu
reports/
  care_attendance_xlsx.py             3-sheet attendance matrix (Management/Male/Female)
  care_attendance_xlsx.xml            ir.actions.report (xlsx)
data/
  sequence.xml                        bulk.attendance sequence
  cron.xml                            daily auto check-out cron
  activity_type.xml                   "Bulk Attendance" activity type
  mail_templates.xml                  approver-request / approved / refused emails
security/
  security.xml                        4 groups + 2 record rules + module categories
  ir.model.access.csv                 CRUD ACLs (no group_id — scoped by rules)
views/
  bulk_attendance.xml                 kanban/tree/absence-tree/form + actions/menus
  hr_employee.xml                     extra-departments page + standalone views
  hr_attendance.xml                   adds department_id to attendance tree
  res_config_settings.xml            approver setting in HR Attendance settings
static/description/icon.png           module icon (no JS/SCSS)
```
